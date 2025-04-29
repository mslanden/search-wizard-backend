#!/usr/bin/env python3
"""
This file contains functions to handle artifact processing for the Search Wizard API.
Copy the functions from this file into api.py to replace the existing logic.
"""

import os
import tempfile
import requests
from urllib.parse import urlparse


def download_pdf_and_extract_text(file_url):
    """
    Download a PDF from a URL and extract text content directly.
    
    Args:
        file_url (str): URL to the PDF file
    
    Returns:
        str: Extracted text content or error message
    """
    # Set up headers for Supabase if needed
    headers = {}
    parsed_url = urlparse(file_url)
    if 'supabase.co' in parsed_url.netloc:
        supabase_key = os.environ.get('SUPABASE_KEY')
        if supabase_key:
            headers['apikey'] = supabase_key
            print("Using Supabase service role key for authentication")
    
    # Download the file directly
    print(f"Downloading PDF from URL: {file_url}")
    response = requests.get(file_url, headers=headers, timeout=30)
    
    if response.status_code != 200:
        print(f"Error downloading PDF: HTTP {response.status_code}")
        return f"[Error downloading PDF: HTTP {response.status_code}]"
    
    # Create a temporary file to safely process the PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        temp_file.write(response.content)
        temp_file_path = temp_file.name
    
    try:
        # Use PyPDF2 to extract text content
        import PyPDF2
        print(f"Processing PDF with PyPDF2 {PyPDF2.__version__}")
        
        with open(temp_file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text_content = ""
            total_pages = len(pdf_reader.pages)
            print(f"PDF has {total_pages} pages")
            
            for page_num in range(total_pages):
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n\n"
                    print(f"Extracted {len(page_text) if page_text else 0} chars from page {page_num+1}")
                except Exception as e:
                    print(f"Error on page {page_num+1}: {str(e)}")
        
        if text_content.strip():
            print(f"Successfully extracted {len(text_content)} chars from PDF")
            return text_content
        else:
            print("Warning: PDF extraction yielded no text content")
            return "[PDF document contains no extractable text]"
    except Exception as e:
        print(f"Error extracting PDF text: {str(e)}")
        return f"[PDF extraction error: {str(e)}]"
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except:
            pass


def get_artifact_content_from_url(url, artifact_name):
    """
    Get content from a URL, handling different content types appropriately.
    
    Args:
        url (str): URL to fetch content from
        artifact_name (str): Name of the artifact for logging
    
    Returns:
        str: Content from the URL
    """
    print(f"Fetching content for {artifact_name} from URL: {url}")
    
    try:
        # Set up headers for Supabase if needed
        headers = {}
        parsed_url = urlparse(url)
        if 'supabase.co' in parsed_url.netloc:
            supabase_key = os.environ.get('SUPABASE_KEY')
            if supabase_key:
                headers['apikey'] = supabase_key
        
        # Make the request
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return f"[Error fetching content: HTTP {response.status_code}]"
        
        # Check content type to handle different formats
        content_type = response.headers.get('Content-Type', '').lower()
        
        # Handle PDF content
        if 'pdf' in content_type or url.lower().endswith('.pdf'):
            return download_pdf_and_extract_text(url)
        
        # Handle text content
        elif 'text' in content_type:
            return response.text
        
        # Handle JSON content
        elif 'json' in content_type:
            import json
            try:
                json_data = response.json()
                return json.dumps(json_data, indent=2)
            except:
                return response.text
        
        # Handle other content types
        else:
            return f"[Binary content of type {content_type} - {len(response.content)} bytes]"
    
    except Exception as e:
        print(f"Error fetching content: {str(e)}")
        return f"[Error: {str(e)}]"


# IMPORTANT: Replace the existing artifact processing code with the following:

# For company artifacts, add this within the company artifact processing section:
"""
# Instead of using the description from the artifact, prioritize downloading from the URL
file_url = artifact.get("fileUrl")
if file_url:
    print(f"Found direct file URL for {name}, using it to fetch content")
    description = get_artifact_content_from_url(file_url, name)
    print(f"Retrieved {len(description)} chars of content")
"""

# For role artifacts, add the same code in the role artifact processing section:
"""
# Instead of using the description from the artifact, prioritize downloading from the URL
file_url = artifact.get("fileUrl")
if file_url:
    print(f"Found direct file URL for {name}, using it to fetch content")
    description = get_artifact_content_from_url(file_url, name)
    print(f"Retrieved {len(description)} chars of content")
"""
