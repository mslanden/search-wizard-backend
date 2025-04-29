#!/usr/bin/env python3
"""
Test script for PDF extraction from URL
"""

import os

# Try to import dotenv, but continue if it fails
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not found, environment variables from .env file will not be loaded")
    # Continue without loading .env

from pdf_extractor import download_and_extract_pdf

# The problematic PDF URL from the debug logs
pdf_url = "https://nbdxduxbnyqluylmjnad.supabase.co/storage/v1/object/sign/company-artifacts/2895f37e-3709-412b-b5b9-74cb35e2fbdd/f2ab0ab7-8186-4857-ac16-b4527d84f006/cd9e63e1-3ff3-4580-bb65-b8943e3199db.pdf?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1cmwiOiJjb21wYW55LWFydGlmYWN0cy8yODk1ZjM3ZS0zNzA5LTQxMmItYjViOS03NGNiMzVlMmZiZGQvZjJhYjBhYjctODE4Ni00ODU3LWFjMTYtYjQ1MjdkODRmMDA2L2NkOWU2M2UxLTNmZjMtNDU4MC1iYjY1LWI4OTQzZTMxOTlkYi5wZGYiLCJpYXQiOjE3NDQwNzI4OTIsImV4cCI6MTc3NTYwODg5Mn0.EQmC9v5wFnTEnk1YtvPYn5nXWyUKfIuRPy6EOFCHdOw"

print("Testing PDF extraction from URL")
print(f"URL: {pdf_url}")

# Try to download and extract text
extracted_text = download_and_extract_pdf(pdf_url, "examplecompany")

# Print results
print(f"Extracted {len(extracted_text)} characters")
print("--- EXTRACT START ---")
print(extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text)
print("--- EXTRACT END ---")
