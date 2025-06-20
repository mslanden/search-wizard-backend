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


def scrape_url_content(url: str) -> str:
    """
    Scrape and extract text content from a URL.
    
    Args:
        url (str): URL to scrape
        
    Returns:
        str: Extracted text content from the webpage
    """
    try:
        from bs4 import BeautifulSoup
        import re
        
        logger.info(f"Scraping content from URL: {url}")
        
        # Add user agent to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()
        
        # Get main content - try common content containers first
        content_selectors = [
            'main', 'article', '[role="main"]', '.content', '#content',
            '.post-content', '.entry-content', '.article-body'
        ]
        
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            # Fallback to body
            main_content = soup.find('body')
        
        if not main_content:
            main_content = soup
        
        # Extract text
        text = main_content.get_text(separator=' ', strip=True)
        
        # Clean up text
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Clean up line breaks
        
        # Extract page title if available
        title = soup.find('title')
        if title:
            title_text = title.get_text().strip()
            text = f"Title: {title_text}\n\n{text}"
        
        logger.info(f"Successfully extracted {len(text)} characters from URL")
        return text
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching URL {url}: {str(e)}")
        return f"[Error fetching URL: {str(e)}]"
    except Exception as e:
        logger.error(f"Error scraping content from {url}: {str(e)}")
        return f"[Error extracting content: {str(e)}]"


def process_text_content(text: str, artifact_type: str = None) -> str:
    """
    Process raw text content based on artifact type.
    
    Args:
        text (str): Raw text content
        artifact_type (str, optional): Type of artifact for specialized processing
        
    Returns:
        str: Processed text content
    """
    try:
        import re
        
        logger.info(f"Processing text content of {len(text)} characters")
        
        # Basic text cleaning
        processed_text = text.strip()
        
        # Normalize whitespace
        processed_text = re.sub(r'\s+', ' ', processed_text)
        
        # Clean up excessive line breaks
        processed_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', processed_text)
        
        # Remove any control characters except newlines and tabs
        processed_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', processed_text)
        
        # Artifact-type specific processing
        if artifact_type:
            artifact_type = artifact_type.lower()
            
            if 'job' in artifact_type or 'posting' in artifact_type:
                # For job postings, try to structure the content
                processed_text = structure_job_posting_text(processed_text)
            elif 'resume' in artifact_type or 'cv' in artifact_type:
                # For resumes, maintain structure better
                processed_text = structure_resume_text(processed_text)
            elif 'company' in artifact_type:
                # For company info, try to extract key sections
                processed_text = structure_company_text(processed_text)
        
        logger.info(f"Text processing complete, output length: {len(processed_text)}")
        return processed_text
        
    except Exception as e:
        logger.error(f"Error processing text content: {str(e)}")
        return text  # Return original text if processing fails


def structure_job_posting_text(text: str) -> str:
    """Structure job posting text to highlight key sections."""
    sections = {
        'title': r'(?i)(job title|position|role):\s*(.+?)(?=\n|$)',
        'company': r'(?i)(company|organization):\s*(.+?)(?=\n|$)',
        'location': r'(?i)(location|where):\s*(.+?)(?=\n|$)',
        'requirements': r'(?i)(requirements?|qualifications?|skills?):(.*?)(?=\n\n|\Z)',
        'responsibilities': r'(?i)(responsibilities?|duties?|role description):(.*?)(?=\n\n|\Z)',
        'benefits': r'(?i)(benefits?|compensation|salary):(.*?)(?=\n\n|\Z)'
    }
    
    structured_text = text
    for section, pattern in sections.items():
        match = re.search(pattern, text, re.DOTALL)
        if match and len(match.groups()) > 1:
            content = match.group(2).strip()
            if content:
                structured_text = structured_text.replace(match.group(0), f"\n\n{section.upper()}:\n{content}")
    
    return structured_text


def structure_resume_text(text: str) -> str:
    """Structure resume text to maintain formatting."""
    # Preserve section headers and structure
    text = re.sub(r'(?i)^(experience|education|skills|summary|objective|contact)(.*)$', 
                  r'\n\1\2\n', text, flags=re.MULTILINE)
    return text


def structure_company_text(text: str) -> str:
    """Structure company information text."""
    # Look for common company info sections
    sections = ['about', 'mission', 'values', 'history', 'products', 'services']
    for section in sections:
        pattern = rf'(?i)^({section}[:\s]*)(.*)$'
        text = re.sub(pattern, rf'\n\1\n\2', text, flags=re.MULTILINE)
    return text
