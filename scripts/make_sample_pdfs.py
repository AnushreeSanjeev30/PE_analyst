"""Write four fictional company documents to data/samples/ for trying the app.

    python scripts/make_sample_pdfs.py

Each is a small, text-based PDF laid out the way the extractor expects: an overview page, risk
factors, the three financial statements as ruled tables, and notes. The companies are invented.
They are built to land on three different outcomes when run with the default valuation inputs
on the New Analysis page:

* Meridian_Software_2025.pdf   -- healthy, no red flags
* Harbor_Logistics_2025.pdf    -- sound numbers, but customer concentration and litigation
* Castell_Retail_2025.pdf      -- going-concern doubt, a covenant breach and a restatement
* Orion_Components_2025.pdf    -- a management summary with gaps. It reports gross profit,
                                  adjusted EBITDA and total liabilities instead of cost of
                                  sales, operating income and equity (the app works those out),
                                  and leaves out interest expense and operating cash flow
                                  (the app asks for them). Use it to see missing figures handled.

The first two share the headline figures the default valuation inputs assume (revenue 1,000,
EBITDA 220, debt 200). Castell does not, so edit the valuation inputs if you want its valuation
to be meaningful; its red flags decide the outcome either way.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.e2e.pdf_builder import Page, build_pdf  # noqa: E402

OUTPUT_DIR = ROOT / "data" / "samples"


def _statements(
    income: list[list[str]], balance: list[list[str]], cash: list[list[str]]
) -> list[Page]:
    header = ["", "2025", "2024"]
    return [
        Page()
        .text("Consolidated Statements of Operations (in millions)", size=12)
        .table([header, *income]),
        Page().text("Consolidated Balance Sheets (in millions)", size=12).table([header, *balance]),
        Page()
        .text("Consolidated Statements of Cash Flows (in millions)", size=12)
        .table([header, *cash]),
    ]


def meridian() -> bytes:
    overview = Page().text("Meridian Software Inc. - 2025 Annual Report", size=14).paragraph([
        "Meridian sells subscription software to independent veterinary clinics in North America.",
        "Market overview: industry demand for vertical practice software grew 12% in 2025.",
        "Recurring revenue was 94% of total revenue and net revenue retention was 112%.",
        "No single customer represented more than 2% of revenue in 2025.",
        "Management strategy focuses on payments cross-sell and disciplined annual pricing.",
        "We expect operating margins to expand as the installed base scales.",
    ])
    risks = Page().text("Item 1A. Risk Factors", size=12).paragraph([
        "Foreign exchange movements may reduce the reported value of our Canadian revenue.",
        "A prolonged economic slowdown could delay purchasing decisions by smaller clinics.",
        "We may be unable to hire engineers quickly enough to deliver our product roadmap.",
    ])
    statements = _statements(
        income=[
            ["Total revenues", "1,000", "900"],
            ["Cost of revenue", "600", "560"],
            ["Operating income", "150", "130"],
            ["Interest expense", "(20)", "(22)"],
            ["Net income", "100", "85"],
        ],
        balance=[
            ["Inventories", "50", "45"],
            ["Total current assets", "200", "180"],
            ["Total assets", "1,000", "900"],
            ["Total current liabilities", "180", "170"],
            ["Long-term debt", "200", "210"],
            ["Total stockholders' equity", "400", "350"],
        ],
        cash=[
            ["Depreciation and amortization", "70", "60"],
            ["Net cash provided by operating activities", "140", "120"],
            ["Purchases of property and equipment", "(40)", "(35)"],
        ],
    )
    notes = Page().text("Notes to Consolidated Financial Statements", size=12).paragraph([
        "Note 1. Revenue is recognized ratably over the subscription term.",
        "Note 2. The term loan matures in 2030. The company was within all financial",
        "ratios required by the lenders throughout 2025.",
        "Note 3. Software development costs are expensed as incurred.",
    ])
    return build_pdf([overview, risks, *statements, notes])


def harbor() -> bytes:
    overview = Page().text("Harbor Logistics Group - 2025 Annual Report", size=14).paragraph([
        "Harbor operates temperature-controlled warehousing and last-mile delivery in the Midwest.",
        "Market overview: industry demand for cold-chain capacity grew 6% in 2025.",
        "Competition is intense, with three national operators expanding into our core region.",
        "Management strategy focuses on route density and automation of two flagship sites.",
        "We expect capital spending to remain elevated through 2026.",
    ])
    risks = Page().text("Item 1A. Risk Factors", size=12).paragraph([
        "Customer concentration is significant: our two largest customers accounted for 46% of",
        "revenue in 2025, and the loss of either could materially reduce our earnings.",
        "We are a defendant in pending litigation brought by a former carrier partner, and an",
        "adverse ruling could require a payment that exceeds our insurance cover.",
        "Driver turnover rose to 38% in 2025 and may increase our labor costs further.",
        "Rising interest rates may increase the cost of refinancing our credit facility.",
    ])
    statements = _statements(
        income=[
            ["Total revenues", "1,000", "930"],
            ["Cost of revenue", "640", "590"],
            ["Operating income", "150", "140"],
            ["Interest expense", "(24)", "(22)"],
            ["Net income", "92", "88"],
        ],
        balance=[
            ["Inventories", "30", "28"],
            ["Total current assets", "210", "195"],
            ["Total assets", "1,050", "980"],
            ["Total current liabilities", "190", "175"],
            ["Long-term debt", "200", "215"],
            ["Total stockholders' equity", "410", "365"],
        ],
        cash=[
            ["Depreciation and amortization", "70", "64"],
            ["Net cash provided by operating activities", "135", "128"],
            ["Purchases of property and equipment", "(70)", "(48)"],
        ],
    )
    notes = Page().text("Notes to Consolidated Financial Statements", size=12).paragraph([
        "Note 1. Revenue is recognized when delivery to the customer is complete.",
        "Note 2. Contingencies. The company has accrued 6 million for the pending claim",
        "described under legal proceedings; the ultimate outcome remains uncertain.",
        "Note 3. The credit facility matures in 2028.",
    ])
    return build_pdf([overview, risks, *statements, notes])


def castell() -> bytes:
    overview = Page().text("Castell Home Retail plc - 2025 Annual Report", size=14).paragraph([
        "Castell operates 140 home-furnishing stores and an online channel in the United Kingdom.",
        "Market overview: industry demand for big-ticket home goods fell 9% in 2025.",
        "Competition from online-only retailers continued to take share from store-based chains.",
        "Management strategy focuses on closing 30 loss-making stores and renegotiating leases.",
    ])
    risks = Page().text("Item 1A. Risk Factors", size=12).paragraph([
        "There is substantial doubt about our ability to continue as a going concern, because",
        "our cash forecast depends on lender support that is uncertain.",
        "We were in covenant breach of our leverage ratio at year end, and lenders could demand",
        "immediate repayment if a waiver is not extended.",
        "Management identified a material weakness in internal control over inventory",
        "valuation, which resulted in a restatement of our 2024 results.",
        "The company is subject to an investigation by the tax authority that may result in",
        "additional liabilities.",
    ])
    statements = _statements(
        income=[
            ["Total revenues", "820", "960"],
            ["Cost of revenue", "640", "700"],
            ["Operating income", "(18)", "34"],
            ["Interest expense", "(52)", "(41)"],
            ["Net income", "(76)", "(12)"],
        ],
        balance=[
            ["Inventories", "210", "240"],
            ["Total current assets", "260", "310"],
            ["Total assets", "780", "900"],
            ["Total current liabilities", "410", "330"],
            ["Long-term debt", "520", "480"],
            ["Total stockholders' equity", "(60)", "20"],
        ],
        cash=[
            ["Depreciation and amortization", "48", "50"],
            ["Net cash provided by operating activities", "(22)", "31"],
            ["Purchases of property and equipment", "(15)", "(28)"],
        ],
    )
    notes = Page().text("Notes to Consolidated Financial Statements", size=12).paragraph([
        "Note 1. Going concern. These statements are prepared on a going concern basis, which",
        "assumes lenders continue to waive the covenant breach described in Note 2.",
        "Note 2. Borrowings. The revolving facility was in default at 31 December 2025.",
        "Note 3. Impairment of 44 million was recognized on store assets.",
    ])
    return build_pdf([overview, risks, *statements, notes])


def orion() -> bytes:
    overview = Page().text("Orion Components Ltd - 2025 Annual Report", size=14).paragraph([
        "Orion designs precision sensors for industrial automation customers in Europe.",
        "Market overview: industry demand for factory sensors grew 9% in 2025.",
        "We are the market leader in high-temperature sensing, with strong customer retention.",
        "Management strategy focuses on aftermarket service contracts and a second plant.",
    ])
    risks = Page().text("Item 1A. Risk Factors", size=12).paragraph([
        "A shortage of specialist semiconductors could delay shipments and reduce our revenue.",
        "Our supply chain depends on two component makers, and disruption at either may",
        "increase our costs.",
        "Currency movements may affect the reported value of sales made outside the eurozone.",
    ])
    statements = _statements(
        income=[
            ["Total revenues", "640", "580"],
            ["Gross profit", "272", "238"],
            ["Adjusted EBITDA", "134", "116"],
            ["Net income", "61", "52"],
        ],
        balance=[
            ["Inventories", "74", "68"],
            ["Total current assets", "236", "214"],
            ["Total assets", "610", "560"],
            ["Total current liabilities", "128", "120"],
            ["Long-term debt", "150", "165"],
            ["Total liabilities", "330", "325"],
        ],
        cash=[
            ["Depreciation and amortization", "38", "34"],
            ["Purchases of property and equipment", "(45)", "(31)"],
        ],
    )
    notes = Page().text("Notes to Consolidated Financial Statements", size=12).paragraph([
        "Note 1. Revenue is recognized on delivery; service contracts are recognized over time.",
        "Note 2. The term loan matures in 2029.",
    ])
    return build_pdf([overview, risks, *statements, notes])


SAMPLES = {
    "Meridian_Software_2025.pdf": meridian,
    "Harbor_Logistics_2025.pdf": harbor,
    "Castell_Retail_2025.pdf": castell,
    "Orion_Components_2025.pdf": orion,
}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, build in SAMPLES.items():
        path = OUTPUT_DIR / name
        path.write_bytes(build())
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
