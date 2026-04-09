"""Infra module: asset related partner service tests."""
from __future__ import annotations

from datetime import date

import pytest

from app.core.exceptions import DuplicateError, NotFoundError
from app.modules.common.models.asset_type_code import AssetTypeCode
from app.modules.common.models.partner import Partner
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.schemas.asset import AssetCreate
from app.modules.infra.schemas.asset_related_partner import (
    AssetRelatedPartnerCreate,
    AssetRelatedPartnerUpdate,
)
from app.modules.infra.services.asset_related_partner_service import (
    create_asset_related_partner,
    delete_asset_related_partner,
    get_asset_related_partner,
    list_asset_related_partners,
    update_asset_related_partner,
)
from app.modules.infra.services.asset_event_service import list_asset_events
from app.modules.infra.services.asset_service import create_asset


def _make_admin_user(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="admin", name="Admin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _setup(db, admin):
    partner = Partner(partner_code="P001", name="ABC Corp")
    maintainer = Partner(partner_code="M001", name="유지보수사", partner_type="유지보수사")
    supplier = Partner(partner_code="S001", name="공급사", partner_type="공급사")
    db.add_all([partner, maintainer, supplier])
    db.flush()

    db.add(
        AssetTypeCode(
            type_key="server",
            code="SVR",
            label="서버",
            kind="hardware",
            sort_order=1,
            is_active=True,
        )
    )
    catalog = ProductCatalog(
        vendor="Dell",
        name="PowerEdge R760",
        product_type="hardware",
        category="서버",
        asset_type_key="server",
    )
    db.add(catalog)
    db.flush()

    asset = create_asset(
        db,
        AssetCreate(
            partner_id=partner.id,
            model_id=catalog.id,
            asset_name="SRV-01",
        ),
        admin,
    )
    return asset, maintainer, supplier


def test_create_and_list_related_partners(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    asset, maintainer, _ = _setup(db_session, admin)

    create_asset_related_partner(
        db_session,
        AssetRelatedPartnerCreate(
            asset_id=asset.id,
            partner_id=maintainer.id,
            relation_type="maintainer",
            is_primary=True,
            valid_from=date(2026, 1, 1),
        ),
        admin,
    )

    rows = list_asset_related_partners(db_session, asset.id)
    assert len(rows) == 1
    assert rows[0]["partner_name"] == "유지보수사"
    assert rows[0]["relation_type"] == "maintainer"
    assert rows[0]["is_primary"] is True
    events = list_asset_events(db_session, asset.id)
    assert events[0].event_type == "maintenance_change"
    assert "유지보수사 연결" in events[0].summary


def test_duplicate_open_ended_relation_rejected(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    asset, maintainer, _ = _setup(db_session, admin)

    create_asset_related_partner(
        db_session,
        AssetRelatedPartnerCreate(
            asset_id=asset.id,
            partner_id=maintainer.id,
            relation_type="maintainer",
        ),
        admin,
    )

    with pytest.raises(DuplicateError):
        create_asset_related_partner(
            db_session,
            AssetRelatedPartnerCreate(
                asset_id=asset.id,
                partner_id=maintainer.id,
                relation_type="maintainer",
            ),
            admin,
        )


def test_primary_relation_switches_same_type(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    asset, maintainer, supplier = _setup(db_session, admin)

    first = create_asset_related_partner(
        db_session,
        AssetRelatedPartnerCreate(
            asset_id=asset.id,
            partner_id=maintainer.id,
            relation_type="supplier",
            is_primary=True,
        ),
        admin,
    )
    second = create_asset_related_partner(
        db_session,
        AssetRelatedPartnerCreate(
            asset_id=asset.id,
            partner_id=supplier.id,
            relation_type="supplier",
            is_primary=True,
            valid_to=date(2026, 12, 31),
        ),
        admin,
    )

    rows = list_asset_related_partners(db_session, asset.id)
    by_id = {row["id"]: row for row in rows}
    assert by_id[first.id]["is_primary"] is False
    assert by_id[second.id]["is_primary"] is True


def test_update_related_partner(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    asset, maintainer, _ = _setup(db_session, admin)

    rel = create_asset_related_partner(
        db_session,
        AssetRelatedPartnerCreate(
            asset_id=asset.id,
            partner_id=maintainer.id,
            relation_type="maintainer",
            note="기본 계약",
        ),
        admin,
    )

    updated = update_asset_related_partner(
        db_session,
        rel.id,
        AssetRelatedPartnerUpdate(
            note="24x7 유지보수",
            valid_to=date(2026, 12, 31),
        ),
        admin,
    )

    assert updated.note == "24x7 유지보수"
    assert updated.valid_to == date(2026, 12, 31)


def test_delete_related_partner(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    asset, maintainer, _ = _setup(db_session, admin)

    rel = create_asset_related_partner(
        db_session,
        AssetRelatedPartnerCreate(
            asset_id=asset.id,
            partner_id=maintainer.id,
            relation_type="maintainer",
        ),
        admin,
    )

    delete_asset_related_partner(db_session, rel.id, admin)

    with pytest.raises(NotFoundError):
        get_asset_related_partner(db_session, rel.id)
    events = list_asset_events(db_session, asset.id)
    assert events[0].event_type == "maintenance_change"
    assert "해제" in events[0].summary


def test_update_related_partner_logs_event(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    asset, maintainer, _ = _setup(db_session, admin)

    rel = create_asset_related_partner(
        db_session,
        AssetRelatedPartnerCreate(
            asset_id=asset.id,
            partner_id=maintainer.id,
            relation_type="maintainer",
        ),
        admin,
    )

    update_asset_related_partner(
        db_session,
        rel.id,
        AssetRelatedPartnerUpdate(note="주간 점검 계약"),
        admin,
    )

    events = list_asset_events(db_session, asset.id)
    assert events[0].event_type == "maintenance_change"
    assert "변경" in events[0].summary
