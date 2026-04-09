# inframgr Tests Reference
# Generated for migration reference - 2026-03-18

# ============================================
# FILE: tests/conftest.py
# ============================================
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base


@pytest.fixture
def db_session(tmp_path: Path) -> Generator[Session, None, None]:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


# ============================================
# FILE: tests/test_asset_contact_service.py
# ============================================
from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.core.exceptions import DuplicateError, NotFoundError
from app.schemas.asset import AssetCreate
from app.schemas.asset_contact import AssetContactCreate, AssetContactUpdate
from app.schemas.contact import ContactCreate
from app.schemas.partner import PartnerCreate
from app.schemas.project import ProjectCreate
from app.services.asset_service import create_asset
from app.services.partner_service import (
    create_asset_contact,
    create_contact,
    create_partner,
    delete_asset_contact,
    get_asset_contact,
    list_asset_contacts,
    update_asset_contact,
)
from app.services.project_service import create_project


@dataclass
class _UserStub:
    login_id: str
    name: str
    role: str


def _admin() -> _UserStub:
    return _UserStub(login_id="admin", name="Admin", role="admin")


def _setup(db):
    project = create_project(
        db, ProjectCreate(project_code="PRJ-001", project_name="Test", client_name="Client"), _admin()
    )
    asset = create_asset(
        db, AssetCreate(project_id=project.id, asset_name="SRV-01", asset_type="server"), _admin()
    )
    partner = create_partner(
        db, PartnerCreate(project_id=project.id, partner_name="ABC Corp", partner_type="supplier"), _admin()
    )
    contact = create_contact(
        db, ContactCreate(partner_id=partner.id, name="홍길동"), _admin()
    )
    return project, asset, partner, contact


def test_create_and_list_asset_contacts(db_session) -> None:
    _, asset, _, contact = _setup(db_session)

    create_asset_contact(
        db_session,
        AssetContactCreate(asset_id=asset.id, contact_id=contact.id, role="운영담당"),
        _admin(),
    )

    acs = list_asset_contacts(db_session, asset.id)
    assert len(acs) == 1
    assert acs[0].role == "운영담당"


def test_create_asset_contact_rejects_duplicate(db_session) -> None:
    _, asset, _, contact = _setup(db_session)

    create_asset_contact(
        db_session,
        AssetContactCreate(asset_id=asset.id, contact_id=contact.id, role="운영담당"),
        _admin(),
    )

    with pytest.raises(DuplicateError):
        create_asset_contact(
            db_session,
            AssetContactCreate(asset_id=asset.id, contact_id=contact.id, role="운영담당"),
            _admin(),
        )


def test_same_contact_different_roles_allowed(db_session) -> None:
    _, asset, _, contact = _setup(db_session)

    create_asset_contact(
        db_session,
        AssetContactCreate(asset_id=asset.id, contact_id=contact.id, role="운영담당"),
        _admin(),
    )
    create_asset_contact(
        db_session,
        AssetContactCreate(asset_id=asset.id, contact_id=contact.id, role="보안담당"),
        _admin(),
    )

    acs = list_asset_contacts(db_session, asset.id)
    assert len(acs) == 2


def test_update_asset_contact(db_session) -> None:
    _, asset, _, contact = _setup(db_session)

    ac = create_asset_contact(
        db_session,
        AssetContactCreate(asset_id=asset.id, contact_id=contact.id, role="운영담당"),
        _admin(),
    )

    updated = update_asset_contact(
        db_session, ac.id, AssetContactUpdate(role="보안담당"), _admin()
    )

    assert updated.role == "보안담당"


def test_delete_asset_contact(db_session) -> None:
    _, asset, _, contact = _setup(db_session)

    ac = create_asset_contact(
        db_session,
        AssetContactCreate(asset_id=asset.id, contact_id=contact.id, role="운영담당"),
        _admin(),
    )

    delete_asset_contact(db_session, ac.id, _admin())

    with pytest.raises(NotFoundError):
        get_asset_contact(db_session, ac.id)


# ============================================
# FILE: tests/test_asset_service.py
# ============================================
from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.core.exceptions import DuplicateError, NotFoundError
from app.schemas.asset import AssetCreate, AssetUpdate
from app.schemas.project import ProjectCreate
from app.services.asset_service import create_asset, delete_asset, list_assets, update_asset
from app.services.project_service import create_project


@dataclass
class _UserStub:
    login_id: str
    name: str
    role: str


def _admin_user() -> _UserStub:
    return _UserStub(login_id="admin", name="Admin", role="admin")


def test_create_and_list_assets(db_session) -> None:
    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Inventory", client_name="Client A"),
        _admin_user(),
    )

    create_asset(
        db_session,
        AssetCreate(project_id=project.id, asset_name="APP-01", asset_type="server"),
        _admin_user(),
    )

    assets = list_assets(db_session, project.id)

    assert len(assets) == 1
    assert assets[0].asset_name == "APP-01"


def test_create_asset_requires_existing_project(db_session) -> None:
    with pytest.raises(NotFoundError):
        create_asset(
            db_session,
            AssetCreate(project_id=999, asset_name="APP-01", asset_type="server"),
            _admin_user(),
        )


def test_create_asset_rejects_duplicate_name_in_same_project(db_session) -> None:
    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Inventory", client_name="Client A"),
        _admin_user(),
    )
    payload = AssetCreate(project_id=project.id, asset_name="APP-01", asset_type="server")
    create_asset(db_session, payload, _admin_user())

    with pytest.raises(DuplicateError):
        create_asset(db_session, payload, _admin_user())


def test_update_and_delete_asset(db_session) -> None:
    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Inventory", client_name="Client A"),
        _admin_user(),
    )
    asset = create_asset(
        db_session,
        AssetCreate(project_id=project.id, asset_name="APP-01", asset_type="server"),
        _admin_user(),
    )

    updated = update_asset(
        db_session,
        asset.id,
        AssetUpdate(status="active", location="Seoul"),
        _admin_user(),
    )
    delete_asset(db_session, asset.id, _admin_user())

    assert updated.status == "active"
    assert updated.location == "Seoul"
    assert list_assets(db_session, project.id) == []


# ============================================
# FILE: tests/test_network_service.py
# ============================================
from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError
from app.schemas.asset import AssetCreate
from app.schemas.asset_ip import AssetIPCreate, AssetIPUpdate
from app.schemas.ip_subnet import IpSubnetCreate, IpSubnetUpdate
from app.schemas.project import ProjectCreate
from app.services.asset_service import create_asset
from app.services.network_service import (
    create_asset_ip,
    create_subnet,
    delete_asset_ip,
    delete_subnet,
    get_asset_ip,
    get_subnet,
    list_asset_ips,
    list_project_ips,
    list_subnets,
    update_asset_ip,
    update_subnet,
)
from app.services.project_service import create_project


@dataclass
class _UserStub:
    login_id: str
    name: str
    role: str


def _admin() -> _UserStub:
    return _UserStub(login_id="admin", name="Admin", role="admin")


def _make_project(db):
    return create_project(
        db,
        ProjectCreate(project_code="PRJ-001", project_name="Test", client_name="Client"),
        _admin(),
    )


def _make_asset(db, project_id: int, name: str = "SRV-01"):
    return create_asset(
        db,
        AssetCreate(project_id=project_id, asset_name=name, asset_type="server"),
        _admin(),
    )


# ── IpSubnet tests ──


def test_create_and_list_subnets(db_session) -> None:
    project = _make_project(db_session)

    create_subnet(
        db_session,
        IpSubnetCreate(
            project_id=project.id,
            name="서비스망-A",
            subnet="10.10.1.0/24",
            role="service",
            region="서울",
        ),
        _admin(),
    )
    create_subnet(
        db_session,
        IpSubnetCreate(
            project_id=project.id,
            name="관리망-A",
            subnet="10.10.2.0/24",
            role="management",
        ),
        _admin(),
    )

    subnets = list_subnets(db_session, project.id)
    assert len(subnets) == 2


def test_create_subnet_requires_existing_project(db_session) -> None:
    with pytest.raises(NotFoundError):
        create_subnet(
            db_session,
            IpSubnetCreate(project_id=9999, name="test", subnet="10.0.0.0/24"),
            _admin(),
        )


def test_update_subnet(db_session) -> None:
    project = _make_project(db_session)
    subnet = create_subnet(
        db_session,
        IpSubnetCreate(project_id=project.id, name="서비스망", subnet="10.10.1.0/24"),
        _admin(),
    )

    updated = update_subnet(
        db_session,
        subnet.id,
        IpSubnetUpdate(region="부산DR", floor="3F", counterpart="XX은행 부산지점"),
        _admin(),
    )

    assert updated.region == "부산DR"
    assert updated.floor == "3F"
    assert updated.counterpart == "XX은행 부산지점"


def test_delete_subnet_blocked_with_assigned_ips(db_session) -> None:
    project = _make_project(db_session)
    subnet = create_subnet(
        db_session,
        IpSubnetCreate(project_id=project.id, name="서비스망", subnet="10.10.1.0/24"),
        _admin(),
    )
    asset = _make_asset(db_session, project.id)
    create_asset_ip(
        db_session,
        AssetIPCreate(asset_id=asset.id, ip_subnet_id=subnet.id, ip_address="10.10.1.10"),
        _admin(),
    )

    with pytest.raises(BusinessRuleError):
        delete_subnet(db_session, subnet.id, _admin())


def test_delete_subnet_without_ips(db_session) -> None:
    project = _make_project(db_session)
    subnet = create_subnet(
        db_session,
        IpSubnetCreate(project_id=project.id, name="서비스망", subnet="10.10.1.0/24"),
        _admin(),
    )

    delete_subnet(db_session, subnet.id, _admin())

    with pytest.raises(NotFoundError):
        get_subnet(db_session, subnet.id)


# ── AssetIP tests ──


def test_create_and_list_asset_ips(db_session) -> None:
    project = _make_project(db_session)
    asset = _make_asset(db_session, project.id)

    create_asset_ip(
        db_session,
        AssetIPCreate(asset_id=asset.id, ip_address="10.10.1.10", ip_type="service"),
        _admin(),
    )
    create_asset_ip(
        db_session,
        AssetIPCreate(asset_id=asset.id, ip_address="10.10.2.10", ip_type="management"),
        _admin(),
    )

    ips = list_asset_ips(db_session, asset.id)
    assert len(ips) == 2


def test_create_asset_ip_requires_existing_asset(db_session) -> None:
    with pytest.raises(NotFoundError):
        create_asset_ip(
            db_session,
            AssetIPCreate(asset_id=9999, ip_address="10.10.1.10"),
            _admin(),
        )


def test_create_asset_ip_with_subnet_reference(db_session) -> None:
    project = _make_project(db_session)
    asset = _make_asset(db_session, project.id)
    subnet = create_subnet(
        db_session,
        IpSubnetCreate(project_id=project.id, name="서비스망", subnet="10.10.1.0/24"),
        _admin(),
    )

    ip = create_asset_ip(
        db_session,
        AssetIPCreate(asset_id=asset.id, ip_subnet_id=subnet.id, ip_address="10.10.1.10"),
        _admin(),
    )

    assert ip.ip_subnet_id == subnet.id


def test_create_asset_ip_rejects_nonexistent_subnet(db_session) -> None:
    project = _make_project(db_session)
    asset = _make_asset(db_session, project.id)

    with pytest.raises(NotFoundError):
        create_asset_ip(
            db_session,
            AssetIPCreate(asset_id=asset.id, ip_subnet_id=9999, ip_address="10.10.1.10"),
            _admin(),
        )


def test_ip_duplicate_rejected_within_same_project(db_session) -> None:
    project = _make_project(db_session)
    asset1 = _make_asset(db_session, project.id, "SRV-01")
    asset2 = _make_asset(db_session, project.id, "SRV-02")

    create_asset_ip(
        db_session,
        AssetIPCreate(asset_id=asset1.id, ip_address="10.10.1.10"),
        _admin(),
    )

    with pytest.raises(DuplicateError):
        create_asset_ip(
            db_session,
            AssetIPCreate(asset_id=asset2.id, ip_address="10.10.1.10"),
            _admin(),
        )


def test_ip_duplicate_allowed_across_projects(db_session) -> None:
    project1 = _make_project(db_session)
    project2 = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-002", project_name="Test2", client_name="Client"),
        _admin(),
    )
    asset1 = _make_asset(db_session, project1.id, "SRV-01")
    asset2 = create_asset(
        db_session,
        AssetCreate(project_id=project2.id, asset_name="SRV-01", asset_type="server"),
        _admin(),
    )

    create_asset_ip(
        db_session,
        AssetIPCreate(asset_id=asset1.id, ip_address="10.10.1.10"),
        _admin(),
    )
    ip2 = create_asset_ip(
        db_session,
        AssetIPCreate(asset_id=asset2.id, ip_address="10.10.1.10"),
        _admin(),
    )

    assert ip2.ip_address == "10.10.1.10"


def test_list_project_ips(db_session) -> None:
    project = _make_project(db_session)
    asset1 = _make_asset(db_session, project.id, "SRV-01")
    asset2 = _make_asset(db_session, project.id, "SRV-02")

    create_asset_ip(db_session, AssetIPCreate(asset_id=asset1.id, ip_address="10.10.1.10"), _admin())
    create_asset_ip(db_session, AssetIPCreate(asset_id=asset2.id, ip_address="10.10.1.20"), _admin())

    all_ips = list_project_ips(db_session, project.id)
    assert len(all_ips) == 2


def test_update_asset_ip(db_session) -> None:
    project = _make_project(db_session)
    asset = _make_asset(db_session, project.id)
    ip = create_asset_ip(
        db_session,
        AssetIPCreate(asset_id=asset.id, ip_address="10.10.1.10"),
        _admin(),
    )

    updated = update_asset_ip(
        db_session,
        ip.id,
        AssetIPUpdate(ip_type="management", is_primary=True),
        _admin(),
    )

    assert updated.ip_type == "management"
    assert updated.is_primary is True


def test_update_asset_ip_rejects_duplicate_address(db_session) -> None:
    project = _make_project(db_session)
    asset = _make_asset(db_session, project.id)
    create_asset_ip(db_session, AssetIPCreate(asset_id=asset.id, ip_address="10.10.1.10"), _admin())
    ip2 = create_asset_ip(db_session, AssetIPCreate(asset_id=asset.id, ip_address="10.10.1.20"), _admin())

    with pytest.raises(DuplicateError):
        update_asset_ip(db_session, ip2.id, AssetIPUpdate(ip_address="10.10.1.10"), _admin())


def test_delete_asset_ip(db_session) -> None:
    project = _make_project(db_session)
    asset = _make_asset(db_session, project.id)
    ip = create_asset_ip(
        db_session,
        AssetIPCreate(asset_id=asset.id, ip_address="10.10.1.10"),
        _admin(),
    )

    delete_asset_ip(db_session, ip.id, _admin())

    with pytest.raises(NotFoundError):
        get_asset_ip(db_session, ip.id)


# ============================================
# FILE: tests/test_partner_service.py
# ============================================
from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.schemas.contact import ContactCreate, ContactUpdate
from app.schemas.partner import PartnerCreate, PartnerUpdate
from app.schemas.project import ProjectCreate
from app.services.partner_service import (
    create_contact,
    create_partner,
    delete_contact,
    delete_partner,
    get_contact,
    get_partner,
    list_contacts,
    list_partners,
    update_contact,
    update_partner,
)
from app.services.project_service import create_project


@dataclass
class _UserStub:
    login_id: str
    name: str
    role: str


def _admin() -> _UserStub:
    return _UserStub(login_id="admin", name="Admin", role="admin")


def _make_project(db):
    return create_project(
        db,
        ProjectCreate(project_code="PRJ-001", project_name="Test", client_name="Client"),
        _admin(),
    )


# ── Partner tests ──


def test_create_and_list_partners(db_session) -> None:
    project = _make_project(db_session)

    create_partner(
        db_session,
        PartnerCreate(project_id=project.id, partner_name="ABC Corp", partner_type="supplier"),
        _admin(),
    )
    create_partner(
        db_session,
        PartnerCreate(project_id=project.id, partner_name="XYZ Telecom", partner_type="telecommunications"),
        _admin(),
    )

    partners = list_partners(db_session, project.id)
    assert len(partners) == 2


def test_create_partner_requires_existing_project(db_session) -> None:
    with pytest.raises(NotFoundError):
        create_partner(
            db_session,
            PartnerCreate(project_id=9999, partner_name="Test", partner_type="supplier"),
            _admin(),
        )


def test_update_partner(db_session) -> None:
    project = _make_project(db_session)
    partner = create_partner(
        db_session,
        PartnerCreate(project_id=project.id, partner_name="ABC Corp", partner_type="supplier"),
        _admin(),
    )

    updated = update_partner(
        db_session,
        partner.id,
        PartnerUpdate(partner_name="ABC Corporation", contact_phone="02-1234-5678"),
        _admin(),
    )

    assert updated.partner_name == "ABC Corporation"
    assert updated.contact_phone == "02-1234-5678"


def test_delete_partner_blocked_with_contacts(db_session) -> None:
    project = _make_project(db_session)
    partner = create_partner(
        db_session,
        PartnerCreate(project_id=project.id, partner_name="ABC Corp", partner_type="supplier"),
        _admin(),
    )
    create_contact(
        db_session,
        ContactCreate(partner_id=partner.id, name="홍길동"),
        _admin(),
    )

    with pytest.raises(BusinessRuleError):
        delete_partner(db_session, partner.id, _admin())


def test_delete_partner_without_contacts(db_session) -> None:
    project = _make_project(db_session)
    partner = create_partner(
        db_session,
        PartnerCreate(project_id=project.id, partner_name="ABC Corp", partner_type="supplier"),
        _admin(),
    )

    delete_partner(db_session, partner.id, _admin())

    with pytest.raises(NotFoundError):
        get_partner(db_session, partner.id)


# ── Contact tests ──


def test_create_and_list_contacts(db_session) -> None:
    project = _make_project(db_session)
    partner = create_partner(
        db_session,
        PartnerCreate(project_id=project.id, partner_name="ABC Corp", partner_type="supplier"),
        _admin(),
    )

    create_contact(
        db_session,
        ContactCreate(partner_id=partner.id, name="홍길동", role="PM", phone="010-1111-2222"),
        _admin(),
    )
    create_contact(
        db_session,
        ContactCreate(partner_id=partner.id, name="김철수", role="엔지니어"),
        _admin(),
    )

    contacts = list_contacts(db_session, partner.id)
    assert len(contacts) == 2


def test_create_contact_requires_existing_partner(db_session) -> None:
    with pytest.raises(NotFoundError):
        create_contact(
            db_session,
            ContactCreate(partner_id=9999, name="홍길동"),
            _admin(),
        )


def test_update_contact(db_session) -> None:
    project = _make_project(db_session)
    partner = create_partner(
        db_session,
        PartnerCreate(project_id=project.id, partner_name="ABC Corp", partner_type="supplier"),
        _admin(),
    )
    contact = create_contact(
        db_session,
        ContactCreate(partner_id=partner.id, name="홍길동"),
        _admin(),
    )

    updated = update_contact(
        db_session,
        contact.id,
        ContactUpdate(email="hong@abc.com", emergency_phone="010-9999-0000"),
        _admin(),
    )

    assert updated.email == "hong@abc.com"
    assert updated.emergency_phone == "010-9999-0000"


def test_delete_contact(db_session) -> None:
    project = _make_project(db_session)
    partner = create_partner(
        db_session,
        PartnerCreate(project_id=project.id, partner_name="ABC Corp", partner_type="supplier"),
        _admin(),
    )
    contact = create_contact(
        db_session,
        ContactCreate(partner_id=partner.id, name="홍길동"),
        _admin(),
    )

    delete_contact(db_session, contact.id, _admin())

    with pytest.raises(NotFoundError):
        get_contact(db_session, contact.id)


# ============================================
# FILE: tests/test_phase_service.py
# ============================================
from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError
from app.schemas.project import ProjectCreate
from app.schemas.project_deliverable import ProjectDeliverableCreate, ProjectDeliverableUpdate
from app.schemas.project_phase import ProjectPhaseCreate, ProjectPhaseUpdate
from app.services.phase_service import (
    create_deliverable,
    create_phase,
    delete_deliverable,
    delete_phase,
    get_deliverable,
    get_phase,
    list_deliverables,
    list_phases,
    update_deliverable,
    update_phase,
)
from app.services.project_service import create_project


@dataclass
class _UserStub:
    login_id: str
    name: str
    role: str


def _admin_user() -> _UserStub:
    return _UserStub(login_id="admin", name="Admin", role="admin")


def _make_project(db_session):
    return create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Test Project", client_name="Client A"),
        _admin_user(),
    )


# ── ProjectPhase tests ──


def test_create_and_list_phases(db_session) -> None:
    project = _make_project(db_session)

    create_phase(
        db_session,
        ProjectPhaseCreate(project_id=project.id, phase_type="analysis"),
        _admin_user(),
    )
    create_phase(
        db_session,
        ProjectPhaseCreate(project_id=project.id, phase_type="design"),
        _admin_user(),
    )

    phases = list_phases(db_session, project.id)
    assert len(phases) == 2
    assert phases[0].phase_type == "analysis"
    assert phases[1].phase_type == "design"


def test_create_phase_requires_existing_project(db_session) -> None:
    with pytest.raises(NotFoundError):
        create_phase(
            db_session,
            ProjectPhaseCreate(project_id=9999, phase_type="analysis"),
            _admin_user(),
        )


def test_create_phase_rejects_duplicate_type_in_same_project(db_session) -> None:
    project = _make_project(db_session)

    create_phase(
        db_session,
        ProjectPhaseCreate(project_id=project.id, phase_type="analysis"),
        _admin_user(),
    )

    with pytest.raises(DuplicateError):
        create_phase(
            db_session,
            ProjectPhaseCreate(project_id=project.id, phase_type="analysis"),
            _admin_user(),
        )


def test_update_phase(db_session) -> None:
    project = _make_project(db_session)
    phase = create_phase(
        db_session,
        ProjectPhaseCreate(project_id=project.id, phase_type="analysis"),
        _admin_user(),
    )

    updated = update_phase(
        db_session,
        phase.id,
        ProjectPhaseUpdate(status="in_progress", task_scope="Full analysis"),
        _admin_user(),
    )

    assert updated.status == "in_progress"
    assert updated.task_scope == "Full analysis"


def test_delete_phase_blocked_with_deliverables(db_session) -> None:
    project = _make_project(db_session)
    phase = create_phase(
        db_session,
        ProjectPhaseCreate(project_id=project.id, phase_type="analysis"),
        _admin_user(),
    )
    create_deliverable(
        db_session,
        ProjectDeliverableCreate(project_phase_id=phase.id, name="Report"),
        _admin_user(),
    )

    with pytest.raises(BusinessRuleError):
        delete_phase(db_session, phase.id, _admin_user())


def test_delete_phase_without_deliverables(db_session) -> None:
    project = _make_project(db_session)
    phase = create_phase(
        db_session,
        ProjectPhaseCreate(project_id=project.id, phase_type="analysis"),
        _admin_user(),
    )

    delete_phase(db_session, phase.id, _admin_user())

    with pytest.raises(NotFoundError):
        get_phase(db_session, phase.id)


# ── ProjectDeliverable tests ──


def test_create_and_list_deliverables(db_session) -> None:
    project = _make_project(db_session)
    phase = create_phase(
        db_session,
        ProjectPhaseCreate(project_id=project.id, phase_type="analysis"),
        _admin_user(),
    )

    create_deliverable(
        db_session,
        ProjectDeliverableCreate(project_phase_id=phase.id, name="Analysis Report"),
        _admin_user(),
    )
    create_deliverable(
        db_session,
        ProjectDeliverableCreate(project_phase_id=phase.id, name="Requirements Doc"),
        _admin_user(),
    )

    deliverables = list_deliverables(db_session, phase.id)
    assert len(deliverables) == 2
    assert deliverables[0].name == "Analysis Report"


def test_create_deliverable_requires_existing_phase(db_session) -> None:
    with pytest.raises(NotFoundError):
        create_deliverable(
            db_session,
            ProjectDeliverableCreate(project_phase_id=9999, name="Report"),
            _admin_user(),
        )


def test_update_deliverable(db_session) -> None:
    project = _make_project(db_session)
    phase = create_phase(
        db_session,
        ProjectPhaseCreate(project_id=project.id, phase_type="analysis"),
        _admin_user(),
    )
    deliverable = create_deliverable(
        db_session,
        ProjectDeliverableCreate(project_phase_id=phase.id, name="Report"),
        _admin_user(),
    )

    updated = update_deliverable(
        db_session,
        deliverable.id,
        ProjectDeliverableUpdate(is_submitted=True, note="Submitted to client"),
        _admin_user(),
    )

    assert updated.is_submitted is True
    assert updated.note == "Submitted to client"


def test_delete_deliverable(db_session) -> None:
    project = _make_project(db_session)
    phase = create_phase(
        db_session,
        ProjectPhaseCreate(project_id=project.id, phase_type="analysis"),
        _admin_user(),
    )
    deliverable = create_deliverable(
        db_session,
        ProjectDeliverableCreate(project_phase_id=phase.id, name="Report"),
        _admin_user(),
    )

    delete_deliverable(db_session, deliverable.id, _admin_user())

    with pytest.raises(NotFoundError):
        get_deliverable(db_session, deliverable.id)


# ============================================
# FILE: tests/test_policy_service.py
# ============================================
from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError, PermissionDeniedError
from app.schemas.asset import AssetCreate
from app.schemas.policy_assignment import PolicyAssignmentCreate, PolicyAssignmentUpdate
from app.schemas.policy_definition import PolicyDefinitionCreate, PolicyDefinitionUpdate
from app.schemas.project import ProjectCreate
from app.services.asset_service import create_asset
from app.services.policy_service import (
    create_assignment,
    create_policy,
    delete_assignment,
    delete_policy,
    get_assignment,
    get_policy,
    list_assignments,
    list_policies,
    update_assignment,
    update_policy,
)
from app.services.project_service import create_project


@dataclass
class _UserStub:
    login_id: str
    name: str
    role: str


def _admin() -> _UserStub:
    return _UserStub(login_id="admin", name="Admin", role="admin")


def _user() -> _UserStub:
    return _UserStub(login_id="user1", name="User", role="user")


# ── PolicyDefinition tests ──


def test_create_and_list_policies(db_session) -> None:
    create_policy(
        db_session,
        PolicyDefinitionCreate(policy_code="SEC-001", policy_name="방화벽 정책", category="보안"),
        _admin(),
    )
    create_policy(
        db_session,
        PolicyDefinitionCreate(policy_code="SEC-002", policy_name="백업 정책", category="운영"),
        _admin(),
    )

    policies = list_policies(db_session)
    assert len(policies) == 2
    assert policies[0].policy_code == "SEC-001"


def test_create_policy_rejects_duplicate_code(db_session) -> None:
    create_policy(
        db_session,
        PolicyDefinitionCreate(policy_code="SEC-001", policy_name="방화벽 정책", category="보안"),
        _admin(),
    )

    with pytest.raises(DuplicateError):
        create_policy(
            db_session,
            PolicyDefinitionCreate(policy_code="SEC-001", policy_name="Other", category="보안"),
            _admin(),
        )


def test_create_policy_requires_admin(db_session) -> None:
    with pytest.raises(PermissionDeniedError):
        create_policy(
            db_session,
            PolicyDefinitionCreate(policy_code="SEC-001", policy_name="방화벽 정책", category="보안"),
            _user(),
        )


def test_update_policy(db_session) -> None:
    policy = create_policy(
        db_session,
        PolicyDefinitionCreate(policy_code="SEC-001", policy_name="방화벽 정책", category="보안"),
        _admin(),
    )

    updated = update_policy(
        db_session,
        policy.id,
        PolicyDefinitionUpdate(policy_name="방화벽 정책 v2", is_active=False),
        _admin(),
    )

    assert updated.policy_name == "방화벽 정책 v2"
    assert updated.is_active is False


def test_delete_policy_blocked_with_assignments(db_session) -> None:
    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Test", client_name="Client"),
        _admin(),
    )
    policy = create_policy(
        db_session,
        PolicyDefinitionCreate(policy_code="SEC-001", policy_name="방화벽 정책", category="보안"),
        _admin(),
    )
    create_assignment(
        db_session,
        PolicyAssignmentCreate(project_id=project.id, policy_definition_id=policy.id),
        _admin(),
    )

    with pytest.raises(BusinessRuleError):
        delete_policy(db_session, policy.id, _admin())


def test_delete_policy_without_assignments(db_session) -> None:
    policy = create_policy(
        db_session,
        PolicyDefinitionCreate(policy_code="SEC-001", policy_name="방화벽 정책", category="보안"),
        _admin(),
    )

    delete_policy(db_session, policy.id, _admin())

    with pytest.raises(NotFoundError):
        get_policy(db_session, policy.id)


# ── PolicyAssignment tests ──


def test_create_and_list_assignments(db_session) -> None:
    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Test", client_name="Client"),
        _admin(),
    )
    policy = create_policy(
        db_session,
        PolicyDefinitionCreate(policy_code="SEC-001", policy_name="방화벽 정책", category="보안"),
        _admin(),
    )

    create_assignment(
        db_session,
        PolicyAssignmentCreate(project_id=project.id, policy_definition_id=policy.id),
        _admin(),
    )

    assignments = list_assignments(db_session, project.id)
    assert len(assignments) == 1
    assert assignments[0].status == "not_checked"


def test_create_assignment_with_asset(db_session) -> None:
    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Test", client_name="Client"),
        _admin(),
    )
    asset = create_asset(
        db_session,
        AssetCreate(project_id=project.id, asset_name="SRV-01", asset_type="server"),
        _admin(),
    )
    policy = create_policy(
        db_session,
        PolicyDefinitionCreate(policy_code="SEC-001", policy_name="방화벽 정책", category="보안"),
        _admin(),
    )

    assignment = create_assignment(
        db_session,
        PolicyAssignmentCreate(
            project_id=project.id,
            asset_id=asset.id,
            policy_definition_id=policy.id,
        ),
        _admin(),
    )

    assert assignment.asset_id == asset.id


def test_create_assignment_rejects_asset_from_other_project(db_session) -> None:
    project1 = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Test", client_name="Client"),
        _admin(),
    )
    project2 = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-002", project_name="Other", client_name="Client"),
        _admin(),
    )
    asset = create_asset(
        db_session,
        AssetCreate(project_id=project2.id, asset_name="SRV-01", asset_type="server"),
        _admin(),
    )
    policy = create_policy(
        db_session,
        PolicyDefinitionCreate(policy_code="SEC-001", policy_name="방화벽 정책", category="보안"),
        _admin(),
    )

    with pytest.raises(BusinessRuleError):
        create_assignment(
            db_session,
            PolicyAssignmentCreate(
                project_id=project1.id,
                asset_id=asset.id,
                policy_definition_id=policy.id,
            ),
            _admin(),
        )


def test_create_assignment_rejects_duplicate(db_session) -> None:
    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Test", client_name="Client"),
        _admin(),
    )
    policy = create_policy(
        db_session,
        PolicyDefinitionCreate(policy_code="SEC-001", policy_name="방화벽 정책", category="보안"),
        _admin(),
    )

    create_assignment(
        db_session,
        PolicyAssignmentCreate(project_id=project.id, policy_definition_id=policy.id),
        _admin(),
    )

    with pytest.raises(DuplicateError):
        create_assignment(
            db_session,
            PolicyAssignmentCreate(project_id=project.id, policy_definition_id=policy.id),
            _admin(),
        )


def test_update_assignment(db_session) -> None:
    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Test", client_name="Client"),
        _admin(),
    )
    policy = create_policy(
        db_session,
        PolicyDefinitionCreate(policy_code="SEC-001", policy_name="방화벽 정책", category="보안"),
        _admin(),
    )
    assignment = create_assignment(
        db_session,
        PolicyAssignmentCreate(project_id=project.id, policy_definition_id=policy.id),
        _admin(),
    )

    updated = update_assignment(
        db_session,
        assignment.id,
        PolicyAssignmentUpdate(status="compliant", checked_by="admin", evidence_note="확인 완료"),
        _admin(),
    )

    assert updated.status == "compliant"
    assert updated.checked_by == "admin"


def test_delete_assignment(db_session) -> None:
    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Test", client_name="Client"),
        _admin(),
    )
    policy = create_policy(
        db_session,
        PolicyDefinitionCreate(policy_code="SEC-001", policy_name="방화벽 정책", category="보안"),
        _admin(),
    )
    assignment = create_assignment(
        db_session,
        PolicyAssignmentCreate(project_id=project.id, policy_definition_id=policy.id),
        _admin(),
    )

    delete_assignment(db_session, assignment.id, _admin())

    with pytest.raises(NotFoundError):
        get_assignment(db_session, assignment.id)


# ============================================
# FILE: tests/test_port_map_service.py
# ============================================
from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.schemas.asset import AssetCreate
from app.schemas.port_map import PortMapCreate, PortMapUpdate
from app.schemas.project import ProjectCreate
from app.services.asset_service import create_asset
from app.services.network_service import (
    create_port_map,
    delete_port_map,
    get_port_map,
    list_port_maps,
    update_port_map,
)
from app.services.project_service import create_project


@dataclass
class _UserStub:
    login_id: str
    name: str
    role: str


def _admin() -> _UserStub:
    return _UserStub(login_id="admin", name="Admin", role="admin")


def _make_project(db):
    return create_project(
        db,
        ProjectCreate(project_code="PRJ-001", project_name="Test", client_name="Client"),
        _admin(),
    )


def _make_asset(db, project_id: int, name: str = "SRV-01"):
    return create_asset(
        db,
        AssetCreate(project_id=project_id, asset_name=name, asset_type="server"),
        _admin(),
    )


def test_create_and_list_port_maps(db_session) -> None:
    project = _make_project(db_session)
    src = _make_asset(db_session, project.id, "WEB-01")
    dst = _make_asset(db_session, project.id, "DB-01")

    create_port_map(
        db_session,
        PortMapCreate(
            project_id=project.id,
            src_asset_id=src.id,
            src_ip="10.10.1.10",
            dst_asset_id=dst.id,
            dst_ip="10.10.1.20",
            protocol="tcp",
            port=5432,
            purpose="PostgreSQL",
        ),
        _admin(),
    )

    maps = list_port_maps(db_session, project.id)
    assert len(maps) == 1
    assert maps[0].port == 5432
    assert maps[0].purpose == "PostgreSQL"


def test_create_port_map_requires_existing_project(db_session) -> None:
    with pytest.raises(NotFoundError):
        create_port_map(
            db_session,
            PortMapCreate(project_id=9999, port=443),
            _admin(),
        )


def test_create_port_map_with_nullable_assets(db_session) -> None:
    """외부 구간 표현: src/dst asset 없이 IP만 지정."""
    project = _make_project(db_session)

    pm = create_port_map(
        db_session,
        PortMapCreate(
            project_id=project.id,
            src_ip="203.0.113.1",
            dst_ip="10.10.1.10",
            port=443,
            purpose="External HTTPS",
        ),
        _admin(),
    )

    assert pm.src_asset_id is None
    assert pm.dst_asset_id is None
    assert pm.src_ip == "203.0.113.1"


def test_create_port_map_rejects_asset_from_other_project(db_session) -> None:
    project1 = _make_project(db_session)
    project2 = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-002", project_name="Other", client_name="Client"),
        _admin(),
    )
    asset_other = _make_asset(db_session, project2.id, "SRV-OTHER")

    with pytest.raises(BusinessRuleError):
        create_port_map(
            db_session,
            PortMapCreate(
                project_id=project1.id,
                src_asset_id=asset_other.id,
                port=80,
            ),
            _admin(),
        )


def test_update_port_map(db_session) -> None:
    project = _make_project(db_session)
    pm = create_port_map(
        db_session,
        PortMapCreate(project_id=project.id, port=80, purpose="HTTP"),
        _admin(),
    )

    updated = update_port_map(
        db_session,
        pm.id,
        PortMapUpdate(port=443, protocol="tcp", purpose="HTTPS", status="approved"),
        _admin(),
    )

    assert updated.port == 443
    assert updated.purpose == "HTTPS"
    assert updated.status == "approved"


def test_delete_port_map(db_session) -> None:
    project = _make_project(db_session)
    pm = create_port_map(
        db_session,
        PortMapCreate(project_id=project.id, port=22, purpose="SSH"),
        _admin(),
    )

    delete_port_map(db_session, pm.id, _admin())

    with pytest.raises(NotFoundError):
        get_port_map(db_session, pm.id)


# ============================================
# FILE: tests/test_project_service.py
# ============================================
from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.core.exceptions import BusinessRuleError, DuplicateError
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.project_service import create_project, delete_project, list_projects, update_project


@dataclass
class _UserStub:
    login_id: str
    name: str
    role: str


def _admin_user() -> _UserStub:
    return _UserStub(login_id="admin", name="Admin", role="admin")


def test_create_and_list_projects(db_session) -> None:
    create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Inventory", client_name="Client A"),
        _admin_user(),
    )

    projects = list_projects(db_session)

    assert len(projects) == 1
    assert projects[0].project_code == "PRJ-001"


def test_create_project_rejects_duplicate_code(db_session) -> None:
    payload = ProjectCreate(project_code="PRJ-001", project_name="Inventory", client_name="Client A")
    create_project(db_session, payload, _admin_user())

    with pytest.raises(DuplicateError):
        create_project(db_session, payload, _admin_user())


def test_delete_project_with_assets_is_blocked(db_session) -> None:
    from app.schemas.asset import AssetCreate
    from app.services.asset_service import create_asset

    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Inventory", client_name="Client A"),
        _admin_user(),
    )
    create_asset(
        db_session,
        AssetCreate(project_id=project.id, asset_name="APP-01", asset_type="server"),
        _admin_user(),
    )

    with pytest.raises(BusinessRuleError):
        delete_project(db_session, project.id, _admin_user())


def test_update_project_changes_fields(db_session) -> None:
    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Inventory", client_name="Client A"),
        _admin_user(),
    )

    updated = update_project(
        db_session,
        project.id,
        ProjectUpdate(project_name="Updated Inventory", status="active"),
        _admin_user(),
    )

    assert updated.project_name == "Updated Inventory"
    assert updated.status == "active"


# ============================================
# FILE: tests/test_smoke.py
# ============================================
from app.core.config import settings


def test_settings_load() -> None:
    assert settings.app_name == "SI Project Inventory"


# ============================================
# FILE: tests/test_user_service.py
# ============================================
from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.core.auth.password import hash_password, verify_password
from app.core.auth.service import authenticate
from app.core.exceptions import DuplicateError, NotFoundError, PermissionDeniedError, UnauthorizedError
from app.modules.common.schemas.user import UserChangePassword, UserCreate, UserResetPassword, UserUpdate
from app.modules.common.services.user_service import (
    change_password,
    create_user,
    ensure_bootstrap_admin,
    get_user,
    get_user_by_login_id,
    list_users,
    reset_password,
    update_user,
)


@dataclass
class _UserStub:
    login_id: str
    name: str
    role: str


def _admin() -> _UserStub:
    return _UserStub(login_id="admin", name="Admin", role="admin")


def _user() -> _UserStub:
    return _UserStub(login_id="user1", name="User", role="user")


# ── User CRUD tests ──


def test_create_and_list_users(db_session) -> None:
    create_user(
        db_session,
        UserCreate(login_id="user1", name="User One", password="pass123"),
        _admin(),
    )

    users = list_users(db_session, _admin())
    assert len(users) == 1
    assert users[0].login_id == "user1"


def test_create_user_rejects_duplicate_login_id(db_session) -> None:
    create_user(
        db_session,
        UserCreate(login_id="user1", name="User One", password="pass123"),
        _admin(),
    )

    with pytest.raises(DuplicateError):
        create_user(
            db_session,
            UserCreate(login_id="user1", name="Another", password="pass456"),
            _admin(),
        )


def test_create_user_requires_admin(db_session) -> None:
    with pytest.raises(PermissionDeniedError):
        create_user(
            db_session,
            UserCreate(login_id="user1", name="User One", password="pass123"),
            _user(),
        )


def test_update_user(db_session) -> None:
    user = create_user(
        db_session,
        UserCreate(login_id="user1", name="User One", password="pass123"),
        _admin(),
    )

    updated = update_user(
        db_session,
        user.id,
        UserUpdate(name="Updated Name", is_active=False),
        _admin(),
    )

    assert updated.name == "Updated Name"
    assert updated.is_active is False


def test_password_hashing(db_session) -> None:
    user = create_user(
        db_session,
        UserCreate(login_id="user1", name="User One", password="mypassword"),
        _admin(),
    )

    assert user.password_hash != "mypassword"
    assert verify_password("mypassword", user.password_hash)


# ── Password change tests ──


def test_change_own_password(db_session) -> None:
    user = create_user(
        db_session,
        UserCreate(login_id="user1", name="User One", password="oldpass"),
        _admin(),
    )

    current_user_stub = _UserStub(login_id="user1", name="User One", role="user")
    change_password(
        db_session,
        user.id,
        UserChangePassword(current_password="oldpass", new_password="newpass"),
        current_user_stub,
    )

    refreshed = get_user(db_session, user.id)
    assert verify_password("newpass", refreshed.password_hash)


def test_change_password_rejects_wrong_current(db_session) -> None:
    user = create_user(
        db_session,
        UserCreate(login_id="user1", name="User One", password="oldpass"),
        _admin(),
    )

    current_user_stub = _UserStub(login_id="user1", name="User One", role="user")
    with pytest.raises(UnauthorizedError):
        change_password(
            db_session,
            user.id,
            UserChangePassword(current_password="wrongpass", new_password="newpass"),
            current_user_stub,
        )


def test_change_password_rejects_other_user(db_session) -> None:
    user = create_user(
        db_session,
        UserCreate(login_id="user1", name="User One", password="oldpass"),
        _admin(),
    )

    other_user_stub = _UserStub(login_id="other", name="Other", role="user")
    with pytest.raises(PermissionDeniedError):
        change_password(
            db_session,
            user.id,
            UserChangePassword(current_password="oldpass", new_password="newpass"),
            other_user_stub,
        )


def test_admin_reset_password(db_session) -> None:
    user = create_user(
        db_session,
        UserCreate(login_id="user1", name="User One", password="oldpass"),
        _admin(),
    )

    reset_password(
        db_session,
        user.id,
        UserResetPassword(new_password="resetpass"),
        _admin(),
    )

    refreshed = get_user(db_session, user.id)
    assert verify_password("resetpass", refreshed.password_hash)


# ── Bootstrap tests ──


def test_bootstrap_admin_creates_user(db_session) -> None:
    ensure_bootstrap_admin(db_session, "admin", "adminpass", "관리자")

    user = get_user_by_login_id(db_session, "admin")
    assert user is not None
    assert user.role == "admin"
    assert verify_password("adminpass", user.password_hash)


def test_bootstrap_admin_idempotent(db_session) -> None:
    ensure_bootstrap_admin(db_session, "admin", "pass1", "관리자")
    ensure_bootstrap_admin(db_session, "admin", "pass2", "관리자")

    user = get_user_by_login_id(db_session, "admin")
    assert verify_password("pass1", user.password_hash)


# ── Authentication tests ──


def test_authenticate_success(db_session) -> None:
    ensure_bootstrap_admin(db_session, "admin", "adminpass", "관리자")

    result = authenticate(db_session, "admin", "adminpass")
    assert result["login_id"] == "admin"
    assert result["role"] == "admin"


def test_authenticate_wrong_password(db_session) -> None:
    ensure_bootstrap_admin(db_session, "admin", "adminpass", "관리자")

    with pytest.raises(UnauthorizedError):
        authenticate(db_session, "admin", "wrongpass")


def test_authenticate_nonexistent_user(db_session) -> None:
    with pytest.raises(UnauthorizedError):
        authenticate(db_session, "nobody", "pass")


def test_authenticate_inactive_user(db_session) -> None:
    user = create_user(
        db_session,
        UserCreate(login_id="user1", name="User One", password="pass123"),
        _admin(),
    )
    update_user(db_session, user.id, UserUpdate(is_active=False), _admin())

    with pytest.raises(UnauthorizedError):
        authenticate(db_session, "user1", "pass123")


