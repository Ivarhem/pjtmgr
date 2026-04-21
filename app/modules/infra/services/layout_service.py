from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.partner import Partner
from app.modules.common.models.user import User
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
            "is_main": center.is_main,
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
            "is_main": room.is_main,
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
            "rack_line_id": rack.rack_line_id,
            "line_position": rack.line_position,
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


def _clear_other_main_centers(db: Session, partner_id: int, keep_center_id: int | None = None) -> None:
    centers = list(db.scalars(select(Center).where(Center.partner_id == partner_id, Center.is_main.is_(True))))
    for center in centers:
        if keep_center_id is not None and center.id == keep_center_id:
            continue
        center.is_main = False


def _clear_other_main_rooms(db: Session, center_id: int, keep_room_id: int | None = None) -> None:
    rooms = list(db.scalars(select(Room).where(Room.center_id == center_id, Room.is_main.is_(True))))
    for room in rooms:
        if keep_room_id is not None and room.id == keep_room_id:
            continue
        room.is_main = False


def create_center(db: Session, payload: CenterCreate, current_user: User) -> Center:
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
    if payload.is_main:
        _clear_other_main_centers(db, payload.partner_id)
    db.add(center)
    db.flush()
    partner = db.get(Partner, payload.partner_id)
    center.system_id = build_center_system_id(partner.partner_code, center_code)
    default_room = Room(
        center_id=center.id,
        room_code="MAIN",
        room_name="기본 전산실",
        is_active=True,
        is_main=True if payload.is_main else False,
        system_id=build_room_system_id(center.system_id, "MAIN"),
    )
    db.add(default_room)
    db.commit()
    db.refresh(center)
    return center


def update_center(db: Session, center_id: int, payload: CenterUpdate, current_user: User) -> Center:
    _require_inventory_edit(current_user)
    center = get_center(db, center_id)
    changes = payload.model_dump(exclude_unset=True)
    next_code = changes.get("center_code", center.center_code)
    code_changed = next_code != center.center_code
    if code_changed:
        _ensure_center_code_unique(db, center.partner_id, next_code, center.id)
    for field, value in changes.items():
        setattr(center, field, value)
    if changes.get("is_main") is True:
        _clear_other_main_centers(db, center.partner_id, center.id)
    if code_changed:
        partner = db.get(Partner, center.partner_id)
        center.system_id = build_center_system_id(partner.partner_code, center.center_code)
        cascade_update_system_ids(db, center)
    db.commit()
    db.refresh(center)
    return center


def delete_center(db: Session, center_id: int, current_user: User) -> None:
    _require_inventory_edit(current_user)
    center = get_center(db, center_id)
    room_exists = db.scalar(select(func.count(Room.id)).where(Room.center_id == center.id)) or 0
    if room_exists:
        raise BusinessRuleError("전산실이 등록된 센터는 먼저 하위 데이터를 정리한 뒤 삭제하세요.", status_code=409)
    db.delete(center)
    db.commit()


def create_room(db: Session, payload: RoomCreate, current_user: User) -> Room:
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
    if payload.is_main:
        _clear_other_main_rooms(db, center.id)
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def update_room(db: Session, room_id: int, payload: RoomUpdate, current_user: User) -> Room:
    _require_inventory_edit(current_user)
    room = get_room(db, room_id)
    changes = payload.model_dump(exclude_unset=True)
    next_code = changes.get("room_code", room.room_code)
    code_changed = next_code != room.room_code
    if code_changed:
        _ensure_room_code_unique(db, room.center_id, next_code, room.id)
    for field, value in changes.items():
        setattr(room, field, value)
    if changes.get("is_main") is True:
        _clear_other_main_rooms(db, room.center_id, room.id)
    if code_changed:
        center = get_center(db, room.center_id)
        room.system_id = build_room_system_id(center.system_id, room.room_code)
        cascade_update_room_system_ids(db, room)
    db.commit()
    db.refresh(room)
    return room


def delete_room(db: Session, room_id: int, current_user: User) -> None:
    _require_inventory_edit(current_user)
    room = get_room(db, room_id)
    rack_exists = db.scalar(select(func.count(Rack.id)).where(Rack.room_id == room.id)) or 0
    if rack_exists:
        raise BusinessRuleError("랙이 등록된 전산실은 먼저 랙을 정리한 뒤 삭제하세요.", status_code=409)
    db.delete(room)
    db.commit()


def create_rack(db: Session, payload: RackCreate, current_user: User) -> Rack:
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
    db.flush()
    if rack.rack_line_id is not None:
        _auto_fill_project_code(db, rack, rack.rack_line_id, rack.line_position)
    db.commit()
    db.refresh(rack)
    return rack


def update_rack(db: Session, rack_id: int, payload: RackUpdate, current_user: User) -> Rack:
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


def delete_rack(db: Session, rack_id: int, current_user: User) -> None:
    _require_inventory_edit(current_user)
    rack = get_rack(db, rack_id)
    db.delete(rack)
    db.commit()


def list_rack_lines(db: Session, room_id: int) -> list[dict]:
    get_room(db, room_id)
    lines = list(
        db.scalars(
            select(RackLine)
            .where(RackLine.room_id == room_id)
            .order_by(RackLine.sort_order.asc(), RackLine.col_index.asc().nullslast(), RackLine.id.asc())
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
                "start_col": line.start_col,
                "start_row": line.start_row,
                "end_col": line.end_col,
                "end_row": line.end_row,
                "direction": line.direction,
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


def create_rack_line(db: Session, room_id: int, payload: RackLineCreate, current_user: User) -> RackLine:
    _require_inventory_edit(current_user)
    room = get_room(db, room_id)
    data = _normalize_rack_line_payload(db, room, payload.model_dump(), None)
    line = RackLine(room_id=room_id, **data)
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def update_rack_line(db: Session, line_id: int, payload: RackLineUpdate, current_user: User) -> RackLine:
    _require_inventory_edit(current_user)
    line = get_rack_line(db, line_id)
    room = get_room(db, line.room_id)
    changes = payload.model_dump(exclude_unset=True)
    before_cells = tuple(_build_line_cells(line))
    normalized = _normalize_rack_line_payload(db, room, changes, line)
    after_cells = tuple(_build_line_cells(type("LineDraft", (), normalized)()))
    line_reassigned = before_cells != after_cells
    for field, value in normalized.items():
        setattr(line, field, value)
    if line_reassigned:
        racks = list(db.scalars(select(Rack).where(Rack.rack_line_id == line.id)))
        for rack in racks:
            rack.rack_line_id = None
            rack.line_position = None
    db.commit()
    db.refresh(line)
    return line


def delete_rack_line(db: Session, line_id: int, current_user: User) -> None:
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
    from app.modules.infra.models.product_catalog import ProductCatalog

    rack = db.get(Rack, rack_id)
    if rack is None:
        raise NotFoundError("Rack not found")

    rows = db.execute(
        select(Asset, ProductCatalog.product_type)
        .join(ProductCatalog, ProductCatalog.id == Asset.model_id, isouter=True)
        .where(Asset.rack_id == rack_id)
        .order_by(Asset.rack_start_unit.asc().nullslast(), Asset.id.asc())
    ).all()
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
            "category": a.category,
            "asset_class": a.asset_class,
            "product_type": product_type or "hardware",
        }
        for a, product_type in rows
    ]


def reorder_racks(db: Session, orders: list[dict], current_user: User) -> None:
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



def _is_unassigned_line_payload(data: dict) -> bool:
    return data.get("col_index") == -1 and not any(
        data.get(key) is not None for key in ("start_col", "start_row", "end_col", "end_row")
    )


def _build_line_cells(line: RackLine | object) -> list[tuple[int, int]]:
    start_col = getattr(line, "start_col", None)
    start_row = getattr(line, "start_row", None)
    end_col = getattr(line, "end_col", None)
    end_row = getattr(line, "end_row", None)
    if None not in (start_col, start_row, end_col, end_row):
        if start_col == end_col:
            step = 1 if end_row >= start_row else -1
            return [(start_col, row) for row in range(start_row, end_row + step, step)]
        if start_row == end_row:
            step = 1 if end_col >= start_col else -1
            return [(col, start_row) for col in range(start_col, end_col + step, step)]
        return []
    col_index = getattr(line, "col_index", None)
    slot_count = int(getattr(line, "slot_count", 0) or 0)
    if col_index is None or col_index < 0 or slot_count <= 0:
        return []
    return [(col_index, row) for row in range(slot_count)]


def _normalize_rack_line_payload(db: Session, room: Room, incoming: dict, existing: RackLine | None) -> dict:
    data = {
        "line_name": existing.line_name if existing else incoming.get("line_name", ""),
        "col_index": existing.col_index if existing else incoming.get("col_index"),
        "slot_count": existing.slot_count if existing else incoming.get("slot_count", room.grid_rows or 1),
        "disabled_slots": list(existing.disabled_slots or []) if existing else list(incoming.get("disabled_slots") or []),
        "prefix": existing.prefix if existing else incoming.get("prefix"),
        "sort_order": existing.sort_order if existing else incoming.get("sort_order", 0),
        "start_col": existing.start_col if existing else incoming.get("start_col"),
        "start_row": existing.start_row if existing else incoming.get("start_row"),
        "end_col": existing.end_col if existing else incoming.get("end_col"),
        "end_row": existing.end_row if existing else incoming.get("end_row"),
        "direction": existing.direction if existing else incoming.get("direction"),
    }
    for field, value in incoming.items():
        data[field] = value

    if not str(data.get("line_name") or "").strip():
        raise BusinessRuleError("라인명을 입력하세요.", status_code=422)
    data["line_name"] = str(data["line_name"]).trim() if hasattr(str(data["line_name"]), "trim") else str(data["line_name"]).strip()
    data["disabled_slots"] = sorted({int(v) for v in (data.get("disabled_slots") or []) if v is not None and int(v) >= 0})

    if _is_unassigned_line_payload(data):
        data["direction"] = None
        data["start_col"] = None
        data["start_row"] = None
        data["end_col"] = None
        data["end_row"] = None
        data["slot_count"] = max(1, int(data.get("slot_count") or room.grid_rows or 1))
        return data

    coord_fields = [data.get("start_col"), data.get("start_row"), data.get("end_col"), data.get("end_row")]
    has_coords = any(value is not None for value in coord_fields)
    if has_coords and None in coord_fields:
        raise BusinessRuleError("라인 시작/종료 좌표를 모두 입력하세요.", status_code=422)

    if has_coords:
        start_col = int(data["start_col"])
        start_row = int(data["start_row"])
        end_col = int(data["end_col"])
        end_row = int(data["end_row"])
        if not (0 <= start_col < room.grid_cols and 0 <= end_col < room.grid_cols):
            raise BusinessRuleError(f"라인 열 좌표는 0 이상 {room.grid_cols - 1} 이하여야 합니다.", status_code=422)
        if not (0 <= start_row < room.grid_rows and 0 <= end_row < room.grid_rows):
            raise BusinessRuleError(f"라인 행 좌표는 0 이상 {room.grid_rows - 1} 이하여야 합니다.", status_code=422)
        if start_col != end_col and start_row != end_row:
            raise BusinessRuleError("라인은 같은 행 또는 같은 열의 직선으로만 배치할 수 있습니다.", status_code=422)
        direction = "vertical" if start_col == end_col else "horizontal"
        data["direction"] = direction
        data["slot_count"] = abs(end_row - start_row) + 1 if direction == "vertical" else abs(end_col - start_col) + 1
        data["col_index"] = min(start_col, end_col)
        data["start_col"] = start_col
        data["start_row"] = start_row
        data["end_col"] = end_col
        data["end_row"] = end_row
    else:
        col_index = data.get("col_index")
        if col_index is None:
            raise BusinessRuleError("라인 배치 좌표를 지정하세요.", status_code=422)
        col_index = int(col_index)
        if col_index < 0 or col_index >= room.grid_cols:
            raise BusinessRuleError(f"col_index는 0 이상 {room.grid_cols - 1} 이하여야 합니다.", status_code=422)
        slot_count = max(1, int(data.get("slot_count") or room.grid_rows or 1))
        data["col_index"] = col_index
        data["slot_count"] = slot_count
        data["direction"] = data.get("direction") or "vertical"
        data["start_col"] = col_index
        data["end_col"] = col_index
        data["start_row"] = 0
        data["end_row"] = min(room.grid_rows - 1, slot_count - 1)

    candidate_cells = set(_build_line_cells(type("LineDraft", (), data)()))
    if not candidate_cells:
        raise BusinessRuleError("유효한 라인 좌표를 계산할 수 없습니다.", status_code=422)
    existing_lines = list(db.scalars(select(RackLine).where(RackLine.room_id == room.id)))
    for other in existing_lines:
        if existing is not None and other.id == existing.id:
            continue
        if _is_unassigned_line_payload({
            "col_index": other.col_index,
            "start_col": other.start_col,
            "start_row": other.start_row,
            "end_col": other.end_col,
            "end_row": other.end_row,
        }):
            continue
        if candidate_cells & set(_build_line_cells(other)):
            raise DuplicateError(f"라인 '{other.line_name}'과(와) 좌표가 겹칩니다.")
    return data

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


def _require_inventory_edit(current_user: User) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")
