from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IpSubnetCreate(BaseModel):
    customer_id: int
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
    customer_id: int
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
