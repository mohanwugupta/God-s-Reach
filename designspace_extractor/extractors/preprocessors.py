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
        from .layout_enhanced import extract_markdown_with_layout, extract_sections_from_markdown, extract_tables_from_markdown
        
        # Extract markdown
        markdown = extract_markdown_with_layout(str(pdf_path))
        
        # Extract sections
        sections = extract_sections_from_markdown(markdown)
        
        # Extract tables
        tables = extract_tables_from_markdown(markdown)
        
        # Build normalized structure
        normalized = {
            "sections": [{"name": name, "content": content} for name, content in sections.items()],
            "paragraphs": [],  # Could be enhanced to split sections into paragraphs
            "tables": tables,
            "figures": [],  # pymupdf4llm doesn't extract figures metadata
            "spans": [],    # Would need enhancement to track positions
            "full_text": markdown,
            "preprocessor": "pymupdf4llm",
            "metadata": {
                "sections_found": len(sections),
                "tables_found": len(tables)
            }
        }
        
        return normalized


class DoclingPreprocessor(PDFPreprocessor):
    """Docling-based PDF preprocessor for complex layouts."""
    
    def __init__(self):
        self.docling = None
        try:
            from docling.document_converter import DocumentConverter
            self.docling = DocumentConverter()
            logger.info("Docling preprocessor initialized successfully")
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
            
            # Extract normalized structure
            normalized = {
                "sections": [],
                "paragraphs": [],
                "tables": [],
                "figures": [],
                "spans": [],
                "full_text": "",
                "preprocessor": "docling",
                "metadata": {
                    "pages": len(doc.pages) if hasattr(doc, 'pages') else 0,
                    "has_tables": len(doc.tables) > 0 if hasattr(doc, 'tables') else False,
                    "has_figures": len(doc.pictures) > 0 if hasattr(doc, 'pictures') else False
                }
            }
            
            # Process text content
            text_parts = []
            if hasattr(doc, 'texts'):
                for item in doc.texts:
                    span = {
                        "text": item.text,
                        "page": item.page_no if hasattr(item, 'page_no') else 0,
                        "bbox": [item.prov[0].bbox.l, item.prov[0].bbox.t, 
                                item.prov[0].bbox.r, item.prov[0].bbox.b] if hasattr(item, 'prov') and item.prov else None
                    }
                    normalized["spans"].append(span)
                    text_parts.append(item.text)
            
            normalized["full_text"] = "\n".join(text_parts)
            
            # Process tables
            if hasattr(doc, 'tables'):
                for table in doc.tables:
                    table_data = {
                        "page": table.page_no if hasattr(table, 'page_no') else 0,
                        "bbox": [table.prov[0].bbox.l, table.prov[0].bbox.t,
                                table.prov[0].bbox.r, table.prov[0].bbox.b] if hasattr(table, 'prov') and table.prov else None,
                        "headers": [],
                        "rows": []
                    }
                    
                    # Extract table structure
                    if hasattr(table, 'export_to_dataframe'):
                        try:
                            df = table.export_to_dataframe()
                            table_data["headers"] = df.columns.tolist()
                            table_data["rows"] = df.values.tolist()
                        except Exception as e:
                            logger.warning(f"Failed to export table to dataframe: {e}")
                    
                    normalized["tables"].append(table_data)
            
            # Process figures
            if hasattr(doc, 'pictures'):
                for picture in doc.pictures:
                    figure_data = {
                        "page": picture.page_no if hasattr(picture, 'page_no') else 0,
                        "bbox": [picture.prov[0].bbox.l, picture.prov[0].bbox.t,
                                picture.prov[0].bbox.r, picture.prov[0].bbox.b] if hasattr(picture, 'prov') and picture.prov else None,
                        "caption": getattr(picture, 'caption', ''),
                        "type": "figure"
                    }
                    normalized["figures"].append(figure_data)
            
            logger.info(f"Docling extracted: {len(normalized['tables'])} tables, {len(normalized['figures'])} figures")
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
    
    def preprocess_pdf(self, pdf_path: Path, preprocessor: Optional[str] = None) -> Dict[str, Any]:
        """
        Preprocess PDF with appropriate tool.
        
        Args:
            pdf_path: Path to PDF file
            preprocessor: Specific preprocessor to use (None for auto-routing)
            
        Returns:
            Normalized document structure
        """
        preprocessor = preprocessor or self.route_pdf(pdf_path)
        
        if preprocessor not in self.preprocessors:
            raise ValueError(f"Unknown preprocessor: {preprocessor}")
        
        proc = self.preprocessors[preprocessor]
        if not proc.is_available():
            logger.warning(f"Preprocessor {preprocessor} not available, falling back to pymupdf4llm")
            proc = self.preprocessors["pymupdf4llm"]
            if not proc.is_available():
                raise RuntimeError("No preprocessors available")
        
        return proc.preprocess(pdf_path)
