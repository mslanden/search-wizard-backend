#!/usr/bin/env python3
"""
PDF Extraction Utility

This script provides functions to download and extract content from PDF files.
"""

import os
import sys
import tempfile
import logging
import requests
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_and_extract_pdf(file_url, name="Unknown"):
    """
    Download PDF from URL and extract its text content.
    
    Args:
        file_url (str): URL to download the PDF from
        name (str): Name of the document (for logging)
        
    Returns:
        str: Extracted text or error message
    """
    logger.info(f"Downloading PDF from URL for {name}: {file_url}")
    
    try:
        # Set up headers for Supabase if needed
        headers = {}
        parsed_url = urlparse(file_url)
        if 'supabase.co' in parsed_url.netloc:
            supabase_key = os.environ.get('SUPABASE_KEY')
            if supabase_key:
                headers['apikey'] = supabase_key
                logger.info("Using Supabase service role key for authentication")

        # Download the file
        response = requests.get(file_url, headers=headers, timeout=30)
        if response.status_code != 200:
            return f"[Error downloading PDF: HTTP {response.status_code}]"
        
        # Save to a temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name
        
        try:
            # Use PyPDF2 to extract text
            import PyPDF2
            logger.info(f"Extracting text using PyPDF2 {PyPDF2.__version__}")
            
            with open(temp_file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                total_pages = len(pdf_reader.pages)
                logger.info(f"PDF has {total_pages} pages")
                
                extracted_text = ""
                for page_num in range(total_pages):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n\n"
                
                if extracted_text.strip():
                    logger.info(f"Successfully extracted {len(extracted_text)} chars of text")
                    return extracted_text
                else:
                    logger.warning("PDF text extraction yielded empty content")
                    
                    # Try an alternative extraction approach for scanned PDFs
                    try:
                        alternate_text = ""
                        for page_num in range(total_pages):
                            page = pdf_reader.pages[page_num]
                            if hasattr(page, 'get_text'):
                                alternate_text += page.get_text("text") + "\n\n"
                            
                        if alternate_text.strip():
                            logger.info(f"Alternative extraction method yielded {len(alternate_text)} chars")
                            return alternate_text
                    except Exception as alt_error:
                        logger.error(f"Alternative extraction failed: {str(alt_error)}")
                        
                    return "[PDF document contained no extractable text]"
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return f"[Error extracting PDF text: {str(e)}]"
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.error(f"Error cleaning up temp file: {str(e)}")
    except Exception as e:
        logger.error(f"Error in PDF extraction process: {str(e)}")
        return f"[Error processing PDF: {str(e)}]"

if __name__ == "__main__":
    # If run directly, process a URL provided as argument
    if len(sys.argv) > 1:
        url = sys.argv[1]
        name = sys.argv[2] if len(sys.argv) > 2 else "CLI Test"
        result = download_and_extract_pdf(url, name)
        print(f"Extracted {len(result)} characters")
        print("--- EXTRACT START ---")
        print(result[:500] + "..." if len(result) > 500 else result)
        print("--- EXTRACT END ---")
    else:
        print("Usage: python pdf_extractor.py <pdf_url> [document_name]")
