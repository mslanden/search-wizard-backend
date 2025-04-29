#!/usr/bin/env python3
"""
API Server for Search Wizard

This FastAPI server exposes endpoints for document generation and other backend functionality.
"""

import os
import json
import sys
import datetime
import requests
from typing import Optional, Dict, List, Any
from fastapi import FastAPI, HTTPException, Body, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables for API keys
load_dotenv()

# Print environment variables for debugging
print("Environment variables loaded:")
print(f"SUPABASE_URL: {'Set' if os.environ.get('SUPABASE_URL') else 'Not set'}")
print(f"SUPABASE_KEY: {'Set' if os.environ.get('SUPABASE_KEY') else 'Not set'}")
print(f"OPENAI_API_KEY: {'Set' if os.environ.get('OPENAI_API_KEY') else 'Not set'}")
print(f"ANTHROPIC_API_KEY: {'Set' if os.environ.get('ANTHROPIC_API_KEY') else 'Not set'}")
print(f"GEMINI_API_KEY: {'Set' if os.environ.get('GEMINI_API_KEY') else 'Not set'}")

from agents.structure_agent import StructureAgent
from agents.writer_agent import WriterAgent
from agents.kb_support import enhance_prompt_with_kb

# Import our utility functions
from utils import extract_text_from_pdf

# Initialize FastAPI app
app = FastAPI(title="Search Wizard API", 
              description="API for document generation and other backend functionality",
              version="1.0.0")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint to verify the API is running"""
    return {"status": "ok", "message": "API is running"}

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# File analysis endpoint
@app.post("/analyze-file")
async def analyze_file(file: UploadFile = File(...)):
    """Analyze a file using the StructureAgent to extract document structure"""
    try:
        # Save the uploaded file to a temporary location
        temp_file_path = f"/tmp/{file.filename}"
        with open(temp_file_path, "wb") as temp_file:
            content = await file.read()
            temp_file.write(content)
            
        # Initialize the structure agent
        structure_agent = StructureAgent(framework="openai")
        
        # Analyze the file
        structure = structure_agent.analyze_structure([temp_file_path])
        
        # Clean up the temporary file
        os.remove(temp_file_path)
        
        return {"structure": structure}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing file: {str(e)}")

# Structure analysis endpoint
@app.post("/analyze-structure")
async def analyze_structure(request: dict = Body(...)):
    """Analyze a document structure from a file URL"""
    try:
        document_id = request.get("documentId")
        file_url = request.get("fileUrl")
        
        if not document_id or not file_url:
            raise HTTPException(status_code=400, detail="Missing documentId or fileUrl")
            
        # Download the file from the URL
        temp_file_path = f"/tmp/document_{document_id}.pdf"
        response = requests.get(file_url)
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Failed to download file: {response.status_code}")
            
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(response.content)
            
        # Initialize the structure agent
        structure_agent = StructureAgent(framework="openai")
        
        # Analyze the file
        structure = structure_agent.analyze_structure([temp_file_path])
        
        # Clean up the temporary file
        os.remove(temp_file_path)
        
        return {"structure": structure}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing structure: {str(e)}")

# Document generation endpoint
@app.post("/generate-document")
async def generate_document(request: dict = Body(...)):
    """Generate a document based on a document type and structure"""
    try:
        document_type = request.get("document_type")
        structure = request.get("structure")
        user_input = request.get("user_input", "")
        
        if not document_type or not structure:
            raise HTTPException(status_code=400, detail="Missing document_type or structure")
        
        # Initialize the writer agent
        writer_agent = WriterAgent(framework="openai")
        
        # Generate the document
        generated_document = writer_agent.create_document_with_structure(
            document_type=document_type,
            structure=structure,
            user_input=user_input
        )
        
        # Return the generated document
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {
            "html_content": generated_document,
            "document_type": document_type,
            "timestamp": timestamp
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating document: {str(e)}")

# Initialize agents at startup
structure_agent = None
writer_agent = None

# Pydantic models for request/response
class DocumentRequest(BaseModel):
    document_type: str
    project_id: Optional[str] = None
    company_artifacts: Optional[List[Dict[str, Any]]] = []
    role_artifacts: Optional[List[Dict[str, Any]]] = []
    user_requirements: Optional[str] = ""

class DocumentResponse(BaseModel):
    html_content: str
    document_type: str
    timestamp: str

def setup_agents():
    """Initialize both agents using available API keys."""
    global structure_agent, writer_agent
    
    # Get API key from environment variables - try in order of preference (OpenAI first)
    api_key = os.getenv("OPENAI_API_KEY")
    framework = "openai"
    
    if not api_key:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        framework = "anthropic"
        
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
        framework = "gemini"
        
    if not api_key:
        print("Error: No API key found in environment variables.")
        print("Please set one of the following in your .env file:")
        print("- OPENAI_API_KEY")
        print("- ANTHROPIC_API_KEY")
        print("- GEMINI_API_KEY")
        return False
    
    # Initialize both agents with the same framework and API key
    structure_agent = StructureAgent(framework=framework, api_key=api_key)
    writer_agent = WriterAgent(framework=framework, api_key=api_key)
    
    return True

@app.on_event("startup")
async def startup_event():
    """Initialize agents when the API server starts."""
    if not setup_agents():
        print("WARNING: Failed to initialize agents. API will not function correctly.")

@app.get("/")
async def root():
    """Root endpoint to check if the API is running."""
    return {"status": "ok", "message": "Search Wizard API is running"}

@app.post("/generate-document", response_model=DocumentResponse)
async def generate_document(request: DocumentRequest):
    """Generate a document based on the provided parameters."""
    # Make sure json is available throughout this function's scope
    import json
    
    global writer_agent
    
    # Check if writer agent is initialized
    if not writer_agent:
        if not setup_agents():
            raise HTTPException(status_code=500, detail="Failed to initialize document generation agents")
    
    try:
        # Prepare knowledge base from artifacts
        knowledge_base = []
    except Exception as e:
        print(f"Error initializing knowledge base: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize knowledge base: {str(e)}")
        
    try:
        
        # Process company artifacts
        print(f"Processing {len(request.company_artifacts)} company artifacts")
        print(f"Company artifacts raw data: {json.dumps(request.company_artifacts, indent=2)}")
        for artifact in request.company_artifacts:
            print(f"Processing artifact: {json.dumps(artifact, indent=2)}")
            print(f"Artifact keys: {list(artifact.keys())}")
            name = artifact.get("name", "")
            
            # Get the actual content from the artifact
            description = artifact.get("description", "")
            
            # If description is empty or very short, try to fetch from file_url
            if not description or len(description) < 10:
                file_url = artifact.get("file_url") or artifact.get("fileUrl")
                file_path = artifact.get("file_path") or artifact.get("filePath")
                
                if file_url:
                    print(f"Attempting to fetch content from file_url: {file_url}")
                    # Check if the URL is a Supabase storage URL or publicly accessible URL
                    try:
                        import requests
                        from urllib.parse import urlparse, quote
                        
                        # Handle Supabase storage URLs
                        parsed_url = urlparse(file_url)
                        
                        # Set appropriate headers based on URL type
                        headers = {}
                        if 'supabase.co' in parsed_url.netloc and '/storage/v1/object/public/' in parsed_url.path:
                            # This is a Supabase storage URL, add authentication if needed
                            supabase_key = os.environ.get('SUPABASE_KEY')
                            if supabase_key:
                                headers['apikey'] = supabase_key
                                print("Added Supabase authentication to request")
                            
                            # Ensure URL is properly encoded
                            path_parts = parsed_url.path.split('/storage/v1/object/public/')
                            if len(path_parts) > 1:
                                encoded_path = '/storage/v1/object/public/' + quote(path_parts[1])
                                file_url = f"{parsed_url.scheme}://{parsed_url.netloc}{encoded_path}"
                                print(f"Encoded Supabase URL: {file_url}")
                        
                        # Make the request with appropriate headers
                        response = requests.get(file_url, headers=headers)
                        
                        if response.status_code == 200:
                            # Check content type to handle binary files
                            content_type = response.headers.get('Content-Type', '')
                            if 'text' in content_type or 'json' in content_type or 'xml' in content_type:
                                description = response.text
                            else:
                                # For binary files, use a placeholder message
                                description = f"[Binary content of type {content_type} - {len(response.content)} bytes]"
                                # For PDF files, extract text content
                                if 'pdf' in content_type:
                                    print(f"Processing PDF file: {name}")
                                    extracted_text = extract_text_from_pdf(response.content)
                                    description = extracted_text
                                    print(f"Extracted {len(description)} chars from PDF")
                            
                            print(f"Successfully fetched content from file_url: {len(description)} chars (Content-Type: {content_type})")
                        else:
                            print(f"Failed to fetch content from file_url: {response.status_code}, Response: {response.text[:100]}")
                    except Exception as e:
                        print(f"Error fetching content from file_url: {type(e).__name__}: {str(e)}")
                elif file_path:
                    print(f"Artifact has file_path but no direct URL: {file_path}")
            
            if not description or len(description) < 10:
                print(f"Warning: No substantial content found for artifact {name}")
            

            # Check if this is raw PDF content by looking for PDF markers in the text
            if 'trailer' in description and 'xref' in description and 'startxref' in description and '\u0000' in description:
                print(f"Detected raw PDF content for {name}, attempting to extract text properly")
                
                # If there's a file_url available, try to download and extract directly from the URL
                file_url = artifact.get("file_url") or artifact.get("fileUrl")
                if file_url:
                    try:
                        print(f"Attempting to download and extract directly from URL: {file_url}")
                        from utils import download_and_extract_pdf
                        extracted_text = download_and_extract_pdf(file_url)
                        if extracted_text and len(extracted_text) > 10:
                            description = extracted_text
                            print(f"Successfully extracted {len(description)} chars of text directly from PDF URL")
                        else:
                            print(f"Direct URL extraction failed, falling back to temp file method")
                            # Continue to temp file approach as fallback
                    except Exception as url_error:
                        print(f"Error downloading and extracting from URL: {str(url_error)}")
                        # Continue to temp file approach as fallback
                
                # If URL extraction failed or wasn't attempted, use temp file approach
                if 'trailer' in description and 'xref' in description and 'startxref' in description:
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                        try:
                            # Write the PDF content to the temporary file
                            temp_file.write(description.encode('utf-8', errors='ignore'))
                            temp_file_path = temp_file.name
                        except Exception as e:
                            print(f"Error writing temp PDF file: {str(e)}")
                            temp_file_path = None
                    
                    if temp_file_path:
                        try:
                            # Use PyPDF2 to extract text
                            import PyPDF2
                            print(f"Attempting to extract text from PDF using PyPDF2 {PyPDF2.__version__}")
                            with open(temp_file_path, 'rb') as f:
                                reader = PyPDF2.PdfReader(f)
                                extracted_text = ""
                                for page in reader.pages:
                                    page_text = page.extract_text()
                                    if page_text:
                                        extracted_text += page_text + "\n\n"
                            
                            # If extraction successful, replace description
                            if extracted_text.strip():
                                description = extracted_text
                                print(f"Successfully extracted {len(description)} chars of text from temp PDF file")
                            else:
                                print("Warning: PDF text extraction yielded empty content")
                        except Exception as pdf_error:
                            print(f"Error extracting text from PDF: {str(pdf_error)}")
                        finally:
                            # Clean up temporary file
                            import os
                            try:
                                os.unlink(temp_file_path)
                            except:
                                pass
                            
            print(f"Company artifact: {name} - {len(description)} chars")
            # Use chunking for large artifacts
            if len(description) > 5000:  # Chunk if over 5k characters
                print(f"Chunking large content for {name} ({len(description)} chars)")
                chunks = naive_linechunk(description)
                for i, chunk in enumerate(chunks):
                    knowledge_base.append({
                        "type": "company",
                        "name": f"{name} (part {i+1}/{len(chunks)})",
                        "content": chunk
                    })
                print(f"Split {name} into {len(chunks)} chunks")
            else:
                knowledge_base.append({
                    "type": "company",
                    "name": name,
                    "content": description
                })
            
        # Process role artifacts
        print(f"Processing {len(request.role_artifacts)} role artifacts")
        print(f"Role artifacts raw data: {json.dumps(request.role_artifacts, indent=2)}")
        for artifact in request.role_artifacts:
            print(f"Processing role artifact: {json.dumps(artifact, indent=2)}")
            print(f"Role artifact keys: {list(artifact.keys())}")
            name = artifact.get("name", "")
            
            # Get the actual content from the artifact
            description = artifact.get("description", "")
            
            # If description is empty or very short, try to fetch from file_url
            if not description or len(description) < 10:
                file_url = artifact.get("file_url") or artifact.get("fileUrl")
                file_path = artifact.get("file_path") or artifact.get("filePath")
                
                if file_url:
                    print(f"Attempting to fetch content from file_url: {file_url}")
                    # Check if the URL is a Supabase storage URL or publicly accessible URL
                    try:
                        import requests
                        from urllib.parse import urlparse, quote
                        
                        # Handle Supabase storage URLs
                        parsed_url = urlparse(file_url)
                        
                        # Set appropriate headers based on URL type
                        headers = {}
                        if 'supabase.co' in parsed_url.netloc and '/storage/v1/object/public/' in parsed_url.path:
                            # This is a Supabase storage URL, add authentication if needed
                            supabase_key = os.environ.get('SUPABASE_KEY')
                            if supabase_key:
                                headers['apikey'] = supabase_key
                                print("Added Supabase authentication to request")
                            
                            # Ensure URL is properly encoded
                            path_parts = parsed_url.path.split('/storage/v1/object/public/')
                            if len(path_parts) > 1:
                                encoded_path = '/storage/v1/object/public/' + quote(path_parts[1])
                                file_url = f"{parsed_url.scheme}://{parsed_url.netloc}{encoded_path}"
                                print(f"Encoded Supabase URL: {file_url}")
                        
                        # Make the request with appropriate headers
                        response = requests.get(file_url, headers=headers)
                        
                        if response.status_code == 200:
                            # Check content type to handle binary files
                            content_type = response.headers.get('Content-Type', '')
                            if 'text' in content_type or 'json' in content_type or 'xml' in content_type:
                                description = response.text
                            else:
                                # For binary files, use a placeholder message
                                description = f"[Binary content of type {content_type} - {len(response.content)} bytes]"
                                # For PDF files, extract text content
                                if 'pdf' in content_type:
                                    print(f"Processing PDF file: {name}")
                                    extracted_text = extract_text_from_pdf(response.content)
                                    description = extracted_text
                                    print(f"Extracted {len(description)} chars from PDF")
                            
                            print(f"Successfully fetched content from file_url: {len(description)} chars (Content-Type: {content_type})")
                        else:
                            print(f"Failed to fetch content from file_url: {response.status_code}, Response: {response.text[:100]}")
                    except Exception as e:
                        print(f"Error fetching content from file_url: {type(e).__name__}: {str(e)}")
                elif file_path:
                    print(f"Artifact has file_path but no direct URL: {file_path}")
            
            if not description or len(description) < 10:
                print(f"Warning: No substantial content found for artifact {name}")
            

            # Check if this is raw PDF content by looking for PDF markers in the text
            if 'trailer' in description and 'xref' in description and 'startxref' in description and '\u0000' in description:
                print(f"Detected raw PDF content for {name}, attempting to extract text properly")
                
                # If there's a file_url available, try to download and extract directly from the URL
                file_url = artifact.get("file_url") or artifact.get("fileUrl")
                if file_url:
                    try:
                        print(f"Attempting to download and extract directly from URL: {file_url}")
                        from utils import download_and_extract_pdf
                        extracted_text = download_and_extract_pdf(file_url)
                        if extracted_text and len(extracted_text) > 10:
                            description = extracted_text
                            print(f"Successfully extracted {len(description)} chars of text directly from PDF URL")
                        else:
                            print(f"Direct URL extraction failed, falling back to temp file method")
                            # Continue to temp file approach as fallback
                    except Exception as url_error:
                        print(f"Error downloading and extracting from URL: {str(url_error)}")
                        # Continue to temp file approach as fallback
                
                # If URL extraction failed or wasn't attempted, use temp file approach
                if 'trailer' in description and 'xref' in description and 'startxref' in description:
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                        try:
                            # Write the PDF content to the temporary file
                            temp_file.write(description.encode('utf-8', errors='ignore'))
                            temp_file_path = temp_file.name
                        except Exception as e:
                            print(f"Error writing temp PDF file: {str(e)}")
                            temp_file_path = None
                    
                    if temp_file_path:
                        try:
                            # Use PyPDF2 to extract text
                            import PyPDF2
                            print(f"Attempting to extract text from PDF using PyPDF2 {PyPDF2.__version__}")
                            with open(temp_file_path, 'rb') as f:
                                reader = PyPDF2.PdfReader(f)
                                extracted_text = ""
                                for page in reader.pages:
                                    page_text = page.extract_text()
                                    if page_text:
                                        extracted_text += page_text + "\n\n"
                            
                            # If extraction successful, replace description
                            if extracted_text.strip():
                                description = extracted_text
                                print(f"Successfully extracted {len(description)} chars of text from temp PDF file")
                            else:
                                print("Warning: PDF text extraction yielded empty content")
                        except Exception as pdf_error:
                            print(f"Error extracting text from PDF: {str(pdf_error)}")
                        finally:
                            # Clean up temporary file
                            import os
                            try:
                                os.unlink(temp_file_path)
                            except:
                                pass
            
            print(f"Role artifact: {name} - {len(description)} chars")
            # Use chunking for large artifacts
            if len(description) > 5000:  # Chunk if over 5k characters
                print(f"Chunking large content for {name} ({len(description)} chars)")
                chunks = naive_linechunk(description)
                for i, chunk in enumerate(chunks):
                    knowledge_base.append({
                        "type": "role",
                        "name": f"{name} (part {i+1}/{len(chunks)})",
                        "content": chunk
                    })
                print(f"Split {name} into {len(chunks)} chunks")
            else:
                knowledge_base.append({
                    "type": "role",
                    "name": name,
                    "content": description
                })
        
        # We'll use this knowledge base directly in the prompt instead of writing to a file
        print(f"Total artifacts processed: {len(knowledge_base)}")
        
        # Convert knowledge_base to a format that can be directly included in the prompt
        kb_content = ""
        for item in knowledge_base:
            kb_content += f"\n--- {item['type'].upper()}: {item['name']} ---\n{item['content']}\n\n"
        
        # Get the structure directly from golden_examples based on document type
        print(f"Fetching structure for document type: {request.document_type}")
        
        # Import required modules if not already imported
        try:
            from supabase import create_client
            import os  # Explicitly import os at this scope
            # json is already imported at the top level
            
            # Get Supabase credentials
            supabase_url = os.environ.get('SUPABASE_URL')
            supabase_key = os.environ.get('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                print("ERROR: Supabase credentials not found in environment variables")
                raise HTTPException(
                    status_code=500, 
                    detail="Supabase credentials missing. Please set SUPABASE_URL and SUPABASE_KEY in .env file"
                )
            
            # Initialize Supabase client
            # For service-role access to bypass RLS policies, we need to use service_key not anon key
            supabase = create_client(supabase_url, supabase_key)
            print(f"Successfully initialized Supabase client with URL: {supabase_url}")
            
            # Debug auth issue - get the JWT token from the key to check role
            import base64
            import json
            
            # Extract the payload part of the JWT (second part)
            try:
                jwt_parts = supabase_key.split('.')
                if len(jwt_parts) >= 2:
                    # Decode the base64 payload
                    payload = jwt_parts[1]
                    # Add padding if needed
                    payload += '=' * (4 - len(payload) % 4) if len(payload) % 4 else ''
                    decoded = base64.b64decode(payload).decode('utf-8')
                    jwt_data = json.loads(decoded)
                    print(f"DEBUG: JWT role: {jwt_data.get('role', 'unknown')}")
                else:
                    print("DEBUG: Invalid JWT format")
            except Exception as e:
                print(f"DEBUG: Error decoding JWT: {str(e)}")
            
            # Match the frontend approach by using the user ID directly
            # This follows the same logic as the frontend's getGoldenExamples function
            user_id = "2895f37e-3709-412b-b5b9-74cb35e2fbdd"  # This is the ID we found in our database query
            
            print(f"DEBUG: Using direct URL approach to bypass RLS")
            
            # Hard-code direct URLs from our database query
            structure_urls = {
                "Role Doc - Structure": "https://nbdxduxbnyqluylmjnad.supabase.co/storage/v1/object/sign/golden-examples/2895f37e-3709-412b-b5b9-74cb35e2fbdd/structures/53ce10ea-6659-4680-acc2-199a7d5ad410.json?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1cmwiOiJnb2xkZW4tZXhhbXBsZXMvMjg5NWYzN2UtMzcwOS00MTJiLWI1YjktNzRjYjM1ZTJmYmRkL3N0cnVjdHVyZXMvNTNjZTEwZWEtNjY1OS00NjgwLWFjYzItMTk5YTdkNWFkNDEwLmpzb24iLCJpYXQiOjE3NDQwNzUxMDYsImV4cCI6MTc3NTYxMTEwNn0.B-SAc30Q5RYoKUpxLBVe_fyqZiiB8lCCioxX_tT3g2c",
                "hiring - Structure": "https://nbdxduxbnyqluylmjnad.supabase.co/storage/v1/object/sign/golden-examples/2895f37e-3709-412b-b5b9-74cb35e2fbdd/structures/1d253552-b8b7-441d-8426-1d793258df33.json?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1cmwiOiJnb2xkZW4tZXhhbXBsZXMvMjg5NWYzN2UtMzcwOS00MTJiLWI1YjktNzRjYjM1ZTJmYmRkL3N0cnVjdHVyZXMvMWQyNTM1NTItYjhiNy00NDFkLTg0MjYtMWQ3OTMyNThkZjMzLmpzb24iLCJpYXQiOjE3NDQwNzUzMjMsImV4cCI6MTc3NTYxMTMyM30.SvKzh0mwGrfT18W4YLmzmGXuI3KM3AwuUVQ11DEsSTw"
            }
            
            # Query structures by user_id to work with RLS policies (keeping for backward compatibility)
            all_structures = supabase.table('golden_examples').select('*')\
                .eq('user_id', user_id)\
                .execute()
            
            # Debug: Print all structures found
            all_struct_data = getattr(all_structures, 'data', None)
            if all_struct_data is None and hasattr(all_structures, '__getitem__'):
                try:
                    all_struct_data = all_structures['data']
                except (KeyError, TypeError):
                    all_struct_data = []
            
            print(f"DEBUG: Found {len(all_struct_data or [])} total items in golden_examples table")
            for idx, item in enumerate(all_struct_data or []):
                name = ''
                example_type = ''
                if hasattr(item, 'get'):
                    name = item.get('name', '')
                    example_type = item.get('example_type', '')
                elif hasattr(item, '__getitem__'):
                    try:
                        name = item['name']
                        example_type = item['example_type']
                    except (KeyError, TypeError):
                        pass
                else:
                    name = getattr(item, 'name', '')
                    example_type = getattr(item, 'example_type', '')
                
                print(f"DEBUG: Item {idx+1}: name='{name}', type='{example_type}'")
            
            # Now query for the specific structure we need
            # Following the frontend approach to match successful queries
            print(f"Searching for structure with name: {request.document_type} and user_id: {user_id}")
            
            # Search by name AND user_id using the same approach as above
            response = supabase.table('golden_examples').select('*')\
                .eq('user_id', user_id)\
                .eq('name', request.document_type)\
                .execute()
            
            # Parse the response to get data
            result_data = getattr(response, 'data', None)
            if result_data is None and hasattr(response, '__getitem__'):
                try:
                    result_data = response['data']
                except (KeyError, TypeError):
                    result_data = []
                    
            # Log what we found
            if result_data and len(result_data) > 0:
                print(f"DEBUG: Found structure with name '{request.document_type}'")
                # Show what we found
                for idx, item in enumerate(result_data):
                    name = ''
                    example_type = ''
                    if hasattr(item, 'get'):
                        name = item.get('name', '')
                        example_type = item.get('example_type', '')
                    elif hasattr(item, '__getitem__'):
                        try:
                            name = item['name']
                            example_type = item['example_type']
                        except (KeyError, TypeError):
                            pass
                    else:
                        name = getattr(item, 'name', '')
                        example_type = getattr(item, 'example_type', '')
                    
                    print(f"DEBUG: Found match: name='{name}', type='{example_type}'")
            else:
                print(f"DEBUG: No structure found with name '{request.document_type}'")
            
            # Handle the response correctly based on the Supabase client version
            # Modern Supabase client returns an object with a data property
            result_data = getattr(response, 'data', None)
            
            # If data is not directly accessible as an attribute, try as a dictionary
            if result_data is None and hasattr(response, '__getitem__'):
                try:
                    result_data = response['data']
                except (KeyError, TypeError):
                    result_data = []
            
            if not result_data or len(result_data) == 0:
                print(f"ERROR: Structure not found for document type: {request.document_type}")
                # Get available structures using the same user_id to bypass RLS
                matching_structures = supabase.table('golden_examples').select('name').eq('user_id', user_id).execute()
                
                # Handle response based on Supabase client version
                struct_data = getattr(matching_structures, 'data', None)
                if struct_data is None and hasattr(matching_structures, '__getitem__'):
                    try:
                        struct_data = matching_structures['data']
                    except (KeyError, TypeError):
                        struct_data = []
                
                # Extract names from the struct_data
                available_structures = []
                for item in struct_data or []:
                    if hasattr(item, 'get'):
                        name = item.get('name', '')
                    elif hasattr(item, '__getitem__'):
                        try:
                            name = item['name']
                        except (KeyError, TypeError):
                            name = ''
                    else:
                        name = getattr(item, 'name', '')
                    
                    if name:
                        available_structures.append(name)
                
                # No fallbacks - if structure not found, provide a detailed error message
                print(f"ERROR: No fallbacks available. Structure must be added to Supabase.")
                
                # Prepare an informative error message
                error_detail = f"Structure not found for document type: {request.document_type}. "
                
                # Add available structures with their exact names if there are any
                if available_structures:
                    error_detail += f"Available structures: {', '.join(available_structures)}"
                else:
                    error_detail += "No structures available in the database. Please add a structure for this document type in Supabase."
                
                error_detail += "\n\nTo fix this issue:\n"
                error_detail += f"1. Check that Supabase credentials are properly set in your .env file. Current URL: {supabase_url[:10]}...\n"
                error_detail += f"2. Add a structure to the golden_examples table with name EXACTLY matching '{request.document_type}'\n"
                error_detail += "3. Or, if you're using a different naming convention, update the API to match how your structures are named\n"
                error_detail += "4. Check that the structure is being added with appropriate content format\n"
                error_detail += "5. Review the debug logs to see all available structures in the database"
                
                # Additional debugging info about what we're looking for
                print(f"DEBUG: Looking specifically for a structure with name '{request.document_type}'")
                print(f"DEBUG: Requested document_type was '{request.document_type}'")
                
                # Always raise an error without fallbacks
                raise HTTPException(
                    status_code=404,
                    detail=error_detail
                )
            
            # Extract structure from result
            structure_data = result_data[0] if result_data else {}
            
            # Get the file_url from structure_data
            file_url = None
            if hasattr(structure_data, 'get'):
                file_url = structure_data.get('file_url', '')
            elif hasattr(structure_data, '__getitem__'):
                try:
                    file_url = structure_data['file_url']
                except (KeyError, TypeError):
                    file_url = ''
            else:
                # If it's an object with attributes
                file_url = getattr(structure_data, 'file_url', '')
                
            print(f"DEBUG: Structure file URL: {file_url}")
            
            if not file_url:
                print("ERROR: Structure found but file_url is missing")
                raise HTTPException(
                    status_code=500,
                    detail=f"Structure missing file URL for document type: {request.document_type}"
                )
                
            # Download the structure file from the URL
            import requests
            import json  # Ensure json is imported in this scope
            
            response = requests.get(file_url)
            if response.status_code != 200:
                print(f"ERROR: Failed to download structure file: {response.status_code}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to download structure file: {response.status_code}"
                )
                
            # Use the downloaded file content as the structure_content
            structure_content = response.text
            
            # Parse structure from JSON content
            if isinstance(structure_content, str):
                try:
                    structure = json.loads(structure_content)
                    print(f"Successfully parsed structure from JSON: {json.dumps(structure, indent=2)[:200]}...")
                except json.JSONDecodeError:
                    print(f"ERROR: Failed to parse structure content as JSON: {structure_content[:200]}...")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Invalid structure format for document type: {request.document_type}"
                    )
            else:
                structure = structure_content
                print(f"Using structure object directly: {json.dumps(structure, indent=2)[:200]}...")
                
        except ImportError:
            print("ERROR: Supabase client not installed")
            raise HTTPException(
                status_code=500,
                detail="Supabase client not installed. Please install required dependencies."
            )
        except Exception as e:
            print(f"ERROR fetching structure from Supabase: {type(e).__name__}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch structure: {str(e)}"
            )
        
        print(f"Using structure: {json.dumps(structure, indent=2)}")
        
        print(f"Using structure: {structure}")
        
        # Pre-format the structure JSON to avoid using json.dumps inside the f-string
        structure_json = json.dumps(structure, indent=2)
        
        # Prepare the base prompt
        base_prompt = f"""

## Core Role and Expertise
You are a professional document writer tasked with creating a high-quality {request.document_type} document. Your capabilities span precise structural replication, professional content generation, advanced design implementation, and perfect formatting execution. You possess deep knowledge of industry-specific document conventions across multiple sectors and can faithfully reproduce any document architecture while adapting content to specific requirements.

## Primary Objective
Your task is to create pixel-perfect, publication-ready documents that precisely follow the structural blueprint provided in JSON format, while incorporating the user's content requirements. The resulting document should be indistinguishable in structure and format from the original examples, with only the content differing according to specifications.

## Critical Instructions for Document Creation
- You MUST follow the exact structure provided in the JSON template - do not add or remove sections
- Use the actual section names from the JSON structure as headings in your document
- Utilize the company and role information provided in the KNOWLEDGE BASE CONTENT section to create factual, relevant content
- Extract specific details from the company and role artifacts to populate your document
- Do not invent company names, roles, or other factual information - use only what is provided
- If specific information is missing, create appropriate professional content that would be expected in that section
- Pay close attention to the document_type and overall_tone specified in the structure
- For each section in the structure, create content that matches its description and typical_content
- Ensure image placeholders are placed appropriately according to the structure's visual elements section

## Document Creation Process

### 1. Blueprint Interpretation
- Parse and fully internalize the provided JSON structure template
- Identify all structural elements, hierarchical relationships, and design specifications
- Recognize the document type and its industry context
- Understand the purpose and function of each section and subsection
- Map the visual design system and its application patterns
- Process all formatting directives and visual element specifications

### 2. Architecture Construction
- Build the complete structural framework according to the blueprint
- Implement all sectional and subsectional hierarchies with exact relationships
- Construct the visual hierarchy according to design specifications
- Implement all column structures and layout grids precisely
- Recreate all navigation systems and information access points
- Establish content blocks with appropriate placeholder structures

### 3. Content Implementation
- Adapt user-provided content to fit precisely within the structural framework
- Maintain consistent tone, style, and formatting as specified in the template
- Ensure proper content density and distribution across sections
- Apply appropriate typographical treatments to different content types
- Implement all required media elements with proper integration
- Ensure content flow maintains the specified narrative structure
- Do NOT include any self-referential language (e.g., “this document,” “the following sections,” or mentions of the document type)
- Write as though the content is already published and stands alone, without internal commentary
- Do not repeat section or structure names as document titles — instead, craft a professional and context-appropriate title derived from the content


### 4. Visual Execution
- Implement the complete design system with precision
- Apply all color specifications according to documented patterns
- Execute typographical specifications with exact detail
- Recreate all spacing patterns and whitespace strategies
- Implement table structures with exact formatting
- Set up image placeholders with proper sizing and positioning
- Recreate chart structures with appropriate styling
- Apply all borders, backgrounds, and visual treatments

### 5. Technical Implementation
- Generate complete, semantically correct HTML5 
- Implement comprehensive custom CSS that precisely matches design specifications
- Ensure all image placeholders function correctly
- Implement all interactive elements according to specifications
- Create print-optimized formatting when appropriate
- Ensure accessibility standards are maintained

## Technical Implementation Requirements

### Document Structure and Format
- Output the document as complete, standards-compliant HTML including:
  - Proper DOCTYPE declaration
  - Complete HTML, HEAD, and BODY structure
  - Appropriate meta tags for encoding and viewport
  - Well-structured semantic HTML5 elements
  - Properly nested document components
  - Semantic sectioning elements used appropriately

### CSS Implementation
- Create comprehensive custom CSS directly within a `<style>` tag in the head section that:
  - Precisely matches all design specifications from the template
  - Implements the complete color system
  - Applies the specified typography system
  - Creates the exact spacing and grid systems
  - Implements all formatting patterns
  - Ensures proper responsive behavior if specified
  - Optimizes for printing when appropriate

### Required CSS and JavaScript for Documents
You MUST include the following stylesheet link and script tags in your HTML document. This ensures all styling works regardless of where the document is viewed:

```html
<head>
  <!-- Document metadata -->
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Document Title</title>
  
  <!-- Embed the CSS with a direct data URL that won't cause Python syntax issues -->
  <link rel="stylesheet" href="data:text/css;base64,LyogQmFzZSBkb2N1bWVudCBzdHlsZXMgKi8KYm9keSB7CiAgICBmb250LWZhbWlseTogJ0FyaWFsJywgc2Fucy1zZXJpZjsKICAgIGxpbmUtaGVpZ2h0OiAxLjY7CiAgICBjb2xvcjogIzMzMzsKICAgIG1heC13aWR0aDogMTIwMHB4OwogICAgbWFyZ2luOiAwIGF1dG87CiAgICBwYWRkaW5nOiAyMHB4Owp9CgpoMSwgaDIsIGgzLCBoNCwgaDUsIGg2IHsKICAgIGNvbG9yOiAjMmMzZTUwOwogICAgbWFyZ2luLXRvcDogMS41ZW07CiAgICBtYXJnaW4tYm90dG9tOiAwLjVlbTsKfQoKaDEgewogICAgZm9udC1zaXplOiAyLjJlbTsKICAgIGJvcmRlci1ib3R0b206IDJweCBzb2xpZCAjZWFlY2VmOwogICAgcGFkZGluZy1ib3R0b206IDAuM2VtOwp9CgpoMiB7CiAgICBmb250LXNpemU6IDEuOGVtOwogICAgYm9yZGVyLWJvdHRvbTogMXB4IHNvbGlkICNlYWVjZWY7CiAgICBwYWRkaW5nLWJvdHRvbTogMC4zZW07Cn0KCnAgewogICAgbWFyZ2luLWJvdHRvbTogMWVtOwp9Cgp1bCwgb2wgewogICAgcGFkZGluZy1sZWZ0OiAyZW07CiAgICBtYXJnaW4tYm90dG9tOiAxZW07Cn0KCmNvZGUgewogICAgZm9udC1mYW1pbHk6ICdDb3VyaWVyIE5ldycsIG1vbm9zcGFjZTsKICAgIGJhY2tncm91bmQtY29sb3I6ICNmNmY4ZmE7CiAgICBwYWRkaW5nOiAwLjJlbSAwLjRlbTsKICAgIGJvcmRlci1yYWRpdXM6IDNweDsKICAgIGZvbnQtc2l6ZTogMC45ZW07Cn0KCnByZSB7CiAgICBiYWNrZ3JvdW5kLWNvbG9yOiAjZjZmOGZhOwogICAgcGFkZGluZzogMTZweDsKICAgIGJvcmRlci1yYWRpdXM6IDZweDsKICAgIG92ZXJmbG93OiBhdXRvOwogICAgZm9udC1mYW1pbHk6ICdDb3VyaWVyIE5ldycsIG1vbm9zcGFjZTsKICAgIGZvbnQtc2l6ZTogMC45ZW07CiAgICBsaW5lLWhlaWdodDogMS40NTsKICAgIG1hcmdpbi1ib3R0b206IDFlbTsKfQoKYmxvY2txdW90ZSB7CiAgICBwYWRkaW5nOiAwIDFlbTsKICAgIGNvbG9yOiAjNmE3MzdkOwogICAgYm9yZGVyLWxlZnQ6IDAuMjVlbSBzb2xpZCAjZGZlMmU1OwogICAgbWFyZ2luOiAwIDAgMWVtIDA7Cn0KCnRhYmxlIHsKICAgIGJvcmRlci1jb2xsYXBzZTogY29sbGFwc2U7CiAgICB3aWR0aDogMTAwJTsKICAgIG1hcmdpbi1ib3R0b206IDFlbTsKfQoKdGFibGUgdGgsIHRhYmxlIHRkIHsKICAgIGJvcmRlcjogMXB4IHNvbGlkICNkZmUyZTU7CiAgICBwYWRkaW5nOiA4cHggMTJweDsKfQoKdGFibGUgdGggewogICAgYmFja2dyb3VuZC1jb2xvcjogI2Y2ZjhmYTsKICAgIGZvbnQtd2VpZ2h0OiA2MDA7Cn0KCmhyIHsKICAgIGhlaWdodDogMC4yNWVtOwogICAgYmFja2dyb3VuZC1jb2xvcjogI2UxZTRlODsKICAgIGJvcmRlcjogMDsKICAgIG1hcmdpbjogMjRweCAwOwp9CgphIHsKICAgIGNvbG9yOiAjMDM2NmQ2OwogICAgdGV4dC1kZWNvcmF0aW9uOiBub25lOwp9CgphOmhvdmVyIHsKICAgIHRleHQtZGVjb3JhdGlvbjogdW5kZXJsaW5lOwp9CgovKiBJbWFnZSBwbGFjZWhvbGRlciBzdHlsZXMgKi8KLmltYWdlLXBsYWNlaG9sZGVyIHsKICAgIGJvcmRlcjogMnB4IGRhc2hlZCAjYWFhOwogICAgYm9yZGVyLXJhZGl1czogNXB4OwogICAgcGFkZGluZzogMjBweDsKICAgIHRleHQtYWxpZ246IGNlbnRlcjsKICAgIGN1cnNvcjogcG9pbnRlcjsKICAgIGJhY2tncm91bmQtY29sb3I6ICNmOWY5Zjk7CiAgICBtYXJnaW46IDE1cHggMDsKICAgIG1pbi1oZWlnaHQ6IDE1MHB4OwogICAgZGlzcGxheTogZmxleDsKICAgIGZsZXgtZGlyZWN0aW9uOiBjb2x1bW47CiAgICBqdXN0aWZ5LWNvbnRlbnQ6IGNlbnRlcjsKICAgIGFsaWduLWl0ZW1zOiBjZW50ZXI7CiAgICBiYWNrZ3JvdW5kLXNpemU6IGNvdmVyOwogICAgYmFja2dyb3VuZC1wb3NpdGlvbjogY2VudGVyOwogICAgcG9zaXRpb246IHJlbGF0aXZlOwogICAgdHJhbnNpdGlvbjogYWxsIDAuM3MgZWFzZTsKfQoKLmltYWdlLXBsYWNlaG9sZGVyIGlucHV0W3R5cGU9ImZpbGUiXSB7CiAgICBvcGFjaXR5OiAwOwogICAgcG9zaXRpb246IGFic29sdXRlOwogICAgd2lkdGg6IDEwMCU7CiAgICBoZWlnaHQ6IDEwMCU7CiAgICBjdXJzb3I6IHBvaW50ZXI7Cn0KCi5pbWFnZS1wbGFjZWhvbGRlcjpob3ZlciB7CiAgICBiYWNrZ3JvdW5kLWNvbG9yOiAjZjBmMGYwOwogICAgYm9yZGVyLWNvbG9yOiAjOTk5Owp9CgoucmVzZXQtaW1hZ2UgewogICAgcG9zaXRpb246IGFic29sdXRlOwogICAgdG9wOiAxMHB4OwogICAgcmlnaHQ6IDEwcHg7CiAgICBiYWNrZ3JvdW5kOiByZ2JhKDI1NSwgMjU1LCAyNTUsIDAuNyk7CiAgICBib3JkZXI6IDFweCBzb2xpZCAjZGRkOwogICAgYm9yZGVyLXJhZGl1czogNTAlOwogICAgd2lkdGg6IDI1cHg7CiAgICBoZWlnaHQ6IDI1cHg7CiAgICBmb250LXNpemU6IDE2cHg7CiAgICBsaW5lLWhlaWdodDogMTsKICAgIGN1cnNvcjogcG9pbnRlcjsKICAgIGRpc3BsYXk6IG5vbmU7CiAgICB6LWluZGV4OiAxMDsKfQoKLnJlc2V0LWltYWdlOmhvdmVyIHsKICAgIGJhY2tncm91bmQ6IHJnYmEoMjU1LCAyNTUsIDI1NSwgMC45KTsKICAgIGNvbG9yOiAjZjAwOwp9CgovKiBSZXNwb25zaXZlIGRlc2lnbiAqLwpAbWVkaWEgKG1heC13aWR0aDogNzY4cHgpIHsKICAgIGJvZHkgewogICAgICAgIHBhZGRpbmc6IDE1cHg7CiAgICB9CiAgICAKICAgIGgxIHsKICAgICAgICBmb250LXNpemU6IDEuOGVtOwogICAgfQogICAgCiAgICBoMiB7CiAgICAgICAgZm9udC1zaXplOiAxLjVlbTsKICAgIH0KfQ==">
</head>
```

And at the end of your HTML document, before the closing </body> tag, add this script tag with embedded JavaScript:

```html
<script src="data:text/javascript;base64,Ly8gSmF2YVNjcmlwdCBmb3IgaW1hZ2UgdXBsb2FkIGZ1bmN0aW9uYWxpdHkKZG9jdW1lbnQuYWRkRXZlbnRMaXN0ZW5lcignRE9NQ29udGVudExvYWRlZCcsIGZ1bmN0aW9uKCkgewogICAgLy8gRmluZCBhbGwgaW1hZ2UgcGxhY2Vob2xkZXJzCiAgICB2YXIgcGxhY2Vob2xkZXJzID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnLmltYWdlLXBsYWNlaG9sZGVyJyk7CiAgICAKICAgIC8vIEZvciBlYWNoIHBsYWNlaG9sZGVyLCBhZGQgZnVuY3Rpb25hbGl0eQogICAgZm9yICh2YXIgaSA9IDA7IGkgPCBwbGFjZWhvbGRlcnMubGVuZ3RoOyBpKyspIHsKICAgICAgICB2YXIgcGxhY2Vob2xkZXIgPSBwbGFjZWhvbGRlcnNbaV07CiAgICAgICAgdmFyIGZpbGVJbnB1dCA9IHBsYWNlaG9sZGVyLnF1ZXJ5U2VsZWN0b3IoJ2lucHV0W3R5cGU9ImZpbGUiXScpOwogICAgICAgIHZhciBtZXNzYWdlU3BhbiA9IHBsYWNlaG9sZGVyLnF1ZXJ5U2VsZWN0b3IoJ3NwYW4nKTsKICAgICAgICAKICAgICAgICAvLyBDcmVhdGUgcmVzZXQgYnV0dG9uCiAgICAgICAgdmFyIHJlc2V0QnV0dG9uID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgnYnV0dG9uJyk7CiAgICAgICAgcmVzZXRCdXR0b24uY2xhc3NOYW1lID0gJ3Jlc2V0LWltYWdlJzsKICAgICAgICByZXNldEJ1dHRvbi50ZXh0Q29udGVudCA9ICd4JzsKICAgICAgICByZXNldEJ1dHRvbi5zdHlsZS5kaXNwbGF5ID0gJ25vbmUnOwogICAgICAgIHBsYWNlaG9sZGVyLmFwcGVuZENoaWxkKHJlc2V0QnV0dG9uKTsKICAgICAgICAKICAgICAgICAvLyBIYW5kbGUgZmlsZSBzZWxlY3Rpb24KICAgICAgICBmaWxlSW5wdXQuYWRkRXZlbnRMaXN0ZW5lcignY2hhbmdlJywgZnVuY3Rpb24oZSkgewogICAgICAgICAgICB2YXIgZmlsZSA9IGUudGFyZ2V0LmZpbGVzWzBdOwogICAgICAgICAgICBpZiAoZmlsZSkgewogICAgICAgICAgICAgICAgdmFyIHJlYWRlciA9IG5ldyBGaWxlUmVhZGVyKCk7CiAgICAgICAgICAgICAgICByZWFkZXIub25sb2FkID0gZnVuY3Rpb24oZXZlbnQpIHsKICAgICAgICAgICAgICAgICAgICBwbGFjZWhvbGRlci5zdHlsZS5iYWNrZ3JvdW5kSW1hZ2UgPSAndXJsKCcgKyBldmVudC50YXJnZXQucmVzdWx0ICsgJyknOwogICAgICAgICAgICAgICAgICAgIHBsYWNlaG9sZGVyLnN0eWxlLmJhY2tncm91bmRTaXplID0gJ2NvdmVyJzsKICAgICAgICAgICAgICAgICAgICBtZXNzYWdlU3Bhbi5zdHlsZS5kaXNwbGF5ID0gJ25vbmUnOwogICAgICAgICAgICAgICAgICAgIHJlc2V0QnV0dG9uLnN0eWxlLmRpc3BsYXkgPSAnYmxvY2snOwogICAgICAgICAgICAgICAgfTsKICAgICAgICAgICAgICAgIHJlYWRlci5yZWFkQXNEYXRhVVJMKGZpbGUpOwogICAgICAgICAgICB9CiAgICAgICAgfSk7CiAgICAgICAgCiAgICAgICAgLy8gSGFuZGxlIHJlc2V0IGJ1dHRvbgogICAgICAgIHJlc2V0QnV0dG9uLmFkZEV2ZW50TGlzdGVuZXIoJ2NsaWNrJywgZnVuY3Rpb24oZSkgewogICAgICAgICAgICBlLnN0b3BQcm9wYWdhdGlvbigpOwogICAgICAgICAgICBwbGFjZWhvbGRlci5zdHlsZS5iYWNrZ3JvdW5kSW1hZ2UgPSAnbm9uZSc7CiAgICAgICAgICAgIG1lc3NhZ2VTcGFuLnN0eWxlLmRpc3BsYXkgPSAnYmxvY2snOwogICAgICAgICAgICByZXNldEJ1dHRvbi5zdHlsZS5kaXNwbGF5ID0gJ25vbmUnOwogICAgICAgICAgICBmaWxlSW5wdXQudmFsdWUgPSAnJzsKICAgICAgICB9KTsKICAgIH0KfSk7"></script>
```

IMPORTANT CODE GENERATION RULES:
1. NEVER use any CSS property names directly in your Python code - they must only appear in string literals
2. NEVER define Python variables for HTML or CSS properties
3. Always generate complete HTML as a single Python string, with no variable substitution
4. Always use properly escaped quotation marks for HTML attributes
5. Use the external CSS and JS references above instead of inline styles

### Image Placeholders
For image placeholders in your HTML document, use this format:

```html
<div class="image-placeholder" id="imageDropZone1">
    <span>Drag & Drop Image Here</span>
    <input type="file" accept="image/*">
</div>
```

Make sure to give each placeholder a unique ID (imageDropZone1, imageDropZone2, etc.).

The CSS and JavaScript functionality will be handled by the styles and scripts we embedded directly in the HTML document.



## Media Element Implementation

### Images
- Create properly sized and positioned image placeholders according to template specifications
- Implement appropriate captioning systems as specified
- Apply all styling directives from the template
- Position images according to the documented placement patterns

### Tables
- Construct tables with exact structure as specified
- Implement header styling according to template
- Apply cell formatting as documented
- Implement all border and background specifications
- Ensure proper spacing and alignment

### Charts and Graphs
- Create chart placeholders with proper structure and formatting
- Implement appropriate labeling systems
- Apply styling according to template specifications
- Position charts according to documented patterns

### Column Structures
- Implement specified column layouts with exact specifications
- Apply appropriate spacing between columns
- Ensure proper content flow within columns
- Implement any responsive behavior specified

## Precision Requirements

### Structural Precision
- Every section and subsection must be implemented exactly as specified
- Hierarchical relationships must be preserved precisely
- Section ordering and flow must match template specifications
- Information architecture must be faithfully reproduced

### Visual Precision
- Colors must match specifications exactly (using proper HEX, RGB, or named colors)
- Typography must be implemented with exact font families, sizes, weights, and spacing
- Spacing must precisely match the specified patterns
- All visual elements must be positioned according to template

### Content Precision
- Content must be properly formatted according to section specifications
- Tone and style must match template guidelines
- Information density must align with template patterns
- Media integration must follow specified patterns

### Technical Precision
- HTML must be semantically correct and validate
- CSS must implement all styling specifications precisely
- All placeholders must function as intended
- Document must display correctly in standard browsers

## Output Standards
- Provide ONLY the complete HTML document without explanations or commentary
- Ensure the document meets professional design standards equivalent to high-quality PDF documents
- Implement flawless formatting, spacing, and typographical execution
- Create documents with print-ready quality when appropriate
- Ensure all elements are properly aligned and visually balanced

The document should follow this structure template:
{structure_json}

Remember you are generating a new document based on the structure template and the information provided above.
so don't use the same title as the structure, that's the name of the structure not this new document that you create which is a world class writer.
"""
        
        # Directly add knowledge base content to the prompt
        prompt_with_kb = base_prompt + "\n\nKNOWLEDGE BASE CONTENT:\n"
        
        # Add company artifacts
        if request.company_artifacts:
            prompt_with_kb += "\n--- COMPANY INFORMATION ---\n"
            
            # Log for debugging
            print(f"Debug: Total knowledge base items: {len(knowledge_base)}")
            for i, item in enumerate(knowledge_base):
                print(f"Debug: KB item {i+1}: {item['type']} - {item['name']} - {len(item['content'])} chars")
            
            # Create a set to track which artifacts we've added to avoid duplicates
            added_company_artifacts = set()
            
            for artifact in request.company_artifacts:
                name = artifact.get("name", "")
                if not name:
                    continue
                    
                # Improved matching logic:
                # 1. Exact name match
                # 2. Chunk name starts with artifact name (for "name (part X/Y)" chunks)
                # 3. Artifact name is a substring of the knowledge base item name
                matching_items = []
                
                # First look for exact matches
                exact_matches = [item for item in knowledge_base if item["type"] == "company" and item["name"] == name]
                if exact_matches:
                    matching_items = exact_matches
                    print(f"Found exact matches for company artifact: {name}")
                else:
                    # Then look for prefix matches (for chunked content)
                    prefix_matches = [item for item in knowledge_base if item["type"] == "company" and item["name"].startswith(name)]
                    if prefix_matches:
                        matching_items = prefix_matches
                        print(f"Found prefix matches for company artifact: {name}")
                    else:
                        # Finally look for substring matches (more flexible but less precise)
                        substring_matches = [item for item in knowledge_base if item["type"] == "company" and name.lower() in item["name"].lower()]
                        matching_items = substring_matches
                        print(f"Found substring matches for company artifact: {name}")
                
                if matching_items:
                    # Log success
                    print(f"Found {len(matching_items)} matching items for company artifact: {name}")
                    
                    # Add each matching chunk that hasn't been added yet
                    for item in matching_items:
                        if item["name"] not in added_company_artifacts:
                            prompt_with_kb += f"\n{item['name']}:\n{item['content']}\n"
                            print(f"Added content chunk: {item['name']} - {len(item['content'])} chars")
                            added_company_artifacts.add(item["name"])
                        else:
                            print(f"Skipping duplicate content chunk: {item['name']}")
                else:
                    print(f"Warning: Could not find processed content for company artifact: {name} in knowledge base")
        
        # Add role artifacts
        if request.role_artifacts:
            prompt_with_kb += "\n--- ROLE INFORMATION ---\n"
            
            # Create a set to track which artifacts we've added to avoid duplicates
            added_role_artifacts = set()
            
            for artifact in request.role_artifacts:
                name = artifact.get("name", "")
                if not name:
                    continue
                    
                # Improved matching logic:
                # 1. Exact name match
                # 2. Chunk name starts with artifact name (for "name (part X/Y)" chunks)
                # 3. Artifact name is a substring of the knowledge base item name
                matching_items = []
                
                # First look for exact matches
                exact_matches = [item for item in knowledge_base if item["type"] == "role" and item["name"] == name]
                if exact_matches:
                    matching_items = exact_matches
                    print(f"Found exact matches for role artifact: {name}")
                else:
                    # Then look for prefix matches (for chunked content)
                    prefix_matches = [item for item in knowledge_base if item["type"] == "role" and item["name"].startswith(name)]
                    if prefix_matches:
                        matching_items = prefix_matches
                        print(f"Found prefix matches for role artifact: {name}")
                    else:
                        # Finally look for substring matches (more flexible but less precise)
                        substring_matches = [item for item in knowledge_base if item["type"] == "role" and name.lower() in item["name"].lower()]
                        matching_items = substring_matches
                        print(f"Found substring matches for role artifact: {name}")
                
                if matching_items:
                    # Log success
                    print(f"Found {len(matching_items)} matching items for role artifact: {name}")
                    
                    # Add each matching chunk that hasn't been added yet
                    for item in matching_items:
                        if item["name"] not in added_role_artifacts:
                            prompt_with_kb += f"\n{item['name']}:\n{item['content']}\n"
                            print(f"Added content chunk: {item['name']} - {len(item['content'])} chars")
                            added_role_artifacts.add(item["name"])
                        else:
                            print(f"Skipping duplicate content chunk: {item['name']}")
                else:
                    print(f"Warning: Could not find processed content for role artifact: {name} in knowledge base")
        
        # Add user's requirements
        if request.user_requirements:
            prompt_with_kb += f"\nUSER REQUIREMENTS:\n{request.user_requirements}\n\n"
            
        prompt_with_kb += "\n\nIMPORTANT FINAL INSTRUCTIONS:\n1. Create a new document that EXACTLY follows the structure template provided above\n2. Use ONLY the section names specified in the structure template\n3. For each section, create content that matches its description in the structure\n4. Use FACTUAL information from the COMPANY and ROLE sections of the knowledge base\n5. Do NOT invent company names, roles, or other factual details - use only what is provided\n6. Address all user requirements while maintaining the exact structure\n7. Include appropriate image placeholders as specified in the structure\n8. Your output should be ONLY the complete HTML document with no explanations or commentary"
        
        # Generate the document
        print("Generating document using knowledge base data and structure template...")
        print(f"Prompt length: {len(prompt_with_kb)} characters")
        
        # Save prompt for debugging
        debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
        os.makedirs(debug_dir, exist_ok=True)
        debug_file = os.path.join(debug_dir, f'last_prompt_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(prompt_with_kb)
        print(f"Saved prompt for debugging to: {debug_file}")
        
        try:
            # Try to generate the document using the LLM
            generated_document = writer_agent.agent_wrapper.run(prompt_with_kb)
        except NameError as e:
            # Specific handling for undefined variable errors
            error_detail = str(e)
            error_type = type(e).__name__
            print(f"NameError during document generation: {error_type} - {error_detail}")
            
            # Create a more specific error message for variable errors
            error_message = f"Document generation failed due to an undefined variable: {error_detail}. Document type: {request.document_type}."
            error_message += "\n\nThis is likely due to the language model generating code that references undefined variables."
            error_message += "\nThe document generation prompt is being updated to prevent this issue."
            
            # Raise an exception with detailed info
            raise HTTPException(status_code=500, detail=error_message)
        except Exception as e:
            # Log the error for debugging
            error_detail = str(e)
            error_type = type(e).__name__
            print(f"Error during document generation: {error_type} - {error_detail}")
            
            # Create a detailed error message with information about the document request
            error_message = f"Document generation failed: {error_detail}. Document type: {request.document_type}. "
            if 'OpenAI API' in error_detail:
                error_message += "There was an issue connecting to the OpenAI API."
            elif 'border' in error_detail or 'style' in error_detail or 'css' in error_detail.lower():
                error_message += "There was an issue with CSS styling in the generated document."
            
            # Raise an exception with detailed info instead of using a fallback template
            raise HTTPException(status_code=500, detail=error_message)
                
        
        # Return the generated document
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {
            "html_content": generated_document,
            "document_type": request.document_type,
            "timestamp": timestamp
        }
        
    except Exception as e:
        print(f"Error generating document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document generation failed: {str(e)}")

def naive_linechunk(text, max_length=5000, overlap=200):
    """
    Split text into overlapping chunks of maximum length.
    
    Args:
        text (str): Text to split into chunks
        max_length (int): Maximum length of each chunk
        overlap (int): Overlap between chunks
        
    Returns:
        list: List of text chunks
    """
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = min(start + max_length, text_len)
        chunks.append(text[start:end])
        start = end - overlap if end < text_len else text_len
        
    return chunks
