"""
PDF handling fix for the Search Wizard API

This contains the code you should substitute into api.py to fix PDF artifact handling.
"""

# COMPANY ARTIFACTS SECTION - Replace lines 204-243 with this:
"""
            # Check if this appears to be raw PDF content or if we have a file URL to use directly
            file_url = artifact.get("file_url") or artifact.get("fileUrl")
            if ('trailer' in description or 'xref' in description or 'startxref' in description or '\\ufffd' in description) and file_url:
                print(f"Detected raw/corrupted PDF content for {name}, downloading directly from URL: {file_url}")
                
                # Download the file directly from the URL
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
                            print("Using Supabase service role key for authentication")
                    
                    # Make the request directly to the URL - don't try to modify signed URLs
                    response = requests.get(file_url, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        # Create a temporary file with the downloaded content
                        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                            temp_file.write(response.content)
                            temp_file_path = temp_file.name
                            
                        try:
                            # Use PyPDF2 to extract text directly from the downloaded file
                            import PyPDF2
                            print(f"Processing downloaded PDF with PyPDF2 {PyPDF2.__version__}")
                            
                            with open(temp_file_path, 'rb') as f:
                                pdf_reader = PyPDF2.PdfReader(f)
                                extracted_text = ""
                                total_pages = len(pdf_reader.pages)
                                print(f"PDF has {total_pages} pages")
                                
                                for page_num in range(total_pages):
                                    page = pdf_reader.pages[page_num]
                                    page_text = page.extract_text()
                                    if page_text:
                                        extracted_text += page_text + "\\n\\n"
                                        
                            # If extraction was successful, use it instead of the corrupted content
                            if extracted_text and len(extracted_text.strip()) > 10:
                                description = extracted_text
                                print(f"Successfully extracted {len(description)} chars from downloaded PDF")
                            else:
                                print("Warning: PDF text extraction yielded empty content")
                        except Exception as pdf_error:
                            print(f"Error extracting text from downloaded PDF: {str(pdf_error)}")
                        finally:
                            # Clean up temp file
                            try:
                                os.unlink(temp_file_path)
                            except Exception as e:
                                print(f"Error cleaning up temp file: {str(e)}")
                    else:
                        print(f"Error downloading PDF: HTTP {response.status_code}")
                except Exception as e:
                    print(f"Error processing PDF URL: {str(e)}")
"""

# ROLE ARTIFACTS SECTION - Replace lines 336-375 with this:
"""
            # Check if this appears to be raw PDF content or if we have a file URL to use directly
            file_url = artifact.get("file_url") or artifact.get("fileUrl")
            if ('trailer' in description or 'xref' in description or 'startxref' in description or '\\ufffd' in description) and file_url:
                print(f"Detected raw/corrupted PDF content for {name}, downloading directly from URL: {file_url}")
                
                # Download the file directly from the URL
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
                            print("Using Supabase service role key for authentication")
                    
                    # Make the request directly to the URL - don't try to modify signed URLs
                    response = requests.get(file_url, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        # Create a temporary file with the downloaded content
                        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                            temp_file.write(response.content)
                            temp_file_path = temp_file.name
                            
                        try:
                            # Use PyPDF2 to extract text directly from the downloaded file
                            import PyPDF2
                            print(f"Processing downloaded PDF with PyPDF2 {PyPDF2.__version__}")
                            
                            with open(temp_file_path, 'rb') as f:
                                pdf_reader = PyPDF2.PdfReader(f)
                                extracted_text = ""
                                total_pages = len(pdf_reader.pages)
                                print(f"PDF has {total_pages} pages")
                                
                                for page_num in range(total_pages):
                                    page = pdf_reader.pages[page_num]
                                    page_text = page.extract_text()
                                    if page_text:
                                        extracted_text += page_text + "\\n\\n"
                                        
                            # If extraction was successful, use it instead of the corrupted content
                            if extracted_text and len(extracted_text.strip()) > 10:
                                description = extracted_text
                                print(f"Successfully extracted {len(description)} chars from downloaded PDF")
                            else:
                                print("Warning: PDF text extraction yielded empty content")
                        except Exception as pdf_error:
                            print(f"Error extracting text from downloaded PDF: {str(pdf_error)}")
                        finally:
                            # Clean up temp file
                            try:
                                os.unlink(temp_file_path)
                            except Exception as e:
                                print(f"Error cleaning up temp file: {str(e)}")
                    else:
                        print(f"Error downloading PDF: HTTP {response.status_code}")
                except Exception as e:
                    print(f"Error processing PDF URL: {str(e)}")
"""
