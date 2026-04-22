from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.core.exceptions import DuplicateError
from app.modules.common.models.role import Role
from app.modules.common.models.user import User
from app.modules.infra.models.catalog_attribute_def import CatalogAttributeDef
from app.modules.infra.models.catalog_attribute_option import CatalogAttributeOption
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.services.catalog_alias_service import (
    create_attribute_option_alias,
    delete_attribute_option_alias,
    list_attribute_option_aliases,
    resolve_attribute_option_canonical,
    update_attribute_option_alias,
)
from app.modules.infra.services.product_catalog_attribute_service import replace_product_attributes
from app.modules.infra.services.catalog_attribute_service import create_attribute_option
from app.modules.infra.schemas.catalog_attribute_option import CatalogAttributeOptionCreate
from app.modules.infra.schemas.catalog_attribute_option_alias import (
    CatalogAttributeOptionAliasCreate,
    CatalogAttributeOptionAliasUpdate,
)
from app.modules.infra.schemas.product_catalog_attribute_value import ProductCatalogAttributesUpdate


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://pjtmgr:pjtmgr@localhost:5432/pjtmgr_test",
)


def _normalize_test_db_url(db_url: str) -> str:
    if db_url.startswith("postgresql://"):
        return db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return db_url


def _ensure_test_database_exists(db_url: str) -> None:
    url = make_url(db_url)
    database_name = url.database
    if not database_name or not url.drivername.startswith("postgresql"):
        return
    admin_url = url.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": database_name},
            ).scalar()
            if not exists:
                try:
                    conn.execute(text(f'CREATE DATABASE "{database_name}"'))
                except IntegrityError:
                    pass
    finally:
        admin_engine.dispose()


@pytest.fixture
def local_db_session() -> Generator[Session, None, None]:
    test_db_url = _normalize_test_db_url(TEST_DATABASE_URL)
    _ensure_test_database_exists(test_db_url)
    engine = create_engine(test_db_url, pool_pre_ping=True)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    Base.metadata.create_all(bind=engine)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        engine.dispose()


@pytest.fixture
def admin_user(local_db_session: Session) -> User:
    role = Role(
        name="관리자",
        is_system=True,
        permissions={"admin": True, "modules": {"accounting": "full", "infra": "full"}},
    )
    local_db_session.add(role)
    local_db_session.flush()
    user = User(login_id="catalog_alias_admin", name="CatalogAliasAdmin", role_id=role.id)
    local_db_session.add(user)
    local_db_session.commit()
    local_db_session.refresh(user)
    return user


def _seed_attribute_with_options(db_session: Session):
    attribute = CatalogAttributeDef(
        attribute_key="vendor_series",
        label="Vendor Series",
        value_type="option",
        is_active=True,
        is_required=False,
        is_displayable=True,
        is_system=True,
    )
    db_session.add(attribute)
    db_session.flush()
    primary = CatalogAttributeOption(
        attribute_id=attribute.id,
        option_key="pa_series",
        label="PA Series",
        is_active=True,
    )
    secondary = CatalogAttributeOption(
        attribute_id=attribute.id,
        option_key="fortigate",
        label="FortiGate",
        is_active=True,
    )
    db_session.add_all([primary, secondary])
    db_session.commit()
    db_session.refresh(attribute)
    db_session.refresh(primary)
    db_session.refresh(secondary)
    return attribute, primary, secondary


def test_attribute_option_alias_crud(local_db_session: Session, admin_user: User) -> None:
    attribute, primary, secondary = _seed_attribute_with_options(local_db_session)

    created = create_attribute_option_alias(
        local_db_session,
        CatalogAttributeOptionAliasCreate(
            attribute_key=attribute.attribute_key,
            option_id=primary.id,
            alias_value="Paloalto PA",
            sort_order=20,
            is_active=True,
        ),
        admin_user,
    )
    assert created["option_id"] == primary.id
    assert created["normalized_alias"] == "paloaltopa"

    rows = list_attribute_option_aliases(local_db_session, attribute_key=attribute.attribute_key)
    assert len(rows) == 1
    assert rows[0]["alias_value"] == "Paloalto PA"

    updated = update_attribute_option_alias(
        local_db_session,
        created["id"],
        CatalogAttributeOptionAliasUpdate(
            attribute_key=attribute.attribute_key,
            option_id=secondary.id,
            alias_value="Forti Gate",
            is_active=False,
        ),
        admin_user,
    )
    assert updated["option_id"] == secondary.id
    assert updated["normalized_alias"] == "fortigate"
    assert updated["is_active"] is False

    delete_attribute_option_alias(local_db_session, updated["id"], admin_user)
    assert list_attribute_option_aliases(local_db_session, attribute_key=attribute.attribute_key) == []


def test_resolve_attribute_option_canonical_with_alias(local_db_session: Session, admin_user: User) -> None:
    attribute, primary, _secondary = _seed_attribute_with_options(local_db_session)
    create_attribute_option_alias(
        local_db_session,
        CatalogAttributeOptionAliasCreate(
            attribute_key=attribute.attribute_key,
            option_id=primary.id,
            alias_value="PA-Series",
        ),
        admin_user,
    )

    resolved = resolve_attribute_option_canonical(
        local_db_session,
        attribute_key=attribute.attribute_key,
        raw_value="PA Series",
    )
    assert resolved is not None
    assert resolved.id == primary.id


def test_replace_product_attributes_accepts_option_alias(local_db_session: Session, admin_user: User) -> None:
    attribute, primary, _secondary = _seed_attribute_with_options(local_db_session)
    create_attribute_option_alias(
        local_db_session,
        CatalogAttributeOptionAliasCreate(
            attribute_key=attribute.attribute_key,
            option_id=primary.id,
            alias_value="팔로알토 PA",
        ),
        admin_user,
    )
    domain = CatalogAttributeDef(
        attribute_key="domain",
        label="도메인",
        value_type="option",
        is_active=True,
        is_required=True,
        is_displayable=True,
        is_system=True,
    )
    imp_type = CatalogAttributeDef(
        attribute_key="imp_type",
        label="구현형태",
        value_type="option",
        is_active=True,
        is_required=True,
        is_displayable=True,
        is_system=True,
    )
    local_db_session.add_all([domain, imp_type])
    local_db_session.flush()
    domain_option = CatalogAttributeOption(attribute_id=domain.id, option_key="sec", label="보안", is_active=True)
    imp_type_option = CatalogAttributeOption(attribute_id=imp_type.id, option_key="hw", label="하드웨어", is_active=True)
    local_db_session.add_all([domain_option, imp_type_option])
    product = ProductCatalog(vendor="Palo Alto Networks", name="PA-3220", product_type="hardware")
    local_db_session.add(product)
    local_db_session.commit()
    local_db_session.refresh(product)

    saved = replace_product_attributes(
        local_db_session,
        product.id,
        ProductCatalogAttributesUpdate(
            attributes=[
                {"attribute_key": "domain", "option_key": "sec", "raw_value": None},
                {"attribute_key": "imp_type", "option_key": "hw", "raw_value": None},
                {"attribute_key": attribute.attribute_key, "option_key": None, "raw_value": "팔로알토 PA"},
            ]
        ),
        admin_user,
    )
    target = next(item for item in saved if item["attribute_key"] == attribute.attribute_key)
    assert target["option_id"] == primary.id
    assert target["option_key"] == primary.option_key


def test_create_attribute_option_blocks_duplicate_label_in_same_attribute(local_db_session: Session, admin_user: User) -> None:
    attribute, _primary, _secondary = _seed_attribute_with_options(local_db_session)
    with pytest.raises(DuplicateError, match="같은 아이템명"):
        create_attribute_option(
            local_db_session,
            attribute.id,
            CatalogAttributeOptionCreate(
                option_key="pa_series_alt",
                label="PA Series",
                sort_order=120,
                is_active=True,
            ),
            admin_user,
        )


def test_create_product_family_option_requires_domain_scope(local_db_session: Session, admin_user: User) -> None:
    domain_attribute = CatalogAttributeDef(
        attribute_key="domain",
        label="도메인",
        value_type="option",
        is_active=True,
        is_required=True,
        is_displayable=True,
        is_system=True,
    )
    product_family_attribute = CatalogAttributeDef(
        attribute_key="product_family",
        label="제품군",
        value_type="option",
        is_active=True,
        is_required=False,
        is_displayable=True,
        is_system=True,
    )
    local_db_session.add_all([domain_attribute, product_family_attribute])
    local_db_session.flush()
    sec_domain = CatalogAttributeOption(attribute_id=domain_attribute.id, option_key="sec", label="보안", is_active=True)
    local_db_session.add(sec_domain)
    local_db_session.commit()
    local_db_session.refresh(sec_domain)

    with pytest.raises(Exception, match="도메인 지정이 필요"):
        create_attribute_option(
            local_db_session,
            product_family_attribute.id,
            CatalogAttributeOptionCreate(
                option_key="fw",
                label="방화벽",
                sort_order=100,
                is_active=True,
            ),
            admin_user,
        )

    created = create_attribute_option(
        local_db_session,
        product_family_attribute.id,
        CatalogAttributeOptionCreate(
            option_key="fw",
            label="방화벽",
            domain_option_id=sec_domain.id,
            sort_order=100,
            is_active=True,
        ),
        admin_user,
    )
    assert created.domain_option_id == sec_domain.id
    assert created.domain_option_key == "sec"


def test_replace_product_attributes_blocks_mismatched_product_family_domain(local_db_session: Session, admin_user: User) -> None:
    domain = CatalogAttributeDef(
        attribute_key="domain",
        label="도메인",
        value_type="option",
        is_active=True,
        is_required=True,
        is_displayable=True,
        is_system=True,
    )
    imp_type = CatalogAttributeDef(
        attribute_key="imp_type",
        label="구현형태",
        value_type="option",
        is_active=True,
        is_required=True,
        is_displayable=True,
        is_system=True,
    )
    product_family = CatalogAttributeDef(
        attribute_key="product_family",
        label="제품군",
        value_type="option",
        is_active=True,
        is_required=False,
        is_displayable=True,
        is_system=True,
    )
    local_db_session.add_all([domain, imp_type, product_family])
    local_db_session.flush()
    sec_domain = CatalogAttributeOption(attribute_id=domain.id, option_key="sec", label="보안", is_active=True)
    svr_domain = CatalogAttributeOption(attribute_id=domain.id, option_key="svr", label="서버", is_active=True)
    hw_option = CatalogAttributeOption(attribute_id=imp_type.id, option_key="hw", label="하드웨어", is_active=True)
    local_db_session.add_all([sec_domain, svr_domain, hw_option])
    local_db_session.flush()
    fw_family = CatalogAttributeOption(
        attribute_id=product_family.id,
        option_key="fw",
        label="방화벽",
        domain_option_id=sec_domain.id,
        is_active=True,
    )
    local_db_session.add(fw_family)
    product = ProductCatalog(vendor="Example", name="Mismatch-1", product_type="hardware")
    local_db_session.add(product)
    local_db_session.commit()
    local_db_session.refresh(product)

    with pytest.raises(Exception, match="현재 도메인에 속하지 않습니다"):
        replace_product_attributes(
            local_db_session,
            product.id,
            ProductCatalogAttributesUpdate(
                attributes=[
                    {"attribute_key": "domain", "option_key": "svr", "raw_value": None},
                    {"attribute_key": "imp_type", "option_key": "hw", "raw_value": None},
                    {"attribute_key": "product_family", "option_key": "fw", "raw_value": None},
                ]
            ),
            admin_user,
        )
