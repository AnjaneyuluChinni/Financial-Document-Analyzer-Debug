## Importing libraries and files
import os
from dotenv import load_dotenv

from pypdf import PdfReader

load_dotenv()

## Creating search tool (optional)
try:
    from crewai_tools import SerperDevTool
    search_tool = SerperDevTool() if os.getenv("SERPER_API_KEY") else None
except ImportError:
    search_tool = None

## Creating custom pdf reader tool
class FinancialDocumentTool:
    @staticmethod
    def validate_pdf(file_path: str) -> tuple[bool, str]:
        """Validate if file is a valid PDF and can be read.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not file_path.lower().endswith('.pdf'):
            return False, "File must be a PDF (.pdf extension required)"
        
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"
        
        try:
            reader = PdfReader(file_path)
            if len(reader.pages) == 0:
                return False, "PDF has no pages"
            return True, ""
        except Exception as e:
            return False, f"Invalid PDF file: {str(e)}"
    
    @staticmethod
    def read_data_tool(path: str = "data/sample.pdf") -> str:
        """Tool to read data from a PDF file from a path.
        
        Args:
            path (str): Path of the pdf file.
            
        Returns:
            str: Full Financial Document content
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a valid PDF
        """
        
        # Validate file
        is_valid, error_msg = FinancialDocumentTool.validate_pdf(path)
        if not is_valid:
            raise ValueError(error_msg)

        reader = PdfReader(path)
        pages = []
        
        # Extract and clean text from all pages
        for page_num, page in enumerate(reader.pages):
            try:
                content = page.extract_text() or ""
                cleaned = "\n".join(line.strip() for line in content.splitlines() if line.strip())
                if cleaned:
                    pages.append(cleaned)
            except Exception as e:
                # Log error but continue processing other pages
                print(f"Warning: Error extracting page {page_num}: {str(e)}")
                continue

        if not pages:
            raise ValueError("No readable text content found in PDF")
            
        return "\n\n".join(pages)

## Creating Investment Analysis Tool
class InvestmentTool:
    @staticmethod
    def analyze_investment_tool(financial_document_data: str) -> str:
        """Process and analyze financial document data.
        
        Args:
            financial_document_data (str): Extracted financial document text
            
        Returns:
            str: Investment analysis result
        """
        # Process and analyze the financial document data
        processed_data = financial_document_data
        
        # Clean up the data format
        i = 0
        while i < len(processed_data):
            if processed_data[i:i+2] == "  ":  # Remove double spaces
                processed_data = processed_data[:i] + processed_data[i+1:]
            else:
                i += 1
                
        # TODO: Implement investment analysis logic here
        return "Investment analysis functionality to be implemented"

## Creating Risk Assessment Tool
class RiskTool:
    @staticmethod
    def assess_risk_tool(financial_document_data: str) -> str:
        """Assess risks in financial document.
        
        Args:
            financial_document_data (str): Extracted financial document text
            
        Returns:
            str: Risk assessment result
        """
        # TODO: Implement risk assessment logic here
        return "Risk assessment functionality to be implemented"
    def create_risk_assessment_tool(financial_document_data):
        # TODO: Implement risk assessment logic here
        return "Risk assessment functionality to be implemented"