"""Infra module: policy service tests (PolicyDefinition, PolicyAssignment)."""
from __future__ import annotations

import pytest

from app.core.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.modules.common.models.customer import Customer
from app.modules.infra.schemas.asset import AssetCreate
from app.modules.infra.schemas.policy_assignment import (
    PolicyAssignmentCreate,
    PolicyAssignmentUpdate,
)
from app.modules.infra.schemas.policy_definition import (
    PolicyDefinitionCreate,
    PolicyDefinitionUpdate,
)
from app.modules.infra.schemas.project import ProjectCreate
from app.modules.infra.services.asset_service import create_asset
from app.modules.infra.services.policy_service import (
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
from app.modules.infra.services.project_service import create_project


def _make_admin_user(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="admin", name="Admin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_regular_user(db_session, user_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="user1", name="User", role_id=user_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_customer(db_session):
    customer = Customer(name="테스트고객", business_no="123-45-67890")
    db_session.add(customer)
    db_session.flush()
    return customer


# ── PolicyDefinition tests ──


def test_create_and_list_policies(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)

    create_policy(
        db_session,
        PolicyDefinitionCreate(
            policy_code="SEC-001", policy_name="방화벽 정책", category="보안"
        ),
        admin,
    )
    create_policy(
        db_session,
        PolicyDefinitionCreate(
            policy_code="SEC-002", policy_name="백업 정책", category="운영"
        ),
        admin,
    )

    policies = list_policies(db_session)
    assert len(policies) == 2
    assert policies[0].policy_code == "SEC-001"


def test_create_policy_rejects_duplicate_code(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)

    create_policy(
        db_session,
        PolicyDefinitionCreate(
            policy_code="SEC-001", policy_name="방화벽 정책", category="보안"
        ),
        admin,
    )

    with pytest.raises(DuplicateError):
        create_policy(
            db_session,
            PolicyDefinitionCreate(
                policy_code="SEC-001", policy_name="Other", category="보안"
            ),
            admin,
        )


def test_create_policy_requires_admin(db_session, admin_role_id, user_role_id) -> None:
    # Ensure admin exists (for role seeding) but use regular user
    regular_user = _make_regular_user(db_session, user_role_id)

    with pytest.raises(PermissionDeniedError):
        create_policy(
            db_session,
            PolicyDefinitionCreate(
                policy_code="SEC-001", policy_name="방화벽 정책", category="보안"
            ),
            regular_user,
        )


def test_update_policy(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)

    policy = create_policy(
        db_session,
        PolicyDefinitionCreate(
            policy_code="SEC-001", policy_name="방화벽 정책", category="보안"
        ),
        admin,
    )

    updated = update_policy(
        db_session,
        policy.id,
        PolicyDefinitionUpdate(policy_name="방화벽 정책 v2", is_active=False),
        admin,
    )

    assert updated.policy_name == "방화벽 정책 v2"
    assert updated.is_active is False


def test_delete_policy_blocked_with_assignments(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    customer = _make_customer(db_session)

    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Test", customer_id=customer.id),
        admin,
    )
    policy = create_policy(
        db_session,
        PolicyDefinitionCreate(
            policy_code="SEC-001", policy_name="방화벽 정책", category="보안"
        ),
        admin,
    )
    create_assignment(
        db_session,
        PolicyAssignmentCreate(
            customer_id=customer.id, policy_definition_id=policy.id
        ),
        admin,
    )

    with pytest.raises(BusinessRuleError):
        delete_policy(db_session, policy.id, admin)


def test_delete_policy_without_assignments(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)

    policy = create_policy(
        db_session,
        PolicyDefinitionCreate(
            policy_code="SEC-001", policy_name="방화벽 정책", category="보안"
        ),
        admin,
    )

    delete_policy(db_session, policy.id, admin)

    with pytest.raises(NotFoundError):
        get_policy(db_session, policy.id)


# ── PolicyAssignment tests ──


def test_create_and_list_assignments(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    customer = _make_customer(db_session)

    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Test", customer_id=customer.id),
        admin,
    )
    policy = create_policy(
        db_session,
        PolicyDefinitionCreate(
            policy_code="SEC-001", policy_name="방화벽 정책", category="보안"
        ),
        admin,
    )

    create_assignment(
        db_session,
        PolicyAssignmentCreate(
            customer_id=customer.id, policy_definition_id=policy.id
        ),
        admin,
    )

    assignments = list_assignments(db_session, customer_id=customer.id)
    assert len(assignments) == 1
    assert assignments[0].status == "not_checked"


def test_create_assignment_with_asset(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    customer = _make_customer(db_session)

    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Test", customer_id=customer.id),
        admin,
    )
    asset = create_asset(
        db_session,
        AssetCreate(
            customer_id=customer.id, asset_name="SRV-01", asset_type="server"
        ),
        admin,
    )
    policy = create_policy(
        db_session,
        PolicyDefinitionCreate(
            policy_code="SEC-001", policy_name="방화벽 정책", category="보안"
        ),
        admin,
    )

    assignment = create_assignment(
        db_session,
        PolicyAssignmentCreate(
            customer_id=customer.id,
            asset_id=asset.id,
            policy_definition_id=policy.id,
        ),
        admin,
    )

    assert assignment.asset_id == asset.id


def test_create_assignment_rejects_asset_from_other_customer(
    db_session, admin_role_id
) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    customer1 = _make_customer(db_session)
    customer2 = Customer(name="다른고객", business_no="999-99-99999")
    db_session.add(customer2)
    db_session.flush()

    project1 = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Test", customer_id=customer1.id),
        admin,
    )
    project2 = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-002", project_name="Other", customer_id=customer2.id),
        admin,
    )
    asset = create_asset(
        db_session,
        AssetCreate(
            customer_id=customer2.id, asset_name="SRV-01", asset_type="server"
        ),
        admin,
    )
    policy = create_policy(
        db_session,
        PolicyDefinitionCreate(
            policy_code="SEC-001", policy_name="방화벽 정책", category="보안"
        ),
        admin,
    )

    with pytest.raises(BusinessRuleError):
        create_assignment(
            db_session,
            PolicyAssignmentCreate(
                customer_id=customer1.id,
                asset_id=asset.id,
                policy_definition_id=policy.id,
            ),
            admin,
        )


def test_create_assignment_rejects_duplicate(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    customer = _make_customer(db_session)

    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Test", customer_id=customer.id),
        admin,
    )
    policy = create_policy(
        db_session,
        PolicyDefinitionCreate(
            policy_code="SEC-001", policy_name="방화벽 정책", category="보안"
        ),
        admin,
    )

    create_assignment(
        db_session,
        PolicyAssignmentCreate(
            customer_id=customer.id, policy_definition_id=policy.id
        ),
        admin,
    )

    with pytest.raises(DuplicateError):
        create_assignment(
            db_session,
            PolicyAssignmentCreate(
                customer_id=customer.id, policy_definition_id=policy.id
            ),
            admin,
        )


def test_update_assignment(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    customer = _make_customer(db_session)

    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Test", customer_id=customer.id),
        admin,
    )
    policy = create_policy(
        db_session,
        PolicyDefinitionCreate(
            policy_code="SEC-001", policy_name="방화벽 정책", category="보안"
        ),
        admin,
    )
    assignment = create_assignment(
        db_session,
        PolicyAssignmentCreate(
            customer_id=customer.id, policy_definition_id=policy.id
        ),
        admin,
    )

    updated = update_assignment(
        db_session,
        assignment.id,
        PolicyAssignmentUpdate(
            status="compliant", checked_by="admin", evidence_note="확인 완료"
        ),
        admin,
    )

    assert updated.status == "compliant"
    assert updated.checked_by == "admin"


def test_delete_assignment(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    customer = _make_customer(db_session)

    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Test", customer_id=customer.id),
        admin,
    )
    policy = create_policy(
        db_session,
        PolicyDefinitionCreate(
            policy_code="SEC-001", policy_name="방화벽 정책", category="보안"
        ),
        admin,
    )
    assignment = create_assignment(
        db_session,
        PolicyAssignmentCreate(
            customer_id=customer.id, policy_definition_id=policy.id
        ),
        admin,
    )

    delete_assignment(db_session, assignment.id, admin)

    with pytest.raises(NotFoundError):
        get_assignment(db_session, assignment.id)
