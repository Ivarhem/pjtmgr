"""Infra module metrics / aggregation service for dashboard and summary cards."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.common.models.audit_log import AuditLog
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.common.models.user import User
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_ip import AssetIP
from app.modules.infra.models.period_asset import PeriodAsset
from app.modules.infra.models.period_deliverable import PeriodDeliverable
from app.modules.infra.models.period_phase import PeriodPhase
from app.modules.infra.models.policy_assignment import PolicyAssignment


def get_period_summary(db: Session, contract_period_id: int) -> dict:
    """Single contract period summary: asset count, IP count, policy compliance, deliverable progress."""
    # Asset count via PeriodAsset N:M
    asset_ids_q = select(PeriodAsset.asset_id).where(PeriodAsset.contract_period_id == contract_period_id)

    asset_count = db.scalar(
        select(func.count()).select_from(PeriodAsset).where(
            PeriodAsset.contract_period_id == contract_period_id
        )
    ) or 0

    ip_count = db.scalar(
        select(func.count())
        .select_from(AssetIP)
        .join(Asset, AssetIP.asset_id == Asset.id)
        .where(Asset.id.in_(asset_ids_q))
    ) or 0

    compliance = get_policy_compliance_rate(db, contract_period_id)

    # Deliverable progress
    phase_ids = list(
        db.scalars(select(PeriodPhase.id).where(PeriodPhase.contract_period_id == contract_period_id))
    )
    if phase_ids:
        total_del = db.scalar(
            select(func.count()).where(PeriodDeliverable.period_phase_id.in_(phase_ids))
        ) or 0
        submitted_del = db.scalar(
            select(func.count()).where(
                PeriodDeliverable.period_phase_id.in_(phase_ids),
                PeriodDeliverable.is_submitted.is_(True),
            )
        ) or 0
    else:
        total_del = submitted_del = 0

    # Current phase (first in_progress, or last)
    current_phase = db.scalar(
        select(PeriodPhase.phase_type)
        .where(PeriodPhase.contract_period_id == contract_period_id, PeriodPhase.status == "in_progress")
        .limit(1)
    )

    period = db.get(ContractPeriod, contract_period_id)

    return {
        "contract_period_id": contract_period_id,
        "period_label": period.period_label if period else "",
        "stage": period.stage if period else "",
        "customer_id": period.customer_id if period else None,
        "asset_count": asset_count,
        "ip_count": ip_count,
        "compliance_rate": compliance,
        "deliverable_total": total_del,
        "deliverable_submitted": submitted_del,
        "current_phase": current_phase,
    }


def list_periods_summary(
    db: Session, customer_id: int | None = None
) -> list[dict]:
    """All contract periods summary list for dashboard. Optionally filtered by customer."""
    stmt = select(ContractPeriod.id).order_by(ContractPeriod.id)
    if customer_id is not None:
        stmt = stmt.where(ContractPeriod.customer_id == customer_id)
    period_ids = list(db.scalars(stmt))
    return [get_period_summary(db, pid) for pid in period_ids]


def get_policy_compliance_rate(db: Session, contract_period_id: int) -> float:
    """Policy compliance rate = compliant / (total - not_applicable) * 100.

    Scoped to assets linked to the period via PeriodAsset.
    """
    asset_ids_q = select(PeriodAsset.asset_id).where(PeriodAsset.contract_period_id == contract_period_id)

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
            PeriodDeliverable.id,
            PeriodDeliverable.name,
            PeriodDeliverable.period_phase_id,
            PeriodPhase.phase_type,
            PeriodPhase.contract_period_id,
            ContractPeriod.period_label,
        )
        .join(PeriodPhase, PeriodDeliverable.period_phase_id == PeriodPhase.id)
        .join(ContractPeriod, PeriodPhase.contract_period_id == ContractPeriod.id)
        .where(
            PeriodPhase.status == "in_progress",
            PeriodDeliverable.is_submitted.is_(False),
        )
        .order_by(ContractPeriod.period_label, PeriodPhase.phase_type, PeriodDeliverable.name)
    )
    if customer_id is not None:
        stmt = stmt.where(ContractPeriod.customer_id == customer_id)
    rows = db.execute(stmt).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "phase_type": r.phase_type,
            "contract_period_id": r.contract_period_id,
            "period_label": r.period_label,
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
    contract_period_id: int | None = None,
    limit: int = 100,
) -> list[dict]:
    """List audit logs with lightweight user-name enrichment."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.module == module)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    if contract_period_id is not None:
        stmt = stmt.where(AuditLog.entity_type == "contract_period", AuditLog.entity_id == contract_period_id)

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
