# inframgr Services Reference
# Generated for migration reference - 2026-03-18

# ============================================
# FILE: app/services/asset_service.py
# ============================================
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.authorization import can_edit_inventory
from app.exceptions import DuplicateError, NotFoundError, PermissionDeniedError
from app.models.asset import Asset
from app.models.project import Project
from app.schemas.asset import AssetCreate, AssetUpdate


def list_assets(db: Session, project_id: int | None = None) -> list[Asset]:
    stmt = select(Asset)
    if project_id is not None:
        stmt = stmt.where(Asset.project_id == project_id)
    stmt = stmt.order_by(Asset.project_id.asc(), Asset.asset_name.asc())
    return list(db.scalars(stmt))


def get_asset(db: Session, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise NotFoundError("Asset not found")
    return asset


def create_asset(db: Session, payload: AssetCreate, current_user) -> Asset:
    _require_inventory_edit(current_user)
    _ensure_project_exists(db, payload.project_id)
    _ensure_asset_name_unique(db, payload.project_id, payload.asset_name)

    asset = Asset(**payload.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def update_asset(db: Session, asset_id: int, payload: AssetUpdate, current_user) -> Asset:
    _require_inventory_edit(current_user)
    asset = get_asset(db, asset_id)
    changes = payload.model_dump(exclude_unset=True)

    target_project_id = changes.get("project_id", asset.project_id)
    target_asset_name = changes.get("asset_name", asset.asset_name)

    if "project_id" in changes:
        _ensure_project_exists(db, target_project_id)

    if target_project_id != asset.project_id or target_asset_name != asset.asset_name:
        _ensure_asset_name_unique(db, target_project_id, target_asset_name, asset.id)

    for field, value in changes.items():
        setattr(asset, field, value)

    db.commit()
    db.refresh(asset)
    return asset


def delete_asset(db: Session, asset_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    asset = get_asset(db, asset_id)
    db.delete(asset)
    db.commit()


def _ensure_project_exists(db: Session, project_id: int) -> None:
    if db.get(Project, project_id) is None:
        raise NotFoundError("Project not found")


def _ensure_asset_name_unique(
    db: Session,
    project_id: int,
    asset_name: str,
    asset_id: int | None = None,
) -> None:
    stmt = select(Asset).where(Asset.project_id == project_id, Asset.asset_name == asset_name)
    existing = db.scalar(stmt)
    if existing is None:
        return
    if asset_id is not None and existing.id == asset_id:
        return
    raise DuplicateError("Asset name already exists in the project")


def _require_inventory_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")


# ============================================
# FILE: app/services/network_service.py
# ============================================
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.authorization import can_edit_inventory
from app.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.asset import Asset
from app.models.asset_ip import AssetIP
from app.models.ip_subnet import IpSubnet
from app.models.port_map import PortMap
from app.models.project import Project
from app.schemas.asset_ip import AssetIPCreate, AssetIPUpdate
from app.schemas.ip_subnet import IpSubnetCreate, IpSubnetUpdate
from app.schemas.port_map import PortMapCreate, PortMapUpdate


# ── IpSubnet ──


def list_subnets(db: Session, project_id: int) -> list[IpSubnet]:
    _ensure_project_exists(db, project_id)
    return list(
        db.scalars(
            select(IpSubnet)
            .where(IpSubnet.project_id == project_id)
            .order_by(IpSubnet.name.asc())
        )
    )


def get_subnet(db: Session, subnet_id: int) -> IpSubnet:
    subnet = db.get(IpSubnet, subnet_id)
    if subnet is None:
        raise NotFoundError("IP subnet not found")
    return subnet


def create_subnet(db: Session, payload: IpSubnetCreate, current_user) -> IpSubnet:
    _require_inventory_edit(current_user)
    _ensure_project_exists(db, payload.project_id)

    subnet = IpSubnet(**payload.model_dump())
    db.add(subnet)
    db.commit()
    db.refresh(subnet)
    return subnet


def update_subnet(
    db: Session, subnet_id: int, payload: IpSubnetUpdate, current_user
) -> IpSubnet:
    _require_inventory_edit(current_user)
    subnet = get_subnet(db, subnet_id)
    changes = payload.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(subnet, field, value)

    db.commit()
    db.refresh(subnet)
    return subnet


def delete_subnet(db: Session, subnet_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    subnet = get_subnet(db, subnet_id)

    has_ips = db.scalar(
        select(AssetIP.id).where(AssetIP.ip_subnet_id == subnet_id).limit(1)
    )
    if has_ips is not None:
        raise BusinessRuleError("Subnet with assigned IPs cannot be deleted")

    db.delete(subnet)
    db.commit()


# ── AssetIP ──


def list_asset_ips(db: Session, asset_id: int) -> list[AssetIP]:
    _ensure_asset_exists(db, asset_id)
    return list(
        db.scalars(
            select(AssetIP)
            .where(AssetIP.asset_id == asset_id)
            .order_by(AssetIP.ip_address.asc())
        )
    )


def list_project_ips(db: Session, project_id: int) -> list[AssetIP]:
    """프로젝트 전체 IP 인벤토리 조회."""
    _ensure_project_exists(db, project_id)
    return list(
        db.scalars(
            select(AssetIP)
            .join(Asset, AssetIP.asset_id == Asset.id)
            .where(Asset.project_id == project_id)
            .order_by(AssetIP.ip_address.asc())
        )
    )


def get_asset_ip(db: Session, ip_id: int) -> AssetIP:
    asset_ip = db.get(AssetIP, ip_id)
    if asset_ip is None:
        raise NotFoundError("Asset IP not found")
    return asset_ip


def create_asset_ip(db: Session, payload: AssetIPCreate, current_user) -> AssetIP:
    _require_inventory_edit(current_user)
    asset = _ensure_asset_exists(db, payload.asset_id)

    if payload.ip_subnet_id is not None:
        _ensure_subnet_exists(db, payload.ip_subnet_id)

    _ensure_ip_unique_in_project(db, asset.project_id, payload.ip_address)

    asset_ip = AssetIP(**payload.model_dump())
    db.add(asset_ip)
    db.commit()
    db.refresh(asset_ip)
    return asset_ip


def update_asset_ip(
    db: Session, ip_id: int, payload: AssetIPUpdate, current_user
) -> AssetIP:
    _require_inventory_edit(current_user)
    asset_ip = get_asset_ip(db, ip_id)
    changes = payload.model_dump(exclude_unset=True)

    if "ip_subnet_id" in changes and changes["ip_subnet_id"] is not None:
        _ensure_subnet_exists(db, changes["ip_subnet_id"])

    if "ip_address" in changes and changes["ip_address"] != asset_ip.ip_address:
        asset = db.get(Asset, asset_ip.asset_id)
        _ensure_ip_unique_in_project(db, asset.project_id, changes["ip_address"], ip_id)

    for field, value in changes.items():
        setattr(asset_ip, field, value)

    db.commit()
    db.refresh(asset_ip)
    return asset_ip


def delete_asset_ip(db: Session, ip_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    asset_ip = get_asset_ip(db, ip_id)
    db.delete(asset_ip)
    db.commit()


# ── PortMap ──


def list_port_maps(db: Session, project_id: int) -> list[PortMap]:
    _ensure_project_exists(db, project_id)
    return list(
        db.scalars(
            select(PortMap)
            .where(PortMap.project_id == project_id)
            .order_by(PortMap.id.asc())
        )
    )


def get_port_map(db: Session, port_map_id: int) -> PortMap:
    port_map = db.get(PortMap, port_map_id)
    if port_map is None:
        raise NotFoundError("Port map not found")
    return port_map


def create_port_map(db: Session, payload: PortMapCreate, current_user) -> PortMap:
    _require_inventory_edit(current_user)
    _ensure_project_exists(db, payload.project_id)

    if payload.src_asset_id is not None:
        _ensure_asset_belongs_to_project(db, payload.src_asset_id, payload.project_id)
    if payload.dst_asset_id is not None:
        _ensure_asset_belongs_to_project(db, payload.dst_asset_id, payload.project_id)

    port_map = PortMap(**payload.model_dump())
    db.add(port_map)
    db.commit()
    db.refresh(port_map)
    return port_map


def update_port_map(
    db: Session, port_map_id: int, payload: PortMapUpdate, current_user
) -> PortMap:
    _require_inventory_edit(current_user)
    port_map = get_port_map(db, port_map_id)
    changes = payload.model_dump(exclude_unset=True)

    if "src_asset_id" in changes and changes["src_asset_id"] is not None:
        _ensure_asset_belongs_to_project(db, changes["src_asset_id"], port_map.project_id)
    if "dst_asset_id" in changes and changes["dst_asset_id"] is not None:
        _ensure_asset_belongs_to_project(db, changes["dst_asset_id"], port_map.project_id)

    for field, value in changes.items():
        setattr(port_map, field, value)

    db.commit()
    db.refresh(port_map)
    return port_map


def delete_port_map(db: Session, port_map_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    port_map = get_port_map(db, port_map_id)
    db.delete(port_map)
    db.commit()


# ── Private helpers ──


def _ensure_project_exists(db: Session, project_id: int) -> None:
    if db.get(Project, project_id) is None:
        raise NotFoundError("Project not found")


def _ensure_asset_exists(db: Session, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise NotFoundError("Asset not found")
    return asset


def _ensure_subnet_exists(db: Session, subnet_id: int) -> None:
    if db.get(IpSubnet, subnet_id) is None:
        raise NotFoundError("IP subnet not found")


def _ensure_asset_belongs_to_project(db: Session, asset_id: int, project_id: int) -> None:
    asset = _ensure_asset_exists(db, asset_id)
    if asset.project_id != project_id:
        raise BusinessRuleError("Asset does not belong to this project")


def _ensure_ip_unique_in_project(
    db: Session, project_id: int, ip_address: str, ip_id: int | None = None
) -> None:
    """프로젝트 범위 내 IP 중복 검증."""
    stmt = (
        select(AssetIP)
        .join(Asset, AssetIP.asset_id == Asset.id)
        .where(Asset.project_id == project_id, AssetIP.ip_address == ip_address)
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if ip_id is not None and existing.id == ip_id:
        return
    raise DuplicateError("IP address already exists in this project")


def _require_inventory_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")


# ============================================
# FILE: app/services/partner_service.py
# ============================================
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.authorization import can_edit_inventory
from app.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.asset import Asset
from app.models.asset_contact import AssetContact
from app.models.contact import Contact
from app.models.partner import Partner
from app.models.project import Project
from app.schemas.asset_contact import AssetContactCreate, AssetContactUpdate
from app.schemas.contact import ContactCreate, ContactUpdate
from app.schemas.partner import PartnerCreate, PartnerUpdate


# ── Partner ──


def list_partners(db: Session, project_id: int) -> list[Partner]:
    _ensure_project_exists(db, project_id)
    return list(
        db.scalars(
            select(Partner)
            .where(Partner.project_id == project_id)
            .order_by(Partner.partner_name.asc())
        )
    )


def get_partner(db: Session, partner_id: int) -> Partner:
    partner = db.get(Partner, partner_id)
    if partner is None:
        raise NotFoundError("Partner not found")
    return partner


def create_partner(db: Session, payload: PartnerCreate, current_user) -> Partner:
    _require_inventory_edit(current_user)
    if payload.project_id is not None:
        _ensure_project_exists(db, payload.project_id)

    partner = Partner(**payload.model_dump())
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


def update_partner(
    db: Session, partner_id: int, payload: PartnerUpdate, current_user
) -> Partner:
    _require_inventory_edit(current_user)
    partner = get_partner(db, partner_id)
    changes = payload.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(partner, field, value)

    db.commit()
    db.refresh(partner)
    return partner


def delete_partner(db: Session, partner_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    partner = get_partner(db, partner_id)

    has_contacts = db.scalar(
        select(Contact.id).where(Contact.partner_id == partner_id).limit(1)
    )
    if has_contacts is not None:
        raise BusinessRuleError("Partner with contacts cannot be deleted")

    db.delete(partner)
    db.commit()


# ── Contact ──


def list_contacts(db: Session, partner_id: int) -> list[Contact]:
    _ensure_partner_exists(db, partner_id)
    return list(
        db.scalars(
            select(Contact)
            .where(Contact.partner_id == partner_id)
            .order_by(Contact.name.asc())
        )
    )


def get_contact(db: Session, contact_id: int) -> Contact:
    contact = db.get(Contact, contact_id)
    if contact is None:
        raise NotFoundError("Contact not found")
    return contact


def create_contact(db: Session, payload: ContactCreate, current_user) -> Contact:
    _require_inventory_edit(current_user)
    _ensure_partner_exists(db, payload.partner_id)

    contact = Contact(**payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def update_contact(
    db: Session, contact_id: int, payload: ContactUpdate, current_user
) -> Contact:
    _require_inventory_edit(current_user)
    contact = get_contact(db, contact_id)
    changes = payload.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(contact, field, value)

    db.commit()
    db.refresh(contact)
    return contact


def delete_contact(db: Session, contact_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    contact = get_contact(db, contact_id)
    db.delete(contact)
    db.commit()


# ── AssetContact ──


def list_asset_contacts(db: Session, asset_id: int) -> list[AssetContact]:
    _ensure_asset_exists(db, asset_id)
    return list(
        db.scalars(
            select(AssetContact)
            .where(AssetContact.asset_id == asset_id)
            .order_by(AssetContact.id.asc())
        )
    )


def get_asset_contact(db: Session, asset_contact_id: int) -> AssetContact:
    ac = db.get(AssetContact, asset_contact_id)
    if ac is None:
        raise NotFoundError("Asset contact not found")
    return ac


def create_asset_contact(
    db: Session, payload: AssetContactCreate, current_user
) -> AssetContact:
    _require_inventory_edit(current_user)
    _ensure_asset_exists(db, payload.asset_id)
    _ensure_contact_exists(db, payload.contact_id)
    _ensure_asset_contact_unique(db, payload.asset_id, payload.contact_id, payload.role)

    ac = AssetContact(**payload.model_dump())
    db.add(ac)
    db.commit()
    db.refresh(ac)
    return ac


def update_asset_contact(
    db: Session, asset_contact_id: int, payload: AssetContactUpdate, current_user
) -> AssetContact:
    _require_inventory_edit(current_user)
    ac = get_asset_contact(db, asset_contact_id)
    changes = payload.model_dump(exclude_unset=True)

    if "role" in changes:
        _ensure_asset_contact_unique(
            db, ac.asset_id, ac.contact_id, changes["role"], asset_contact_id
        )

    for field, value in changes.items():
        setattr(ac, field, value)

    db.commit()
    db.refresh(ac)
    return ac


def delete_asset_contact(db: Session, asset_contact_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    ac = get_asset_contact(db, asset_contact_id)
    db.delete(ac)
    db.commit()


# ── Private helpers ──


def _ensure_project_exists(db: Session, project_id: int) -> None:
    if db.get(Project, project_id) is None:
        raise NotFoundError("Project not found")


def _ensure_partner_exists(db: Session, partner_id: int) -> None:
    if db.get(Partner, partner_id) is None:
        raise NotFoundError("Partner not found")


def _ensure_asset_exists(db: Session, asset_id: int) -> None:
    if db.get(Asset, asset_id) is None:
        raise NotFoundError("Asset not found")


def _ensure_contact_exists(db: Session, contact_id: int) -> None:
    if db.get(Contact, contact_id) is None:
        raise NotFoundError("Contact not found")


def _ensure_asset_contact_unique(
    db: Session,
    asset_id: int,
    contact_id: int,
    role: str | None,
    asset_contact_id: int | None = None,
) -> None:
    stmt = select(AssetContact).where(
        AssetContact.asset_id == asset_id,
        AssetContact.contact_id == contact_id,
        AssetContact.role == role,
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if asset_contact_id is not None and existing.id == asset_contact_id:
        return
    raise DuplicateError("This contact-role mapping already exists for the asset")


def _require_inventory_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")


# ============================================
# FILE: app/services/phase_service.py
# ============================================
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.authorization import can_edit_inventory
from app.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.project import Project
from app.models.project_deliverable import ProjectDeliverable
from app.models.project_phase import ProjectPhase
from app.schemas.project_deliverable import ProjectDeliverableCreate, ProjectDeliverableUpdate
from app.schemas.project_phase import ProjectPhaseCreate, ProjectPhaseUpdate


# ── ProjectPhase ──


def list_phases(db: Session, project_id: int) -> list[ProjectPhase]:
    _ensure_project_exists(db, project_id)
    return list(
        db.scalars(
            select(ProjectPhase)
            .where(ProjectPhase.project_id == project_id)
            .order_by(ProjectPhase.id.asc())
        )
    )


def get_phase(db: Session, phase_id: int) -> ProjectPhase:
    phase = db.get(ProjectPhase, phase_id)
    if phase is None:
        raise NotFoundError("Project phase not found")
    return phase


def create_phase(db: Session, payload: ProjectPhaseCreate, current_user) -> ProjectPhase:
    _require_inventory_edit(current_user)
    _ensure_project_exists(db, payload.project_id)
    _ensure_phase_type_unique(db, payload.project_id, payload.phase_type)

    phase = ProjectPhase(**payload.model_dump())
    db.add(phase)
    db.commit()
    db.refresh(phase)
    return phase


def update_phase(
    db: Session, phase_id: int, payload: ProjectPhaseUpdate, current_user
) -> ProjectPhase:
    _require_inventory_edit(current_user)
    phase = get_phase(db, phase_id)
    changes = payload.model_dump(exclude_unset=True)

    if "phase_type" in changes and changes["phase_type"] != phase.phase_type:
        _ensure_phase_type_unique(db, phase.project_id, changes["phase_type"], phase_id)

    for field, value in changes.items():
        setattr(phase, field, value)

    db.commit()
    db.refresh(phase)
    return phase


def delete_phase(db: Session, phase_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    phase = get_phase(db, phase_id)

    has_deliverables = db.scalar(
        select(ProjectDeliverable.id)
        .where(ProjectDeliverable.project_phase_id == phase_id)
        .limit(1)
    )
    if has_deliverables is not None:
        raise BusinessRuleError("Phase with deliverables cannot be deleted")

    db.delete(phase)
    db.commit()


# ── ProjectDeliverable ──


def list_deliverables(db: Session, phase_id: int) -> list[ProjectDeliverable]:
    _ensure_phase_exists(db, phase_id)
    return list(
        db.scalars(
            select(ProjectDeliverable)
            .where(ProjectDeliverable.project_phase_id == phase_id)
            .order_by(ProjectDeliverable.id.asc())
        )
    )


def get_deliverable(db: Session, deliverable_id: int) -> ProjectDeliverable:
    deliverable = db.get(ProjectDeliverable, deliverable_id)
    if deliverable is None:
        raise NotFoundError("Project deliverable not found")
    return deliverable


def create_deliverable(
    db: Session, payload: ProjectDeliverableCreate, current_user
) -> ProjectDeliverable:
    _require_inventory_edit(current_user)
    _ensure_phase_exists(db, payload.project_phase_id)

    deliverable = ProjectDeliverable(**payload.model_dump())
    db.add(deliverable)
    db.commit()
    db.refresh(deliverable)
    return deliverable


def update_deliverable(
    db: Session, deliverable_id: int, payload: ProjectDeliverableUpdate, current_user
) -> ProjectDeliverable:
    _require_inventory_edit(current_user)
    deliverable = get_deliverable(db, deliverable_id)
    changes = payload.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(deliverable, field, value)

    db.commit()
    db.refresh(deliverable)
    return deliverable


def delete_deliverable(db: Session, deliverable_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    deliverable = get_deliverable(db, deliverable_id)
    db.delete(deliverable)
    db.commit()


# ── Private helpers ──


def _ensure_project_exists(db: Session, project_id: int) -> None:
    if db.get(Project, project_id) is None:
        raise NotFoundError("Project not found")


def _ensure_phase_exists(db: Session, phase_id: int) -> None:
    if db.get(ProjectPhase, phase_id) is None:
        raise NotFoundError("Project phase not found")


def _ensure_phase_type_unique(
    db: Session, project_id: int, phase_type: str, phase_id: int | None = None
) -> None:
    stmt = select(ProjectPhase).where(
        ProjectPhase.project_id == project_id,
        ProjectPhase.phase_type == phase_type,
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if phase_id is not None and existing.id == phase_id:
        return
    raise DuplicateError("Phase type already exists in this project")


def _require_inventory_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")


# ============================================
# FILE: app/services/policy_service.py
# ============================================
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.authorization import can_edit_inventory, can_manage_policies
from app.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.asset import Asset
from app.models.policy_assignment import PolicyAssignment
from app.models.policy_definition import PolicyDefinition
from app.models.project import Project
from app.schemas.policy_assignment import PolicyAssignmentCreate, PolicyAssignmentUpdate
from app.schemas.policy_definition import PolicyDefinitionCreate, PolicyDefinitionUpdate


# ── PolicyDefinition ──


def list_policies(db: Session) -> list[PolicyDefinition]:
    return list(
        db.scalars(select(PolicyDefinition).order_by(PolicyDefinition.policy_code.asc()))
    )


def get_policy(db: Session, policy_id: int) -> PolicyDefinition:
    policy = db.get(PolicyDefinition, policy_id)
    if policy is None:
        raise NotFoundError("Policy definition not found")
    return policy


def create_policy(
    db: Session, payload: PolicyDefinitionCreate, current_user
) -> PolicyDefinition:
    _require_policy_manage(current_user)
    _ensure_policy_code_unique(db, payload.policy_code)

    policy = PolicyDefinition(**payload.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def update_policy(
    db: Session, policy_id: int, payload: PolicyDefinitionUpdate, current_user
) -> PolicyDefinition:
    _require_policy_manage(current_user)
    policy = get_policy(db, policy_id)
    changes = payload.model_dump(exclude_unset=True)

    if "policy_code" in changes and changes["policy_code"] != policy.policy_code:
        _ensure_policy_code_unique(db, changes["policy_code"], policy_id)

    for field, value in changes.items():
        setattr(policy, field, value)

    db.commit()
    db.refresh(policy)
    return policy


def delete_policy(db: Session, policy_id: int, current_user) -> None:
    _require_policy_manage(current_user)
    policy = get_policy(db, policy_id)

    has_assignments = db.scalar(
        select(PolicyAssignment.id)
        .where(PolicyAssignment.policy_definition_id == policy_id)
        .limit(1)
    )
    if has_assignments is not None:
        raise BusinessRuleError("Policy with assignments cannot be deleted")

    db.delete(policy)
    db.commit()


# ── PolicyAssignment ──


def list_assignments(db: Session, project_id: int) -> list[PolicyAssignment]:
    _ensure_project_exists(db, project_id)
    return list(
        db.scalars(
            select(PolicyAssignment)
            .where(PolicyAssignment.project_id == project_id)
            .order_by(PolicyAssignment.id.asc())
        )
    )


def get_assignment(db: Session, assignment_id: int) -> PolicyAssignment:
    assignment = db.get(PolicyAssignment, assignment_id)
    if assignment is None:
        raise NotFoundError("Policy assignment not found")
    return assignment


def create_assignment(
    db: Session, payload: PolicyAssignmentCreate, current_user
) -> PolicyAssignment:
    _require_inventory_edit(current_user)
    _ensure_project_exists(db, payload.project_id)
    _ensure_policy_exists(db, payload.policy_definition_id)

    if payload.asset_id is not None:
        _ensure_asset_belongs_to_project(db, payload.asset_id, payload.project_id)

    _ensure_assignment_unique(
        db, payload.project_id, payload.asset_id, payload.policy_definition_id
    )

    assignment = PolicyAssignment(**payload.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def update_assignment(
    db: Session, assignment_id: int, payload: PolicyAssignmentUpdate, current_user
) -> PolicyAssignment:
    _require_inventory_edit(current_user)
    assignment = get_assignment(db, assignment_id)
    changes = payload.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(assignment, field, value)

    db.commit()
    db.refresh(assignment)
    return assignment


def delete_assignment(db: Session, assignment_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    assignment = get_assignment(db, assignment_id)
    db.delete(assignment)
    db.commit()


# ── Private helpers ──


def _ensure_project_exists(db: Session, project_id: int) -> None:
    if db.get(Project, project_id) is None:
        raise NotFoundError("Project not found")


def _ensure_policy_exists(db: Session, policy_id: int) -> None:
    if db.get(PolicyDefinition, policy_id) is None:
        raise NotFoundError("Policy definition not found")


def _ensure_policy_code_unique(
    db: Session, policy_code: str, policy_id: int | None = None
) -> None:
    stmt = select(PolicyDefinition).where(PolicyDefinition.policy_code == policy_code)
    existing = db.scalar(stmt)
    if existing is None:
        return
    if policy_id is not None and existing.id == policy_id:
        return
    raise DuplicateError("Policy code already exists")


def _ensure_asset_belongs_to_project(
    db: Session, asset_id: int, project_id: int
) -> None:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise NotFoundError("Asset not found")
    if asset.project_id != project_id:
        raise BusinessRuleError("Asset does not belong to this project")


def _ensure_assignment_unique(
    db: Session,
    project_id: int,
    asset_id: int | None,
    policy_definition_id: int,
    assignment_id: int | None = None,
) -> None:
    stmt = select(PolicyAssignment).where(
        PolicyAssignment.project_id == project_id,
        PolicyAssignment.asset_id == asset_id,
        PolicyAssignment.policy_definition_id == policy_definition_id,
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if assignment_id is not None and existing.id == assignment_id:
        return
    raise DuplicateError("This policy assignment already exists")


def _require_policy_manage(current_user) -> None:
    if not can_manage_policies(current_user):
        raise PermissionDeniedError("Policy management permission required")


def _require_inventory_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")


# ============================================
# FILE: app/services/project_service.py
# ============================================
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.authorization import can_edit_inventory
from app.exceptions import BusinessRuleError, DuplicateError, NotFoundError, PermissionDeniedError
from app.models.asset import Asset
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


def list_projects(db: Session) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.project_code.asc())))


def get_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project not found")
    return project


def create_project(db: Session, payload: ProjectCreate, current_user) -> Project:
    _require_inventory_edit(current_user)
    _ensure_project_code_unique(db, payload.project_code)

    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project_id: int, payload: ProjectUpdate, current_user) -> Project:
    _require_inventory_edit(current_user)
    project = get_project(db, project_id)
    changes = payload.model_dump(exclude_unset=True)

    if "project_code" in changes and changes["project_code"] != project.project_code:
        _ensure_project_code_unique(db, changes["project_code"], project_id)

    for field, value in changes.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    project = get_project(db, project_id)

    has_assets = db.scalar(select(Asset.id).where(Asset.project_id == project_id).limit(1))
    if has_assets is not None:
        raise BusinessRuleError("Project with assets cannot be deleted")

    db.delete(project)
    db.commit()


def _ensure_project_code_unique(db: Session, project_code: str, project_id: int | None = None) -> None:
    stmt = select(Project).where(Project.project_code == project_code)
    existing = db.scalar(stmt)
    if existing is None:
        return
    if project_id is not None and existing.id == project_id:
        return
    raise DuplicateError("Project code already exists")


def _require_inventory_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")


# ============================================
# FILE: app/services/sync_service.py
# ============================================
"""Sales API 동기화 서비스.

sales 시스템에서 거래처(Customer→Partner), 담당자(CustomerContact→Contact),
사용자(User) 데이터를 가져와 로컬 DB에 upsert한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import BusinessRuleError
from app.models.contact import Contact
from app.models.partner import Partner
from app.models.user import User


SOURCE = "sales"


@dataclass
class SyncResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class SyncSummary:
    partners: SyncResult = field(default_factory=SyncResult)
    contacts: SyncResult = field(default_factory=SyncResult)
    users: SyncResult = field(default_factory=SyncResult)


class SalesApiClient:
    """Sales API HTTP 클라이언트. 세션 쿠키 기반 인증."""

    def __init__(self) -> None:
        if not settings.sales_api_enabled:
            raise BusinessRuleError("Sales API 연동이 비활성화되어 있습니다.")
        if not settings.sales_api_base_url:
            raise BusinessRuleError("SALES_API_BASE_URL이 설정되지 않았습니다.")

        self._base = settings.sales_api_base_url.rstrip("/")
        self._client = httpx.Client(timeout=30.0)
        self._authenticated = False

    def login(self) -> None:
        resp = self._client.post(
            f"{self._base}/auth/login",
            json={
                "login_id": settings.sales_api_login_id,
                "password": settings.sales_api_password,
            },
        )
        if resp.status_code != 200:
            raise BusinessRuleError(f"Sales API 로그인 실패: {resp.status_code}")
        self._authenticated = True

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self._authenticated:
            self.login()
        resp = self._client.get(f"{self._base}/{path.lstrip('/')}", params=params)
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self._client.close()


def sync_customers(db: Session, client: SalesApiClient) -> SyncResult:
    """Sales Customer → Partner upsert."""
    result = SyncResult()
    try:
        customers = client.get("/customers")
    except Exception as e:
        result.errors.append(f"거래처 조회 실패: {e}")
        return result

    for cust in customers:
        ext_id = cust.get("id")
        if ext_id is None:
            result.skipped += 1
            continue

        existing = db.scalar(
            select(Partner).where(
                Partner.external_source == SOURCE,
                Partner.external_id == ext_id,
            )
        )

        if existing:
            existing.partner_name = cust.get("name", existing.partner_name)
            existing.note = cust.get("notes", existing.note)
            result.updated += 1
        else:
            partner = Partner(
                partner_name=cust.get("name", ""),
                partner_type="client",
                note=cust.get("notes"),
                external_id=ext_id,
                external_source=SOURCE,
            )
            db.add(partner)
            result.created += 1

    db.flush()
    return result


def sync_contacts(db: Session, client: SalesApiClient) -> SyncResult:
    """Sales CustomerContact → Contact upsert."""
    result = SyncResult()

    partners = list(
        db.scalars(
            select(Partner).where(
                Partner.external_source == SOURCE,
                Partner.external_id.isnot(None),
            )
        )
    )

    for partner in partners:
        try:
            contacts_data = client.get(f"/customers/{partner.external_id}/contacts")
        except Exception:
            result.skipped += 1
            continue

        for ct in contacts_data:
            ext_id = ct.get("id")
            if ext_id is None:
                result.skipped += 1
                continue

            existing = db.scalar(
                select(Contact).where(
                    Contact.external_source == SOURCE,
                    Contact.external_id == ext_id,
                )
            )

            if existing:
                existing.name = ct.get("name", existing.name)
                existing.phone = ct.get("phone", existing.phone)
                existing.email = ct.get("email", existing.email)
                result.updated += 1
            else:
                contact = Contact(
                    partner_id=partner.id,
                    name=ct.get("name", ""),
                    phone=ct.get("phone"),
                    email=ct.get("email"),
                    external_id=ext_id,
                    external_source=SOURCE,
                )
                db.add(contact)
                result.created += 1

    db.flush()
    return result


def sync_users(db: Session, client: SalesApiClient) -> SyncResult:
    """Sales User → User upsert (role은 pjtmgr 자체 유지)."""
    result = SyncResult()
    try:
        users = client.get("/users")
    except Exception as e:
        result.errors.append(f"사용자 조회 실패: {e}")
        return result

    for u in users:
        ext_id = u.get("id")
        login_id = u.get("login_id")
        if not login_id:
            result.skipped += 1
            continue

        existing = db.scalar(select(User).where(User.login_id == login_id))

        if existing:
            existing.name = u.get("name", existing.name)
            if existing.external_id is None:
                existing.external_id = ext_id
                existing.external_source = SOURCE
            result.updated += 1
        else:
            user = User(
                login_id=login_id,
                name=u.get("name", login_id),
                password_hash="!synced",
                role="user",
                is_active=u.get("is_active", True),
                external_id=ext_id,
                external_source=SOURCE,
            )
            db.add(user)
            result.created += 1

    db.flush()
    return result


def sync_all(db: Session) -> SyncSummary:
    """Sales API에서 전체 동기화를 실행한다."""
    client = SalesApiClient()
    summary = SyncSummary()

    try:
        client.login()
        summary.partners = sync_customers(db, client)
        summary.contacts = sync_contacts(db, client)
        summary.users = sync_users(db, client)
        db.commit()
    except Exception as e:
        db.rollback()
        raise BusinessRuleError(f"동기화 실패: {e}") from e
    finally:
        client.close()

    return summary


# ============================================
# FILE: app/services/user_service.py
# ============================================
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.authorization import can_manage_users
from app.auth.password import hash_password, verify_password
from app.exceptions import (
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
    UnauthorizedError,
)
from app.models.user import User
from app.schemas.user import UserChangePassword, UserCreate, UserResetPassword, UserUpdate


def list_users(db: Session, current_user) -> list[User]:
    _require_user_manage(current_user)
    return list(db.scalars(select(User).order_by(User.login_id.asc())))


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    return user


def get_user_by_login_id(db: Session, login_id: str) -> User | None:
    return db.scalar(select(User).where(User.login_id == login_id))


def create_user(db: Session, payload: UserCreate, current_user) -> User:
    _require_user_manage(current_user)
    _ensure_login_id_unique(db, payload.login_id)

    user = User(
        login_id=payload.login_id,
        name=payload.name,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, payload: UserUpdate, current_user) -> User:
    _require_user_manage(current_user)
    user = get_user(db, user_id)
    changes = payload.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


def change_password(
    db: Session, user_id: int, payload: UserChangePassword, current_user
) -> None:
    """사용자 본인의 비밀번호 변경."""
    user = get_user(db, user_id)

    if current_user.login_id != user.login_id:
        raise PermissionDeniedError("Can only change your own password")

    if not verify_password(payload.current_password, user.password_hash):
        raise UnauthorizedError("Current password is incorrect")

    user.password_hash = hash_password(payload.new_password)
    db.commit()


def reset_password(
    db: Session, user_id: int, payload: UserResetPassword, current_user
) -> None:
    """관리자가 다른 사용자의 비밀번호를 초기화."""
    _require_user_manage(current_user)
    user = get_user(db, user_id)
    user.password_hash = hash_password(payload.new_password)
    db.commit()


def ensure_bootstrap_admin(db: Session, login_id: str, password: str, name: str) -> None:
    """앱 시작 시 부트스트랩 관리자 계정이 없으면 생성.

    이미 존재하지만 해시 형식이 변경된 경우(SHA-256→bcrypt 등) 비밀번호를 갱신한다.
    """
    existing = get_user_by_login_id(db, login_id)
    if existing is not None:
        if not existing.password_hash.startswith("$2"):
            existing.password_hash = hash_password(password)
            db.commit()
        return

    user = User(
        login_id=login_id,
        name=name,
        password_hash=hash_password(password),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()


# ── Private helpers ──


def _ensure_login_id_unique(db: Session, login_id: str, user_id: int | None = None) -> None:
    existing = get_user_by_login_id(db, login_id)
    if existing is None:
        return
    if user_id is not None and existing.id == user_id:
        return
    raise DuplicateError("Login ID already exists")


def _require_user_manage(current_user) -> None:
    if not can_manage_users(current_user):
        raise PermissionDeniedError("User management permission required")


