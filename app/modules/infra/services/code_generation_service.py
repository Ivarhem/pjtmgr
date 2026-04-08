from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.infra.models.center import Center
from app.modules.infra.models.rack import Rack
from app.modules.infra.models.rack_line import RackLine
from app.modules.infra.models.room import Room


TEMPLATE_VARIABLES = {
    "center.prefix",
    "room.prefix",
    "line.prefix",
    "rack.position",
    "rack.project_code",
    "unit",
}

_VAR_PATTERN = re.compile(r"\{([^}]+)\}")


def build_center_system_id(partner_code: str, center_code: str) -> str:
    return f"{partner_code}-{center_code}"


def build_room_system_id(center_system_id: str, room_code: str) -> str:
    return f"{center_system_id}-{room_code}"


def build_rack_system_id(room_system_id: str, rack_code: str) -> str:
    return f"{room_system_id}-{rack_code}"


def render_template(template: str, context: dict[str, str]) -> str:
    """템플릿 문자열의 {variable}을 context 값으로 치환한다."""
    variables = _VAR_PATTERN.findall(template)
    for var in variables:
        if var not in TEMPLATE_VARIABLES:
            raise ValueError(f"지원하지 않는 템플릿 변수: {{{var}}}")
    result = template
    for var in variables:
        value = context.get(var, "")
        result = result.replace(f"{{{var}}}", str(value))
    return result


def preview_rack_codes(db: Session, template: str, room_ids: list[int]) -> dict:
    """템플릿에 따라 변경 대상 목록을 반환한다 (미리보기)."""
    changes = []
    for room_id in room_ids:
        room = db.get(Room, room_id)
        if not room:
            continue
        center = db.get(Center, room.center_id)
        lines = list(db.scalars(select(RackLine).where(RackLine.room_id == room_id)))
        for line in lines:
            racks = list(db.scalars(select(Rack).where(Rack.rack_line_id == line.id)))
            for rack in racks:
                context = {
                    "center.prefix": center.prefix or "",
                    "room.prefix": room.prefix or "",
                    "line.prefix": line.prefix or "",
                    "rack.position": str((rack.line_position or 0) + 1),
                }
                missing = [k for k, v in context.items() if not v and f"{{{k}}}" in template]
                generated = render_template(template, context) if not missing else None
                changes.append(
                    {
                        "id": rack.id,
                        "system_id": rack.system_id,
                        "current_project_code": rack.project_code,
                        "generated_project_code": generated,
                        "missing_fields": missing,
                    }
                )
    will_update = sum(1 for c in changes if c["generated_project_code"] is not None)
    return {
        "template": template,
        "changes": changes,
        "summary": {"total": len(changes), "will_update": will_update, "skipped": len(changes) - will_update},
    }


def generate_rack_codes(db: Session, template: str, room_ids: list[int]) -> dict:
    """템플릿에 따라 프로젝트코드를 일괄 적용한다."""
    preview = preview_rack_codes(db, template, room_ids)
    updated = 0
    for change in preview["changes"]:
        if change["generated_project_code"] is not None:
            rack = db.get(Rack, change["id"])
            if rack:
                rack.project_code = change["generated_project_code"]
                updated += 1
    db.commit()
    return {"updated": updated, "skipped": preview["summary"]["skipped"]}


def cascade_update_system_ids(db: Session, center: Center) -> None:
    """센터의 system_id가 변경되었을 때, 하위 전산실/랙의 system_id를 재귀 갱신한다."""
    rooms = list(db.scalars(select(Room).where(Room.center_id == center.id)))
    for room in rooms:
        room.system_id = build_room_system_id(center.system_id, room.room_code)
        racks = list(db.scalars(select(Rack).where(Rack.room_id == room.id)))
        for rack in racks:
            rack.system_id = build_rack_system_id(room.system_id, rack.rack_code)


def cascade_update_room_system_ids(db: Session, room: Room) -> None:
    """전산실의 system_id가 변경되었을 때, 하위 랙의 system_id를 재귀 갱신한다."""
    racks = list(db.scalars(select(Rack).where(Rack.room_id == room.id)))
    for rack in racks:
        rack.system_id = build_rack_system_id(room.system_id, rack.rack_code)
