## Importing libraries and files
import json
from crewai import Task

from agents import financial_analyst, verifier, investment_advisor, risk_assessor

## Creating a verification task
verification = Task(
    description=(
        "Use the extracted document text in {document_text} to verify if the file is a financial document. "
        "Look for financial statements, reporting periods, company identifiers, revenue, expenses, or other financial metrics. "
        "Return ONLY valid JSON with no markdown or explanatory text."
    ),
    expected_output=(
        "Valid JSON object: "
        '{"is_valid": true/false, "confidence": "high/medium/low", '
        '"evidence": ["list", "of", "supporting", "indicators"], '
        '"summary": "brief explanation"}'
    ),
    agent=verifier,
    async_execution=False,
)

## Creating a task to extract and analyze financial data
analyze_financial_document = Task(
    description=(
        "Use only the extracted document text provided in {document_text}. "
        "Answer the user query: {query}. Extract key financial metrics and summarize performance. "
        "You MUST attempt to extract the following when present: Revenue, Operating income, Net income, "
        "Free cash flow, Margins (gross/operating/net), and YoY changes for any reported metrics. "
        "Summarize notable trends and material changes when performance discussion exists. "
        "If a metric is not explicitly found in the document, return null for that metric's value or evidence. "
        "Do NOT infer, assume, or hallucinate missing data. "
        "Return ONLY valid JSON with no markdown, explanations, or additional text."
    ),
    expected_output=(
        "Valid JSON object: "
        '{"summary": "string", '
        '"key_metrics": [{"metric": "string", "value": "string", "evidence": "string"}], '
        '"data_quality": {"complete": true/false, "missing_fields": ["list", "of", "missing", "metrics"]}}'
    ),
    agent=financial_analyst,
    async_execution=False,
)

## Creating an investment analysis task
investment_analysis = Task(
    description=(
        "Use only the extracted document text provided in {document_text}. "
        "Provide investment considerations based on documented financial data. "
        "Identify 2 to 4 upside drivers (growth, margins, competitive advantages), "
        "2 to 4 downside risks (leverage, declining metrics, market pressures), "
        "and 2 to 3 open questions (unresolved uncertainties, missing data). "
        "Ground every item in document evidence (metrics, statements, or cited figures). "
        "Do not provide personalized financial advice. "
        "Return ONLY valid JSON with no markdown or explanatory text."
    ),
    expected_output=(
        "Valid JSON object: "
        '{"investment_considerations": '
        '{"upside": ["string"], "downside": ["string"], "open_questions": ["string"]}}'
    ),
    agent=investment_advisor,
    async_execution=False,
)

## Creating a risk assessment task
risk_assessment = Task(
    description=(
        "Use only the extracted document text provided in {document_text}. "
        "Identify material risks and explain their evidence, impact, likelihood, and mitigation. "
        "Cover liquidity, leverage, market, operational, and regulatory risks when applicable. "
        "If a risk category has no evidence in the document, use null. "
        "Return ONLY valid JSON with no markdown or additional text."
    ),
    expected_output=(
        "Valid JSON object: "
        '{"risk_register": ['
        '{"risk": "string", "evidence": "string", "impact": "high/medium/low", "likelihood": "high/medium/low", "mitigation": "string"}'
        ']}'
    ),
    agent=risk_assessor,
    async_execution=False,
)
