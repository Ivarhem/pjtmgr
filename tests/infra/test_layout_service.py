from __future__ import annotations

import pytest

from app.core.exceptions import BusinessRuleError, DuplicateError
from app.modules.common.models.partner import Partner
from app.modules.infra.schemas.center import CenterCreate, CenterUpdate
from app.modules.infra.schemas.rack import RackCreate, RackUpdate
from app.modules.infra.schemas.room import RoomCreate, RoomUpdate
from app.modules.infra.services.layout_service import (
    create_center,
    create_rack,
    create_room,
    delete_center,
    delete_room,
    list_centers,
    list_racks,
    list_rooms,
    update_center,
    update_rack,
    update_room,
)


def _make_admin_user(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="layout_admin", name="Layout Admin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_create_center_creates_default_main_room(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = Partner(partner_code="L101", name="레이아웃고객")
    db_session.add(partner)
    db_session.commit()
    db_session.refresh(partner)

    center = create_center(
        db_session,
        CenterCreate(partner_id=partner.id, center_name="A센터"),
        admin,
    )

    assert center.center_code == "CTR-001"
    rooms = list_rooms(db_session, center.id)
    assert len(rooms) == 1
    assert rooms[0]["room_code"] == "MAIN"


def test_create_room_and_rack(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = Partner(partner_code="L102", name="레이아웃고객2")
    db_session.add(partner)
    db_session.commit()
    db_session.refresh(partner)

    center = create_center(
        db_session,
        CenterCreate(partner_id=partner.id, center_name="B센터"),
        admin,
    )
    room = create_room(
        db_session,
        RoomCreate(center_id=center.id, room_name="네트워크실"),
        admin,
    )
    rack = create_rack(
        db_session,
        RackCreate(room_id=room.id, rack_name="Firewall Rack", total_units=42),
        admin,
    )

    centers = list_centers(db_session, partner.id)
    rooms = list_rooms(db_session, center.id)
    racks = list_racks(db_session, room.id)
    assert room.room_code == "ROOM-001"
    assert rack.rack_code == "RACK-001"
    assert centers[0]["room_count"] == 2
    assert centers[0]["rack_count"] == 1
    assert rooms[1]["rack_count"] == 1
    assert racks[0]["rack_code"] == "RACK-001"


def test_duplicate_center_code_rejected(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = Partner(partner_code="L103", name="레이아웃고객3")
    db_session.add(partner)
    db_session.commit()
    db_session.refresh(partner)

    create_center(
        db_session,
        CenterCreate(partner_id=partner.id, center_code="IDC-A", center_name="A센터"),
        admin,
    )
    with pytest.raises(DuplicateError):
        create_center(
            db_session,
            CenterCreate(partner_id=partner.id, center_code="IDC-A", center_name="A센터2"),
            admin,
        )


def test_delete_center_with_rooms_rejected(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = Partner(partner_code="L104", name="레이아웃고객4")
    db_session.add(partner)
    db_session.commit()
    db_session.refresh(partner)

    center = create_center(
        db_session,
        CenterCreate(partner_id=partner.id, center_name="C센터"),
        admin,
    )

    with pytest.raises(BusinessRuleError):
        delete_center(db_session, center.id, admin)


def test_delete_room_with_racks_rejected(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = Partner(partner_code="L105", name="레이아웃고객5")
    db_session.add(partner)
    db_session.commit()
    db_session.refresh(partner)

    center = create_center(
        db_session,
        CenterCreate(partner_id=partner.id, center_name="D센터"),
        admin,
    )
    room = list_rooms(db_session, center.id)[0]
    create_rack(
        db_session,
        RackCreate(room_id=room["id"], total_units=42),
        admin,
    )

    with pytest.raises(BusinessRuleError):
        delete_room(db_session, room["id"], admin)


def test_update_center_room_rack(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = Partner(partner_code="L106", name="레이아웃고객6")
    db_session.add(partner)
    db_session.commit()
    db_session.refresh(partner)

    center = create_center(
        db_session,
        CenterCreate(partner_id=partner.id, center_name="E센터"),
        admin,
    )
    room = list_rooms(db_session, center.id)[0]
    rack = create_rack(
        db_session,
        RackCreate(room_id=room["id"], total_units=42),
        admin,
    )

    updated_center = update_center(db_session, center.id, CenterUpdate(center_name="E센터-수정"), admin)
    updated_room = update_room(db_session, room["id"], RoomUpdate(room_name="기본 전산실-수정"), admin)
    updated_rack = update_rack(db_session, rack.id, RackUpdate(rack_name="Core Rack", total_units=45), admin)

    assert updated_center.center_name == "E센터-수정"
    assert updated_room.room_name == "기본 전산실-수정"
    assert updated_rack.rack_name == "Core Rack"
    assert updated_rack.total_units == 45
