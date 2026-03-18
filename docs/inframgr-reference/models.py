# inframgr Models Reference
# Generated for migration reference - 2026-03-18

# ============================================
# FILE: app/models/__init__.py
# ============================================
from app.models.asset import Asset
from app.models.asset_contact import AssetContact
from app.models.asset_ip import AssetIP
from app.models.base import Base
from app.models.contact import Contact
from app.models.ip_subnet import IpSubnet
from app.models.partner import Partner
from app.models.policy_assignment import PolicyAssignment
from app.models.policy_definition import PolicyDefinition
from app.models.port_map import PortMap
from app.models.project import Project
from app.models.project_deliverable import ProjectDeliverable
from app.models.project_phase import ProjectPhase
from app.models.user import User


# ============================================
# FILE: app/models/asset.py
# ============================================
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Asset(TimestampMixin, Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    asset_name: Mapped[str] = mapped_column(String(255), index=True)
    asset_type: Mapped[str] = mapped_column(String(50))
    vendor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    environment: Mapped[str] = mapped_column(String(30), default="prod")
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="planned")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Equipment Spec
    center: Mapped[str | None] = mapped_column(String(100), nullable=True)
    operation_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    equipment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rack_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rack_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phase: Mapped[str | None] = mapped_column(String(50), nullable=True)
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_no: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Logical Config
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cluster: Mapped[str | None] = mapped_column(String(200), nullable=True)
    service_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    zone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    service_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mgmt_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Hardware Config
    size_unit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lc_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ha_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    utp_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    power_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    power_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Asset Info
    asset_class: Mapped[str | None] = mapped_column(String(50), nullable=True)
    asset_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year_acquired: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dept: Mapped[str | None] = mapped_column(String(100), nullable=True)
    primary_contact_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    secondary_contact_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    maintenance_vendor: Mapped[str | None] = mapped_column(String(200), nullable=True)


# ============================================
# FILE: app/models/asset_contact.py
# ============================================
from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AssetContact(TimestampMixin, Base):
    __tablename__ = "asset_contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), index=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)


# ============================================
# FILE: app/models/asset_ip.py
# ============================================
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AssetIP(TimestampMixin, Base):
    __tablename__ = "asset_ips"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    ip_subnet_id: Mapped[int | None] = mapped_column(
        ForeignKey("ip_subnets.id"), index=True, nullable=True
    )
    ip_address: Mapped[str] = mapped_column(String(64), index=True)
    ip_type: Mapped[str] = mapped_column(String(30), default="service")
    interface_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    zone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    service_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vlan_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    network: Mapped[str | None] = mapped_column(String(64), nullable=True)
    netmask: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gateway: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dns_primary: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dns_secondary: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


# ============================================
# FILE: app/models/base.py
# ============================================
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ============================================
# FILE: app/models/contact.py
# ============================================
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Contact(TimestampMixin, Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    emergency_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_source: Mapped[str | None] = mapped_column(String(30), nullable=True)


# ============================================
# FILE: app/models/ip_subnet.py
# ============================================
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class IpSubnet(TimestampMixin, Base):
    __tablename__ = "ip_subnets"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    subnet: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(30), default="service")
    vlan_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    gateway: Mapped[str | None] = mapped_column(String(64), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    floor: Mapped[str | None] = mapped_column(String(50), nullable=True)
    counterpart: Mapped[str | None] = mapped_column(String(200), nullable=True)
    allocation_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    netmask: Mapped[str | None] = mapped_column(String(64), nullable=True)
    zone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


# ============================================
# FILE: app/models/partner.py
# ============================================
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Partner(TimestampMixin, Base):
    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    partner_name: Mapped[str] = mapped_column(String(255), index=True)
    partner_type: Mapped[str] = mapped_column(String(50))
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    business_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_source: Mapped[str | None] = mapped_column(String(30), nullable=True)


# ============================================
# FILE: app/models/policy_assignment.py
# ============================================
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PolicyAssignment(TimestampMixin, Base):
    __tablename__ = "policy_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    policy_definition_id: Mapped[int] = mapped_column(ForeignKey("policy_definitions.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="not_checked")
    exception_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    checked_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    evidence_note: Mapped[str | None] = mapped_column(Text, nullable=True)


# ============================================
# FILE: app/models/policy_definition.py
# ============================================
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PolicyDefinition(TimestampMixin, Base):
    __tablename__ = "policy_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    policy_name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    security_domain: Mapped[str | None] = mapped_column(String(200), nullable=True)
    requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
    architecture_element: Mapped[str | None] = mapped_column(String(200), nullable=True)
    control_point: Mapped[str | None] = mapped_column(String(200), nullable=True)
    iso27001_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nist_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    isms_p_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    implementation_example: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)


# ============================================
# FILE: app/models/port_map.py
# ============================================
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PortMap(TimestampMixin, Base):
    __tablename__ = "port_maps"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    src_asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    src_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dst_asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    dst_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    protocol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="required")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Common
    seq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cable_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cable_request: Mapped[str | None] = mapped_column(String(200), nullable=True)
    connection_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Start side
    src_mid: Mapped[str | None] = mapped_column(String(100), nullable=True)
    src_rack_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    src_rack_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    src_vendor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    src_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    src_hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    src_cluster: Mapped[str | None] = mapped_column(String(200), nullable=True)
    src_slot: Mapped[str | None] = mapped_column(String(30), nullable=True)
    src_port_name: Mapped[str | None] = mapped_column(String(30), nullable=True)
    src_service_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    src_zone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    src_vlan: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # End side
    dst_mid: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dst_rack_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dst_rack_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dst_vendor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dst_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dst_hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dst_cluster: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dst_slot: Mapped[str | None] = mapped_column(String(30), nullable=True)
    dst_port_name: Mapped[str | None] = mapped_column(String(30), nullable=True)
    dst_service_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dst_zone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dst_vlan: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Cable info
    cable_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    cable_speed: Mapped[str | None] = mapped_column(String(30), nullable=True)
    duplex: Mapped[str | None] = mapped_column(String(30), nullable=True)
    cable_category: Mapped[str | None] = mapped_column(String(50), nullable=True)


# ============================================
# FILE: app/models/project.py
# ============================================
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    project_name: Mapped[str] = mapped_column(String(255), index=True)
    client_name: Mapped[str] = mapped_column(String(255))
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="planned")
    external_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_source: Mapped[str | None] = mapped_column(String(30), nullable=True)


# ============================================
# FILE: app/models/project_deliverable.py
# ============================================
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ProjectDeliverable(TimestampMixin, Base):
    __tablename__ = "project_deliverables"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_phase_id: Mapped[int] = mapped_column(ForeignKey("project_phases.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    submitted_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


# ============================================
# FILE: app/models/project_phase.py
# ============================================
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ProjectPhase(TimestampMixin, Base):
    __tablename__ = "project_phases"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    phase_type: Mapped[str] = mapped_column(String(30))
    task_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    deliverables_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    cautions: Mapped[str | None] = mapped_column(Text, nullable=True)
    submission_required: Mapped[bool] = mapped_column(default=False)
    submission_status: Mapped[str] = mapped_column(String(30), default="pending")
    status: Mapped[str] = mapped_column(String(30), default="not_started")


# ============================================
# FILE: app/models/user.py
# ============================================
from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    login_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    external_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_source: Mapped[str | None] = mapped_column(String(30), nullable=True)


