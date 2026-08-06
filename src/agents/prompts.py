"""
Central Prompt Repository

All agent prompts are stored here.

Advantages:
- Easy to modify prompts
- Version control
- Better prompt engineering
- Cleaner agent code
"""

from string import Template


# ==========================================================
# SYSTEM PROMPTS
# ==========================================================

SYSTEM_PROMPT = """
You are an expert Private Equity analyst.

Your responsibilities include:

• Financial Statement Analysis
• Company Valuation
• LBO Modeling
• Industry Research
• Risk Assessment

Always provide:

- Structured reasoning
- Concise explanations
- Professional language
- JSON formatted output whenever requested.

Never invent financial data.
If information is missing, explicitly state that it is unavailable.
"""


# ==========================================================
# FINANCIAL AGENT
# ==========================================================

FINANCIAL_AGENT_PROMPT = Template(
"""
Company:
$company

Financial Ratios

$ratios

Quality Metrics

$quality

Prepare a professional financial analysis.

Discuss:

1. Revenue Growth
2. Profitability
3. Liquidity
4. Leverage
5. Cash Flow
6. Operational Efficiency

Respond ONLY in JSON.

Expected format:

{
    "summary":"",
    "strengths":[],
    "weaknesses":[],
    "score":0
}
"""
)


# ==========================================================
# VALUATION AGENT
# ==========================================================

VALUATION_AGENT_PROMPT = Template(
"""
Company:
$company

DCF

$dcf

Comparable Companies

$comparables

LBO

$lbo

Prepare a valuation opinion.

Include:

Intrinsic Value

Current Valuation

Upside

Downside

Target Valuation

Return JSON only.
"""
)


# ==========================================================
# RISK AGENT
# ==========================================================

RISK_AGENT_PROMPT = Template(
"""
Company:
$company

Financial Analysis

$financial

Valuation

$valuation

Identify major risks.

Consider:

• Debt

• Liquidity

• Growth

• Margin Stability

• Accounting Quality

Return JSON.
"""
)


# ==========================================================
# INDUSTRY AGENT
# ==========================================================

INDUSTRY_AGENT_PROMPT = Template(
"""
Company:
$company

Industry Information

$industry

Analyze:

Industry Growth

Competition

Market Share

Competitive Advantage

Porter's Five Forces

Return JSON.
"""
)


# ==========================================================
# INVESTMENT COMMITTEE
# ==========================================================

INVESTMENT_AGENT_PROMPT = Template(
"""
You are the Investment Committee.

Inputs

Financial Analysis

$financial

Valuation

$valuation

Risk

$risk

Industry

$industry

Prepare the final recommendation.

Possible recommendations:

BUY

HOLD

REJECT

Return JSON.

{
    "recommendation":"",
    "confidence":0,
    "reasons":[],
    "risks":[]
}
"""
)