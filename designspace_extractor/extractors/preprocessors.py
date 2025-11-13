"""
PDF preprocessing adapters for Docling integration with pymupdf4llm.
Routes PDFs to appropriate preprocessors based on complexity.
"""
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PDFCharacteristics:
    """Characteristics of a PDF for routing decisions."""
    has_tables: bool = False
    has_figures: bool = False
    is_multi_column: bool = False
    has_scanned_pages: bool = False
    text_selectable: bool = True
    complexity_score: int = 0  # 0-10 scale


class PDFPreprocessor(ABC):
    """Abstract base class for PDF preprocessors."""
    
    @abstractmethod
    def preprocess(self, pdf_path: Path) -> Dict[str, Any]:
        """Preprocess PDF and return normalized document structure."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this preprocessor is available."""
        pass


class Pymupdf4llmPreprocessor(PDFPreprocessor):
    """Your existing pymupdf4llm-based preprocessor."""
    
    def __init__(self):
        self.available = True  # Assume it's available since you use it
    
    def is_available(self) -> bool:
        return self.available
    
    def preprocess(self, pdf_path: Path) -> Dict[str, Any]:
        logger.info(f"Preprocessing {pdf_path.name} with pymupdf4llm")
        
        # Use your existing layout_enhanced.py logic
        from .layout_enhanced import (
            extract_markdown_with_layout, 
            extract_sections_from_markdown, 
            extract_tables_from_markdown,
            detect_multi_column_layout
        )
        
        # Import pypdf for metadata
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader
        
        # Extract markdown
        markdown = extract_markdown_with_layout(str(pdf_path))
        
        # Extract sections (returns dict)
        sections = extract_sections_from_markdown(markdown)
        
        # Extract tables (returns list)
        tables = extract_tables_from_markdown(markdown)
        
        # Get page count and metadata
        page_count = 0
        metadata = {}
        try:
            reader = PdfReader(str(pdf_path))
            page_count = len(reader.pages)
            if reader.metadata:
                metadata = {
                    'title': reader.metadata.get('/Title', ''),
                    'author': reader.metadata.get('/Author', ''),
                    'subject': reader.metadata.get('/Subject', ''),
                    'creator': reader.metadata.get('/Creator', ''),
                }
        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}")
        
        # Detect multi-column layout
        is_multi_column = detect_multi_column_layout(str(pdf_path))
        
        # Build normalized structure matching PDFExtractor expectations
        normalized = {
            "full_text": markdown,
            "markdown_text": markdown,
            "sections": sections,  # Already a dict
            "tables": tables,      # Already a list
            "page_count": page_count,
            "metadata": metadata,
            "extraction_method": "pymupdf4llm",
            "is_multi_column": is_multi_column
        }
        
        return normalized


class DoclingPreprocessor(PDFPreprocessor):
    """Docling-based PDF preprocessor for complex layouts."""
    
    def __init__(self):
        self.docling = None
        try:
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            
            # Configure for offline mode - disable OCR to avoid downloads
            # OCR requires models that need to be downloaded, which fails on offline compute nodes
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = False  # Disable OCR to avoid model downloads
            
            self.docling = DocumentConverter(
                format_options={
                    "pdf": PdfFormatOption(pipeline_options=pipeline_options)
                }
            )
            logger.info("Docling preprocessor initialized successfully (OCR disabled for offline mode)")
        except ImportError:
            logger.warning("Docling not available. Install with: pip install docling")
        except Exception as e:
            logger.warning(f"Failed to initialize Docling: {e}")
    
    def is_available(self) -> bool:
        return self.docling is not None
    
    def preprocess(self, pdf_path: Path) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("Docling not available")
        
        logger.info(f"Preprocessing {pdf_path.name} with Docling")
        
        try:
            # Convert document
            result = self.docling.convert(str(pdf_path))
            doc = result.document
            
            # Process text content
            text_parts = []
            sections = {}  # Dict of section_name: content
            
            if hasattr(doc, 'texts'):
                for item in doc.texts:
                    text_parts.append(item.text)
            
            full_text = "\n".join(text_parts)
            
            # Try to extract sections (basic implementation)
            # In reality, Docling might have structured section detection
            sections = {"full_document": full_text}
            
            # Process tables - convert to simple list format
            tables = []
            if hasattr(doc, 'tables'):
                for table in doc.tables:
                    table_content = ""
                    if hasattr(table, 'export_to_markdown'):
                        try:
                            table_content = table.export_to_markdown()
                        except:
                            pass
                    elif hasattr(table, 'export_to_dataframe'):
                        try:
                            df = table.export_to_dataframe()
                            table_content = df.to_markdown()
                        except:
                            pass
                    
                    if table_content:
                        tables.append({
                            'content': table_content,
                            'page': table.page_no if hasattr(table, 'page_no') else 0
                        })
            
            # Get metadata
            page_count = len(doc.pages) if hasattr(doc, 'pages') else 0
            metadata = {
                'tables_found': len(tables),
                'figures_found': len(doc.pictures) if hasattr(doc, 'pictures') else 0,
                'pages': page_count
            }
            
            # Build normalized structure matching PDFExtractor expectations
            normalized = {
                "full_text": full_text,
                "markdown_text": full_text,
                "sections": sections,  # Dict format
                "tables": tables,      # List format
                "page_count": page_count,
                "metadata": metadata,
                "extraction_method": "docling",
                "is_multi_column": True  # Docling handles complex layouts
            }
            
            logger.info(f"Docling extracted: {len(tables)} tables, {page_count} pages")
            return normalized
            
        except Exception as e:
            logger.error(f"Docling preprocessing failed: {e}")
            raise


class PDFPreprocessorRouter:
    """Routes PDFs between pymupdf4llm and Docling based on complexity."""
    
    def __init__(self):
        self.preprocessors = {
            "pymupdf4llm": Pymupdf4llmPreprocessor(),
            "docling": DoclingPreprocessor()
        }
        logger.info(f"Preprocessor router initialized. Available: {[k for k, v in self.preprocessors.items() if v.is_available()]}")
    
    def detect_characteristics(self, pdf_path: Path) -> PDFCharacteristics:
        """Quick analysis to determine PDF complexity."""
        chars = PDFCharacteristics()
        
        try:
            # Try basic text extraction to check characteristics
            import fitz
            doc = fitz.open(pdf_path)
            
            # Check first few pages
            for page_num in range(min(3, len(doc))):
                page = doc[page_num]
                text = page.get_text()
                
                # Check for table indicators
                table_count = text.lower().count("table")
                if table_count >= 2:  # Multiple table mentions suggest structured content
                    chars.has_tables = True
                    chars.complexity_score += 2
                
                # Check for figure indicators  
                figure_count = text.count("Figure") + text.count("Fig.")
                if figure_count >= 2:
                    chars.has_figures = True
                    chars.complexity_score += 1
                
                # Check text length (short text might indicate scanned)
                if len(text.strip()) < 500:
                    chars.has_scanned_pages = True
                    chars.complexity_score += 3
                
                # Check for multi-column indicators
                lines = text.split('\n')
                short_lines = [line for line in lines if len(line.strip()) < 60]
                if len(short_lines) > len(lines) * 0.6:  # >60% short lines
                    chars.is_multi_column = True
                    chars.complexity_score += 2
            
            chars.text_selectable = len(doc) > 0
            doc.close()
            
            logger.debug(f"PDF characteristics for {pdf_path.name}: complexity={chars.complexity_score}, "
                        f"tables={chars.has_tables}, figures={chars.has_figures}, "
                        f"scanned={chars.has_scanned_pages}")
            
        except Exception as e:
            logger.warning(f"Error detecting PDF characteristics: {e}")
            chars.has_scanned_pages = True
            chars.complexity_score = 8  # Assume complex if detection fails
        
        return chars
    
    def route_pdf(self, pdf_path: Path, force_preprocessor: Optional[str] = None) -> str:
        """
        Determine which preprocessor to use.
        
        Args:
            pdf_path: Path to PDF file
            force_preprocessor: Force a specific preprocessor (None for auto)
            
        Returns:
            Preprocessor name to use
        """
        if force_preprocessor:
            if force_preprocessor in self.preprocessors and self.preprocessors[force_preprocessor].is_available():
                logger.info(f"Using forced preprocessor: {force_preprocessor}")
                return force_preprocessor
            else:
                logger.warning(f"Forced preprocessor {force_preprocessor} not available, falling back to auto")
        
        # Auto-routing logic
        chars = self.detect_characteristics(pdf_path)
        
        # Route to Docling if:
        # - Has tables (Docling preserves structure better)
        # - Has figures (Docling extracts metadata)
        # - High complexity score (>=5)
        # - Scanned pages (better OCR potential)
        if (chars.has_tables or chars.has_figures or 
            chars.complexity_score >= 5 or chars.has_scanned_pages):
            if self.preprocessors["docling"].is_available():
                logger.info(f"Routing {pdf_path.name} to Docling (complexity={chars.complexity_score}, "
                           f"tables={chars.has_tables}, figures={chars.has_figures})")
                return "docling"
            else:
                logger.info(f"Docling preferred for {pdf_path.name} but not available, using pymupdf4llm")
                return "pymupdf4llm"
        
        # Default to your existing pymupdf4llm for simple PDFs
        logger.info(f"Routing {pdf_path.name} to pymupdf4llm (complexity={chars.complexity_score})")
        return "pymupdf4llm"
    
    def preprocess_pdf(self, pdf_path, preprocessor: Optional[str] = None) -> Dict[str, Any]:
        """
        Preprocess PDF with appropriate tool.
        
        Args:
            pdf_path: Path to PDF file (Path object or string)
            preprocessor: Specific preprocessor to use ('auto', 'pymupdf4llm', 'docling', or None for auto-routing)
            
        Returns:
            Normalized document structure
        """
        # Ensure pdf_path is a Path object
        pdf_path = Path(pdf_path) if not isinstance(pdf_path, Path) else pdf_path
        
        # Handle 'auto' or None -> route based on PDF characteristics
        if preprocessor is None or preprocessor == 'auto':
            preprocessor = self.route_pdf(pdf_path)
        
        if preprocessor not in self.preprocessors:
            raise ValueError(f"Unknown preprocessor: {preprocessor}")
        
        proc = self.preprocessors[preprocessor]
        if not proc.is_available():
            logger.warning(f"Preprocessor {preprocessor} not available, falling back to pymupdf4llm")
            proc = self.preprocessors["pymupdf4llm"]
            if not proc.is_available():
                raise RuntimeError("No preprocessors available")
        
        # Try to preprocess, with fallback to pymupdf4llm if it fails
        try:
            return proc.preprocess(pdf_path)
        except Exception as e:
            # If Docling fails (e.g., needs internet for models), fallback to pymupdf4llm
            if preprocessor == "docling" and self.preprocessors["pymupdf4llm"].is_available():
                logger.warning(f"Docling preprocessing failed ({e}), falling back to pymupdf4llm")
                return self.preprocessors["pymupdf4llm"].preprocess(pdf_path)
            else:
                # Re-raise if pymupdf4llm also failed or we're already using pymupdf4llm
                raise
