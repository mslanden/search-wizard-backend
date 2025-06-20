#!/usr/bin/env python3
"""
Document Generator Demo Script

This script demonstrates how to use the StructureAgent and WriterAgent together
to generate high-quality documents. The StructureAgent analyzes example documents
to extract a structured template, which is then provided to the WriterAgent to 
create new documents based on user requirements.
"""

import os
import json
import sys
import datetime
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables for API keys
load_dotenv()

from agents.structure_agent import StructureAgent
from agents.writer_agent import WriterAgent
from agents.kb_support import enhance_prompt_with_kb


def setup_agents():
    """Initialize both agents using available API keys."""
    # Get API key from environment variables - try in order of preference (Anthropic first)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    framework = "anthropic"
    
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        framework = "openai"
        
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
        framework = "gemini"
        
    if not api_key:
        print("Error: No API key found in environment variables.")
        print("Please set one of the following in your .env file:")
        print("- OPENAI_API_KEY")
        print("- ANTHROPIC_API_KEY")
        print("- GEMINI_API_KEY")
        return None, None
    
    # Initialize both agents with the same framework and API key
    structure_agent = StructureAgent(framework=framework, api_key=api_key)
    writer_agent = WriterAgent(framework=framework, api_key=api_key)
    
    return structure_agent, writer_agent


def save_structure_to_file(structure, filename="document_structure.json"):
    """Save the generated structure to a file for reuse."""
    try:
        with open(filename, 'w') as f:
            json.dump(structure, f, indent=2)
        print(f"Structure saved to {filename}")
    except Exception as e:
        print(f"Error saving structure to file: {str(e)}")


def load_structure_from_file(filename="document_structure.json"):
    """Load a previously saved structure from a file."""
    try:
        with open(filename, 'r') as f:
            structure = json.load(f)
        print(f"Structure loaded from {filename}")
        return structure
    except Exception as e:
        print(f"Error loading structure from file: {str(e)}")
        return None


def main():
    """Main function demonstrating the document generation workflow."""
    print("=" * 80)
    print("DOCUMENT GENERATOR DEMO")
    print("=" * 80)
    
    # Setup agents
    structure_agent, writer_agent = setup_agents()
    if not structure_agent or not writer_agent:
        return
        
    # Check for examples in Example-docs directory
    example_docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Example-docs')
    if os.path.exists(example_docs_dir) and os.path.isdir(example_docs_dir):
        print(f"\nFound Example-docs directory. Looking for examples there.")
        # Update document directories
        structure_agent.documents_dir = example_docs_dir
        writer_agent.documents_dir = example_docs_dir
    
    # List available example documents
    print("\nAvailable example documents:")
    examples = writer_agent.list_available_examples()
    for example in examples:
        print(f"- {example}")
    
    if not examples:
        print("\nNo example documents found. Please add some to the documents directory.")
        return
    
    # Let user select which examples to use for analysis
    print("\nSelect which examples to use for structure analysis (comma-separated numbers):")
    for i, example in enumerate(examples):
        print(f"{i+1}. {example}")
    
    try:
        selection = input("Your selection (default: 1): ").strip()
        if not selection:
            selection = "1"
        
        # Properly parse selection string - handle both comma and space separated values
        selection = selection.replace(' ', ',')
        indices = []
        
        # Process each part of the selection
        for part in selection.split(','):
            part = part.strip()
            if not part:
                continue
            try:
                idx = int(part) - 1
                if 0 <= idx < len(examples):
                    indices.append(idx)
                else:
                    print(f"Warning: Selection {part} is out of range (1-{len(examples)})")
            except ValueError:
                print(f"Warning: Ignoring invalid selection '{part}'")
        
        selected_examples = [examples[idx] for idx in indices if 0 <= idx < len(examples)]
        
        if not selected_examples:
            selected_examples = [examples[0]]
            print(f"Invalid selection. Using default: {examples[0]}")
        else:
            print(f"\nSelected examples: {', '.join(selected_examples)}")
    except Exception:
        selected_examples = [examples[0]]
        print(f"Invalid selection. Using default: {examples[0]}")
    
    # STEP 1: Analyze structure
    print("\nSTEP 1: Analyzing document structure...")
    
    # Ask user if they want to use all selected examples or just the first one
    if len(selected_examples) > 1:
        use_all = input(f"\nYou selected {len(selected_examples)} documents. Using multiple documents may exceed token limits.\nDo you want to use all selected documents? (y/n, default: n): ").strip().lower() == 'y'
        if not use_all:
            print(f"Using only the first selected example to prevent token limit issues.")
            original_selection = selected_examples.copy()
            selected_examples = selected_examples[:1]
            print(f"Analyzing: {selected_examples[0]}")
        else:
            print(f"Attempting to analyze all {len(selected_examples)} selected documents together.\nThis may fail if total content exceeds model token limits.")
    else:
        print(f"Analyzing: {selected_examples[0]}")

    
    # Try to analyze structure with a retry mechanism
    max_attempts = 2
    structure = None
    
    for attempt in range(max_attempts):
        try:
            structure = structure_agent.analyze_structure(selected_examples)
            
            # Check if we got a valid structure or a 'No response' error
            if not structure or structure.get("raw_structure") == "No response":
                print(f"Warning: Received incomplete response from the model (attempt {attempt+1}).")
                if attempt < max_attempts - 1:
                    print("Retrying structure analysis...")
                    # Small delay before retry
                    import time
                    time.sleep(2)
                else:
                    # On final attempt failure, create a fallback structure
                    print("Using fallback document structure...")
                    # Create a basic document structure based on the filename
                    filename = selected_examples[0].split('/')[-1].lower()
                    doc_type = "Generic Document"
                    
                    # Try to infer document type from filename/path
                    if "role" in filename or "job" in filename:
                        doc_type = "Job Description"
                    elif "report" in filename:
                        doc_type = "Analytical Report"
                    elif "briefing" in filename:
                        doc_type = "Briefing Document"
                    
                    structure = {
                        "document_type": doc_type,
                        "sections": [
                            {"name": "Title", "description": "Document title", "typical_content": "Main heading"},
                            {"name": "Summary", "description": "Executive summary", "typical_content": "Brief overview"},
                            {"name": "Main Content", "description": "Core information", "typical_content": "Details and analysis"},
                            {"name": "Conclusion", "description": "Closing remarks", "typical_content": "Final thoughts and next steps"}
                        ],
                        "overall_tone": "Professional",
                        "formatting_notes": "Clean, organized layout"
                    }
            else:
                # If we got a valid structure, break the retry loop
                break
        except Exception as e:
            print(f"Error during structure analysis (attempt {attempt+1}/{max_attempts}): {str(e)}")
            if attempt == max_attempts - 1:
                # Use a simple fallback structure on final error
                structure = {
                    "document_type": "Generic Document",
                    "sections": [
                        {"name": "Introduction", "description": "Opening section", "typical_content": "Context and background"},
                        {"name": "Body", "description": "Main content", "typical_content": "Primary information"},
                        {"name": "Conclusion", "description": "Closing section", "typical_content": "Summary and recommendations"}
                    ],
                    "overall_tone": "Professional",
                    "formatting_notes": "Standard formatting"
                }
    
    print("\nEXTRACTED DOCUMENT STRUCTURE:")
    print("-" * 50)
    print(json.dumps(structure, indent=2))
    print("-" * 50)
    
    # Option to save structure for reuse
    save_option = input("\nSave this structure for future use? (y/n, default: y): ").strip().lower()
    if save_option != "n":
        save_structure_to_file(structure)
    
    # STEP 2: Get user requirements
    print("\nSTEP 2: Enter your document requirements:")
    print("(Press Enter twice when finished)")
    
    lines = []
    while True:
        line = input()
        if not line and lines and not lines[-1]:
            # Two consecutive empty lines
            break
        lines.append(line)
    
    user_input = "\n".join(lines).strip()
    if not user_input:
        print("\nError: No user requirements provided. Please specify what kind of document you want to create.")
        return
    
    # STEP 3: Generate document using structure and knowledge base
    print("\nSTEP 3: Generating document with structured approach and knowledge base...")
    
    # Start with base prompt
    base_prompt = writer_agent.system_prompt + "\n\n"
    
    # Add document structure
    base_prompt += "DOCUMENT STRUCTURE TEMPLATE:\n"
    base_prompt += json.dumps(structure, indent=2) + "\n\n"
    base_prompt += """
    - Follow the document structure template carefully when creating the new document.
    - The structure template is a JSON object that defines the sections, subsections, design, and any additional elements of the document.
    - Output the document in HTML format with a full HTML structure, including DOCTYPE, html, head, and body tags.
    - Create your own custom CSS directly within a <style> tag in the head section. The CSS should be tailored to the specific document you're generating.
    - IMPORTANT: Your CSS must include styles for the image placeholders. At minimum, include these styles for image placeholders to work properly:
        .image-placeholder {
            border: 2px dashed #aaa;
            border-radius: 5px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            background-color: #f9f9f9;
            margin: 15px 0;
            min-height: 150px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            background-size: cover;
            background-position: center;
            position: relative;
            transition: all 0.3s ease;
        }
        .image-placeholder input[type="file"] {
            opacity: 0;
            position: absolute;
            width: 100%;
            height: 100%;
            cursor: pointer;
        }
    - Also include the following script reference in the head section for image upload functionality:
        <script src="../static/image-upload.js"></script>
    
    - The document should be professional and well formatted.
    - Only write the full HTML document.
    - If you need to add images, tables, charts, or any other elements, add them to the HTML document.
    
    - For images, use the following placeholder structure:
    <div class="image-placeholder" id="imageDropZone[UNIQUE_NUMBER]">
        <span>Drag & Drop Image Here</span>
        <input type="file" accept="image/*">
    </div>
    
    - Make sure each image placeholder has a unique ID (imageDropZone1, imageDropZone2, etc.)
    - These placeholders allow users to drag & drop or select images that will be displayed in the document.
    - The included JavaScript will handle the image upload and display functionality.
    - You can adjust the design or styles of any image places holders, circular images, behind text images, etc.
    
    - Feel free to style with inline CSS for any component-specific styling (but general styling is in the CSS file).
    - The document should be designed as porfessional pdf documents. 
    - All created documents should be held to the highest standards of professionalism and quality.
    - Your response should be ONLY the document HTML - no explanations or other text.
    
    \n\n
    """
    
    # Add knowledge base content
    knowledge_base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'knowledge_base')
    prompt_with_kb = enhance_prompt_with_kb(base_prompt, knowledge_base_dir)
    
    # Remove example documents to prevent context length issues
    # The structure agent has already extracted the necessary structure
    # so we don't need to include the full example documents again
    
    # Add user's requirements
    prompt_with_kb += "USER REQUIREMENTS:\n" + user_input + "\n\n"
    prompt_with_kb += "Please create a new document based on the structure template, user requirements, and Knowledge Base. Focus on using factual information from the Knowledge Base while following the document structure template and addressing user requirements."
    
    # Save prompt for debugging if needed
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'last_prompt.txt'), 'w', encoding='utf-8') as f:
        f.write(prompt_with_kb)
    
    # Generate the document
    print("\nGenerating document using knowledge base data and structure template...")
    generated_document = writer_agent.agent_wrapper.run(prompt_with_kb)
    
    # Save the HTML document to file
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate a unique filename based on timestamp if none provided
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"document_{timestamp}.html"
    
    # Ask user for filename
    custom_filename = input(f"\nEnter filename to save document (default: {output_filename}): ").strip()
    if custom_filename:
        if not custom_filename.endswith('.html'):
            custom_filename += '.html'
        output_filename = custom_filename
    
    output_path = os.path.join(output_dir, output_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(generated_document)
    
    print(f"\nHTML document saved to: {output_path}")
    
    print("\nGENERATED DOCUMENT:")
    print("=" * 80)
    print(generated_document)
    print("=" * 80)
    
    # For comparison: Generate document with traditional approach
    compare_option = input("\nGenerate a comparison document using traditional approach? (y/n, default: n): ").strip().lower()
    if compare_option == "y":
        print("\nGenerating comparison document with traditional approach...")
        traditional_document = writer_agent.create_document(user_input, selected_examples)
        
        print("\nTRADITIONAL APPROACH DOCUMENT:")
        print("=" * 80)
        print(traditional_document)
        print("=" * 80)
    
    print("\nDemo completed!")


if __name__ == "__main__":
    main()
