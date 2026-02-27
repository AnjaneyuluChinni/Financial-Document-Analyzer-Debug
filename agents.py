## Importing libraries and files
import os
from dotenv import load_dotenv

from crewai import LLM, Agent

from tools import search_tool

load_dotenv()

### Loading LLM (Gemini)
gemini_api_key = os.getenv("GEMINI_API_KEY")
gemini_model = os.getenv("GEMINI_MODEL", "gemini/gemini-1.5-flash")
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY is not set. Get your free API key from https://aistudio.google.com/app/apikey")

llm = LLM(model=gemini_model, api_key=gemini_api_key)

def _agent_tools():
    tools = []
    if search_tool is not None:
        tools.append(search_tool)
    return tools

# Creating a document verifier agent
verifier = Agent(
    role="Financial Document Verifier",
    goal="Verify the file is a financial document and return valid JSON: {\"is_valid\": bool, \"confidence\": str, \"evidence\": list, \"summary\": str}. Return ONLY JSON, never markdown.",
    verbose=True,
    memory=True,
    backstory=(
        "You are careful and conservative. You check for common financial statements, reporting periods, company identifiers, "
        "and financial metrics before confirming validity. You always respond with ONLY valid JSON format, never markdown or explanatory text."
    ),
    tools=_agent_tools(),
    llm=llm,
    max_iter=2,
    max_rpm=5,
    allow_delegation=False,
)

# Creating an Experienced Financial Analyst agent
financial_analyst = Agent(
    role="Senior Financial Analyst",
    goal="Extract and analyze financial metrics from the document and return STRICT valid JSON: {\"summary\": str, \"key_metrics\": list, \"data_quality\": dict}. NEVER return markdown or explanatory text.",
    verbose=True,
    memory=True,
    backstory=(
        "You are a meticulous analyst who relies on financial statements and quantified evidence. "
        "You avoid speculation and clearly distinguish facts from assumptions. "
        "You ALWAYS respond with ONLY valid JSON format, never markdown. If data is missing, use null."
    ),
    tools=_agent_tools(),
    llm=llm,
    max_iter=3,
    max_rpm=5,
    allow_delegation=False,
)

# Creating an investment analyst agent
investment_advisor = Agent(
    role="Investment Analyst",
    goal="Analyze investment considerations and return STRICT valid JSON: {\"investment_considerations\": {\"upside\": list, \"downside\": list, \"open_questions\": list}}. Return ONLY JSON, never markdown.",
    verbose=True,
    memory=True,
    backstory=(
        "You evaluate valuation, growth, cash flow strength, and risk in a neutral, professional tone. "
        "You provide balanced analysis without personalized advice. You ALWAYS respond with ONLY valid JSON format, never markdown."
    ),
    tools=_agent_tools(),
    llm=llm,
    max_iter=2,
    max_rpm=5,
    allow_delegation=False,
)

# Creating a risk assessment agent
risk_assessor = Agent(
    role="Risk Assessment Specialist",
    goal="Identify material risks and return STRICT valid JSON: {\"risk_register\": [{\"risk\": str, \"evidence\": str, \"impact\": str, \"likelihood\": str, \"mitigation\": str}]}. Return ONLY JSON, never markdown.",
    verbose=True,
    memory=True,
    backstory=(
        "You focus on liquidity, leverage, market, regulatory, and operational risks. You quantify when possible and explain impact clearly. "
        "You ALWAYS respond with ONLY valid JSON format, never markdown. Use null for missing evidence."
    ),
    tools=_agent_tools(),
    llm=llm,
    max_iter=2,
    max_rpm=5,
    allow_delegation=False,
)
