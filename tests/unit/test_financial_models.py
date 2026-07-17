from pe_analyst.engines.financial import (
    FinancialStatement,
)


def test_financial_statement():
    statement = FinancialStatement(
        revenue=1000,
        cost_of_goods_sold=500,
        ebitda=250,
        ebit=200,
        net_income=150,
        operating_cash_flow=180,
        capital_expenditure=50,
        total_assets=1200,
        shareholders_equity=700,
        total_debt=300,
        interest_expense=20,
        current_assets=500,
        inventory=80,
        current_liabilities=250,
    )

    assert statement.revenue == 1000
    assert statement.ebitda == 250