"""Bulk asset update service tests."""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.modules.common.models.partner import Partner
from app.modules.common.models.user import User
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.schemas.asset import AssetBulkUpdateItem
from app.modules.infra.services.asset_service import bulk_update_assets


def _make_admin(db: Session, admin_role_id: int) -> User:
    user = User(login_id="bulk_admin", name="Admin", role_id=admin_role_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_partner(db: Session) -> Partner:
    partner = Partner(name="테스트고객", partner_code="BT01")
    db.add(partner)
    db.flush()
    return partner


def _make_catalog(db: Session, name: str = "TestModel") -> ProductCatalog:
    catalog = ProductCatalog(vendor="TestVendor", name=name, product_type="hardware")
    db.add(catalog)
    db.flush()
    return catalog


def _make_asset(db: Session, partner_id: int, name: str) -> Asset:
    catalog = _make_catalog(db, name=f"Model-{name}")
    asset = Asset(partner_id=partner_id, asset_name=name, model_id=catalog.id)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@pytest.fixture
def setup(db_session: Session, admin_role_id: int):
    admin = _make_admin(db_session, admin_role_id)
    partner = _make_partner(db_session)
    a1 = _make_asset(db_session, partner.id, "자산A")
    a2 = _make_asset(db_session, partner.id, "자산B")
    return {"admin": admin, "a1": a1, "a2": a2, "db": db_session}


def test_bulk_update_changes_multiple_assets(setup):
    """2건의 자산을 일괄 업데이트한다."""
    db, admin, a1, a2 = setup["db"], setup["admin"], setup["a1"], setup["a2"]
    items = [
        AssetBulkUpdateItem(id=a1.id, changes={"hostname": "host-a"}),
        AssetBulkUpdateItem(id=a2.id, changes={"hostname": "host-b", "status": "active"}),
    ]
    results = bulk_update_assets(db, items, admin)
    assert len(results) == 2
    assert results[0].hostname == "host-a"
    assert results[1].hostname == "host-b"
    assert results[1].status == "active"


def test_bulk_update_skips_empty_changes(setup):
    """변경사항이 없는 항목은 건너뛴다."""
    db, admin, a1, a2 = setup["db"], setup["admin"], setup["a1"], setup["a2"]
    items = [
        AssetBulkUpdateItem(id=a1.id, changes={}),
        AssetBulkUpdateItem(id=a2.id, changes={"hostname": "updated"}),
    ]
    results = bulk_update_assets(db, items, admin)
    assert len(results) == 1
    assert results[0].hostname == "updated"


def test_bulk_update_filters_unknown_fields(setup):
    """AssetUpdate에 없는 필드는 무시한다."""
    db, admin, a1 = setup["db"], setup["admin"], setup["a1"]
    items = [AssetBulkUpdateItem(id=a1.id, changes={"hostname": "ok", "fake_field": "ignored"})]
    results = bulk_update_assets(db, items, admin)
    assert len(results) == 1
    assert results[0].hostname == "ok"
