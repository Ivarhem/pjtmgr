from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.modules.infra.models.classification_layout import ClassificationLayout
from app.modules.infra.models.classification_layout_level import ClassificationLayoutLevel
from app.modules.infra.models.classification_layout_level_key import ClassificationLayoutLevelKey
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.models.product_catalog_attribute_value import ProductCatalogAttributeValue


def build_catalog_tree(
    db: Session,
    layout_id: int,
    product_type: str | None = None,
    q: str | None = None,
) -> list[dict]:
    layout = _load_layout_definition(db, layout_id)
    products = _load_products(db, product_type=product_type, q=q)
    matrix = _load_product_attribute_matrix(db, [product["id"] for product in products])
    return _group_products_by_layout(layout, products, matrix)


def build_catalog_table(
    db: Session,
    layout_id: int,
    product_type: str | None = None,
    q: str | None = None,
) -> list[dict]:
    layout = _load_layout_definition(db, layout_id)
    products = _load_products(db, product_type=product_type, q=q)
    matrix = _load_product_attribute_matrix(db, [product["id"] for product in products])
    rows: list[dict] = []
    for product in products:
        product_attrs = matrix.get(product["id"], {})
        labels = [
            _build_level_label(level["keys"], product_attrs, level.get("joiner") or ", ")
            for level in layout["levels"]
        ]
        rows.append(
            {
                "product_id": product["id"],
                "vendor": product["vendor"],
                "name": product["name"],
                "version": product["version"],
                "levels": labels,
                "display_path": " | ".join(labels),
            }
        )
    return rows


def list_products_by_layout_path(db: Session, layout_id: int, path_values: list[str]) -> list[dict]:
    layout = _load_layout_definition(db, layout_id)
    products = _load_products(db)
    matrix = _load_product_attribute_matrix(db, [product["id"] for product in products])
    matched: list[dict] = []
    for product in products:
        labels = [
            _build_level_label(level["keys"], matrix.get(product["id"], {}), level.get("joiner") or ", ")
            for level in layout["levels"]
        ]
        if labels[: len(path_values)] == path_values:
            matched.append(product)
    return matched


def _load_layout_definition(db: Session, layout_id: int) -> dict:
    layout = db.scalar(
        select(ClassificationLayout)
        .options(
            selectinload(ClassificationLayout.levels)
            .selectinload(ClassificationLayoutLevel.keys)
            .selectinload(ClassificationLayoutLevelKey.attribute)
        )
        .where(ClassificationLayout.id == layout_id)
    )
    if layout is None:
        raise NotFoundError("분류 레이아웃을 찾을 수 없습니다.")
    return {
        "id": layout.id,
        "name": layout.name,
        "levels": [
            {
                "level_no": level.level_no,
                "alias": level.alias,
                "joiner": level.joiner,
                "keys": [
                    {
                        "attribute_id": key.attribute_id,
                        "attribute_key": key.attribute.attribute_key if key.attribute else None,
                        "attribute_label": key.attribute.label if key.attribute else None,
                    }
                    for key in sorted(level.keys, key=lambda item: (item.sort_order, item.id))
                    if key.is_visible
                ],
            }
            for level in sorted(layout.levels, key=lambda item: (item.level_no, item.id))
        ],
    }


def _load_product_attribute_matrix(db: Session, product_ids: list[int] | None = None) -> dict[int, dict[str, dict]]:
    stmt = select(ProductCatalogAttributeValue).options(
        selectinload(ProductCatalogAttributeValue.attribute),
        selectinload(ProductCatalogAttributeValue.option),
    )
    if product_ids is not None:
        if not product_ids:
            return {}
        stmt = stmt.where(ProductCatalogAttributeValue.product_id.in_(product_ids))
    rows = list(db.scalars(stmt))
    matrix: dict[int, dict[str, dict]] = defaultdict(dict)
    for row in rows:
        if row.attribute is None:
            continue
        matrix[row.product_id][row.attribute.attribute_key] = {
            "attribute_key": row.attribute.attribute_key,
            "attribute_label": row.attribute.label,
            "option_key": row.option.option_key if row.option else None,
            "option_label": row.option.label if row.option else None,
            "raw_value": row.raw_value,
        }
    return matrix


def _build_level_label(level_keys: list[dict], product_attrs: dict[str, dict], joiner: str) -> str:
    values: list[str] = []
    for key in level_keys:
        attr = product_attrs.get(key["attribute_key"])
        if not attr:
            continue
        value = attr.get("option_label") or attr.get("option_key") or attr.get("raw_value")
        if value:
            values.append(str(value))
    return joiner.join(values) if values else "—"


def _group_products_by_layout(layout: dict, products: list[dict], matrix: dict[int, dict[str, dict]]) -> list[dict]:
    root: dict[str, dict] = {}
    for product in products:
        product_attrs = matrix.get(product["id"], {})
        labels = [
            _build_level_label(level["keys"], product_attrs, level.get("joiner") or ", ")
            for level in layout["levels"]
        ]
        cursor = root
        path: list[str] = []
        for index, label in enumerate(labels, start=1):
            path.append(label)
            node = cursor.setdefault(
                label,
                {
                    "key": label,
                    "label": label,
                    "level": index,
                    "path": list(path),
                    "product_count": 0,
                    "children": {},
                },
            )
            node["product_count"] += 1
            cursor = node["children"]
    return _flatten_tree(root)


def _flatten_tree(nodes: dict[str, dict]) -> list[dict]:
    result: list[dict] = []
    for node in nodes.values():
        children = _flatten_tree(node["children"])
        result.append(
            {
                "key": node["key"],
                "label": node["label"],
                "level": node["level"],
                "path": node["path"],
                "product_count": node["product_count"],
                "children": children,
            }
        )
    return sorted(result, key=lambda item: item["label"])


def _load_products(db: Session, product_type: str | None = None, q: str | None = None) -> list[dict]:
    stmt = select(ProductCatalog).order_by(ProductCatalog.vendor.asc(), ProductCatalog.name.asc(), ProductCatalog.id.asc())
    if product_type:
        stmt = stmt.where(ProductCatalog.product_type == product_type)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where((ProductCatalog.vendor.ilike(like)) | (ProductCatalog.name.ilike(like)))
    products = list(db.scalars(stmt))
    return [
        {
            "id": product.id,
            "vendor": product.vendor,
            "name": product.name,
            "version": product.version,
            "product_type": product.product_type,
        }
        for product in products
    ]
