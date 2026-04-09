# inframgr Schemas Reference
# Generated for migration reference - 2026-03-18

# ============================================
# FILE: app/schemas/asset.py
# ============================================
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AssetCreate(BaseModel):
    project_id: int
    asset_name: str
    asset_type: str
    vendor: str | None = None
    model: str | None = None
    role: str | None = None
    environment: str = "prod"
    location: str | None = None
    status: str = "planned"
    note: str | None = None
    # Equipment Spec
    center: str | None = None
    operation_type: str | None = None
    equipment_id: str | None = None
    rack_no: str | None = None
    rack_unit: str | None = None
    phase: str | None = None
    received_date: date | None = None
    category: str | None = None
    subcategory: str | None = None
    serial_no: str | None = None
    # Logical Config
    hostname: str | None = None
    cluster: str | None = None
    service_name: str | None = None
    zone: str | None = None
    service_ip: str | None = None
    mgmt_ip: str | None = None
    # Hardware Config
    size_unit: int | None = None
    lc_count: int | None = None
    ha_count: int | None = None
    utp_count: int | None = None
    power_count: int | None = None
    power_type: str | None = None
    firmware_version: str | None = None
    # Asset Info
    asset_class: str | None = None
    asset_number: str | None = None
    year_acquired: int | None = None
    dept: str | None = None
    primary_contact_name: str | None = None
    secondary_contact_name: str | None = None
    maintenance_vendor: str | None = None


class AssetUpdate(BaseModel):
    project_id: int | None = None
    asset_name: str | None = None
    asset_type: str | None = None
    vendor: str | None = None
    model: str | None = None
    role: str | None = None
    environment: str | None = None
    location: str | None = None
    status: str | None = None
    note: str | None = None
    # Equipment Spec
    center: str | None = None
    operation_type: str | None = None
    equipment_id: str | None = None
    rack_no: str | None = None
    rack_unit: str | None = None
    phase: str | None = None
    received_date: date | None = None
    category: str | None = None
    subcategory: str | None = None
    serial_no: str | None = None
    # Logical Config
    hostname: str | None = None
    cluster: str | None = None
    service_name: str | None = None
    zone: str | None = None
    service_ip: str | None = None
    mgmt_ip: str | None = None
    # Hardware Config
    size_unit: int | None = None
    lc_count: int | None = None
    ha_count: int | None = None
    utp_count: int | None = None
    power_count: int | None = None
    power_type: str | None = None
    firmware_version: str | None = None
    # Asset Info
    asset_class: str | None = None
    asset_number: str | None = None
    year_acquired: int | None = None
    dept: str | None = None
    primary_contact_name: str | None = None
    secondary_contact_name: str | None = None
    maintenance_vendor: str | None = None


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    asset_name: str
    asset_type: str
    vendor: str | None
    model: str | None
    role: str | None
    environment: str
    location: str | None
    status: str
    note: str | None
    # Equipment Spec
    center: str | None = None
    operation_type: str | None = None
    equipment_id: str | None = None
    rack_no: str | None = None
    rack_unit: str | None = None
    phase: str | None = None
    received_date: date | None = None
    category: str | None = None
    subcategory: str | None = None
    serial_no: str | None = None
    # Logical Config
    hostname: str | None = None
    cluster: str | None = None
    service_name: str | None = None
    zone: str | None = None
    service_ip: str | None = None
    mgmt_ip: str | None = None
    # Hardware Config
    size_unit: int | None = None
    lc_count: int | None = None
    ha_count: int | None = None
    utp_count: int | None = None
    power_count: int | None = None
    power_type: str | None = None
    firmware_version: str | None = None
    # Asset Info
    asset_class: str | None = None
    asset_number: str | None = None
    year_acquired: int | None = None
    dept: str | None = None
    primary_contact_name: str | None = None
    secondary_contact_name: str | None = None
    maintenance_vendor: str | None = None
    created_at: datetime
    updated_at: datetime


# ============================================
# FILE: app/schemas/asset_contact.py
# ============================================
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetContactCreate(BaseModel):
    asset_id: int
    contact_id: int
    role: str | None = None


class AssetContactUpdate(BaseModel):
    role: str | None = None


class AssetContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    contact_id: int
    role: str | None
    created_at: datetime
    updated_at: datetime


# ============================================
# FILE: app/schemas/asset_ip.py
# ============================================
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetIPCreate(BaseModel):
    asset_id: int
    ip_subnet_id: int | None = None
    ip_address: str
    ip_type: str = "service"
    interface_name: str | None = None
    is_primary: bool = False
    zone: str | None = None
    service_name: str | None = None
    hostname: str | None = None
    vlan_id: str | None = None
    network: str | None = None
    netmask: str | None = None
    gateway: str | None = None
    dns_primary: str | None = None
    dns_secondary: str | None = None
    note: str | None = None


class AssetIPUpdate(BaseModel):
    ip_subnet_id: int | None = None
    ip_address: str | None = None
    ip_type: str | None = None
    interface_name: str | None = None
    is_primary: bool | None = None
    zone: str | None = None
    service_name: str | None = None
    hostname: str | None = None
    vlan_id: str | None = None
    network: str | None = None
    netmask: str | None = None
    gateway: str | None = None
    dns_primary: str | None = None
    dns_secondary: str | None = None
    note: str | None = None


class AssetIPRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    ip_subnet_id: int | None
    ip_address: str
    ip_type: str
    interface_name: str | None
    is_primary: bool
    zone: str | None
    service_name: str | None
    hostname: str | None
    vlan_id: str | None
    network: str | None
    netmask: str | None
    gateway: str | None
    dns_primary: str | None
    dns_secondary: str | None
    note: str | None
    created_at: datetime
    updated_at: datetime


# ============================================
# FILE: app/schemas/contact.py
# ============================================
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ContactCreate(BaseModel):
    partner_id: int
    name: str
    department: str | None = None
    title: str | None = None
    role: str | None = None
    email: str | None = None
    phone: str | None = None
    emergency_phone: str | None = None
    note: str | None = None


class ContactUpdate(BaseModel):
    name: str | None = None
    department: str | None = None
    title: str | None = None
    role: str | None = None
    email: str | None = None
    phone: str | None = None
    emergency_phone: str | None = None
    note: str | None = None


class ContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    partner_id: int
    name: str
    department: str | None
    title: str | None
    role: str | None
    email: str | None
    phone: str | None
    emergency_phone: str | None
    note: str | None
    created_at: datetime
    updated_at: datetime


# ============================================
# FILE: app/schemas/ip_subnet.py
# ============================================
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IpSubnetCreate(BaseModel):
    project_id: int
    name: str
    subnet: str
    role: str = "service"
    vlan_id: str | None = None
    gateway: str | None = None
    region: str | None = None
    floor: str | None = None
    counterpart: str | None = None
    allocation_type: str | None = None
    category: str | None = None
    netmask: str | None = None
    zone: str | None = None
    description: str | None = None
    note: str | None = None


class IpSubnetUpdate(BaseModel):
    name: str | None = None
    subnet: str | None = None
    role: str | None = None
    vlan_id: str | None = None
    gateway: str | None = None
    region: str | None = None
    floor: str | None = None
    counterpart: str | None = None
    allocation_type: str | None = None
    category: str | None = None
    netmask: str | None = None
    zone: str | None = None
    description: str | None = None
    note: str | None = None


class IpSubnetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    subnet: str
    role: str
    vlan_id: str | None
    gateway: str | None
    region: str | None
    floor: str | None
    counterpart: str | None
    allocation_type: str | None
    category: str | None
    netmask: str | None
    zone: str | None
    description: str | None
    note: str | None
    created_at: datetime
    updated_at: datetime


# ============================================
# FILE: app/schemas/partner.py
# ============================================
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PartnerCreate(BaseModel):
    project_id: int | None = None
    partner_name: str
    partner_type: str
    contact_phone: str | None = None
    address: str | None = None
    business_no: str | None = None
    note: str | None = None


class PartnerUpdate(BaseModel):
    partner_name: str | None = None
    partner_type: str | None = None
    contact_phone: str | None = None
    address: str | None = None
    business_no: str | None = None
    note: str | None = None


class PartnerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    partner_name: str
    partner_type: str
    contact_phone: str | None
    address: str | None
    business_no: str | None
    note: str | None
    created_at: datetime
    updated_at: datetime


# ============================================
# FILE: app/schemas/policy_assignment.py
# ============================================
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PolicyAssignmentCreate(BaseModel):
    project_id: int
    asset_id: int | None = None
    policy_definition_id: int
    status: str = "not_checked"
    exception_reason: str | None = None
    checked_by: str | None = None
    checked_date: date | None = None
    evidence_note: str | None = None


class PolicyAssignmentUpdate(BaseModel):
    status: str | None = None
    exception_reason: str | None = None
    checked_by: str | None = None
    checked_date: date | None = None
    evidence_note: str | None = None


class PolicyAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    asset_id: int | None
    policy_definition_id: int
    status: str
    exception_reason: str | None
    checked_by: str | None
    checked_date: date | None
    evidence_note: str | None
    created_at: datetime
    updated_at: datetime


# ============================================
# FILE: app/schemas/policy_definition.py
# ============================================
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PolicyDefinitionCreate(BaseModel):
    policy_code: str
    policy_name: str
    category: str
    description: str | None = None
    is_active: bool = True
    effective_from: date | None = None
    effective_to: date | None = None
    security_domain: str | None = None
    requirement: str | None = None
    architecture_element: str | None = None
    control_point: str | None = None
    iso27001_ref: str | None = None
    nist_ref: str | None = None
    isms_p_ref: str | None = None
    implementation_example: str | None = None
    evidence: str | None = None


class PolicyDefinitionUpdate(BaseModel):
    policy_code: str | None = None
    policy_name: str | None = None
    category: str | None = None
    description: str | None = None
    is_active: bool | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    security_domain: str | None = None
    requirement: str | None = None
    architecture_element: str | None = None
    control_point: str | None = None
    iso27001_ref: str | None = None
    nist_ref: str | None = None
    isms_p_ref: str | None = None
    implementation_example: str | None = None
    evidence: str | None = None


class PolicyDefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_code: str
    policy_name: str
    category: str
    description: str | None
    is_active: bool
    effective_from: date | None
    effective_to: date | None
    security_domain: str | None
    requirement: str | None
    architecture_element: str | None
    control_point: str | None
    iso27001_ref: str | None
    nist_ref: str | None
    isms_p_ref: str | None
    implementation_example: str | None
    evidence: str | None
    created_at: datetime
    updated_at: datetime


# ============================================
# FILE: app/schemas/port_map.py
# ============================================
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PortMapCreate(BaseModel):
    project_id: int
    src_asset_id: int | None = None
    src_ip: str | None = None
    dst_asset_id: int | None = None
    dst_ip: str | None = None
    protocol: str | None = None
    port: int | None = None
    purpose: str | None = None
    status: str = "required"
    note: str | None = None

    # Common
    seq: int | None = None
    cable_no: str | None = None
    cable_request: str | None = None
    connection_type: str | None = None
    summary: str | None = None

    # Start side
    src_mid: str | None = None
    src_rack_no: str | None = None
    src_rack_unit: str | None = None
    src_vendor: str | None = None
    src_model: str | None = None
    src_hostname: str | None = None
    src_cluster: str | None = None
    src_slot: str | None = None
    src_port_name: str | None = None
    src_service_name: str | None = None
    src_zone: str | None = None
    src_vlan: str | None = None

    # End side
    dst_mid: str | None = None
    dst_rack_no: str | None = None
    dst_rack_unit: str | None = None
    dst_vendor: str | None = None
    dst_model: str | None = None
    dst_hostname: str | None = None
    dst_cluster: str | None = None
    dst_slot: str | None = None
    dst_port_name: str | None = None
    dst_service_name: str | None = None
    dst_zone: str | None = None
    dst_vlan: str | None = None

    # Cable info
    cable_type: str | None = None
    cable_speed: str | None = None
    duplex: str | None = None
    cable_category: str | None = None


class PortMapUpdate(BaseModel):
    src_asset_id: int | None = None
    src_ip: str | None = None
    dst_asset_id: int | None = None
    dst_ip: str | None = None
    protocol: str | None = None
    port: int | None = None
    purpose: str | None = None
    status: str | None = None
    note: str | None = None

    # Common
    seq: int | None = None
    cable_no: str | None = None
    cable_request: str | None = None
    connection_type: str | None = None
    summary: str | None = None

    # Start side
    src_mid: str | None = None
    src_rack_no: str | None = None
    src_rack_unit: str | None = None
    src_vendor: str | None = None
    src_model: str | None = None
    src_hostname: str | None = None
    src_cluster: str | None = None
    src_slot: str | None = None
    src_port_name: str | None = None
    src_service_name: str | None = None
    src_zone: str | None = None
    src_vlan: str | None = None

    # End side
    dst_mid: str | None = None
    dst_rack_no: str | None = None
    dst_rack_unit: str | None = None
    dst_vendor: str | None = None
    dst_model: str | None = None
    dst_hostname: str | None = None
    dst_cluster: str | None = None
    dst_slot: str | None = None
    dst_port_name: str | None = None
    dst_service_name: str | None = None
    dst_zone: str | None = None
    dst_vlan: str | None = None

    # Cable info
    cable_type: str | None = None
    cable_speed: str | None = None
    duplex: str | None = None
    cable_category: str | None = None


class PortMapRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    src_asset_id: int | None
    src_ip: str | None
    dst_asset_id: int | None
    dst_ip: str | None
    protocol: str | None
    port: int | None
    purpose: str | None
    status: str
    note: str | None
    created_at: datetime
    updated_at: datetime

    # Common
    seq: int | None = None
    cable_no: str | None = None
    cable_request: str | None = None
    connection_type: str | None = None
    summary: str | None = None

    # Start side
    src_mid: str | None = None
    src_rack_no: str | None = None
    src_rack_unit: str | None = None
    src_vendor: str | None = None
    src_model: str | None = None
    src_hostname: str | None = None
    src_cluster: str | None = None
    src_slot: str | None = None
    src_port_name: str | None = None
    src_service_name: str | None = None
    src_zone: str | None = None
    src_vlan: str | None = None

    # End side
    dst_mid: str | None = None
    dst_rack_no: str | None = None
    dst_rack_unit: str | None = None
    dst_vendor: str | None = None
    dst_model: str | None = None
    dst_hostname: str | None = None
    dst_cluster: str | None = None
    dst_slot: str | None = None
    dst_port_name: str | None = None
    dst_service_name: str | None = None
    dst_zone: str | None = None
    dst_vlan: str | None = None

    # Cable info
    cable_type: str | None = None
    cable_speed: str | None = None
    duplex: str | None = None
    cable_category: str | None = None


# ============================================
# FILE: app/schemas/project.py
# ============================================
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    project_code: str
    project_name: str
    client_name: str
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    status: str = "planned"


class ProjectUpdate(BaseModel):
    project_code: str | None = None
    project_name: str | None = None
    client_name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    status: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_code: str
    project_name: str
    client_name: str
    start_date: date | None
    end_date: date | None
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


# ============================================
# FILE: app/schemas/project_deliverable.py
# ============================================
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ProjectDeliverableCreate(BaseModel):
    project_phase_id: int
    name: str
    description: str | None = None
    is_submitted: bool = False
    submitted_at: date | None = None
    note: str | None = None


class ProjectDeliverableUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_submitted: bool | None = None
    submitted_at: date | None = None
    note: str | None = None


class ProjectDeliverableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_phase_id: int
    name: str
    description: str | None
    is_submitted: bool
    submitted_at: date | None
    note: str | None
    created_at: datetime
    updated_at: datetime


# ============================================
# FILE: app/schemas/project_phase.py
# ============================================
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectPhaseCreate(BaseModel):
    project_id: int
    phase_type: str
    task_scope: str | None = None
    deliverables_note: str | None = None
    cautions: str | None = None
    submission_required: bool = False
    submission_status: str = "pending"
    status: str = "not_started"


class ProjectPhaseUpdate(BaseModel):
    phase_type: str | None = None
    task_scope: str | None = None
    deliverables_note: str | None = None
    cautions: str | None = None
    submission_required: bool | None = None
    submission_status: str | None = None
    status: str | None = None


class ProjectPhaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    phase_type: str
    task_scope: str | None
    deliverables_note: str | None
    cautions: str | None
    submission_required: bool
    submission_status: str
    status: str
    created_at: datetime
    updated_at: datetime


# ============================================
# FILE: app/schemas/user.py
# ============================================
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    login_id: str
    name: str
    password: str
    role: str = "user"


class UserUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserChangePassword(BaseModel):
    current_password: str
    new_password: str


class UserResetPassword(BaseModel):
    new_password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login_id: str
    name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


