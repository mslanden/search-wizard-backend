#!/usr/bin/env python3
"""
Utility functions for the Search Wizard API.
"""

import io
import os
import logging
import requests
import tempfile
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_and_extract_pdf(file_url, headers=None, name="Unknown"):
    """
    Download a PDF file from a URL and extract its text content.
    Specialized function that focuses just on PDF extraction with robust error handling.
    
    Args:
        file_url (str): URL to the PDF file
        headers (dict, optional): Request headers for authentication
        name (str, optional): Name of the file for logging purposes
        
    Returns:
        str: Extracted text from the PDF, or error message if extraction fails
    """
    logger.info(f"Downloading and extracting PDF from URL: {file_url}")
    
    # Initialize headers if none provided
    if headers is None:
        headers = {}
    
    # Add Supabase authentication if needed
    parsed_url = urlparse(file_url)
    if 'supabase.co' in parsed_url.netloc and 'apikey' not in headers:
        supabase_key = os.environ.get('SUPABASE_KEY')
        if supabase_key:
            headers['apikey'] = supabase_key
            logger.info("Added Supabase authentication to request")
    
    try:
        # Download the PDF file
        response = requests.get(file_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            error_msg = f"Failed to download PDF: HTTP {response.status_code}"
            logger.error(error_msg)
            return f"[{error_msg}]"
        
        # Check if the response content is actually a PDF
        content_type = response.headers.get('Content-Type', '').lower()
        if not ('pdf' in content_type or file_url.lower().endswith('.pdf')):
            logger.warning(f"URL may not be a PDF. Content-Type: {content_type}")
        
        # Extract text using our extract_text_from_pdf function
        extracted_text = extract_text_from_pdf(response.content)
        logger.info(f"PDF extraction complete: {len(extracted_text)} chars")
        
        # Verify the quality of extracted text
        if len(extracted_text) < 100 and not extracted_text.strip():
            logger.warning("Very little text extracted from PDF - may be scanned or image-based")
        
        # Check for common error markers
        if any(marker in extracted_text for marker in ['[PDF extraction error', '[Content does not appear', '[PDF document contains no']):
            logger.warning(f"Extraction encountered issues: {extracted_text[:100]}...")
        
        return extracted_text
    
    except Exception as e:
        error_msg = f"Error downloading/extracting PDF: {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        return f"[{error_msg}]"

def download_and_extract_from_url(file_url, name="Unknown"):
    """
    Download content from a URL and extract text if it's a PDF.
    
    Args:
        file_url (str): URL to download content from
        name (str): Name of the file/artifact for logging purposes
    
    Returns:
        str: Extracted text or downloaded content
    """
    logger.info(f"Downloading content from URL for {name}: {file_url}")
    
    try:
        import requests
        import tempfile
        from urllib.parse import urlparse
        
        # Set up headers for Supabase if needed
        headers = {}
        parsed_url = urlparse(file_url)
        if 'supabase.co' in parsed_url.netloc:
            supabase_key = os.environ.get('SUPABASE_KEY')
            if supabase_key:
                headers['apikey'] = supabase_key
                logger.info("Using Supabase service role key for authentication")
                # For Supabase sign URLs, we shouldn't need to modify them
        
        # Download the file directly
        response = requests.get(file_url, headers=headers, timeout=30)
        if response.status_code == 200:
            # Check content type
            content_type = response.headers.get('Content-Type', '').lower()
            logger.info(f"Downloaded content ({len(response.content)} bytes) with type: {content_type}")
            
            # Handle PDF content
            if 'pdf' in content_type or file_url.lower().endswith('.pdf'):
                logger.info(f"Processing PDF file: {name}")
                # Save to a temporary file to ensure proper handling
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                    temp_file.write(response.content)
                    temp_file_path = temp_file.name
                
                try:
                    # Use PyPDF2 to extract text
                    import PyPDF2
                    logger.info(f"Extracting from downloaded PDF using PyPDF2 {PyPDF2.__version__}")
                    
                    with open(temp_file_path, 'rb') as f:
                        pdf_reader = PyPDF2.PdfReader(f)
                        extracted_text = ""
                        total_pages = len(pdf_reader.pages)
                        logger.info(f"PDF has {total_pages} pages")
                        
                        for page_num in range(total_pages):
                            page = pdf_reader.pages[page_num]
                            page_text = page.extract_text()
                            if page_text:
                                extracted_text += page_text + "\n\n"
                                
                        if extracted_text.strip():
                            logger.info(f"Successfully extracted {len(extracted_text)} chars of text from PDF")
                            return extracted_text
                        else:
                            logger.warning("PDF text extraction yielded empty content")
                            return "[PDF document contained no extractable text]"  
                except Exception as pdf_error:
                    logger.error(f"Error extracting text from downloaded PDF: {str(pdf_error)}")
                    return f"[PDF extraction error: {str(pdf_error)}]"  
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(temp_file_path)
                    except Exception as e:
                        logger.error(f"Error cleaning up temp file: {str(e)}")
            
            # For text content, return as is
            elif 'text' in content_type:
                return response.text
            
            # For JSON, format it nicely
            elif 'json' in content_type:
                try:
                    import json
                    json_data = response.json()
                    return json.dumps(json_data, indent=2)
                except:
                    return response.text
            
            # For other types, return a placeholder
            else:
                return f"[Binary content of type {content_type} - {len(response.content)} bytes]"
        else:
            logger.error(f"Failed to download file: HTTP {response.status_code}")
            return f"[Error downloading file: HTTP {response.status_code}]"
    
    except Exception as e:
        logger.error(f"Error downloading/processing URL: {type(e).__name__}: {str(e)}")
        return f"[Error processing URL: {str(e)}]"

def extract_text_from_pdf(pdf_content):
    """
    Extract text from PDF binary content.
    
    Args:
        pdf_content (bytes): Binary content of the PDF file
        
    Returns:
        str: Extracted text from the PDF
    """
    # First, save a small sample of the PDF content for debugging
    sample = pdf_content[:100].hex()
    logger.info(f"PDF content sample (first 100 bytes): {sample}")
    logger.info(f"Total PDF content size: {len(pdf_content)} bytes")
    
    try:
        # Import PyPDF2 here to avoid import errors if not available
        import PyPDF2
        print(f"Using PyPDF2 version: {PyPDF2.__version__}")
        
        # Create a file-like object from the content
        pdf_stream = io.BytesIO(pdf_content)
        pdf_stream.seek(0)  # Ensure we're at the start of the stream
        
        # Try to validate if this is actually a PDF
        if pdf_content[:4] != b'%PDF':
            logger.warning("Content does not appear to be a valid PDF (missing %PDF header)")
            # Try to recover by looking for PDF signature anywhere in the first 1KB
            pdf_sig_pos = pdf_content[:1024].find(b'%PDF')
            if pdf_sig_pos >= 0:
                logger.info(f"Found PDF signature at position {pdf_sig_pos}, attempting recovery")
                pdf_stream = io.BytesIO(pdf_content[pdf_sig_pos:])
            else:
                return "[Content does not appear to be a valid PDF file]" 
        
        # Use PyPDF2 to extract text
        pdf_reader = PyPDF2.PdfReader(pdf_stream)
        
        # Extract text from all pages
        extracted_text = ""
        total_pages = len(pdf_reader.pages)
        logger.info(f"Extracting text from PDF with {total_pages} pages")
        
        for page_num in range(total_pages):
            try:
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n\n"
                logger.info(f"Extracted {len(page_text) if page_text else 0} chars from page {page_num+1}")
            except Exception as page_error:
                logger.error(f"Error extracting text from page {page_num+1}: {str(page_error)}")
                extracted_text += f"[Error extracting page {page_num+1}]\n\n"
            
        if not extracted_text.strip():
            logger.warning("PDF text extraction yielded empty content")
            # Try an alternative extraction method
            try:
                # Try a different approach for scanned PDFs
                alternate_text = ""
                for page_num in range(total_pages):
                    page = pdf_reader.pages[page_num]
                    # Try to get text using different extraction parameters
                    if hasattr(page, 'get_text'):
                        alternate_text += page.get_text("text") + "\n\n"
                    
                if alternate_text.strip():
                    logger.info(f"Alternative extraction method yielded {len(alternate_text)} chars")
                    return alternate_text
            except Exception as alt_error:
                logger.error(f"Alternative extraction method failed: {str(alt_error)}")
            
            return "[PDF document contains no extractable text content or may be scanned/image-based]"  
        
        logger.info(f"Successfully extracted {len(extracted_text)} chars of text from PDF")
        
        # Check for common PDF issues that might indicate extraction problems
        if "trailer" in extracted_text and "xref" in extracted_text and "startxref" in extracted_text:
            logger.warning("Extracted text contains PDF structure elements - may be raw PDF")
            return "[PDF extraction error: raw PDF structure detected in output]"  
            
        return extracted_text
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {type(e).__name__}: {str(e)}")
        return f"[PDF text extraction failed: {str(e)}]"
