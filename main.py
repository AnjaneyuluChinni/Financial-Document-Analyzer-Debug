from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
import os
import uuid
import json
import sqlite3
import re
from datetime import datetime
from typing import Optional, Dict, Any

from crewai import Crew, Process
from agents import financial_analyst, investment_advisor, risk_assessor, verifier
from task import (
    analyze_financial_document as analyze_financial_document_task,
    investment_analysis,
    risk_assessment,
    verification,
)
from tools import FinancialDocumentTool

app = FastAPI(
    title="Financial Document Analyzer",
    description="Analyze financial documents using AI agents with structured JSON output",
    version="2.0"
)

# Database initialization
def init_db():
    """Initialize SQLite database with schema for analysis results"""
    os.makedirs("outputs", exist_ok=True)
    db_path = "outputs/analysis_results.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                query TEXT,
                verification_result TEXT,
                financial_analysis TEXT,
                investment_analysis TEXT,
                risk_assessment TEXT,
                combined_result TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        conn.commit()

def save_analysis_to_db(
    file_id: str,
    filename: str,
    query: str,
    unified_result: Dict[str, Any]
):
    """Save unified analysis result to database as JSON"""
    db_path = "outputs/analysis_results.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            INSERT INTO analyses 
            (id, filename, query, verification_result, financial_analysis, 
             investment_analysis, risk_assessment, combined_result, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            file_id,
            filename,
            query,
            None,  # verification_result no longer stored separately
            None,  # financial_analysis no longer stored separately
            None,  # investment_analysis no longer stored separately
            None,  # risk_assessment no longer stored separately
            json.dumps(unified_result),  # unified result stored as combined_result
            datetime.now().isoformat()
        ))
        conn.commit()

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract valid JSON object from text that may contain markdown or extra content.
    Handles JSON objects wrapped in markdown code blocks or surrounded by extra text.
    """
    text = text.strip()
    
    # Try direct JSON parsing first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks
    json_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
    matches = re.findall(json_pattern, text)
    if matches:
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
    
    # Try to find JSON object in the text
    json_pattern = r'\{[\s\S]*\}'
    matches = re.findall(json_pattern, text)
    
    # Try matches from longest to shortest (more likely to be complete)
    for match in sorted(matches, key=len, reverse=True):
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    return None

def find_json_objects(text: str) -> list[str]:
    """
    Extract balanced JSON object strings from text using brace matching.
    Avoids regex issues with nested objects and arrays.
    """
    objects: list[str] = []
    stack = 0
    start_idx = None
    in_string = False
    escape = False

    for idx, ch in enumerate(text):
        if ch == "\\" and in_string:
            escape = not escape
            continue
        if ch == '"' and not escape:
            in_string = not in_string
        escape = False

        if in_string:
            continue

        if ch == "{":
            if stack == 0:
                start_idx = idx
            stack += 1
        elif ch == "}":
            if stack > 0:
                stack -= 1
                if stack == 0 and start_idx is not None:
                    objects.append(text[start_idx:idx + 1])
                    start_idx = None

    return objects

def normalize_value(value: Any) -> Any:
    """Normalize placeholder null-like strings to actual None values."""
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in {"null", "none", "n/a", "na", ""}:
            return None
    return value

def normalize_metric_item(item: Any) -> Optional[Dict[str, Any]]:
    """Normalize key metric entries into dicts with cleaned values."""
    if item is None:
        return None
    if isinstance(item, str):
        metric = normalize_value(item)
        if metric is None:
            return None
        return {"metric": metric, "value": None, "evidence": None}
    if isinstance(item, dict):
        metric = normalize_value(item.get("metric"))
        value = normalize_value(item.get("value"))
        evidence = normalize_value(item.get("evidence"))
        if metric is None and value is None and evidence is None:
            return None
        return {"metric": metric, "value": value, "evidence": evidence}
    return None

def normalize_string_list(items: Any) -> list[str]:
    """Normalize list entries, dropping null-like placeholders."""
    if not isinstance(items, list):
        return []
    cleaned: list[str] = []
    for item in items:
        value = normalize_value(item)
        if isinstance(value, str) and value.strip() != "":
            cleaned.append(value)
    return cleaned

def parse_outputs_from_text(crew_output: str) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Parse crew output text and classify JSON objects by content.
    Returns a dict with verification, financial_analysis, investment_analysis, and risk_assessment.
    """
    parsed_outputs: Dict[str, Optional[Dict[str, Any]]] = {
        "verification": None,
        "financial_analysis": None,
        "investment_analysis": None,
        "risk_assessment": None
    }

    output_jsons = find_json_objects(crew_output)

    # Fallback when the crew output is a single JSON blob without multiple objects
    if not output_jsons:
        fallback_json = extract_json_from_text(crew_output)
        if isinstance(fallback_json, dict):
            output_jsons = [json.dumps(fallback_json)]

    for json_text in output_jsons:
        try:
            parsed = json.loads(json_text) if isinstance(json_text, str) else json_text
            if isinstance(parsed, dict):
                if "is_valid" in parsed and "confidence" in parsed:
                    parsed_outputs["verification"] = parsed
                elif "risk_register" in parsed:
                    parsed_outputs["risk_assessment"] = parsed
                elif "investment_considerations" in parsed:
                    parsed_outputs["investment_analysis"] = parsed
                elif "key_metrics" in parsed or "summary" in parsed:
                    parsed_outputs["financial_analysis"] = parsed
        except json.JSONDecodeError:
            continue

    return parsed_outputs

def merge_analysis_outputs(
    verification: Optional[Dict],
    financial_analysis: Optional[Dict],
    investment_analysis: Optional[Dict],
    risk_assessment: Optional[Dict]
) -> Dict[str, Any]:
    """
    Merge all agent outputs into a single unified JSON structure.
    Returns a clean, deterministic response with no null fields or duplicates.
    """
    
    # Start with default structure
    unified_analysis = {
        "summary": None,
        "key_metrics": [],
        "investment_considerations": {
            "upside": [],
            "downside": [],
            "open_questions": []
        },
        "risk_register": []
    }
    
    # Extract summary from financial analysis
    if financial_analysis and isinstance(financial_analysis, dict):
        if "summary" in financial_analysis:
            unified_analysis["summary"] = normalize_value(financial_analysis["summary"])
        
        # Extract key metrics
        if "key_metrics" in financial_analysis and isinstance(financial_analysis["key_metrics"], list):
            normalized_metrics = []
            for metric_item in financial_analysis["key_metrics"]:
                cleaned_item = normalize_metric_item(metric_item)
                if cleaned_item is not None:
                    normalized_metrics.append(cleaned_item)
            unified_analysis["key_metrics"] = normalized_metrics
    
    # Extract investment considerations
    if investment_analysis and isinstance(investment_analysis, dict):
        if "investment_considerations" in investment_analysis:
            inv_cons = investment_analysis["investment_considerations"]
            if isinstance(inv_cons, dict):
                if "upside" in inv_cons and isinstance(inv_cons["upside"], list):
                    unified_analysis["investment_considerations"]["upside"] = normalize_string_list(inv_cons["upside"])
                if "downside" in inv_cons and isinstance(inv_cons["downside"], list):
                    unified_analysis["investment_considerations"]["downside"] = normalize_string_list(inv_cons["downside"])
                if "open_questions" in inv_cons and isinstance(inv_cons["open_questions"], list):
                    unified_analysis["investment_considerations"]["open_questions"] = normalize_string_list(inv_cons["open_questions"])
    
    # Extract risk register
    if risk_assessment and isinstance(risk_assessment, dict):
        if "risk_register" in risk_assessment and isinstance(risk_assessment["risk_register"], list):
            # Filter out entries with all null/missing values
            risk_register = risk_assessment["risk_register"]
            cleaned_risks = []
            for risk_item in risk_register:
                if isinstance(risk_item, dict):
                    cleaned_item = {
                        "risk": normalize_value(risk_item.get("risk")),
                        "evidence": normalize_value(risk_item.get("evidence")),
                        "impact": normalize_value(risk_item.get("impact")),
                        "likelihood": normalize_value(risk_item.get("likelihood")),
                        "mitigation": normalize_value(risk_item.get("mitigation"))
                    }
                    # Keep only if at least one field has content
                    if any(value is not None for value in cleaned_item.values()):
                        cleaned_risks.append(cleaned_item)
            unified_analysis["risk_register"] = cleaned_risks

    # Fallback: use verifier summary if financial summary is missing
    if unified_analysis["summary"] is None and verification and isinstance(verification, dict):
        unified_analysis["summary"] = normalize_value(verification.get("summary"))
    
    return unified_analysis

def validate_pdf_upload(file: UploadFile) -> tuple[bool, Optional[str]]:
    """Validate uploaded file is a PDF"""
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        return False, "File must be a PDF (.pdf extension required)"
    return True, None

async def run_crew(query: str, document_text: str) -> Dict[str, Any]:
    """
    Run the crew workflow with pre-loaded document text.
    Returns unified structured JSON output with no null fields or raw output.
    Safely extracts and parses JSON from LLM outputs.
    """
    if not document_text or len(document_text.strip()) == 0:
        raise ValueError("Document text is empty - no content to analyze")
    
    financial_crew = Crew(
        agents=[verifier, financial_analyst, investment_advisor, risk_assessor],
        tasks=[verification, analyze_financial_document_task, investment_analysis, risk_assessment],
        process=Process.sequential,
    )
    
    # Run crew with document text context
    result = financial_crew.kickoff({
        "query": query,
        "document_text": document_text
    })
    
    # Parse crew output which may contain multiple JSON objects
    crew_output = str(result).strip()
    
    parsed_outputs = parse_outputs_from_text(crew_output)

    # Targeted retry to improve completeness if any section is missing
    needs_financial_retry = (
        parsed_outputs["financial_analysis"] is None
        or not parsed_outputs["financial_analysis"].get("key_metrics")
        or parsed_outputs["financial_analysis"].get("summary") in {None, "", "null"}
    )
    needs_investment_retry = (
        parsed_outputs["investment_analysis"] is None
        or not parsed_outputs["investment_analysis"].get("investment_considerations")
        or not any(
            parsed_outputs["investment_analysis"].get("investment_considerations", {}).get(key)
            for key in ["upside", "downside", "open_questions"]
        )
    )

    if needs_financial_retry:
        retry_financial = Crew(
            agents=[financial_analyst],
            tasks=[analyze_financial_document_task],
            process=Process.sequential,
        )
        retry_output = str(retry_financial.kickoff({
            "query": query,
            "document_text": document_text
        })).strip()
        retry_parsed = parse_outputs_from_text(retry_output)
        if retry_parsed.get("financial_analysis"):
            parsed_outputs["financial_analysis"] = retry_parsed["financial_analysis"]

    if needs_investment_retry:
        retry_investment = Crew(
            agents=[investment_advisor],
            tasks=[investment_analysis],
            process=Process.sequential,
        )
        retry_output = str(retry_investment.kickoff({
            "query": query,
            "document_text": document_text
        })).strip()
        retry_parsed = parse_outputs_from_text(retry_output)
        if retry_parsed.get("investment_analysis"):
            parsed_outputs["investment_analysis"] = retry_parsed["investment_analysis"]
    
    # Merge all outputs into unified structure (no null fields, no raw_output)
    unified_result = merge_analysis_outputs(
        verification=parsed_outputs["verification"],
        financial_analysis=parsed_outputs["financial_analysis"],
        investment_analysis=parsed_outputs["investment_analysis"],
        risk_assessment=parsed_outputs["risk_assessment"]
    )
    
    return unified_result

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Financial Document Analyzer API is running",
        "version": "2.0",
        "endpoints": ["/docs", "/analyze", "/history"]
    }

@app.post("/analyze")
async def analyze_financial_document_endpoint(
    file: UploadFile = File(..., description="PDF file to analyze"),
    query: str = Form(
        default="Provide comprehensive financial analysis including key metrics, investment considerations, and risk assessment"
    )
) -> JSONResponse:
    """
    Analyze financial document and return fully structured, deterministic JSON.
    
    Returns unified analysis object with:
    - summary: string or null
    - key_metrics: array
    - investment_considerations: object with upside, downside, open_questions
    - risk_register: array
    
    No null fields, no raw output, no markdown.
    """
    
    file_id = str(uuid.uuid4())
    file_path = f"data/financial_document_{file_id}.pdf"
    
    try:
        # Validate file upload
        is_valid, error_msg = validate_pdf_upload(file)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        
        # Read and validate uploaded file
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        # Save uploaded file temporarily
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Validate PDF and extract text (single-pass read)
        try:
            document_text = FinancialDocumentTool.read_data_tool(file_path)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid PDF: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading PDF: {str(e)}")
        
        # Validate extracted content
        if not document_text or len(document_text.strip()) == 0:
            raise HTTPException(status_code=400, detail="PDF contains no readable text content")
        
        # Validate query
        if not query or query.strip() == "":
            query = "Provide comprehensive financial analysis including key metrics, investment considerations, and risk assessment"
        
        # Run crew with document text (single-pass extraction used for all tasks)
        try:
            unified_analysis = await run_crew(query=query.strip(), document_text=document_text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error during analysis: {str(e)}")
        
        # Validate unified result can be serialized to JSON
        try:
            # This ensures the result is JSON-serializable
            json_str = json.dumps(unified_analysis)
        except (TypeError, ValueError) as e:
            raise HTTPException(status_code=500, detail=f"Analysis result is not JSON serializable: {str(e)}")
        
        # Save to database
        try:
            save_analysis_to_db(
                file_id=file_id,
                filename=file.filename,
                query=query,
                unified_result=unified_analysis
            )
        except Exception as e:
            # Log error but don't fail the response
            print(f"Database save error: {str(e)}")
        
        # Return clean, unified JSON response
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "file_id": file_id,
                "filename": file.filename,
                "query": query,
                "analysis": unified_analysis,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error processing document: {str(e)}"
        )
    finally:
        # Clean up uploaded file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass  # Ignore cleanup errors

@app.get("/history")
async def get_analysis_history(limit: int = 50) -> JSONResponse:
    """
    Retrieve analysis history from database, ordered by most recent first.
    Returns unified analysis results with all JSON parsed.
    
    Parameters:
    - limit: Maximum number of results to return (default 50, max 1000)
    
    Returns:
    - count: Number of results returned
    - analyses: List of past analyses with unified JSON analysis field
    """
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 1000")
    
    db_path = "outputs/analysis_results.db"
    
    if not os.path.exists(db_path):
        return JSONResponse(
            status_code=200,
            content={"count": 0, "analyses": []}
        )
    
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM analyses ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            analyses = []
            for row in cursor.fetchall():
                analysis = dict(row)
                
                # Parse combined_result JSON (main unified analysis output)
                if analysis.get("combined_result"):
                    try:
                        analysis["analysis"] = json.loads(analysis["combined_result"])
                    except json.JSONDecodeError:
                        analysis["analysis"] = None
                else:
                    analysis["analysis"] = None
                
                # Remove individual fields (no longer used)
                analysis.pop("verification_result", None)
                analysis.pop("financial_analysis", None)
                analysis.pop("investment_analysis", None)
                analysis.pop("risk_assessment", None)
                analysis.pop("combined_result", None)
                
                analyses.append(analysis)
            
            return JSONResponse(
                status_code=200,
                content={
                    "count": len(analyses),
                    "analyses": analyses
                }
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving history: {str(e)}"
        )

if __name__ == "__main__":
    init_db()
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

