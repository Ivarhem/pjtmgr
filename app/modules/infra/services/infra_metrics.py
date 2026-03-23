"""Infra module metrics / aggregation service for dashboard and summary cards."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.common.models.audit_log import AuditLog
from app.modules.common.models.user import User
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_ip import AssetIP
from app.modules.infra.models.policy_assignment import PolicyAssignment
from app.modules.infra.models.project import Project
from app.modules.infra.models.project_asset import ProjectAsset
from app.modules.infra.models.project_deliverable import ProjectDeliverable
from app.modules.infra.models.project_phase import ProjectPhase


def get_project_summary(db: Session, project_id: int) -> dict:
    """Single project summary: asset count, IP count, policy compliance, deliverable progress."""
    # Asset count via ProjectAsset N:M
    asset_ids_q = select(ProjectAsset.asset_id).where(ProjectAsset.project_id == project_id)

    asset_count = db.scalar(
        select(func.count()).select_from(ProjectAsset).where(
            ProjectAsset.project_id == project_id
        )
    ) or 0

    ip_count = db.scalar(
        select(func.count())
        .select_from(AssetIP)
        .join(Asset, AssetIP.asset_id == Asset.id)
        .where(Asset.id.in_(asset_ids_q))
    ) or 0

    compliance = get_policy_compliance_rate(db, project_id)

    # Deliverable progress
    phase_ids = list(
        db.scalars(select(ProjectPhase.id).where(ProjectPhase.project_id == project_id))
    )
    if phase_ids:
        total_del = db.scalar(
            select(func.count()).where(ProjectDeliverable.project_phase_id.in_(phase_ids))
        ) or 0
        submitted_del = db.scalar(
            select(func.count()).where(
                ProjectDeliverable.project_phase_id.in_(phase_ids),
                ProjectDeliverable.is_submitted.is_(True),
            )
        ) or 0
    else:
        total_del = submitted_del = 0

    # Current phase (first in_progress, or last)
    current_phase = db.scalar(
        select(ProjectPhase.phase_type)
        .where(ProjectPhase.project_id == project_id, ProjectPhase.status == "in_progress")
        .limit(1)
    )

    project = db.get(Project, project_id)

    return {
        "project_id": project_id,
        "project_code": project.project_code if project else "",
        "project_name": project.project_name if project else "",
        "status": project.status if project else "",
        "customer_id": project.customer_id if project else None,
        "asset_count": asset_count,
        "ip_count": ip_count,
        "compliance_rate": compliance,
        "deliverable_total": total_del,
        "deliverable_submitted": submitted_del,
        "current_phase": current_phase,
    }


def list_projects_summary(
    db: Session, customer_id: int | None = None
) -> list[dict]:
    """All projects summary list for dashboard. Optionally filtered by customer."""
    stmt = select(Project.id).order_by(Project.id)
    if customer_id is not None:
        stmt = stmt.where(Project.customer_id == customer_id)
    project_ids = list(db.scalars(stmt))
    return [get_project_summary(db, pid) for pid in project_ids]


def get_policy_compliance_rate(db: Session, project_id: int) -> float:
    """Policy compliance rate = compliant / (total - not_applicable) * 100.

    Scoped to assets linked to the project via ProjectAsset.
    """
    asset_ids_q = select(ProjectAsset.asset_id).where(ProjectAsset.project_id == project_id)

    total = db.scalar(
        select(func.count()).where(PolicyAssignment.asset_id.in_(asset_ids_q))
    ) or 0
    not_applicable = db.scalar(
        select(func.count()).where(
            PolicyAssignment.asset_id.in_(asset_ids_q),
            PolicyAssignment.status == "not_applicable",
        )
    ) or 0
    compliant = db.scalar(
        select(func.count()).where(
            PolicyAssignment.asset_id.in_(asset_ids_q),
            PolicyAssignment.status == "compliant",
        )
    ) or 0

    denominator = total - not_applicable
    if denominator <= 0:
        return 0.0
    return round(compliant / denominator * 100, 1)


def get_unsubmitted_deliverables(db: Session, customer_id: int | None = None) -> list[dict]:
    """Unsubmitted deliverables in in_progress phases."""
    stmt = (
        select(
            ProjectDeliverable.id,
            ProjectDeliverable.name,
            ProjectDeliverable.project_phase_id,
            ProjectPhase.phase_type,
            ProjectPhase.project_id,
            Project.project_code,
            Project.project_name,
        )
        .join(ProjectPhase, ProjectDeliverable.project_phase_id == ProjectPhase.id)
        .join(Project, ProjectPhase.project_id == Project.id)
        .where(
            ProjectPhase.status == "in_progress",
            ProjectDeliverable.is_submitted.is_(False),
        )
        .order_by(Project.project_code, ProjectPhase.phase_type, ProjectDeliverable.name)
    )
    if customer_id is not None:
        stmt = stmt.where(Project.customer_id == customer_id)
    rows = db.execute(stmt).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "phase_type": r.phase_type,
            "project_id": r.project_id,
            "project_code": r.project_code,
            "project_name": r.project_name,
        }
        for r in rows
    ]


def get_non_compliant_assignments(db: Session, customer_id: int | None = None) -> list[dict]:
    """Policy assignments with non_compliant status. Optionally filtered by customer."""
    from app.modules.common.models.customer import Customer

    stmt = (
        select(
            PolicyAssignment.id,
            PolicyAssignment.customer_id,
            PolicyAssignment.asset_id,
            PolicyAssignment.status,
            PolicyAssignment.exception_reason,
            PolicyAssignment.checked_by,
            PolicyAssignment.checked_date,
            Customer.name.label("customer_name"),
        )
        .join(Customer, PolicyAssignment.customer_id == Customer.id)
        .where(PolicyAssignment.status == "non_compliant")
    )
    if customer_id is not None:
        stmt = stmt.where(PolicyAssignment.customer_id == customer_id)
    stmt = stmt.order_by(Customer.name, PolicyAssignment.id)
    rows = db.execute(stmt).all()
    return [
        {
            "id": r.id,
            "customer_id": r.customer_id,
            "customer_name": r.customer_name,
            "asset_id": r.asset_id,
            "status": r.status,
            "exception_reason": r.exception_reason,
            "checked_by": r.checked_by,
            "checked_date": str(r.checked_date) if r.checked_date else None,
        }
        for r in rows
    ]


def list_audit_logs(
    db: Session,
    *,
    module: str,
    project_id: int | None = None,
    limit: int = 100,
) -> list[dict]:
    """List audit logs with lightweight user-name enrichment."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.module == module)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    if project_id is not None:
        stmt = stmt.where(AuditLog.entity_type == "project", AuditLog.entity_id == project_id)

    logs = list(db.scalars(stmt))
    user_ids = {log.user_id for log in logs if log.user_id}
    users: dict[int, str] = {}
    if user_ids:
        users = {
            user.id: user.name
            for user in db.scalars(select(User).where(User.id.in_(user_ids)))
        }

    return [
        {
            "id": log.id,
            "user_name": users.get(log.user_id, "-"),
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "summary": log.summary,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
