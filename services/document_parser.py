"""
Document Parser Service for Search Wizard
Main service that orchestrates document parsing with intelligent routing
"""

import os
import hashlib
import asyncio
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import time

from .llamaparse_client import LlamaParseClient, LlamaParseError
from .cache_service import CacheService
from ..utils import extract_text_from_pdf, extract_text_from_docx, process_url_content
from dotenv import load_dotenv

load_dotenv()

class ParserType(Enum):
    """Available parser types"""
    LLAMAPARSE_PREMIUM = "llamaparse_premium"
    LLAMAPARSE_FAST = "llamaparse_fast"
    LEGACY_PYMUPDF = "legacy_pymupdf"
    BASIC_FALLBACK = "basic_fallback"

@dataclass
class ParsedDocument:
    """
    Enhanced document structure from parsing
    """
    # Basic metadata
    file_path: str
    file_type: str
    file_hash: str
    parser_used: str
    parsing_quality_score: float
    complexity_score: int
    
    # Content structure
    text_content: str
    sections: list
    tables: list
    images: list
    
    # Layout information
    page_count: int
    layout_info: Dict[str, Any]
    
    # Processing metadata
    parsing_time: float
    token_count: int
    
    # Enhanced content from LlamaParse
    enhanced_content: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/caching"""
        return {
            'file_path': self.file_path,
            'file_type': self.file_type,
            'file_hash': self.file_hash,
            'parser_used': self.parser_used,
            'parsing_quality_score': self.parsing_quality_score,
            'complexity_score': self.complexity_score,
            'text_content': self.text_content,
            'sections': self.sections,
            'tables': self.tables,
            'images': self.images,
            'page_count': self.page_count,
            'layout_info': self.layout_info,
            'parsing_time': self.parsing_time,
            'token_count': self.token_count,
            'enhanced_content': self.enhanced_content
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParsedDocument':
        """Create instance from dictionary"""
        return cls(**data)
    
    def to_legacy_format(self) -> Dict[str, Any]:
        """Convert to your current system format for backward compatibility"""
        return {
            'content': self.text_content,
            'structure': self.extract_structure_template(),
            'metadata': {
                'parser': self.parser_used,
                'quality': self.parsing_quality_score,
                'pages': self.page_count,
                'complexity': self.complexity_score
            }
        }
    
    def extract_structure_template(self) -> Dict[str, Any]:
        """Extract structure template for golden examples"""
        return {
            'document_type': self._infer_document_type(),
            'sections': self.sections,
            'tables': [self._table_to_template(table) for table in self.tables],
            'visual_elements': self.layout_info,
            'content_patterns': self._analyze_content_patterns()
        }
    
    def _infer_document_type(self) -> str:
        """Infer document type from content"""
        content_lower = self.text_content.lower()
        
        if any(word in content_lower for word in ['financial', 'revenue', 'profit', 'balance sheet']):
            return 'financial'
        elif any(word in content_lower for word in ['candidate', 'resume', 'experience', 'skills']):
            return 'candidate_report'
        elif any(word in content_lower for word in ['company', 'organization', 'business', 'annual report']):
            return 'company_info'
        elif any(word in content_lower for word in ['role', 'position', 'job', 'responsibilities']):
            return 'role_specification'
        else:
            return 'general'
    
    def _table_to_template(self, table: Dict) -> Dict:
        """Convert table to template format"""
        return {
            'structure': table.get('structure', {}),
            'headers': table.get('headers', []),
            'row_count': table.get('row_count', 0),
            'formatting': table.get('formatting', {})
        }
    
    def _analyze_content_patterns(self) -> Dict[str, Any]:
        """Analyze content patterns for template creation"""
        return {
            'average_paragraph_length': len(self.text_content.split('\n\n')),
            'section_count': len(self.sections),
            'table_count': len(self.tables),
            'image_count': len(self.images),
            'content_density': len(self.text_content) / max(self.page_count, 1)
        }

class DocumentComplexityAnalyzer:
    """Analyzes document complexity to determine best parsing strategy"""
    
    def analyze_complexity(self, file_path: str) -> int:
        """
        Analyze document complexity and return score from 1-10
        Higher score = more complex = needs LlamaParse
        """
        complexity_score = 0
        
        try:
            # File size factor
            file_size = os.path.getsize(file_path)
            if file_size > 10 * 1024 * 1024:  # > 10MB
                complexity_score += 3
            elif file_size > 1 * 1024 * 1024:  # > 1MB
                complexity_score += 1
            
            # File type factor
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in ['.pptx', '.ppt']:
                complexity_score += 4  # PowerPoint usually complex
            elif file_ext in ['.docx', '.doc']:
                complexity_score += 2  # Word docs moderately complex
            elif file_ext == '.pdf':
                # Quick PDF analysis
                pdf_complexity = self._analyze_pdf_complexity(file_path)
                complexity_score += pdf_complexity
            
            return min(complexity_score, 10)  # Cap at 10
            
        except Exception:
            return 5  # Default to medium complexity if analysis fails
    
    def _analyze_pdf_complexity(self, file_path: str) -> int:
        """Analyze PDF-specific complexity factors"""
        try:
            # Try to extract some text to see if it's scanned
            sample_text = extract_text_from_pdf(file_path)
            
            # If very little text extracted, likely scanned
            if len(sample_text) < 100:
                return 4  # High complexity - needs OCR
            
            # Check for tables (simple heuristic)
            if '\t' in sample_text or '|' in sample_text:
                return 2  # Has tables
            
            return 1  # Simple PDF
            
        except Exception:
            return 3  # Unknown complexity

class DocumentRouter:
    """Intelligent routing for document parsing"""
    
    def __init__(self):
        self.complexity_analyzer = DocumentComplexityAnalyzer()
        self.enable_llamaparse = os.getenv("ENABLE_LLAMAPARSE", "false").lower() == "true"
        self.pricing_tier = os.getenv("LLAMAPARSE_PRICING_TIER", "fast")
    
    def determine_parsing_strategy(self, file_path: str, document_type: str = None, user_preferences: Dict = None) -> ParserType:
        """
        Determine the best parsing strategy based on document characteristics
        """
        if not self.enable_llamaparse:
            return ParserType.LEGACY_PYMUPDF
        
        # Analyze document complexity
        complexity_score = self.complexity_analyzer.analyze_complexity(file_path)
        file_size = os.path.getsize(file_path)
        
        # Decision logic
        if complexity_score >= 8:  # Very high complexity
            return ParserType.LLAMAPARSE_PREMIUM
        elif complexity_score >= 5:  # Medium-high complexity
            if self.pricing_tier == "premium":
                return ParserType.LLAMAPARSE_PREMIUM
            else:
                return ParserType.LLAMAPARSE_FAST
        elif complexity_score >= 3:  # Medium complexity
            return ParserType.LLAMAPARSE_FAST
        elif file_size > 50 * 1024 * 1024:  # Large files
            return ParserType.LLAMAPARSE_FAST
        else:
            return ParserType.LEGACY_PYMUPDF  # Simple docs

class DocumentParserService:
    """
    Main document parsing service with intelligent routing and caching
    """
    
    def __init__(self):
        self.router = DocumentRouter()
        self.cache = CacheService()
        self.llamaparse_client = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.llamaparse_client = LlamaParseClient()
        await self.llamaparse_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.llamaparse_client:
            await self.llamaparse_client.__aexit__(exc_type, exc_val, exc_tb)
    
    def get_file_hash(self, file_path: str) -> str:
        """Generate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    async def parse_document(self, file_path: str, document_type: str = None, user_preferences: Dict = None) -> ParsedDocument:
        """
        Main parsing method with intelligent routing and caching
        """
        # Generate file hash for caching
        file_hash = self.get_file_hash(file_path)
        
        # Check cache first
        cached_result = await self.cache.get_parsed_document(file_hash)
        if cached_result:
            return ParsedDocument.from_dict(cached_result)
        
        # Determine parsing strategy
        parser_type = self.router.determine_parsing_strategy(file_path, document_type, user_preferences)
        
        start_time = time.time()
        
        try:
            # Parse with appropriate method
            if parser_type in [ParserType.LLAMAPARSE_PREMIUM, ParserType.LLAMAPARSE_FAST]:
                result = await self._parse_with_llamaparse(file_path, parser_type, document_type)
            else:
                result = await self._parse_with_fallback(file_path, parser_type)
            
            # Cache result
            await self.cache.cache_parsed_document(file_hash, result.to_dict())
            
            return result
            
        except Exception as e:
            # Fallback on error
            print(f"Parsing failed with {parser_type}, falling back: {str(e)}")
            return await self._parse_with_fallback(file_path, ParserType.LEGACY_PYMUPDF)
    
    async def _parse_with_llamaparse(self, file_path: str, parser_type: ParserType, document_type: str = None) -> ParsedDocument:
        """Parse document using LlamaParse"""
        mode = "premium" if parser_type == ParserType.LLAMAPARSE_PREMIUM else "fast"
        
        start_time = time.time()
        
        try:
            llamaparse_result = await self.llamaparse_client.parse_document(file_path, mode, document_type)
            parsing_time = time.time() - start_time
            
            # Convert LlamaParse result to our format
            return self._convert_llamaparse_result(file_path, llamaparse_result, parser_type.value, parsing_time)
            
        except LlamaParseError as e:
            raise Exception(f"LlamaParse failed: {str(e)}")
    
    async def _parse_with_fallback(self, file_path: str, parser_type: ParserType) -> ParsedDocument:
        """Parse document using fallback methods"""
        start_time = time.time()
        
        try:
            # Use your existing parsing logic
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.pdf':
                text_content = extract_text_from_pdf(file_path)
            elif file_ext in ['.docx', '.doc']:
                text_content = extract_text_from_docx(file_path)
            else:
                # Basic text extraction
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text_content = f.read()
            
            parsing_time = time.time() - start_time
            
            return ParsedDocument(
                file_path=file_path,
                file_type=file_ext,
                file_hash=self.get_file_hash(file_path),
                parser_used=parser_type.value,
                parsing_quality_score=0.6,  # Moderate quality for fallback
                complexity_score=self.router.complexity_analyzer.analyze_complexity(file_path),
                text_content=text_content,
                sections=self._extract_basic_sections(text_content),
                tables=[],  # Basic parsing doesn't extract tables
                images=[],  # Basic parsing doesn't extract images
                page_count=1,  # Estimate
                layout_info={},
                parsing_time=parsing_time,
                token_count=len(text_content.split())
            )
            
        except Exception as e:
            raise Exception(f"Fallback parsing failed: {str(e)}")
    
    def _convert_llamaparse_result(self, file_path: str, llamaparse_result: Dict, parser_used: str, parsing_time: float) -> ParsedDocument:
        """Convert LlamaParse result to ParsedDocument format"""
        
        # Extract main content
        text_content = llamaparse_result.get('text', '')
        
        # Extract structured data
        sections = llamaparse_result.get('sections', [])
        tables = llamaparse_result.get('tables', [])
        images = llamaparse_result.get('images', [])
        
        # Calculate quality score based on LlamaParse result
        quality_score = self._calculate_quality_score(llamaparse_result)
        
        return ParsedDocument(
            file_path=file_path,
            file_type=os.path.splitext(file_path)[1].lower(),
            file_hash=self.get_file_hash(file_path),
            parser_used=parser_used,
            parsing_quality_score=quality_score,
            complexity_score=self.router.complexity_analyzer.analyze_complexity(file_path),
            text_content=text_content,
            sections=sections,
            tables=tables,
            images=images,
            page_count=llamaparse_result.get('page_count', 1),
            layout_info=llamaparse_result.get('layout_info', {}),
            parsing_time=parsing_time,
            token_count=len(text_content.split()),
            enhanced_content=llamaparse_result  # Store full LlamaParse result
        )
    
    def _calculate_quality_score(self, llamaparse_result: Dict) -> float:
        """Calculate parsing quality score from LlamaParse result"""
        score = 0.8  # Base score for LlamaParse
        
        # Bonus for structured data
        if llamaparse_result.get('tables'):
            score += 0.1
        if llamaparse_result.get('images'):
            score += 0.05
        if llamaparse_result.get('sections'):
            score += 0.05
        
        return min(score, 1.0)
    
    def _extract_basic_sections(self, text_content: str) -> list:
        """Extract basic sections from text (fallback method)"""
        # Simple section detection based on line breaks and formatting
        sections = []
        lines = text_content.split('\n')
        
        current_section = {"title": "Content", "content": "", "level": 1}
        
        for line in lines:
            if line.strip() and (line.isupper() or len(line) < 100):
                # Likely a header
                if current_section["content"]:
                    sections.append(current_section)
                current_section = {"title": line.strip(), "content": "", "level": 1}
            else:
                current_section["content"] += line + "\n"
        
        if current_section["content"]:
            sections.append(current_section)
        
        return sections

# Convenience function for easy usage
async def parse_document(file_path: str, document_type: str = None) -> ParsedDocument:
    """
    Convenience function to parse a document
    """
    async with DocumentParserService() as service:
        return await service.parse_document(file_path, document_type)