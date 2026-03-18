from app.modules.accounting.models.contract import Contract
from app.modules.accounting.models.contract_period import ContractPeriod
from app.modules.common.models.customer import Customer
from app.modules.accounting.models.monthly_forecast import MonthlyForecast
from app.modules.accounting.models.transaction_line import STATUS_CONFIRMED, TransactionLine
from app.modules.common.models.user import User
from app.modules.accounting.services import dashboard as dashboard_service


def test_target_vs_actual_splits_planned_unplanned_and_lost_revenue(db_session) -> None:
    owner = User(name="담당", login_id="owner", role="user")
    customer = Customer(name="고객사")
    db_session.add_all([owner, customer])
    db_session.flush()

    planned_contract = Contract(
        contract_name="계획 사업",
        contract_type="MA",
        contract_code="MA-2026-0001",
        owner_user_id=owner.id,
        end_customer_id=customer.id,
        status="active",
    )
    unplanned_contract = Contract(
        contract_name="신규 사업",
        contract_type="MA",
        contract_code="MA-2026-0002",
        owner_user_id=owner.id,
        end_customer_id=customer.id,
        status="active",
    )
    lost_contract = Contract(
        contract_name="실주 사업",
        contract_type="MA",
        contract_code="MA-2026-0003",
        owner_user_id=owner.id,
        end_customer_id=customer.id,
        status="active",
    )
    db_session.add_all([planned_contract, unplanned_contract, lost_contract])
    db_session.flush()

    planned_period = ContractPeriod(
        contract_id=planned_contract.id,
        period_year=2026,
        period_label="Y26P",
        stage="70%",
        is_planned=True,
        start_month="2026-01-01",
        end_month="2026-03-01",
    )
    unplanned_period = ContractPeriod(
        contract_id=unplanned_contract.id,
        period_year=2026,
        period_label="Y26N",
        stage="70%",
        is_planned=False,
        start_month="2026-01-01",
        end_month="2026-03-01",
    )
    lost_period = ContractPeriod(
        contract_id=lost_contract.id,
        period_year=2026,
        period_label="Y26L",
        stage="실주",
        is_planned=True,
        start_month="2026-01-01",
        end_month="2026-03-01",
    )
    db_session.add_all([planned_period, unplanned_period, lost_period])
    db_session.flush()

    db_session.add_all(
        [
            MonthlyForecast(
                contract_period_id=planned_period.id,
                forecast_month="2026-01-01",
                revenue_amount=100,
                gp_amount=20,
            ),
            MonthlyForecast(
                contract_period_id=lost_period.id,
                forecast_month="2026-01-01",
                revenue_amount=50,
                gp_amount=10,
            ),
            TransactionLine(
                contract_id=planned_contract.id,
                revenue_month="2026-01-01",
                line_type="revenue",
                customer_id=customer.id,
                supply_amount=80,
                status=STATUS_CONFIRMED,
                created_by=owner.id,
            ),
            TransactionLine(
                contract_id=unplanned_contract.id,
                revenue_month="2026-01-01",
                line_type="revenue",
                customer_id=customer.id,
                supply_amount=30,
                status=STATUS_CONFIRMED,
                created_by=owner.id,
            ),
        ]
    )
    db_session.commit()

    response = dashboard_service.get_target_vs_actual(
        db_session,
        date_from="2026-01",
        date_to="2026-03",
        group_by="month",
        current_user=owner,
    )

    january = response.rows[0]
    assert january.label == "2026-01"
    assert january.target_revenue == 150
    assert january.actual_revenue == 110
    assert january.planned_actual_revenue == 80
    assert january.unplanned_actual_revenue == 30
    assert january.lost_revenue == 50
    assert january.gap == 40
    assert january.achievement_rate == 73.3

    assert response.totals.target_revenue == 150
    assert response.totals.actual_revenue == 110
    assert response.totals.lost_revenue == 50


def test_dashboard_summary_regroups_monthly_trend_by_quarter(db_session) -> None:
    owner = User(name="담당2", login_id="owner2", role="user")
    customer = Customer(name="고객사2")
    db_session.add_all([owner, customer])
    db_session.flush()

    contract = Contract(
        contract_name="분기 집계 사업",
        contract_type="MA",
        contract_code="MA-2026-0004",
        owner_user_id=owner.id,
        end_customer_id=customer.id,
        status="active",
    )
    db_session.add(contract)
    db_session.flush()

    period = ContractPeriod(
        contract_id=contract.id,
        period_year=2026,
        period_label="Y26Q",
        stage="70%",
        is_planned=True,
        start_month="2026-01-01",
        end_month="2026-06-01",
    )
    db_session.add(period)
    db_session.flush()

    db_session.add_all(
        [
            MonthlyForecast(contract_period_id=period.id, forecast_month="2026-01-01", revenue_amount=100, gp_amount=20),
            MonthlyForecast(contract_period_id=period.id, forecast_month="2026-02-01", revenue_amount=150, gp_amount=30),
            MonthlyForecast(contract_period_id=period.id, forecast_month="2026-04-01", revenue_amount=200, gp_amount=40),
            TransactionLine(
                contract_id=contract.id,
                revenue_month="2026-01-01",
                line_type="revenue",
                customer_id=customer.id,
                supply_amount=90,
                status=STATUS_CONFIRMED,
                created_by=owner.id,
            ),
            TransactionLine(
                contract_id=contract.id,
                revenue_month="2026-04-01",
                line_type="revenue",
                customer_id=customer.id,
                supply_amount=180,
                status=STATUS_CONFIRMED,
                created_by=owner.id,
            ),
        ]
    )
    db_session.commit()

    response = dashboard_service.get_dashboard(
        db_session,
        date_from="2026-01",
        date_to="2026-06",
        group_by="quarter",
        current_user=owner,
    )

    assert [row["month"] for row in response["trend"]] == ["Q1", "Q2"]
    assert response["trend"][0]["forecast_revenue"] == 250
    assert response["trend"][0]["planned_forecast"] == 250
    assert response["trend"][0]["actual_revenue"] == 90
    assert response["trend"][1]["forecast_revenue"] == 200
    assert response["trend"][1]["actual_revenue"] == 180
