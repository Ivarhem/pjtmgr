from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.partner import Partner
from app.modules.infra.models.center import Center
from app.modules.infra.models.rack import Rack
from app.modules.infra.models.room import Room
from app.modules.infra.schemas.center import CenterCreate, CenterUpdate
from app.modules.infra.schemas.rack import RackCreate, RackUpdate
from app.modules.infra.schemas.room import RoomCreate, RoomUpdate


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
    default_room = Room(
        center_id=center.id,
        room_code="MAIN",
        room_name="기본 전산실",
        is_active=True,
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
    if next_code != center.center_code:
        _ensure_center_code_unique(db, center.partner_id, next_code, center.id)
    for field, value in changes.items():
        setattr(center, field, value)
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
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def update_room(db: Session, room_id: int, payload: RoomUpdate, current_user) -> Room:
    _require_inventory_edit(current_user)
    room = get_room(db, room_id)
    changes = payload.model_dump(exclude_unset=True)
    next_code = changes.get("room_code", room.room_code)
    if next_code != room.room_code:
        _ensure_room_code_unique(db, room.center_id, next_code, room.id)
    for field, value in changes.items():
        setattr(room, field, value)
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
    if next_code != rack.rack_code:
        _ensure_rack_code_unique(db, rack.room_id, next_code, rack.id)
    for field, value in changes.items():
        setattr(rack, field, value)
    db.commit()
    db.refresh(rack)
    return rack


def delete_rack(db: Session, rack_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    rack = get_rack(db, rack_id)
    db.delete(rack)
    db.commit()


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
