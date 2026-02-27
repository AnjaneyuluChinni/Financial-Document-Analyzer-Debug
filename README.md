# Financial Document Analyzer - CrewAI Debug Challenge

## Project Overview

A production-grade financial document analysis system that processes PDFs using CrewAI multi-agent framework. The system performs verification, financial analysis, investment recommendations, and risk assessment through a sequential workflow.

---

## Bugs Found and Fixed

### 1. Undefined LLM Configuration (agents.py)
Circular reference: `llm = llm`. Fixed with proper environment variable initialization and validation. Impact: System crash on startup.

### 2. Malicious Agent Prompts (agents.py)
Agent prompts instructed hallucination and ignored financial regulatory constraints. Corrected to enforce document-grounded, evidence-based analysis only.

### 3. Unsafe Task Descriptions (task.py)
Task instructions directed agents to invent metrics and ignore source documents. Updated to require explicit citation and use "Not Found" for missing data.

### 4. Incorrect Tool Wiring (agents.py & task.py)
Parameter `tool=` used instead of `tools=`. Prevented agent access to PDF reading functionality.

### 5. PDF Parsing Failure (tools.py)
Undefined `Pdf` class used instead of pypdf. Implemented proper PdfReader with text extraction and whitespace normalization across all pages.

### 6. Dependency Version Conflicts (requirements.txt)
Multiple version mismatches with CrewAI 0.130.0 including: pydantic (v1 vs v2), onnxruntime, openai, and opentelemetry packages. Resolved all conflicts for clean install.

### 7. Filename Error (README.md)
Documentation referenced `requirement.txt` instead of `requirements.txt`. Corrected to match actual filename.

### 8. Task-Agent Misalignment (task.py)
All tasks assigned to `financial_analyst` instead of specialized agents. Restructured to use `verifier`, `investment_advisor`, and `risk_assessor` for proper specialization.

---

## Architecture Improvements

**Single-Pass PDF Loading:** Document is loaded once and reused across all tasks instead of being parsed separately by each agent. Benefit: 75% reduction in PDF parsing overhead.

**Database Persistence:** SQLite database stores all analysis results with timestamp for audit trails and compliance.

**Agent Specialization:** Dedicated agents for verification, financial analysis, investment recommendations, and risk assessment enable focused, optimized processing.

**Deterministic Prompts:** Agents instructed to rely exclusively on document content, cite specific phrasing, and use "Not Found" for missing data rather than inferring.

---

## Setup & Installation

### Prerequisites
- Python 3.11+
- Valid Gemini API key

### Installation Steps
```bash
git clone <repository>
cd financial-document-analyzer-debug
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
`

### Environment Variables
Set the following variables before running:

```bash
# Required
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini/gemini-1.5-flash

# Optional
SERPER_API_KEY=your_serper_key_here
`

Obtain a free Gemini API key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).

### Running the Server
```bash
python main.py
`
API available at `http://localhost:8000`

---

## API Documentation


```
GET /
```
### Health Check
### Interactive API Documentation (OpenAPI/Swagger)
```
GET /docs
```

**Description:** Interactive OpenAPI (Swagger UI) documentation with live endpoint testing.

**Access:** `http://localhost:8000/docs`

**Features:**
- View all endpoints and parameters
- Send test requests directly from the UI
- View request/response schemas
- Try the `/analyze` endpoint with file upload

**Alternative Docs Format:**
```
GET /redoc
```
ReDoc documentation at `http://localhost:8000/redoc`

---

### Analyze Document
`
POST /analyze
`

**Parameters:**
- `file` (required): PDF document
- `query` (optional): Analysis query; defaults to general investment insight analysis

**Example Request:**
```bash
curl -X POST "http://localhost:8000/analyze" \
  -F "file=@document.pdf" \
  -F "query=Revenue analysis"
`

**Response:**
```json
{
  "status": "success",
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "Revenue analysis",
  "file_processed": "document.pdf",
  "analysis": {
    "verification": "Valid financial document",
    "financial_analysis": {
      "summary": "Key metrics and trends",
      "revenue": "2025 revenue increased 12% YoY",
      "margins": "Gross margin improved to 42%"
    },
    "investment_analysis": {
      "upside": "Growth potential from market expansion",
      "downside": "Competitive pressure in core markets",
      "rating": "Buy"
    },
    "risk_assessment": {
      "primary_risks": ["Market volatility", "Supply chain concentration"],
      "mitigation": "Diversification efforts underway"
    }
  }
}
`

### Retrieve Analysis History
`
GET /history
`

**Response:**
```json
{
  "analyses": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "q2_2025_report.pdf",
      "query": "Revenue analysis",
      "timestamp": "2026-02-26T14:23:45.123456",
      "analysis": {
        "verification": "Valid financial document",
        "financial_analysis": "...",
        "investment_analysis": "...",
        "risk_assessment": "..."
      }
    }
  ]
}
`

---

## Project Structure

`
financial-document-analyzer-debug/
├── main.py                      # FastAPI server and database layer
├── agents.py                    # CrewAI agent definitions
├── task.py                      # Task definitions for multi-agent workflow
├── tools.py                     # PDF reading and document processing
├── requirements.txt             # Python dependencies
├── README.md                    # Documentation
├── data/                        # Temporary uploaded PDFs
├── outputs/
│   └── analysis_results.db      # SQLite analysis database
└── venv/                        # Python virtual environment
`

---

## Configuration

**Agent Settings (agents.py):**
- `max_iter`: 2-3 iterations per agent
- `max_rpm`: 5 requests per minute
- `memory`: Enabled for context retention
- `verbose`: Enabled for debugging

**Task Execution (task.py):**
- Sequential execution for deterministic output
- Document text injected via context variables
- Output validation enforced

**Database (SQLite):**
- Persists all analysis results with full audit trail
- Timestamp recorded for compliance tracking

---

## Database Schema

**analyses table:**

| Column | Type | Purpose |
|--------|------|---------|
| id | TEXT (PK) | Unique analysis identifier |
| filename | TEXT | Original PDF filename |
| query | TEXT | User-provided query |
| verification_result | TEXT | Document verification output |
| financial_analysis | TEXT | Financial summary and metrics |
| investment_analysis | TEXT | Investment recommendations |
| risk_assessment | TEXT | Risk evaluation with evidence |
| timestamp | TEXT | ISO8601 timestamp |

---

## Key Improvements

- **Deterministic Prompts:** Agents grounded in document content, cite sources explicitly, use "Not Found" for missing data
- **Single-Pass PDF Loading:** Document parsed once and reused across all tasks
- **Database Persistence:** Complete analysis history with ISO8601 timestamps
- **Structured Output:** JSON-formatted analysis results with clear sections
- **Error Handling:** Graceful cleanup and detailed error messages
- **Agent Specialization:** Dedicated agents for verification, financial analysis, investment recommendations, and risk assessment
- **Environment-Based Configuration:** No hardcoded credentials or settings

---

## Known Limitations

- **Sequential Processing:** Currently processes one document at a time. Can be upgraded with async tasks or job queues
- **Context Window:** Limited by underlying LLM token limit (~128K tokens for relevant context)
- **Complex PDF Formats:** Tables and multi-column layouts may require post-processing
- **Regulatory Compliance:** System outputs are LLM-generated and not certified financial analysis

---

## Future Enhancements

- Background job queue (Celery + Redis) for concurrent processing
- Email notifications on analysis completion
- Batch document processing
- Document comparison and trend analysis
- REST API authentication and rate limiting
- Export to multiple formats (Excel, PDF reports)
- Dashboard UI for analysis review and management

---

## Project Status

All bugs identified and fixed. System verified for document processing, analysis generation, and database persistence. Ready for production deployment with appropriate oversight for regulated financial use.
