from __future__ import annotations

import pytest

from app.core.exceptions import DuplicateError
from app.modules.common.models.asset_type_code import AssetTypeCode
from app.modules.infra.models.classification_node import ClassificationNode
from app.modules.infra.models.classification_scheme import ClassificationScheme
from app.modules.infra.schemas.asset_type_classification_mapping import (
    AssetTypeClassificationMappingCreate,
    AssetTypeClassificationMappingUpdate,
)
from app.modules.infra.services.asset_type_classification_mapping_service import (
    create_asset_type_classification_mapping,
    list_asset_type_classification_mappings,
    update_asset_type_classification_mapping,
)


def _seed_global_scheme(db_session):
    scheme = ClassificationScheme(scope_type="global", name="글로벌 기본 분류체계", is_active=True)
    db_session.add(scheme)
    db_session.flush()

    root = ClassificationNode(
        scheme_id=scheme.id,
        node_code="HW",
        node_name="하드웨어",
        level=1,
        sort_order=10,
        is_active=True,
    )
    db_session.add(root)
    db_session.flush()

    child = ClassificationNode(
        scheme_id=scheme.id,
        parent_id=root.id,
        node_code="HW-SRV",
        node_name="서버",
        level=2,
        sort_order=20,
        is_active=True,
    )
    db_session.add(child)
    db_session.flush()
    return scheme, root, child


def test_create_mapping_returns_label_and_path(db_session) -> None:
    db_session.add(
        AssetTypeCode(
            type_key="server",
            code="SVR",
            label="서버",
            kind="hardware",
            sort_order=1,
            is_active=True,
        )
    )
    db_session.flush()
    _seed_global_scheme(db_session)
    db_session.commit()

    row = create_asset_type_classification_mapping(
        db_session,
        AssetTypeClassificationMappingCreate(
            asset_type_key="server",
            classification_node_code="HW-SRV",
            is_default=True,
            is_allowed=True,
            sort_order=10,
            note="기본 서버 분류",
        ),
    )

    assert row.asset_type_label == "서버"
    assert row.classification_node_name == "서버"
    assert row.classification_path_label == "하드웨어 > 서버"


def test_default_mapping_switches_to_latest_for_same_asset_type(db_session) -> None:
    db_session.add(
        AssetTypeCode(
            type_key="server",
            code="SVR",
            label="서버",
            kind="hardware",
            sort_order=1,
            is_active=True,
        )
    )
    scheme, root, child = _seed_global_scheme(db_session)
    db_session.add(
        ClassificationNode(
            scheme_id=scheme.id,
            parent_id=root.id,
            node_code="HW-ETC",
            node_name="기타장비",
            level=2,
            sort_order=30,
            is_active=True,
        )
    )
    db_session.commit()

    first = create_asset_type_classification_mapping(
        db_session,
        AssetTypeClassificationMappingCreate(
            asset_type_key="server",
            classification_node_code=child.node_code,
            is_default=True,
            is_allowed=True,
            sort_order=10,
        ),
    )
    second = create_asset_type_classification_mapping(
        db_session,
        AssetTypeClassificationMappingCreate(
            asset_type_key="server",
            classification_node_code="HW-ETC",
            is_default=False,
            is_allowed=True,
            sort_order=20,
        ),
    )

    updated = update_asset_type_classification_mapping(
        db_session,
        second.id,
        AssetTypeClassificationMappingUpdate(is_default=True),
    )

    rows = list_asset_type_classification_mappings(db_session)
    by_code = {row.classification_node_code: row for row in rows}
    assert by_code["HW-SRV"].is_default is False
    assert by_code["HW-ETC"].is_default is True
    assert updated.is_default is True


def test_duplicate_mapping_rejected(db_session) -> None:
    db_session.add(
        AssetTypeCode(
            type_key="server",
            code="SVR",
            label="서버",
            kind="hardware",
            sort_order=1,
            is_active=True,
        )
    )
    _seed_global_scheme(db_session)
    db_session.commit()

    payload = AssetTypeClassificationMappingCreate(
        asset_type_key="server",
        classification_node_code="HW-SRV",
        is_default=True,
        is_allowed=True,
        sort_order=10,
    )
    create_asset_type_classification_mapping(db_session, payload)

    with pytest.raises(DuplicateError):
        create_asset_type_classification_mapping(db_session, payload)
