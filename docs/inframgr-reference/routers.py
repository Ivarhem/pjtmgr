# inframgr Routers Reference
# Generated for migration reference - 2026-03-18

# ============================================
# FILE: app/routers/__init__.py
# ============================================
"""Application routers."""


# ============================================
# FILE: app/routers/asset_contacts.py
# ============================================
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.schemas.asset_contact import AssetContactCreate, AssetContactRead, AssetContactUpdate
from app.services.partner_service import (
    create_asset_contact,
    delete_asset_contact,
    get_asset_contact,
    list_asset_contacts,
    update_asset_contact,
)


router = APIRouter(tags=["asset-contacts"])


@router.get(
    "/api/v1/assets/{asset_id}/contacts",
    response_model=list[AssetContactRead],
)
def list_asset_contacts_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[AssetContactRead]:
    return list_asset_contacts(db, asset_id)


@router.post(
    "/api/v1/assets/{asset_id}/contacts",
    response_model=AssetContactRead,
    status_code=status.HTTP_201_CREATED,
)
def create_asset_contact_endpoint(
    asset_id: int,
    payload: AssetContactCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetContactRead:
    payload.asset_id = asset_id
    return create_asset_contact(db, payload, current_user)


@router.patch(
    "/api/v1/asset-contacts/{asset_contact_id}",
    response_model=AssetContactRead,
)
def update_asset_contact_endpoint(
    asset_contact_id: int,
    payload: AssetContactUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetContactRead:
    return update_asset_contact(db, asset_contact_id, payload, current_user)


@router.delete(
    "/api/v1/asset-contacts/{asset_contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_asset_contact_endpoint(
    asset_contact_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_asset_contact(db, asset_contact_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================
# FILE: app/routers/asset_ips.py
# ============================================
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.schemas.asset_ip import AssetIPCreate, AssetIPRead, AssetIPUpdate
from app.services.network_service import (
    create_asset_ip,
    delete_asset_ip,
    get_asset_ip,
    list_asset_ips,
    list_project_ips,
    update_asset_ip,
)


router = APIRouter(tags=["asset-ips"])


@router.get(
    "/api/v1/assets/{asset_id}/ips",
    response_model=list[AssetIPRead],
)
def list_asset_ips_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[AssetIPRead]:
    return list_asset_ips(db, asset_id)


@router.post(
    "/api/v1/assets/{asset_id}/ips",
    response_model=AssetIPRead,
    status_code=status.HTTP_201_CREATED,
)
def create_asset_ip_endpoint(
    asset_id: int,
    payload: AssetIPCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetIPRead:
    payload.asset_id = asset_id
    return create_asset_ip(db, payload, current_user)


@router.get(
    "/api/v1/projects/{project_id}/ip-inventory",
    response_model=list[AssetIPRead],
)
def list_project_ips_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[AssetIPRead]:
    return list_project_ips(db, project_id)


@router.get(
    "/api/v1/asset-ips/{ip_id}",
    response_model=AssetIPRead,
)
def get_asset_ip_endpoint(
    ip_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetIPRead:
    return get_asset_ip(db, ip_id)


@router.patch(
    "/api/v1/asset-ips/{ip_id}",
    response_model=AssetIPRead,
)
def update_asset_ip_endpoint(
    ip_id: int,
    payload: AssetIPUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetIPRead:
    return update_asset_ip(db, ip_id, payload, current_user)


@router.delete(
    "/api/v1/asset-ips/{ip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_asset_ip_endpoint(
    ip_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_asset_ip(db, ip_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================
# FILE: app/routers/assets.py
# ============================================
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.schemas.asset import AssetCreate, AssetRead, AssetUpdate
from app.services.asset_service import (
    create_asset,
    delete_asset,
    get_asset,
    list_assets,
    update_asset,
)


router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


@router.get("", response_model=list[AssetRead])
def list_assets_endpoint(
    project_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[AssetRead]:
    return list_assets(db, project_id)


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset_endpoint(
    payload: AssetCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetRead:
    return create_asset(db, payload, current_user)


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetRead:
    return get_asset(db, asset_id)


@router.patch("/{asset_id}", response_model=AssetRead)
def update_asset_endpoint(
    asset_id: int,
    payload: AssetUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetRead:
    return update_asset(db, asset_id, payload, current_user)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_asset(db, asset_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================
# FILE: app/routers/contacts.py
# ============================================
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.schemas.contact import ContactCreate, ContactRead, ContactUpdate
from app.services.partner_service import (
    create_contact,
    delete_contact,
    get_contact,
    list_contacts,
    update_contact,
)


router = APIRouter(tags=["contacts"])


@router.get(
    "/api/v1/partners/{partner_id}/contacts",
    response_model=list[ContactRead],
)
def list_contacts_endpoint(
    partner_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ContactRead]:
    return list_contacts(db, partner_id)


@router.post(
    "/api/v1/partners/{partner_id}/contacts",
    response_model=ContactRead,
    status_code=status.HTTP_201_CREATED,
)
def create_contact_endpoint(
    partner_id: int,
    payload: ContactCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ContactRead:
    payload.partner_id = partner_id
    return create_contact(db, payload, current_user)


@router.get(
    "/api/v1/contacts/{contact_id}",
    response_model=ContactRead,
)
def get_contact_endpoint(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ContactRead:
    return get_contact(db, contact_id)


@router.patch(
    "/api/v1/contacts/{contact_id}",
    response_model=ContactRead,
)
def update_contact_endpoint(
    contact_id: int,
    payload: ContactUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ContactRead:
    return update_contact(db, contact_id, payload, current_user)


@router.delete(
    "/api/v1/contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_contact_endpoint(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_contact(db, contact_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================
# FILE: app/routers/ip_subnets.py
# ============================================
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.schemas.ip_subnet import IpSubnetCreate, IpSubnetRead, IpSubnetUpdate
from app.services.network_service import (
    create_subnet,
    delete_subnet,
    get_subnet,
    list_subnets,
    update_subnet,
)


router = APIRouter(tags=["ip-subnets"])


@router.get(
    "/api/v1/projects/{project_id}/ip-subnets",
    response_model=list[IpSubnetRead],
)
def list_subnets_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[IpSubnetRead]:
    return list_subnets(db, project_id)


@router.post(
    "/api/v1/projects/{project_id}/ip-subnets",
    response_model=IpSubnetRead,
    status_code=status.HTTP_201_CREATED,
)
def create_subnet_endpoint(
    project_id: int,
    payload: IpSubnetCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> IpSubnetRead:
    payload.project_id = project_id
    return create_subnet(db, payload, current_user)


@router.get(
    "/api/v1/ip-subnets/{subnet_id}",
    response_model=IpSubnetRead,
)
def get_subnet_endpoint(
    subnet_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> IpSubnetRead:
    return get_subnet(db, subnet_id)


@router.patch(
    "/api/v1/ip-subnets/{subnet_id}",
    response_model=IpSubnetRead,
)
def update_subnet_endpoint(
    subnet_id: int,
    payload: IpSubnetUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> IpSubnetRead:
    return update_subnet(db, subnet_id, payload, current_user)


@router.delete(
    "/api/v1/ip-subnets/{subnet_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_subnet_endpoint(
    subnet_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_subnet(db, subnet_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================
# FILE: app/routers/pages.py
# ============================================
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates


router = APIRouter(tags=["pages"])

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _get_session_user(request: Request) -> dict[str, str] | None:
    login_id = request.session.get("login_id")
    if not login_id:
        return None
    return {
        "login_id": login_id,
        "name": request.session.get("name", login_id),
        "role": request.session.get("role", "user"),
    }


def _require_login(request: Request) -> dict[str, str] | None:
    """세션 사용자를 반환하거나, 미인증이면 None을 반환한다."""
    return _get_session_user(request)


def _page_context(request: Request, active_page: str, **extra: Any) -> dict[str, Any]:
    user = _get_session_user(request)
    return {"request": request, "current_user": user, "active_page": active_page, **extra}


# ── Public routes ──


@router.get("/")
def index(request: Request) -> RedirectResponse:
    if _get_session_user(request) is None:
        return RedirectResponse(url="/login", status_code=302)
    return RedirectResponse(url="/projects", status_code=302)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    if _get_session_user(request) is not None:
        return RedirectResponse(url="/projects", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


# ── Authenticated page routes ──


@router.get("/projects", response_class=HTMLResponse)
def projects_page(request: Request) -> HTMLResponse:
    if _get_session_user(request) is None:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("projects.html", _page_context(request, "projects"))


@router.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail_page(request: Request, project_id: int) -> HTMLResponse:
    if _get_session_user(request) is None:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        "project_detail.html", _page_context(request, "projects", project_id=project_id)
    )


@router.get("/assets", response_class=HTMLResponse)
def assets_page(request: Request) -> HTMLResponse:
    if _get_session_user(request) is None:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("assets.html", _page_context(request, "assets"))


@router.get("/ip-inventory", response_class=HTMLResponse)
def ip_inventory_page(request: Request) -> HTMLResponse:
    if _get_session_user(request) is None:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("ip_inventory.html", _page_context(request, "ip-inventory"))


@router.get("/port-maps", response_class=HTMLResponse)
def port_maps_page(request: Request) -> HTMLResponse:
    if _get_session_user(request) is None:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("port_maps.html", _page_context(request, "port-maps"))


@router.get("/policies", response_class=HTMLResponse)
def policies_page(request: Request) -> HTMLResponse:
    if _get_session_user(request) is None:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("policies.html", _page_context(request, "policies"))


@router.get("/partners", response_class=HTMLResponse)
def partners_page(request: Request) -> HTMLResponse:
    if _get_session_user(request) is None:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("partners.html", _page_context(request, "partners"))


# ============================================
# FILE: app/routers/partners.py
# ============================================
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.schemas.partner import PartnerCreate, PartnerRead, PartnerUpdate
from app.services.partner_service import (
    create_partner,
    delete_partner,
    get_partner,
    list_partners,
    update_partner,
)


router = APIRouter(tags=["partners"])


@router.get(
    "/api/v1/projects/{project_id}/partners",
    response_model=list[PartnerRead],
)
def list_partners_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[PartnerRead]:
    return list_partners(db, project_id)


@router.post(
    "/api/v1/projects/{project_id}/partners",
    response_model=PartnerRead,
    status_code=status.HTTP_201_CREATED,
)
def create_partner_endpoint(
    project_id: int,
    payload: PartnerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PartnerRead:
    payload.project_id = project_id
    return create_partner(db, payload, current_user)


@router.get(
    "/api/v1/partners/{partner_id}",
    response_model=PartnerRead,
)
def get_partner_endpoint(
    partner_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PartnerRead:
    return get_partner(db, partner_id)


@router.patch(
    "/api/v1/partners/{partner_id}",
    response_model=PartnerRead,
)
def update_partner_endpoint(
    partner_id: int,
    payload: PartnerUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PartnerRead:
    return update_partner(db, partner_id, payload, current_user)


@router.delete(
    "/api/v1/partners/{partner_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_partner_endpoint(
    partner_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_partner(db, partner_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================
# FILE: app/routers/policies.py
# ============================================
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.schemas.policy_definition import (
    PolicyDefinitionCreate,
    PolicyDefinitionRead,
    PolicyDefinitionUpdate,
)
from app.services.policy_service import (
    create_policy,
    delete_policy,
    get_policy,
    list_policies,
    update_policy,
)


router = APIRouter(prefix="/api/v1/policies", tags=["policies"])


@router.get("", response_model=list[PolicyDefinitionRead])
def list_policies_endpoint(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[PolicyDefinitionRead]:
    return list_policies(db)


@router.post("", response_model=PolicyDefinitionRead, status_code=status.HTTP_201_CREATED)
def create_policy_endpoint(
    payload: PolicyDefinitionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PolicyDefinitionRead:
    return create_policy(db, payload, current_user)


@router.get("/{policy_id}", response_model=PolicyDefinitionRead)
def get_policy_endpoint(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PolicyDefinitionRead:
    return get_policy(db, policy_id)


@router.patch("/{policy_id}", response_model=PolicyDefinitionRead)
def update_policy_endpoint(
    policy_id: int,
    payload: PolicyDefinitionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PolicyDefinitionRead:
    return update_policy(db, policy_id, payload, current_user)


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy_endpoint(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_policy(db, policy_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================
# FILE: app/routers/policy_assignments.py
# ============================================
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.schemas.policy_assignment import (
    PolicyAssignmentCreate,
    PolicyAssignmentRead,
    PolicyAssignmentUpdate,
)
from app.services.policy_service import (
    create_assignment,
    delete_assignment,
    get_assignment,
    list_assignments,
    update_assignment,
)


router = APIRouter(tags=["policy-assignments"])


@router.get(
    "/api/v1/projects/{project_id}/policy-assignments",
    response_model=list[PolicyAssignmentRead],
)
def list_assignments_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[PolicyAssignmentRead]:
    return list_assignments(db, project_id)


@router.post(
    "/api/v1/projects/{project_id}/policy-assignments",
    response_model=PolicyAssignmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment_endpoint(
    project_id: int,
    payload: PolicyAssignmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PolicyAssignmentRead:
    payload.project_id = project_id
    return create_assignment(db, payload, current_user)


@router.get(
    "/api/v1/policy-assignments/{assignment_id}",
    response_model=PolicyAssignmentRead,
)
def get_assignment_endpoint(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PolicyAssignmentRead:
    return get_assignment(db, assignment_id)


@router.patch(
    "/api/v1/policy-assignments/{assignment_id}",
    response_model=PolicyAssignmentRead,
)
def update_assignment_endpoint(
    assignment_id: int,
    payload: PolicyAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PolicyAssignmentRead:
    return update_assignment(db, assignment_id, payload, current_user)


@router.delete(
    "/api/v1/policy-assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_assignment_endpoint(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_assignment(db, assignment_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================
# FILE: app/routers/port_maps.py
# ============================================
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.schemas.port_map import PortMapCreate, PortMapRead, PortMapUpdate
from app.services.network_service import (
    create_port_map,
    delete_port_map,
    get_port_map,
    list_port_maps,
    update_port_map,
)


router = APIRouter(tags=["port-maps"])


@router.get(
    "/api/v1/projects/{project_id}/port-maps",
    response_model=list[PortMapRead],
)
def list_port_maps_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[PortMapRead]:
    return list_port_maps(db, project_id)


@router.post(
    "/api/v1/projects/{project_id}/port-maps",
    response_model=PortMapRead,
    status_code=status.HTTP_201_CREATED,
)
def create_port_map_endpoint(
    project_id: int,
    payload: PortMapCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PortMapRead:
    payload.project_id = project_id
    return create_port_map(db, payload, current_user)


@router.get(
    "/api/v1/port-maps/{port_map_id}",
    response_model=PortMapRead,
)
def get_port_map_endpoint(
    port_map_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PortMapRead:
    return get_port_map(db, port_map_id)


@router.patch(
    "/api/v1/port-maps/{port_map_id}",
    response_model=PortMapRead,
)
def update_port_map_endpoint(
    port_map_id: int,
    payload: PortMapUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PortMapRead:
    return update_port_map(db, port_map_id, payload, current_user)


@router.delete(
    "/api/v1/port-maps/{port_map_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_port_map_endpoint(
    port_map_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_port_map(db, port_map_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================
# FILE: app/routers/project_deliverables.py
# ============================================
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.schemas.project_deliverable import (
    ProjectDeliverableCreate,
    ProjectDeliverableRead,
    ProjectDeliverableUpdate,
)
from app.services.phase_service import (
    create_deliverable,
    delete_deliverable,
    get_deliverable,
    list_deliverables,
    update_deliverable,
)


router = APIRouter(tags=["project-deliverables"])


@router.get(
    "/api/v1/project-phases/{phase_id}/deliverables",
    response_model=list[ProjectDeliverableRead],
)
def list_deliverables_endpoint(
    phase_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ProjectDeliverableRead]:
    return list_deliverables(db, phase_id)


@router.post(
    "/api/v1/project-phases/{phase_id}/deliverables",
    response_model=ProjectDeliverableRead,
    status_code=status.HTTP_201_CREATED,
)
def create_deliverable_endpoint(
    phase_id: int,
    payload: ProjectDeliverableCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectDeliverableRead:
    payload.project_phase_id = phase_id
    return create_deliverable(db, payload, current_user)


@router.get(
    "/api/v1/project-deliverables/{deliverable_id}",
    response_model=ProjectDeliverableRead,
)
def get_deliverable_endpoint(
    deliverable_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectDeliverableRead:
    return get_deliverable(db, deliverable_id)


@router.patch(
    "/api/v1/project-deliverables/{deliverable_id}",
    response_model=ProjectDeliverableRead,
)
def update_deliverable_endpoint(
    deliverable_id: int,
    payload: ProjectDeliverableUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectDeliverableRead:
    return update_deliverable(db, deliverable_id, payload, current_user)


@router.delete(
    "/api/v1/project-deliverables/{deliverable_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_deliverable_endpoint(
    deliverable_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_deliverable(db, deliverable_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================
# FILE: app/routers/project_phases.py
# ============================================
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.schemas.project_phase import ProjectPhaseCreate, ProjectPhaseRead, ProjectPhaseUpdate
from app.services.phase_service import (
    create_phase,
    delete_phase,
    get_phase,
    list_phases,
    update_phase,
)


router = APIRouter(tags=["project-phases"])


@router.get(
    "/api/v1/projects/{project_id}/phases",
    response_model=list[ProjectPhaseRead],
)
def list_phases_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ProjectPhaseRead]:
    return list_phases(db, project_id)


@router.post(
    "/api/v1/projects/{project_id}/phases",
    response_model=ProjectPhaseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_phase_endpoint(
    project_id: int,
    payload: ProjectPhaseCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectPhaseRead:
    payload.project_id = project_id
    return create_phase(db, payload, current_user)


@router.get(
    "/api/v1/project-phases/{phase_id}",
    response_model=ProjectPhaseRead,
)
def get_phase_endpoint(
    phase_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectPhaseRead:
    return get_phase(db, phase_id)


@router.patch(
    "/api/v1/project-phases/{phase_id}",
    response_model=ProjectPhaseRead,
)
def update_phase_endpoint(
    phase_id: int,
    payload: ProjectPhaseUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectPhaseRead:
    return update_phase(db, phase_id, payload, current_user)


@router.delete(
    "/api/v1/project-phases/{phase_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_phase_endpoint(
    phase_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_phase(db, phase_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================
# FILE: app/routers/projects.py
# ============================================
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.project_service import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)


router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects_endpoint(
    _: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ProjectRead]:
    return list_projects(db)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project_endpoint(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectRead:
    return create_project(db, payload, current_user)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectRead:
    return get_project(db, project_id)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project_endpoint(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectRead:
    return update_project(db, project_id, payload, current_user)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_project(db, project_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================
# FILE: app/routers/sync.py
# ============================================
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.database import get_db
from app.services.sync_service import sync_all


router = APIRouter(tags=["sync"])


@router.post("/api/v1/sync")
def run_sync(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
) -> dict:
    summary = sync_all(db)
    return {
        "partners": {
            "created": summary.partners.created,
            "updated": summary.partners.updated,
            "skipped": summary.partners.skipped,
            "errors": summary.partners.errors,
        },
        "contacts": {
            "created": summary.contacts.created,
            "updated": summary.contacts.updated,
            "skipped": summary.contacts.skipped,
            "errors": summary.contacts.errors,
        },
        "users": {
            "created": summary.users.created,
            "updated": summary.users.updated,
            "skipped": summary.users.skipped,
            "errors": summary.users.errors,
        },
    }


# ============================================
# FILE: app/routers/users.py
# ============================================
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.database import get_db
from app.schemas.user import (
    UserChangePassword,
    UserCreate,
    UserRead,
    UserResetPassword,
    UserUpdate,
)
from app.services.user_service import (
    change_password,
    create_user,
    get_user,
    list_users,
    reset_password,
    update_user,
)


router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users_endpoint(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
) -> list[UserRead]:
    return list_users(db, current_user)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
) -> UserRead:
    return create_user(db, payload, current_user)


@router.get("/{user_id}", response_model=UserRead)
def get_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
) -> UserRead:
    return get_user(db, user_id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user_endpoint(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
) -> UserRead:
    return update_user(db, user_id, payload, current_user)


@router.post("/{user_id}/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password_endpoint(
    user_id: int,
    payload: UserChangePassword,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    change_password(db, user_id, payload, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password_endpoint(
    user_id: int,
    payload: UserResetPassword,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
) -> Response:
    reset_password(db, user_id, payload, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


