"""Infra module: phase and deliverable service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError
from app.modules.common.models.contract import Contract
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.common.models.partner import Partner
from app.modules.infra.schemas.period_deliverable import (
    PeriodDeliverableCreate,
    PeriodDeliverableUpdate,
)
from app.modules.infra.schemas.period_phase import (
    PeriodPhaseCreate,
    PeriodPhaseUpdate,
)
from app.modules.infra.services.phase_service import (
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


def _make_admin_user(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="admin", name="Admin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_partner(db_session):
    partner = Partner(name="테스트고객", business_no="123-45-67890")
    db_session.add(partner)
    db_session.flush()
    return partner


def _make_period(db_session, admin) -> ContractPeriod:
    """Create a Contract + ContractPeriod and return the period."""
    partner = _make_partner(db_session)
    contract = Contract(
        contract_name="Test Contract",
        contract_type="인프라",
        end_partner_id=partner.id,
    )
    db_session.add(contract)
    db_session.flush()
    period = ContractPeriod(
        contract_id=contract.id,
        period_year=2025,
        period_label="Y25",
        stage="50%",
        partner_id=partner.id,
    )
    db_session.add(period)
    db_session.commit()
    db_session.refresh(period)
    return period


# -- PeriodPhase tests --


def test_create_and_list_phases(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    period = _make_period(db_session, admin)

    create_phase(
        db_session,
        PeriodPhaseCreate(contract_period_id=period.id, phase_type="analysis"),
        admin,
    )
    create_phase(
        db_session,
        PeriodPhaseCreate(contract_period_id=period.id, phase_type="design"),
        admin,
    )

    phases = list_phases(db_session, period.id)
    assert len(phases) == 2
    assert phases[0].phase_type == "analysis"
    assert phases[1].phase_type == "design"


def test_create_phase_requires_existing_period(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    with pytest.raises(NotFoundError):
        create_phase(
            db_session,
            PeriodPhaseCreate(contract_period_id=9999, phase_type="analysis"),
            admin,
        )


def test_create_phase_rejects_duplicate_type_in_same_period(
    db_session, admin_role_id
) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    period = _make_period(db_session, admin)

    create_phase(
        db_session,
        PeriodPhaseCreate(contract_period_id=period.id, phase_type="analysis"),
        admin,
    )

    with pytest.raises(DuplicateError):
        create_phase(
            db_session,
            PeriodPhaseCreate(contract_period_id=period.id, phase_type="analysis"),
            admin,
        )


def test_update_phase(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    period = _make_period(db_session, admin)
    phase = create_phase(
        db_session,
        PeriodPhaseCreate(contract_period_id=period.id, phase_type="analysis"),
        admin,
    )

    updated = update_phase(
        db_session,
        phase.id,
        PeriodPhaseUpdate(status="in_progress", task_scope="Full analysis"),
        admin,
    )

    assert updated.status == "in_progress"
    assert updated.task_scope == "Full analysis"


def test_delete_phase_blocked_with_deliverables(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    period = _make_period(db_session, admin)
    phase = create_phase(
        db_session,
        PeriodPhaseCreate(contract_period_id=period.id, phase_type="analysis"),
        admin,
    )
    create_deliverable(
        db_session,
        PeriodDeliverableCreate(period_phase_id=phase.id, name="Report"),
        admin,
    )

    with pytest.raises(BusinessRuleError):
        delete_phase(db_session, phase.id, admin)


def test_delete_phase_without_deliverables(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    period = _make_period(db_session, admin)
    phase = create_phase(
        db_session,
        PeriodPhaseCreate(contract_period_id=period.id, phase_type="analysis"),
        admin,
    )

    delete_phase(db_session, phase.id, admin)

    with pytest.raises(NotFoundError):
        get_phase(db_session, phase.id)


# -- PeriodDeliverable tests --


def test_create_and_list_deliverables(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    period = _make_period(db_session, admin)
    phase = create_phase(
        db_session,
        PeriodPhaseCreate(contract_period_id=period.id, phase_type="analysis"),
        admin,
    )

    create_deliverable(
        db_session,
        PeriodDeliverableCreate(
            period_phase_id=phase.id, name="Analysis Report"
        ),
        admin,
    )
    create_deliverable(
        db_session,
        PeriodDeliverableCreate(
            period_phase_id=phase.id, name="Requirements Doc"
        ),
        admin,
    )

    deliverables = list_deliverables(db_session, phase.id)
    assert len(deliverables) == 2
    assert deliverables[0].name == "Analysis Report"


def test_create_deliverable_requires_existing_phase(
    db_session, admin_role_id
) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    with pytest.raises(NotFoundError):
        create_deliverable(
            db_session,
            PeriodDeliverableCreate(period_phase_id=9999, name="Report"),
            admin,
        )


def test_update_deliverable(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    period = _make_period(db_session, admin)
    phase = create_phase(
        db_session,
        PeriodPhaseCreate(contract_period_id=period.id, phase_type="analysis"),
        admin,
    )
    deliverable = create_deliverable(
        db_session,
        PeriodDeliverableCreate(period_phase_id=phase.id, name="Report"),
        admin,
    )

    updated = update_deliverable(
        db_session,
        deliverable.id,
        PeriodDeliverableUpdate(is_submitted=True, note="Submitted to client"),
        admin,
    )

    assert updated.is_submitted is True
    assert updated.note == "Submitted to client"


def test_delete_deliverable(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    period = _make_period(db_session, admin)
    phase = create_phase(
        db_session,
        PeriodPhaseCreate(contract_period_id=period.id, phase_type="analysis"),
        admin,
    )
    deliverable = create_deliverable(
        db_session,
        PeriodDeliverableCreate(period_phase_id=phase.id, name="Report"),
        admin,
    )

    delete_deliverable(db_session, deliverable.id, admin)

    with pytest.raises(NotFoundError):
        get_deliverable(db_session, deliverable.id)
