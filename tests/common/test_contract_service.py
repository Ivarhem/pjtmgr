"""Common Contract/ContractPeriod CRUD tests.

Note: These tests require a PostgreSQL test database. Tests that need DB
interaction are structured but marked with a note about DB dependency.
"""
from __future__ import annotations

import pytest

from app.modules.common.schemas.contract import ContractCreate, ContractUpdate
from app.modules.common.schemas.contract_period import ContractPeriodCreate, ContractPeriodUpdate


class TestContractCRUD:
    def test_create_contract_basic(self, db_session, admin_role_id):
        """Contract 생성 시 기본 필드가 올바르게 설정되는지 확인."""
        from app.modules.common.services.contract_service import create_contract

        result = create_contract(
            db_session,
            ContractCreate(contract_name="테스트사업", contract_type="인프라"),
        )
        assert result["contract_name"] == "테스트사업"
        assert result["contract_type"] == "인프라"
        assert result["status"] == "active"

    def test_create_contract_validates_type(self, db_session, admin_role_id):
        """유효하지 않은 contract_type 처리 확인 (Pydantic 검증 또는 서비스 규칙)."""
        # ContractCreate의 contract_type은 str이므로 서비스 레이어에서 검증할 수도 있음.
        # 현재 ContractCreate는 임의 str을 허용하므로 이 테스트는 placeholder.
        pass

    def test_delete_contract_sets_cancelled(self, db_session, admin_role_id):
        """Contract 삭제 시 status가 cancelled로 변경."""
        from app.modules.common.services.contract_service import (
            create_contract,
            delete_contract,
            get_contract,
        )

        result = create_contract(
            db_session,
            ContractCreate(contract_name="삭제대상", contract_type="인프라"),
        )
        contract_id = result["id"]
        delete_contract(db_session, contract_id)
        updated = get_contract(db_session, contract_id)
        assert updated["status"] == "cancelled"

    def test_restore_contract(self, db_session, admin_role_id):
        """cancelled 상태의 Contract 복구."""
        from app.modules.common.services.contract_service import (
            create_contract,
            delete_contract,
            restore_contract,
        )

        result = create_contract(
            db_session,
            ContractCreate(contract_name="복구대상", contract_type="인프라"),
        )
        contract_id = result["id"]
        delete_contract(db_session, contract_id)
        restored = restore_contract(db_session, contract_id)
        assert restored["status"] == "active"


class TestContractPeriodCRUD:
    def test_create_period_basic(self, db_session, admin_role_id):
        """Period 생성 기본 동작."""
        from app.modules.common.services.contract_service import (
            create_contract,
            create_period,
        )

        contract = create_contract(
            db_session,
            ContractCreate(contract_name="기간사업", contract_type="인프라"),
        )
        period = create_period(
            db_session,
            contract["id"],
            ContractPeriodCreate(period_year=2025),
        )
        assert period["period_year"] == 2025
        assert period["contract_id"] == contract["id"]
        assert period["period_label"] == "Y25"

    def test_create_period_inherits_owner(self, db_session, admin_role_id):
        """Period 생성 시 owner_user_id 미지정이면 Contract에서 상속."""
        from app.modules.common.models.user import User
        from app.modules.common.services.contract_service import (
            create_contract,
            create_period,
        )

        user = User(login_id="owner", name="Owner", role_id=admin_role_id)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        contract = create_contract(
            db_session,
            ContractCreate(
                contract_name="소유자사업",
                contract_type="인프라",
                owner_user_id=user.id,
            ),
        )
        period = create_period(
            db_session,
            contract["id"],
            ContractPeriodCreate(period_year=2025),
        )
        assert period["owner_user_id"] == user.id

    def test_delete_last_period_cancels_contract(self, db_session, admin_role_id):
        """마지막 Period 삭제 시 Contract status가 cancelled로 변경."""
        from app.modules.common.services.contract_service import (
            create_contract,
            create_period,
            delete_period,
            get_contract,
        )

        contract = create_contract(
            db_session,
            ContractCreate(contract_name="단일기간사업", contract_type="인프라"),
        )
        period = create_period(
            db_session,
            contract["id"],
            ContractPeriodCreate(period_year=2025),
        )
        delete_period(db_session, period["id"])
        updated = get_contract(db_session, contract["id"])
        assert updated["status"] == "cancelled"

    def test_list_periods_by_customer_id(self, db_session, admin_role_id):
        """list_periods(customer_id=X) 필터링 확인."""
        from app.modules.common.models.customer import Customer
        from app.modules.common.services.contract_service import (
            create_contract,
            create_period,
            list_periods,
        )

        cust_a = Customer(name="PeriodCustA")
        cust_b = Customer(name="PeriodCustB")
        db_session.add_all([cust_a, cust_b])
        db_session.commit()

        c1 = create_contract(
            db_session,
            ContractCreate(contract_name="A사업", contract_type="인프라", end_customer_id=cust_a.id),
        )
        c2 = create_contract(
            db_session,
            ContractCreate(contract_name="B사업", contract_type="인프라", end_customer_id=cust_b.id),
        )

        create_period(
            db_session, c1["id"],
            ContractPeriodCreate(period_year=2025, customer_id=cust_a.id),
        )
        create_period(
            db_session, c2["id"],
            ContractPeriodCreate(period_year=2025, customer_id=cust_b.id),
        )

        periods_a = list_periods(db_session, customer_id=cust_a.id)
        assert len(periods_a) == 1
        assert periods_a[0]["customer_id"] == cust_a.id
