#!/usr/bin/env python3
"""
Fix PDF Handling

This script adds dedicated functions to properly download and extract text from PDF files.
The code will be copied into api.py to replace the current PDF handling logic.
"""

import os
import tempfile
import requests
from urllib.parse import urlparse


def download_and_extract_pdf(file_url, name="Unknown"):
    """
    Download PDF from URL and extract its text content directly.
    
    Args:
        file_url (str): URL to download the PDF from
        name (str): Name of the document for logging
        
    Returns:
        str: Extracted text or error message
    """
    print(f"Downloading PDF directly from URL for {name}: {file_url}")
    
    try:
        # Set up headers for Supabase if needed
        headers = {}
        parsed_url = urlparse(file_url)
        if 'supabase.co' in parsed_url.netloc:
            supabase_key = os.environ.get('SUPABASE_KEY')
            if supabase_key:
                headers['apikey'] = supabase_key
                print("Using Supabase service role key for authentication")

        # Download the file (handle signed URLs directly without modification)
        response = requests.get(file_url, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"Error downloading PDF: HTTP {response.status_code}")
            return f"[Error downloading PDF: HTTP {response.status_code}]"
        
        # Save to a temporary file to process with PyPDF2
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name
        
        try:
            # Use PyPDF2 to extract text
            import PyPDF2
            print(f"Extracting text using PyPDF2 {PyPDF2.__version__}")
            
            with open(temp_file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                total_pages = len(pdf_reader.pages)
                print(f"PDF has {total_pages} pages")
                
                extracted_text = ""
                for page_num in range(total_pages):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n\n"
                
                if extracted_text.strip():
                    print(f"Successfully extracted {len(extracted_text)} chars of text")
                    return extracted_text
                else:
                    print("PDF text extraction yielded empty content")
                    return "[PDF document contained no extractable text]"
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            return f"[Error extracting PDF text: {str(e)}]"
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                print(f"Error cleaning up temp file: {str(e)}")
    except Exception as e:
        print(f"Error in PDF extraction process: {str(e)}")
        return f"[Error processing PDF: {str(e)}]"


# Company artifact processing (replace lines ~204-243)
def company_pdf_detection_code():
    """Code to replace the current company PDF detection logic"""
    return """
            # Check if we have a corrupt PDF content or need to use file URL directly
            file_url = artifact.get("fileUrl")
            if file_url and ('trailer' in description or 'xref' in description or 'startxref' in description or '\\ufffd' in description):
                print(f"Detected corrupted PDF content for {name}, attempting to download and extract from URL directly")
                
                # Download and extract text from PDF URL directly
                extracted_text = download_and_extract_pdf(file_url, name)
                
                # If extraction was successful, use the extracted text
                if extracted_text and len(extracted_text) > 10 and not extracted_text.startswith("[Error"):
                    description = extracted_text
                    print(f"Successfully extracted {len(description)} chars of text from PDF URL directly")
                else:
                    print(f"Warning: Direct URL extraction failed: {extracted_text[:100]}")
    """


# Role artifact processing (replace lines ~336-375)
def role_pdf_detection_code():
    """Code to replace the current role PDF detection logic"""
    return """
            # Check if we have a corrupt PDF content or need to use file URL directly
            file_url = artifact.get("fileUrl")
            if file_url and ('trailer' in description or 'xref' in description or 'startxref' in description or '\\ufffd' in description):
                print(f"Detected corrupted PDF content for {name}, attempting to download and extract from URL directly")
                
                # Download and extract text from PDF URL directly
                extracted_text = download_and_extract_pdf(file_url, name)
                
                # If extraction was successful, use the extracted text
                if extracted_text and len(extracted_text) > 10 and not extracted_text.startswith("[Error"):
                    description = extracted_text
                    print(f"Successfully extracted {len(description)} chars of text from PDF URL directly")
                else:
                    print(f"Warning: Direct URL extraction failed: {extracted_text[:100]}")
    """
