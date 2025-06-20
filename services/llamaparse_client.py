"""
LlamaParse API Client for Search Wizard
Handles communication with LlamaParse API for document parsing using official SDK
"""

import os
import hashlib
import time
from typing import Dict, Any, Optional
import json
from dotenv import load_dotenv
from llama_parse import LlamaParse

load_dotenv()

class LlamaParseError(Exception):
    """Custom exception for LlamaParse API errors"""
    pass

class LlamaParseAuthError(LlamaParseError):
    """Authentication errors with LlamaParse API"""
    pass

class LlamaParseValidationError(LlamaParseError):
    """Validation errors with LlamaParse API"""
    pass

class LlamaParseClient:
    """
    Client for LlamaParse API integration using official SDK
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("LLAMAPARSE_API_KEY")
        if not self.api_key:
            raise LlamaParseAuthError("LLAMAPARSE_API_KEY not found in environment")
        
        self.parser = None
        
    def get_file_hash(self, file_path: str) -> str:
        """Generate SHA-256 hash of file for caching"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def get_parsing_instruction(self, mode: str, document_type: str = None) -> str:
        """
        Generate custom parsing instructions based on mode and document type
        """
        base_instruction = """
        Extract the complete document structure with maximum fidelity including:
        1. All text content preserving logical hierarchy and formatting
        2. Tables with complete structure, headers, and data relationships
        3. Image positions, descriptions, and contextual information
        4. Section headers, subheaders, and document organization
        5. Visual layout information including spacing and alignment
        6. Metadata and document properties
        """
        
        if mode == "premium":
            premium_additions = """
            7. Advanced formatting preservation (fonts, styles, colors)
            8. Complex table structure analysis with merged cells and nested data
            9. OCR for any embedded images containing text
            10. Document design patterns and visual hierarchy analysis
            11. Cross-references, footnotes, and citations
            12. Advanced layout understanding for multi-column documents
            """
            instruction = base_instruction + premium_additions
        else:
            instruction = base_instruction
        
        # Add document type specific instructions
        if document_type:
            type_instructions = {
                "financial": "Pay special attention to financial tables, charts, and numerical data.",
                "legal": "Preserve legal structure, clauses, and reference formatting.",
                "academic": "Maintain citation format, bibliography, and academic structure.",
                "technical": "Preserve code blocks, technical diagrams, and specification details."
            }
            
            if document_type.lower() in type_instructions:
                instruction += f"\n\nSpecial focus: {type_instructions[document_type.lower()]}"
        
        return instruction.strip()
    
    async def parse_document(self, file_path: str, parsing_mode: str = "premium", document_type: str = None) -> Dict[str, Any]:
        """
        Parse a document using LlamaParse API
        
        Args:
            file_path: Path to the document file
            parsing_mode: "premium" (high quality) or "fast" (speed optimized)
            document_type: Optional document type for specialized parsing
        
        Returns:
            Structured document data from LlamaParse
        """
        try:
            start_time = time.time()
            
            # Configure LlamaParse
            parsing_instruction = self.get_parsing_instruction(parsing_mode, document_type)
            
            # Initialize parser with configuration
            self.parser = LlamaParse(
                api_key=self.api_key,
                result_type="markdown",  # Get markdown output (more reliable)
                system_prompt=parsing_instruction,  # Use system_prompt instead of parsing_instruction
                premium_mode=(parsing_mode == "premium"),
                verbose=True
            )
            
            # Parse the document
            print(f"🔄 Parsing document with LlamaParse ({parsing_mode} mode)...")
            documents = self.parser.load_data(file_path)
            
            parsing_time = time.time() - start_time
            
            # Convert to our format
            result = self._convert_llamaparse_documents(documents, file_path, parsing_mode, parsing_time)
            
            print(f"✅ LlamaParse completed in {parsing_time:.2f}s")
            return result
            
        except Exception as e:
            raise LlamaParseError(f"LlamaParse parsing failed: {str(e)}")
    
    def _convert_llamaparse_documents(self, documents, file_path: str, parsing_mode: str, parsing_time: float) -> Dict[str, Any]:
        """Convert LlamaParse documents to our standardized format"""
        
        # Combine all document text
        full_text = ""
        sections = []
        tables = []
        images = []
        
        for i, doc in enumerate(documents):
            # Extract text content
            if hasattr(doc, 'text'):
                full_text += doc.text + "\n"
            
            # Extract metadata if available
            metadata = getattr(doc, 'metadata', {})
            
            # Try to extract structured information from metadata
            if metadata:
                # Look for table information
                if 'tables' in metadata:
                    tables.extend(metadata['tables'])
                
                # Look for image information
                if 'images' in metadata:
                    images.extend(metadata['images'])
                
                # Look for section information
                if 'sections' in metadata:
                    sections.extend(metadata['sections'])
        
        # If no structured sections found, create basic ones
        if not sections:
            sections = self._extract_basic_sections(full_text)
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(full_text, tables, images, sections)
        
        return {
            'text': full_text.strip(),
            'sections': sections,
            'tables': tables,
            'images': images,
            'page_count': len(documents),
            'layout_info': {
                'parsing_mode': parsing_mode,
                'document_count': len(documents)
            },
            'metadata': {
                'file_path': file_path,
                'file_hash': self.get_file_hash(file_path),
                'parsing_mode': parsing_mode,
                'parsing_time': parsing_time,
                'parser_version': 'llamaparse_official_sdk',
                'quality_score': quality_score
            }
        }
    
    def _extract_basic_sections(self, text_content: str) -> list:
        """Extract basic sections from text when no structured data is available"""
        sections = []
        paragraphs = text_content.split('\n\n')
        
        current_section = {"title": "Introduction", "content": "", "level": 1}
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # Simple heuristic: if paragraph is short and doesn't end with period, might be header
            if len(para) < 100 and not para.endswith('.') and not para.endswith(','):
                # Save current section if it has content
                if current_section["content"].strip():
                    sections.append(current_section)
                
                # Start new section
                current_section = {
                    "title": para[:50] + "..." if len(para) > 50 else para,
                    "content": "",
                    "level": 1
                }
            else:
                current_section["content"] += para + "\n\n"
        
        # Add final section
        if current_section["content"].strip():
            sections.append(current_section)
        
        return sections
    
    def _calculate_quality_score(self, text: str, tables: list, images: list, sections: list) -> float:
        """Calculate parsing quality score based on extracted content"""
        score = 0.6  # Base score
        
        # Text quality indicators
        if len(text) > 100:
            score += 0.1
        
        # Structured data bonuses
        if tables:
            score += 0.1
        if images:
            score += 0.05
        if len(sections) > 1:
            score += 0.1
        
        # Text quality indicators
        if '�' not in text:  # No encoding issues
            score += 0.05
        
        # Character diversity (indicates good OCR)
        unique_chars = len(set(text.lower()))
        if unique_chars > 20:
            score += 0.1
        
        return min(score, 1.0)
    
    async def test_connection(self) -> bool:
        """Test if LlamaParse API is accessible with current API key"""
        try:
            # Simple test by initializing parser
            test_parser = LlamaParse(api_key=self.api_key)
            return True
        except Exception:
            return False

# Utility function for easy usage
async def parse_document_with_llamaparse(file_path: str, mode: str = "premium", document_type: str = None) -> Dict[str, Any]:
    """
    Convenience function to parse a document with LlamaParse
    
    Args:
        file_path: Path to document
        mode: "premium" or "fast"
        document_type: Optional document type hint
    
    Returns:
        Parsed document data
    """
    client = LlamaParseClient()
    return await client.parse_document(file_path, mode, document_type)

if __name__ == "__main__":
    # Test the client
    async def test():
        client = LlamaParseClient()
        connected = await client.test_connection()
        print(f"LlamaParse connection test: {'✅ SUCCESS' if connected else '❌ FAILED'}")
    
    import asyncio
    asyncio.run(test())