"""Build document-extraction eval cases from SEC EDGAR 10-K filings (free, no API key).

For each ticker it:
  1. downloads the 10-K's primary HTML document for the fiscal year,
  2. converts it to PDF with headless Edge/Chrome if one is installed,
  3. reads the filing's own XBRL facts (companyfacts API) as ground truth,
  4. writes datasets/document_extraction/<ticker>_<fy>.json.

XBRL is what the company itself tagged in that filing, so the expected values need no manual
labelling. SEC requires a User-Agent with contact details: set SEC_USER_AGENT in .env, e.g.
"PE-Analyst you@example.com".

Usage:
    python scripts/build_edgar_cases.py MSFT ADBE CRM --fiscal-year 2024
    python scripts/build_edgar_cases.py NKE --fiscal-year 2024 --split holdout
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from pe_analyst.core.config import get_settings
from pe_analyst.evaluation import DATASETS_DIR

# FinancialStatement field -> XBRL us-gaap tags, most preferred first.
XBRL_TAGS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
    ),
    "cost_of_goods_sold": ("CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"),
    "ebit": ("OperatingIncomeLoss",),
    "net_income": ("NetIncomeLoss", "ProfitLoss"),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "capital_expenditure": ("PaymentsToAcquirePropertyPlantAndEquipment",),
    "total_assets": ("Assets",),
    "shareholders_equity": ("StockholdersEquity",),
    "total_debt": ("LongTermDebt", "DebtInstrumentCarryingAmount", "LongTermDebtNoncurrent"),
    "interest_expense": ("InterestExpense", "InterestExpenseNonoperating"),
    "current_assets": ("AssetsCurrent",),
    "inventory": ("InventoryNet",),
    "current_liabilities": ("LiabilitiesCurrent",),
}

_BROWSERS = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "msedge",
    "google-chrome",
    "chromium",
    "chrome",
)


def sec_client() -> httpx.Client:
    agent = get_settings().sec_user_agent
    if not agent or "example.com" in agent:
        sys.exit("Set SEC_USER_AGENT in .env to 'PE-Analyst <your email>' (SEC requires it).")
    return httpx.Client(headers={"User-Agent": agent}, timeout=60.0, follow_redirects=True)


def get_json(client: httpx.Client, url: str) -> Any:
    time.sleep(0.15)  # SEC fair-access limit is 10 requests/second
    response = client.get(url)
    response.raise_for_status()
    return response.json()


def lookup_cik(client: httpx.Client, ticker: str) -> int:
    tickers = get_json(client, "https://www.sec.gov/files/company_tickers.json")
    for entry in tickers.values():
        if entry["ticker"].upper() == ticker.upper():
            return int(entry["cik_str"])
    raise SystemExit(f"Ticker {ticker} not found on EDGAR")


def find_10k(submissions: dict[str, Any], fiscal_year: int) -> dict[str, str]:
    """The 10-K whose fiscal year (per its XBRL facts) is ``fiscal_year``."""

    recent = submissions["filings"]["recent"]
    candidates = [
        {
            "accession": recent["accessionNumber"][index],
            "primary_document": recent["primaryDocument"][index],
            "report_date": recent["reportDate"][index],
        }
        for index, form in enumerate(recent["form"])
        if form == "10-K"
    ]
    # A fiscal year's 10-K reports a period ending in that year (or early next for 52/53 weeks).
    for candidate in candidates:
        if candidate["report_date"].startswith(str(fiscal_year)):
            return candidate
    for candidate in candidates:
        if candidate["report_date"].startswith(str(fiscal_year + 1) + "-0"):
            return candidate
    raise SystemExit(f"No 10-K found for fiscal year {fiscal_year}")


def _duration_days(fact: dict[str, Any]) -> int | None:
    if "start" not in fact:
        return None
    return (date.fromisoformat(fact["end"]) - date.fromisoformat(fact["start"])).days


def facts_for_filing(
    companyfacts: dict[str, Any], accession: str
) -> tuple[dict[str, float], dict[str, float], list[str]]:
    """(current, previous, notes) values reported in the given 10-K."""

    gaap = companyfacts["facts"].get("us-gaap", {})
    current: dict[str, float] = {}
    previous: dict[str, float] = {}
    notes: list[str] = []

    def periods(tag: str) -> list[dict[str, Any]]:
        units = gaap.get(tag, {}).get("units", {}).get("USD", [])
        filed = [fact for fact in units if fact.get("accn") == accession]
        annual = [
            fact for fact in filed if _duration_days(fact) is None or _duration_days(fact) > 300
        ]
        unique = {fact["end"]: fact for fact in annual}
        return sorted(unique.values(), key=lambda fact: fact["end"], reverse=True)

    for name, tags in XBRL_TAGS.items():
        for tag in tags:
            values = periods(tag)
            if values:
                current[name] = float(values[0]["val"])
                if len(values) > 1:
                    previous[name] = float(values[1]["val"])
                notes.append(f"{name} <- us-gaap:{tag}")
                break

    depreciation = periods("DepreciationDepletionAndAmortization") or periods(
        "DepreciationAndAmortization"
    )
    if depreciation and "ebit" in current:
        current["ebitda"] = current["ebit"] + float(depreciation[0]["val"])
        if len(depreciation) > 1 and "ebit" in previous:
            previous["ebitda"] = previous["ebit"] + float(depreciation[1]["val"])
        notes.append("ebitda <- OperatingIncomeLoss + DepreciationDepletionAndAmortization")
    return current, previous, notes


def html_to_pdf(html_path: Path, pdf_path: Path) -> bool:
    for browser in _BROWSERS:
        executable = browser if Path(browser).is_file() else shutil.which(browser)
        if not executable:
            continue
        result = subprocess.run(
            [
                executable,
                "--headless",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_path}",
                html_path.resolve().as_uri(),
            ],
            capture_output=True,
            timeout=180,
            check=False,
        )
        if result.returncode == 0 and pdf_path.is_file():
            return True
    return False


def build_case(
    client: httpx.Client, ticker: str, fiscal_year: int, split: str, out_dir: Path
) -> None:
    cik = lookup_cik(client, ticker)
    submissions = get_json(client, f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
    filing = find_10k(submissions, fiscal_year)
    companyfacts = get_json(
        client, f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    )
    current, previous, notes = facts_for_filing(companyfacts, filing["accession"])
    if not current:
        print(f"  {ticker}: no XBRL facts matched filing {filing['accession']}; skipped")
        return

    samples = out_dir / "samples"
    samples.mkdir(parents=True, exist_ok=True)
    stem = f"{ticker.lower()}_{fiscal_year}"
    html_path, pdf_path = samples / f"{stem}.html", samples / f"{stem}.pdf"
    accession = filing["accession"].replace("-", "")
    url = (
        f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{filing['primary_document']}"
    )
    time.sleep(0.15)
    html = client.get(url)
    html.raise_for_status()
    html_path.write_bytes(html.content)
    converted = pdf_path.is_file() or html_to_pdf(html_path, pdf_path)

    case = {
        "id": f"{stem}-10k-financials",
        "split": split,
        "input": f"samples/{stem}.pdf",
        "expected": {"current": current, "previous": previous},
        "metadata": {
            "source": url,
            "company": submissions.get("name"),
            "cik": cik,
            "accession": filing["accession"],
            "report_date": filing["report_date"],
            "units": "USD (raw, from XBRL)",
            "xbrl_mapping": notes,
        },
    }
    (out_dir / f"{stem}.json").write_text(json.dumps(case, indent=2), encoding="utf-8")
    status = "PDF ready" if converted else f"convert {html_path.name} to {pdf_path.name} manually"
    print(f"  {ticker} FY{fiscal_year}: {len(current)} fields; {status}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("tickers", nargs="+")
    parser.add_argument("--fiscal-year", type=int, required=True)
    parser.add_argument("--split", choices=["dev", "holdout"], default="dev")
    parser.add_argument("--out", type=Path, default=DATASETS_DIR / "document_extraction")
    args = parser.parse_args()

    with sec_client() as client:
        for ticker in args.tickers:
            try:
                build_case(client, ticker, args.fiscal_year, args.split, args.out)
            except (httpx.HTTPError, KeyError) as error:
                print(f"  {ticker}: failed ({error})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
