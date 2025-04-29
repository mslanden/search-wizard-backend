"""Helper module for knowledge base support in document generation."""

import os
from typing import Dict, List, Optional, Any

def load_knowledge_base_content(knowledge_base_dir: str) -> Dict[str, str]:
    """Load content from all files in the knowledge_base directory.
    
    Args:
        knowledge_base_dir (str): Path to the knowledge base directory
        
    Returns:
        Dict[str, str]: Dictionary mapping filenames to their content.
    """
    knowledge_base = {}
    
    try:
        if os.path.exists(knowledge_base_dir) and os.path.isdir(knowledge_base_dir):
            # Define supported file extensions
            supported_extensions = ['.txt', '.md', '.pdf', '.docx', '.doc']
            
            # Walk through all subdirectories
            for root, _, files in os.walk(knowledge_base_dir):
                for file in files:
                    if os.path.splitext(file)[1].lower() in supported_extensions:
                        # Get path relative to knowledge_base_dir
                        rel_path = os.path.relpath(os.path.join(root, file), knowledge_base_dir)
                        full_path = os.path.join(root, file)
                        
                        # Get file extension
                        file_extension = os.path.splitext(file)[1].lower()
                        content = ""
                        
                        # Process file based on extension
                        try:
                            if file_extension == '.pdf':
                                import PyPDF2
                                with open(full_path, 'rb') as f:
                                    reader = PyPDF2.PdfReader(f)
                                    text = ""
                                    for page in reader.pages:
                                        page_text = page.extract_text()
                                        if page_text:
                                            text += page_text + "\n\n"
                                    content = text.strip()
                            elif file_extension in ['.docx', '.doc']:
                                import docx
                                doc = docx.Document(full_path)
                                content = '\n\n'.join([paragraph.text for paragraph in doc.paragraphs if paragraph.text])
                            else:
                                with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                                    content = f.read()
                                    
                            knowledge_base[rel_path] = content
                        except Exception as e:
                            print(f"Error loading knowledge base file {rel_path}: {str(e)}")
    except Exception as e:
        print(f"Error loading knowledge base: {str(e)}")
        
    return knowledge_base

def enhance_prompt_with_kb(prompt: str, knowledge_base_dir: str) -> str:
    """Add knowledge base content to the prompt.
    
    Args:
        prompt (str): The existing prompt
        knowledge_base_dir (str): Path to the knowledge base directory
        
    Returns:
        str: Prompt with knowledge base content incorporated
    """
    knowledge_base = load_knowledge_base_content(knowledge_base_dir)
    
    if knowledge_base:
        # Add section header
        prompt += "\nKNOWLEDGE BASE CONTENT:\n"
        
        # Add each knowledge base file with truncation if needed
        for filename, content in knowledge_base.items():
            # Truncate long content (5000 chars max per file)
            if len(content) > 5000:
                displayed_content = content[:5000] + "\n[Content truncated due to length...]\n"
            else:
                displayed_content = content
                
            prompt += f"\n--- {filename} ---\n{displayed_content}\n"
        
        # Add usage instructions
        prompt += "\n\nUse the knowledge base content above as the source of factual information for creating the document.\n\n"
    
    return prompt