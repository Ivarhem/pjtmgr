from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.partner import Partner
from app.modules.infra.models.center import Center
from app.modules.infra.models.rack import Rack
from app.modules.infra.models.rack_line import RackLine
from app.modules.infra.models.room import Room
from app.modules.infra.schemas.center import CenterCreate, CenterUpdate
from app.modules.infra.schemas.rack import RackCreate, RackUpdate
from app.modules.infra.schemas.rack_line import RackLineCreate, RackLineUpdate
from app.modules.infra.schemas.room import RoomCreate, RoomUpdate
from app.modules.infra.services.code_generation_service import (
    build_center_system_id,
    build_rack_system_id,
    build_room_system_id,
    cascade_update_room_system_ids,
    cascade_update_system_ids,
)


def list_centers(db: Session, partner_id: int) -> list[dict]:
    _ensure_partner_exists(db, partner_id)
    rows = list(
        db.execute(
            select(
                Center,
                func.count(func.distinct(Room.id)).label("room_count"),
                func.count(func.distinct(Rack.id)).label("rack_count"),
            )
            .outerjoin(Room, Room.center_id == Center.id)
            .outerjoin(Rack, Rack.room_id == Room.id)
            .where(Center.partner_id == partner_id)
            .group_by(Center.id)
            .order_by(Center.center_code.asc(), Center.id.asc())
        )
    )
    return [
        {
            "id": center.id,
            "partner_id": center.partner_id,
            "center_code": center.center_code,
            "center_name": center.center_name,
            "location": center.location,
            "is_active": center.is_active,
            "note": center.note,
            "system_id": center.system_id,
            "prefix": center.prefix,
            "project_code": center.project_code,
            "room_count": room_count,
            "rack_count": rack_count,
            "created_at": center.created_at,
            "updated_at": center.updated_at,
        }
        for center, room_count, rack_count in rows
    ]


def list_rooms(db: Session, center_id: int) -> list[dict]:
    center = get_center(db, center_id)
    rows = list(
        db.execute(
            select(Room, func.count(Rack.id))
            .outerjoin(Rack, Rack.room_id == Room.id)
            .where(Room.center_id == center.id)
            .group_by(Room.id)
            .order_by(Room.room_code.asc(), Room.id.asc())
        )
    )
    return [
        {
            "id": room.id,
            "center_id": room.center_id,
            "center_code": center.center_code,
            "center_name": center.center_name,
            "room_code": room.room_code,
            "room_name": room.room_name,
            "floor": room.floor,
            "is_active": room.is_active,
            "note": room.note,
            "system_id": room.system_id,
            "prefix": room.prefix,
            "project_code": room.project_code,
            "racks_per_row": room.racks_per_row,
            "grid_cols": room.grid_cols,
            "grid_rows": room.grid_rows,
            "rack_count": rack_count,
            "created_at": room.created_at,
            "updated_at": room.updated_at,
        }
        for room, rack_count in rows
    ]


def list_racks(db: Session, room_id: int) -> list[dict]:
    room = get_room(db, room_id)
    center = get_center(db, room.center_id)
    rows = list(
        db.scalars(select(Rack).where(Rack.room_id == room.id).order_by(Rack.rack_code.asc(), Rack.id.asc()))
    )
    return [
        {
            "id": rack.id,
            "room_id": rack.room_id,
            "room_code": room.room_code,
            "room_name": room.room_name,
            "center_code": center.center_code,
            "center_name": center.center_name,
            "rack_code": rack.rack_code,
            "rack_name": rack.rack_name,
            "total_units": rack.total_units,
            "location_detail": rack.location_detail,
            "is_active": rack.is_active,
            "note": rack.note,
            "system_id": rack.system_id,
            "project_code": rack.project_code,
            "created_at": rack.created_at,
            "updated_at": rack.updated_at,
        }
        for rack in rows
    ]


def get_center(db: Session, center_id: int) -> Center:
    center = db.get(Center, center_id)
    if center is None:
        raise NotFoundError("Center not found")
    return center


def get_room(db: Session, room_id: int) -> Room:
    room = db.get(Room, room_id)
    if room is None:
        raise NotFoundError("Room not found")
    return room


def get_rack(db: Session, rack_id: int) -> Rack:
    rack = db.get(Rack, rack_id)
    if rack is None:
        raise NotFoundError("Rack not found")
    return rack


def create_center(db: Session, payload: CenterCreate, current_user) -> Center:
    _require_inventory_edit(current_user)
    _ensure_partner_exists(db, payload.partner_id)
    center_code = (payload.center_code or "").strip() or _generate_next_code(
        db,
        Center,
        Center.center_code,
        prefix="CTR",
        scope_filters=(Center.partner_id == payload.partner_id,),
    )
    _ensure_center_code_unique(db, payload.partner_id, center_code)
    center = Center(**payload.model_dump(exclude={"center_code"}), center_code=center_code)
    db.add(center)
    db.flush()
    partner = db.get(Partner, payload.partner_id)
    center.system_id = build_center_system_id(partner.partner_code, center_code)
    default_room = Room(
        center_id=center.id,
        room_code="MAIN",
        room_name="기본 전산실",
        is_active=True,
        system_id=build_room_system_id(center.system_id, "MAIN"),
    )
    db.add(default_room)
    db.commit()
    db.refresh(center)
    return center


def update_center(db: Session, center_id: int, payload: CenterUpdate, current_user) -> Center:
    _require_inventory_edit(current_user)
    center = get_center(db, center_id)
    changes = payload.model_dump(exclude_unset=True)
    next_code = changes.get("center_code", center.center_code)
    code_changed = next_code != center.center_code
    if code_changed:
        _ensure_center_code_unique(db, center.partner_id, next_code, center.id)
    for field, value in changes.items():
        setattr(center, field, value)
    if code_changed:
        partner = db.get(Partner, center.partner_id)
        center.system_id = build_center_system_id(partner.partner_code, center.center_code)
        cascade_update_system_ids(db, center)
    db.commit()
    db.refresh(center)
    return center


def delete_center(db: Session, center_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    center = get_center(db, center_id)
    room_exists = db.scalar(select(func.count(Room.id)).where(Room.center_id == center.id)) or 0
    if room_exists:
        raise BusinessRuleError("전산실이 등록된 센터는 먼저 하위 데이터를 정리한 뒤 삭제하세요.", status_code=409)
    db.delete(center)
    db.commit()


def create_room(db: Session, payload: RoomCreate, current_user) -> Room:
    _require_inventory_edit(current_user)
    center = get_center(db, payload.center_id)
    room_code = (payload.room_code or "").strip() or _generate_next_code(
        db,
        Room,
        Room.room_code,
        prefix="ROOM",
        scope_filters=(Room.center_id == center.id,),
    )
    _ensure_room_code_unique(db, center.id, room_code)
    room = Room(**payload.model_dump(exclude={"room_code"}), room_code=room_code)
    room.system_id = build_room_system_id(center.system_id, room_code)
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def update_room(db: Session, room_id: int, payload: RoomUpdate, current_user) -> Room:
    _require_inventory_edit(current_user)
    room = get_room(db, room_id)
    changes = payload.model_dump(exclude_unset=True)
    next_code = changes.get("room_code", room.room_code)
    code_changed = next_code != room.room_code
    if code_changed:
        _ensure_room_code_unique(db, room.center_id, next_code, room.id)
    for field, value in changes.items():
        setattr(room, field, value)
    if code_changed:
        center = get_center(db, room.center_id)
        room.system_id = build_room_system_id(center.system_id, room.room_code)
        cascade_update_room_system_ids(db, room)
    db.commit()
    db.refresh(room)
    return room


def delete_room(db: Session, room_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    room = get_room(db, room_id)
    rack_exists = db.scalar(select(func.count(Rack.id)).where(Rack.room_id == room.id)) or 0
    if rack_exists:
        raise BusinessRuleError("랙이 등록된 전산실은 먼저 랙을 정리한 뒤 삭제하세요.", status_code=409)
    db.delete(room)
    db.commit()


def create_rack(db: Session, payload: RackCreate, current_user) -> Rack:
    _require_inventory_edit(current_user)
    room = get_room(db, payload.room_id)
    _ensure_total_units(payload.total_units)
    rack_code = (payload.rack_code or "").strip() or _generate_next_code(
        db,
        Rack,
        Rack.rack_code,
        prefix="RACK",
        scope_filters=(Rack.room_id == room.id,),
    )
    _ensure_rack_code_unique(db, room.id, rack_code)
    rack = Rack(**payload.model_dump(exclude={"rack_code"}), rack_code=rack_code)
    rack.system_id = build_rack_system_id(room.system_id, rack_code)
    db.add(rack)
    db.commit()
    db.refresh(rack)
    return rack


def update_rack(db: Session, rack_id: int, payload: RackUpdate, current_user) -> Rack:
    _require_inventory_edit(current_user)
    rack = get_rack(db, rack_id)
    changes = payload.model_dump(exclude_unset=True)
    next_code = changes.get("rack_code", rack.rack_code)
    next_units = changes.get("total_units", rack.total_units)
    _ensure_total_units(next_units)
    code_changed = next_code != rack.rack_code
    if code_changed:
        _ensure_rack_code_unique(db, rack.room_id, next_code, rack.id)

    # Detect rack_line_id change for auto-fill
    old_line_id = rack.rack_line_id
    new_line_id = changes.get("rack_line_id", old_line_id)

    for field, value in changes.items():
        setattr(rack, field, value)
    if code_changed:
        room = get_room(db, rack.room_id)
        rack.system_id = build_rack_system_id(room.system_id, rack.rack_code)

    # Auto-fill project_code when rack is placed on a line
    if "rack_line_id" in changes and new_line_id is not None and new_line_id != old_line_id:
        _auto_fill_project_code(db, rack, new_line_id, changes.get("line_position"))

    db.commit()
    db.refresh(rack)
    return rack


def delete_rack(db: Session, rack_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    rack = get_rack(db, rack_id)
    db.delete(rack)
    db.commit()


def list_rack_lines(db: Session, room_id: int) -> list[dict]:
    get_room(db, room_id)
    lines = list(
        db.scalars(
            select(RackLine).where(RackLine.room_id == room_id).order_by(RackLine.col_index.asc(), RackLine.id.asc())
        )
    )
    result = []
    for line in lines:
        racks = list(
            db.scalars(select(Rack).where(Rack.rack_line_id == line.id).order_by(Rack.line_position.asc(), Rack.id.asc()))
        )
        result.append(
            {
                "id": line.id,
                "room_id": line.room_id,
                "line_name": line.line_name,
                "col_index": line.col_index,
                "slot_count": line.slot_count,
                "disabled_slots": line.disabled_slots or [],
                "sort_order": line.sort_order,
                "prefix": line.prefix,
                "created_at": line.created_at,
                "updated_at": line.updated_at,
                "racks": [
                    {
                        "id": r.id,
                        "rack_code": r.rack_code,
                        "rack_name": r.rack_name,
                        "system_id": r.system_id,
                        "project_code": r.project_code,
                        "line_position": r.line_position,
                        "total_units": r.total_units,
                    }
                    for r in racks
                ],
            }
        )
    return result


def get_rack_line(db: Session, line_id: int) -> RackLine:
    line = db.get(RackLine, line_id)
    if line is None:
        raise NotFoundError("RackLine not found")
    return line


def create_rack_line(db: Session, room_id: int, payload: RackLineCreate, current_user) -> RackLine:
    _require_inventory_edit(current_user)
    room = get_room(db, room_id)
    if payload.col_index < 0 or payload.col_index >= room.grid_cols:
        raise BusinessRuleError(
            f"col_index는 0 이상 {room.grid_cols - 1} 이하여야 합니다.", status_code=422
        )
    _ensure_rack_line_col_unique(db, room_id, payload.col_index)
    line = RackLine(room_id=room_id, **payload.model_dump())
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def update_rack_line(db: Session, line_id: int, payload: RackLineUpdate, current_user) -> RackLine:
    _require_inventory_edit(current_user)
    line = get_rack_line(db, line_id)
    changes = payload.model_dump(exclude_unset=True)
    next_col = changes.get("col_index", line.col_index)
    if next_col != line.col_index:
        room = get_room(db, line.room_id)
        if next_col < 0 or next_col >= room.grid_cols:
            raise BusinessRuleError(
                f"col_index는 0 이상 {room.grid_cols - 1} 이하여야 합니다.", status_code=422
            )
        _ensure_rack_line_col_unique(db, line.room_id, next_col, line.id)
    for field, value in changes.items():
        setattr(line, field, value)
    db.commit()
    db.refresh(line)
    return line


def delete_rack_line(db: Session, line_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    line = get_rack_line(db, line_id)
    # Nullify FK on racks belonging to this line
    racks = list(db.scalars(select(Rack).where(Rack.rack_line_id == line.id)))
    for rack in racks:
        rack.rack_line_id = None
        rack.line_position = None
    db.delete(line)
    db.commit()


def list_rack_assets(db: Session, rack_id: int) -> list[dict]:
    """해당 랙에 배치된 자산 목록 (rack_start_unit 순 정렬)."""
    from app.modules.infra.models.asset import Asset

    rack = db.get(Rack, rack_id)
    if rack is None:
        raise NotFoundError("Rack not found")

    assets = list(db.scalars(
        select(Asset)
        .where(Asset.rack_id == rack_id)
        .order_by(Asset.rack_start_unit.asc().nullslast(), Asset.id.asc())
    ))
    return [
        {
            "id": a.id,
            "asset_name": a.asset_name,
            "hostname": a.hostname,
            "rack_start_unit": a.rack_start_unit,
            "rack_end_unit": a.rack_end_unit,
            "size_unit": a.size_unit,
            "status": a.status,
            "environment": a.environment,
            "rack_unit": a.rack_unit,
        }
        for a in assets
    ]


def reorder_racks(db: Session, orders: list[dict], current_user) -> None:
    """벌크 랙 sort_order 업데이트. orders: [{id: int, sort_order: int}, ...]"""
    _require_inventory_edit(current_user)

    for item in orders:
        rack = db.get(Rack, item["id"])
        if rack:
            rack.sort_order = item["sort_order"]
    db.commit()


def _auto_fill_project_code(db: Session, rack: Rack, line_id: int, position: int | None) -> None:
    """Auto-fill rack project_code from template when rack is placed on a line."""
    if line_id is None:
        return
    line = db.get(RackLine, line_id)
    if not line:
        return
    room = db.get(Room, line.room_id)
    if not room:
        return
    center = db.get(Center, room.center_id)
    if not center:
        return

    from app.modules.common.models.contract_period import ContractPeriod

    period = db.scalar(
        select(ContractPeriod).where(
            ContractPeriod.partner_id == center.partner_id,
            ContractPeriod.rack_project_code_template.isnot(None),
        ).order_by(ContractPeriod.id.desc())
    )
    if not period or not period.rack_project_code_template:
        return

    from app.modules.infra.services.code_generation_service import render_template

    context = {
        "center.prefix": center.prefix or "",
        "room.prefix": room.prefix or "",
        "line.prefix": line.prefix or "",
        "rack.position": str((position or 0) + 1),
    }
    try:
        rack.project_code = render_template(period.rack_project_code_template, context)
    except ValueError:
        pass


def _ensure_partner_exists(db: Session, partner_id: int) -> None:
    if db.get(Partner, partner_id) is None:
        raise NotFoundError("Partner not found")


def _ensure_center_code_unique(db: Session, partner_id: int, center_code: str, center_id: int | None = None) -> None:
    existing = db.scalar(select(Center).where(Center.partner_id == partner_id, Center.center_code == center_code))
    if existing is None:
        return
    if center_id is not None and existing.id == center_id:
        return
    raise DuplicateError("같은 고객사에 이미 등록된 센터 코드입니다.")


def _ensure_room_code_unique(db: Session, center_id: int, room_code: str, room_id: int | None = None) -> None:
    existing = db.scalar(select(Room).where(Room.center_id == center_id, Room.room_code == room_code))
    if existing is None:
        return
    if room_id is not None and existing.id == room_id:
        return
    raise DuplicateError("같은 센터에 이미 등록된 전산실 코드입니다.")


def _ensure_rack_code_unique(db: Session, room_id: int, rack_code: str, rack_id: int | None = None) -> None:
    existing = db.scalar(select(Rack).where(Rack.room_id == room_id, Rack.rack_code == rack_code))
    if existing is None:
        return
    if rack_id is not None and existing.id == rack_id:
        return
    raise DuplicateError("같은 전산실에 이미 등록된 랙 코드입니다.")


def _ensure_rack_line_col_unique(
    db: Session, room_id: int, col_index: int, line_id: int | None = None
) -> None:
    existing = db.scalar(
        select(RackLine).where(RackLine.room_id == room_id, RackLine.col_index == col_index)
    )
    if existing is None:
        return
    if line_id is not None and existing.id == line_id:
        return
    raise DuplicateError("같은 전산실에 이미 등록된 열 위치(col_index)입니다.")


def _ensure_total_units(total_units: int) -> None:
    if total_units <= 0:
        raise BusinessRuleError("랙 총 유닛 수는 1 이상이어야 합니다.", status_code=422)


def _generate_next_code(db: Session, model, field, prefix: str, scope_filters: tuple) -> str:
    index = 1
    while True:
        candidate = f"{prefix}-{index:03d}"
        existing = db.scalar(select(model).where(*scope_filters, field == candidate))
        if existing is None:
            return candidate
        index += 1


def _require_inventory_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")
