"""
Layout extraction module using PyMuPDF for enhanced PDF parsing.
Provides word-level and block-level text extraction with coordinates.
"""
from pathlib import Path
from typing import List, Dict, Any
import fitz  # PyMuPDF


def extract_words(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Extract words with bounding boxes from PDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of pages with word data: [{"page": int, "words": [(x0, y0, x1, y1, "word", block, line, word_no), ...]}]
    """
    doc = fitz.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc):
        words = page.get_text("words")  # (x0, y0, x1, y1, "word", block, line, word_no)
        pages.append({"page": i + 1, "words": words})
    doc.close()
    return pages


def page_text_blocks(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Extract text blocks with bounding boxes from PDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of pages with block data: [{"page": int, "blocks": [(x0, y0, x1, y1, text, block_no, ...), ...]}]
    """
    doc = fitz.open(str(pdf_path))
    out = []
    for i, page in enumerate(doc):
        blocks = page.get_text("blocks")  # [(x0, y0, x1, y1, text, block_no, ...)]
        out.append({"page": i + 1, "blocks": blocks})
    doc.close()
    return out


def extract_page_dict(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Extract detailed page structure including fonts and positions.

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of page dictionaries with detailed layout info
    """
    doc = fitz.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc):
        page_dict = page.get_text("dict")
        pages.append({"page": i + 1, "dict": page_dict})
    doc.close()
    return pages
