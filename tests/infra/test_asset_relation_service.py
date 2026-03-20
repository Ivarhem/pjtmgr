"""Infra module: asset relation service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.common.models.customer import Customer
from app.modules.infra.schemas.asset import AssetCreate
from app.modules.infra.schemas.asset_relation import AssetRelationCreate, AssetRelationUpdate
from app.modules.infra.schemas.project import ProjectCreate
from app.modules.infra.services.asset_relation_service import (
    create_asset_relation,
    delete_asset_relation,
    list_by_asset,
    update_asset_relation,
)
from app.modules.infra.services.asset_service import create_asset
from app.modules.infra.services.project_service import create_project


def _make_admin(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="rel_admin", name="RelAdmin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_customer(db_session):
    customer = Customer(name="테스트고객", business_no="123-45-67890")
    db_session.add(customer)
    db_session.flush()
    return customer


def test_create_and_list_relations(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    customer = _make_customer(db_session)
    proj = create_project(db_session, ProjectCreate(project_code="REL-01", project_name="Rel Test", customer_id=customer.id), admin)
    svr = create_asset(db_session, AssetCreate(customer_id=customer.id, asset_name="SVR-R1", asset_type="server"), admin)
    db_obj = create_asset(db_session, AssetCreate(customer_id=customer.id, asset_name="DB-R1", asset_type="server"), admin)

    rel = create_asset_relation(db_session, AssetRelationCreate(src_asset_id=svr.id, dst_asset_id=db_obj.id, relation_type="HOSTS"), admin)
    assert rel.relation_type == "HOSTS"

    rels = list_by_asset(db_session, svr.id)
    assert len(rels) == 1
    assert rels[0]["dst_asset_name"] == "DB-R1"

    # 역방향 조회
    rels2 = list_by_asset(db_session, db_obj.id)
    assert len(rels2) == 1
    assert rels2[0]["src_asset_name"] == "SVR-R1"


def test_self_relation_rejected(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    customer = _make_customer(db_session)
    proj = create_project(db_session, ProjectCreate(project_code="REL-02", project_name="Self Test", customer_id=customer.id), admin)
    svr = create_asset(db_session, AssetCreate(customer_id=customer.id, asset_name="SVR-R2", asset_type="server"), admin)

    with pytest.raises(BusinessRuleError):
        create_asset_relation(db_session, AssetRelationCreate(src_asset_id=svr.id, dst_asset_id=svr.id, relation_type="HOSTS"), admin)


def test_delete_relation(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    customer = _make_customer(db_session)
    proj = create_project(db_session, ProjectCreate(project_code="REL-03", project_name="Del Test", customer_id=customer.id), admin)
    svr = create_asset(db_session, AssetCreate(customer_id=customer.id, asset_name="SVR-R3", asset_type="server"), admin)
    fw = create_asset(db_session, AssetCreate(customer_id=customer.id, asset_name="FW-R3", asset_type="security"), admin)

    rel = create_asset_relation(db_session, AssetRelationCreate(src_asset_id=fw.id, dst_asset_id=svr.id, relation_type="PROTECTS"), admin)
    delete_asset_relation(db_session, rel.id, admin)
    assert len(list_by_asset(db_session, svr.id)) == 0


def test_update_relation(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    customer = _make_customer(db_session)
    proj = create_project(db_session, ProjectCreate(project_code="REL-04", project_name="Upd Test", customer_id=customer.id), admin)
    svr = create_asset(db_session, AssetCreate(customer_id=customer.id, asset_name="SVR-R4", asset_type="server"), admin)
    app = create_asset(db_session, AssetCreate(customer_id=customer.id, asset_name="APP-R4", asset_type="server"), admin)

    rel = create_asset_relation(db_session, AssetRelationCreate(src_asset_id=svr.id, dst_asset_id=app.id, relation_type="HOSTS"), admin)
    updated = update_asset_relation(db_session, rel.id, AssetRelationUpdate(relation_type="DEPENDS_ON"), admin)
    assert updated.relation_type == "DEPENDS_ON"
