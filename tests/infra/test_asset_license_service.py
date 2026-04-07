"""Infra module: asset license service tests."""
from __future__ import annotations

from datetime import date

import pytest

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.modules.common.models.partner import Partner
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.schemas.asset_license import AssetLicenseCreate, AssetLicenseUpdate
from app.modules.infra.services.asset_license_service import (
    create_asset_license,
    delete_asset_license,
    get_asset_license,
    list_asset_licenses,
    update_asset_license,
)


def _make_admin_user(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="admin_lic", name="Admin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_asset(db, partner_name: str = "Test Corp", asset_name: str = "SRV-01") -> Asset:
    """Create partner, catalog, and asset directly (bypassing create_asset service)."""
    partner = Partner(partner_code="P001", name=partner_name)
    db.add(partner)
    db.flush()

    catalog = ProductCatalog(vendor="Dell", name="PowerEdge R760", product_type="hardware")
    db.add(catalog)
    db.flush()

    asset = Asset(partner_id=partner.id, asset_name=asset_name, model_id=catalog.id)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def test_create_and_list_asset_licenses(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    asset = _make_asset(db_session)

    create_asset_license(
        db_session,
        AssetLicenseCreate(
            asset_id=asset.id,
            license_type="OEM",
            license_key="XXXX-YYYY-ZZZZ",
            licensed_to="ABC Corp",
            start_date=date(2025, 1, 1),
            end_date=date(2027, 12, 31),
        ),
        admin,
    )

    rows = list_asset_licenses(db_session, asset.id)
    assert len(rows) == 1
    assert rows[0].license_type == "OEM"
    assert rows[0].license_key == "XXXX-YYYY-ZZZZ"
    assert rows[0].licensed_to == "ABC Corp"
    assert rows[0].start_date == date(2025, 1, 1)
    assert rows[0].end_date == date(2027, 12, 31)


def test_list_asset_licenses_unknown_asset_raises(db_session, admin_role_id) -> None:
    _make_admin_user(db_session, admin_role_id)
    with pytest.raises(NotFoundError):
        list_asset_licenses(db_session, 99999)


def test_create_asset_license_minimal(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    asset = _make_asset(db_session)

    lic = create_asset_license(
        db_session,
        AssetLicenseCreate(asset_id=asset.id, license_type="subscription"),
        admin,
    )

    assert lic.id is not None
    assert lic.license_type == "subscription"
    assert lic.license_key is None
    assert lic.end_date is None


def test_update_asset_license(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    asset = _make_asset(db_session)

    lic = create_asset_license(
        db_session,
        AssetLicenseCreate(asset_id=asset.id, license_type="OEM"),
        admin,
    )

    updated = update_asset_license(
        db_session,
        lic.id,
        AssetLicenseUpdate(
            license_type="volume",
            license_key="NEW-KEY",
            end_date=date(2028, 6, 30),
        ),
        admin,
    )

    assert updated.license_type == "volume"
    assert updated.license_key == "NEW-KEY"
    assert updated.end_date == date(2028, 6, 30)


def test_update_asset_license_not_found(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    with pytest.raises(NotFoundError):
        update_asset_license(
            db_session,
            99999,
            AssetLicenseUpdate(license_type="OEM"),
            admin,
        )


def test_delete_asset_license(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    asset = _make_asset(db_session)

    lic = create_asset_license(
        db_session,
        AssetLicenseCreate(asset_id=asset.id, license_type="OEM"),
        admin,
    )

    delete_asset_license(db_session, lic.id, admin)

    with pytest.raises(NotFoundError):
        get_asset_license(db_session, lic.id)


def test_delete_asset_license_not_found(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    with pytest.raises(NotFoundError):
        delete_asset_license(db_session, 99999, admin)


def _make_readonly_user(db_session, readonly_role_id: int):
    """Create a user with no infra edit permission (영업담당자 role)."""
    from app.modules.common.models.user import User

    user = User(login_id="readonly_lic", name="ReadOnly", role_id=readonly_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_permission_denied_for_non_admin(db_session, admin_role_id, user_role_id) -> None:
    """A user without inventory edit permission cannot create, update, or delete licenses."""
    admin = _make_admin_user(db_session, admin_role_id)
    readonly = _make_readonly_user(db_session, user_role_id)
    asset = _make_asset(db_session)

    # Create a license as admin first so update/delete tests have a target.
    lic = create_asset_license(
        db_session,
        AssetLicenseCreate(asset_id=asset.id, license_type="OEM"),
        admin,
    )

    # create — should be blocked
    with pytest.raises(PermissionDeniedError):
        create_asset_license(
            db_session,
            AssetLicenseCreate(asset_id=asset.id, license_type="volume"),
            readonly,
        )

    # update — should be blocked
    with pytest.raises(PermissionDeniedError):
        update_asset_license(
            db_session,
            lic.id,
            AssetLicenseUpdate(license_type="subscription"),
            readonly,
        )

    # delete — should be blocked
    with pytest.raises(PermissionDeniedError):
        delete_asset_license(db_session, lic.id, readonly)


def test_multiple_licenses_per_asset(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    asset = _make_asset(db_session)

    for ltype in ["OEM", "subscription", "volume"]:
        create_asset_license(
            db_session,
            AssetLicenseCreate(asset_id=asset.id, license_type=ltype),
            admin,
        )

    rows = list_asset_licenses(db_session, asset.id)
    assert len(rows) == 3
    types = [r.license_type for r in rows]
    assert "OEM" in types
    assert "subscription" in types
    assert "volume" in types
