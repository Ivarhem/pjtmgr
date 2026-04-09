import pytest
from app.modules.infra.services.code_generation_service import (
    build_center_system_id,
    build_room_system_id,
    build_rack_system_id,
    render_template,
    TEMPLATE_VARIABLES,
)


def test_build_center_system_id():
    assert build_center_system_id("P000", "C01") == "P000-C01"


def test_build_room_system_id():
    assert build_room_system_id("P000-C01", "R01") == "P000-C01-R01"


def test_build_rack_system_id():
    assert build_rack_system_id("P000-C01-R01", "A12") == "P000-C01-R01-A12"


def test_render_template_rack_project_code():
    context = {
        "center.prefix": "S",
        "room.prefix": "07A",
        "line.prefix": "A",
        "rack.position": "12",
    }
    result = render_template("{center.prefix}{room.prefix}-{line.prefix}{rack.position}", context)
    assert result == "S07A-A12"


def test_render_template_asset_project_code():
    context = {
        "rack.project_code": "S07A-A12",
        "unit": "41",
    }
    result = render_template("{rack.project_code}-{unit}", context)
    assert result == "S07A-A12-41"


def test_render_template_missing_prefix_returns_empty():
    context = {
        "center.prefix": "",
        "room.prefix": "07A",
        "line.prefix": "A",
        "rack.position": "12",
    }
    result = render_template("{center.prefix}{room.prefix}-{line.prefix}{rack.position}", context)
    assert result == "07A-A12"


def test_render_template_invalid_variable_raises():
    with pytest.raises(ValueError, match="지원하지 않는 템플릿 변수"):
        render_template("{invalid.var}", {})
