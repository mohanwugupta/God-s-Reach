"""
Enhanced PDF layout extraction using pymupdf4llm for correct column ordering
and improved text quality. This module provides layout-aware text extraction
that preserves structure and handles multi-column layouts correctly.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional
import re

logger = logging.getLogger(__name__)

def extract_markdown_with_layout(pdf_path: str, **kwargs) -> str:
    """
    Extract PDF content as clean Markdown with correct reading order.
    
    This function uses pymupdf4llm which:
    - Correctly orders multi-column layouts
    - Preserves section headers
    - Extracts tables as Markdown tables
    - Handles equations and special characters
    - Fixes word spacing issues
    
    Args:
        pdf_path: Path to PDF file
        **kwargs: Additional arguments passed to pymupdf4llm:
            - page_chunks: bool = False (split by pages)
            - margins: tuple = (0, 50, 0, 50) (left, top, right, bottom)
            - dpi: int = 150 (image resolution)
    
    Returns:
        Markdown-formatted text with preserved structure
    """
    try:
        import pymupdf4llm
    except ImportError:
        logger.warning("pymupdf4llm not available, falling back to basic extraction")
        return _fallback_extract_text(pdf_path)
    
    try:
        # Extract as Markdown with layout preservation
        markdown = pymupdf4llm.to_markdown(
            pdf_path,
            page_chunks=kwargs.get('page_chunks', False),
            margins=kwargs.get('margins', (0, 50, 0, 50)),  # Ignore headers/footers
            dpi=kwargs.get('dpi', 150)
        )
        
        # Post-process to clean up common issues
        markdown = _clean_markdown(markdown)
        
        logger.debug(f"Extracted {len(markdown)} chars as Markdown from {Path(pdf_path).name}")
        return markdown
        
    except Exception as e:
        logger.warning(f"pymupdf4llm extraction failed: {e}, falling back to basic extraction")
        return _fallback_extract_text(pdf_path)


def _fallback_extract_text(pdf_path: str) -> str:
    """Fallback to basic PyMuPDF extraction if pymupdf4llm fails"""
    import fitz
    
    doc = fitz.open(pdf_path)
    text = ""
    
    for page in doc:
        text += page.get_text()
    
    doc.close()
    return text


def _clean_markdown(text: str) -> str:
    """
    Clean extracted Markdown to fix common issues.
    
    Handles:
    - Manuscript line numbers
    - Excessive whitespace
    - Malformed headers
    - Concatenated words (basic fix)
    """
    # Remove manuscript line numbers (e.g., "\n123\n")
    text = re.sub(r'\n\d{1,3}\s*\n', '\n', text)
    
    # Collapse multiple newlines (but preserve double for paragraphs)
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    
    # Fix common spacing issues around punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    text = re.sub(r'([.,;:!?])([A-Z])', r'\1 \2', text)
    
    # Strip extra whitespace
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    return text


def extract_sections_from_markdown(markdown: str) -> Dict[str, str]:
    """
    Parse Markdown to extract text by section.
    
    Looks for common section headers:
    - Abstract
    - Introduction
    - Methods / Materials and Methods
    - Results
    - Discussion
    - References
    
    Returns:
        Dictionary mapping section names to content
    """
    sections = {}
    current_section = "preamble"
    current_content = []
    
    # Common section headers in scientific papers
    section_patterns = [
        (r'^#{1,3}\s*(abstract)', 'abstract'),
        (r'^#{1,3}\s*(introduction)', 'introduction'),
        (r'^#{1,3}\s*(methods?|materials?\s+and\s+methods?|experimental\s+procedures?)', 'methods'),
        (r'^#{1,3}\s*(results?)', 'results'),
        (r'^#{1,3}\s*(discussion)', 'discussion'),
        (r'^#{1,3}\s*(conclusion)', 'conclusion'),
        (r'^#{1,3}\s*(references?|bibliography)', 'references'),
        (r'^#{1,3}\s*(appendix|supplementary)', 'appendix'),
    ]
    
    for line in markdown.split('\n'):
        # Check if line is a section header
        matched = False
        for pattern, section_name in section_patterns:
            if re.match(pattern, line.lower()):
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                
                # Start new section
                current_section = section_name
                current_content = []
                matched = True
                break
        
        if not matched:
            current_content.append(line)
    
    # Save final section
    if current_content:
        sections[current_section] = '\n'.join(current_content)
    
    logger.debug(f"Extracted {len(sections)} sections: {list(sections.keys())}")
    return sections


def extract_tables_from_markdown(markdown: str) -> List[Dict[str, str]]:
    """
    Extract Markdown tables and convert to structured format.
    
    Markdown tables look like:
    | Header1 | Header2 |
    |---------|---------|
    | Value1  | Value2  |
    
    Returns:
        List of dictionaries with 'headers' and 'rows' keys
    """
    tables = []
    lines = markdown.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check if line starts a table (contains |)
        if line.startswith('|') and '|' in line:
            # Extract header row
            headers = [cell.strip() for cell in line.split('|')[1:-1]]
            
            # Skip separator row
            i += 1
            if i >= len(lines) or not lines[i].strip().startswith('|'):
                i += 1
                continue
            
            # Extract data rows
            i += 1
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                row = [cell.strip() for cell in lines[i].split('|')[1:-1]]
                rows.append(row)
                i += 1
            
            tables.append({
                'headers': headers,
                'rows': rows,
                'n_rows': len(rows),
                'n_cols': len(headers)
            })
            
        i += 1
    
    logger.debug(f"Extracted {len(tables)} tables from Markdown")
    return tables


def detect_multi_column_layout(pdf_path: str, sample_pages: int = 3) -> bool:
    """
    Detect if PDF uses multi-column layout by analyzing X-coordinates.
    
    Args:
        pdf_path: Path to PDF file
        sample_pages: Number of pages to sample (default: first 3)
    
    Returns:
        True if multi-column layout detected
    """
    import fitz
    
    try:
        doc = fitz.open(pdf_path)
        
        all_x_coords = []
        for page_num in range(min(sample_pages, len(doc))):
            page = doc[page_num]
            blocks = page.get_text('dict')['blocks']
            
            # Collect left X-coordinates of text blocks
            for block in blocks:
                if block['type'] == 0:  # Text block
                    all_x_coords.append(block['bbox'][0])
        
        doc.close()
        
        # Cluster X-coordinates to detect columns
        if len(all_x_coords) < 10:
            return False
        
        from sklearn.cluster import DBSCAN
        import numpy as np
        
        X = np.array([[x] for x in all_x_coords])
        clustering = DBSCAN(eps=50, min_samples=3).fit(X)
        
        n_clusters = len(set(clustering.labels_)) - (1 if -1 in clustering.labels_ else 0)
        
        is_multi_column = n_clusters >= 2
        logger.debug(f"Detected {n_clusters} columns in {Path(pdf_path).name}: {'multi-column' if is_multi_column else 'single-column'}")
        
        return is_multi_column
        
    except Exception as e:
        logger.warning(f"Column detection failed: {e}")
        return False


if __name__ == "__main__":
    # Test the enhanced extraction
    import sys
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        
        print("="*80)
        print(f"Testing enhanced extraction on: {pdf_path}")
        print("="*80)
        
        # Detect layout
        is_multi = detect_multi_column_layout(pdf_path)
        print(f"\nLayout: {'Multi-column' if is_multi else 'Single-column'}")
        
        # Extract as Markdown
        markdown = extract_markdown_with_layout(pdf_path)
        print(f"\nExtracted {len(markdown)} characters")
        print(f"\nFirst 1000 characters:")
        print("-"*80)
        print(markdown[:1000])
        
        # Extract sections
        sections = extract_sections_from_markdown(markdown)
        print(f"\n\nSections found: {list(sections.keys())}")
        
        if 'methods' in sections:
            print(f"\nMethods section preview:")
            print("-"*80)
            print(sections['methods'][:500])
        
        # Extract tables
        tables = extract_tables_from_markdown(markdown)
        print(f"\n\nTables found: {len(tables)}")
        for i, table in enumerate(tables[:3], 1):
            print(f"\nTable {i}: {table['n_rows']} rows × {table['n_cols']} cols")
            print(f"Headers: {table['headers']}")
    else:
        print("Usage: python layout_enhanced.py <pdf_path>")
