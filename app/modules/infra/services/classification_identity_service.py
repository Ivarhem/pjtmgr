from __future__ import annotations

from typing import Any


PRIMARY_LAYOUT_ATTRIBUTE_KEYS = {"domain", "imp_type"}


def is_valid_primary_layout_attribute(attribute_key: str | None) -> bool:
    return attribute_key in PRIMARY_LAYOUT_ATTRIBUTE_KEYS


def resolve_primary_layout_attribute_key(layout: Any | None) -> str:
    level_key = _extract_level_attribute_key(layout, 1)
    return level_key if is_valid_primary_layout_attribute(level_key) else "domain"


def derive_asset_type_identity(
    attr_map: dict[str, dict[str, str | None]],
    layout: Any | None = None,
) -> dict[str, str | None]:
    domain = attr_map.get("domain", {})
    imp_type = attr_map.get("imp_type", {})
    if not domain.get("option_key") or not imp_type.get("option_key"):
        return {
            "asset_type_key": None,
            "asset_type_code": None,
            "asset_type_label": None,
            "primary_attribute_key": resolve_primary_layout_attribute_key(layout),
        }

    primary_key = resolve_primary_layout_attribute_key(layout)
    secondary_key = "imp_type" if primary_key == "domain" else "domain"
    ordered = [attr_map.get(primary_key, {}), attr_map.get(secondary_key, {})]
    option_keys = [item.get("option_key") for item in ordered if item.get("option_key")]
    labels = [item.get("label") for item in ordered if item.get("label")]
    return {
        "asset_type_key": "_".join(option_keys) if option_keys else None,
        "asset_type_code": "-".join(key.upper() for key in option_keys) if option_keys else None,
        "asset_type_label": "-".join(labels) if labels else None,
        "primary_attribute_key": primary_key,
    }


def _extract_level_attribute_key(layout: Any | None, level_no: int) -> str | None:
    if layout is None:
        return None
    levels = _get_layout_levels(layout)
    for level in levels:
        current_level_no = _get_value(level, "level_no")
        if current_level_no != level_no:
            continue
        keys = _get_value(level, "keys") or []
        if not keys:
            attribute_keys = _get_value(level, "attribute_keys") or []
            return attribute_keys[0] if attribute_keys else None
        first_key = keys[0]
        return _get_value(first_key, "attribute_key")
    return None


def _get_layout_levels(layout: Any) -> list[Any]:
    levels = _get_value(layout, "levels")
    return list(levels or [])


def _get_value(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)
