#!/usr/bin/env python3
"""
Quick integration test for Phase 1 enhanced PDF extraction.
Tests the full pipeline with pymupdf4llm integration.
"""

import sys
from pathlib import Path

def test_integration(pdf_path: str):
    """Test the integrated PDFExtractor with enhanced extraction"""
    
    print("="*80)
    print("PHASE 1 INTEGRATION TEST")
    print("="*80)
    
    from extractors.pdfs import PDFExtractor
    
    # Initialize extractor (use_rag is auto-detected, not a parameter)
    extractor = PDFExtractor(use_llm=False)
    
    print(f"\n📄 Testing: {Path(pdf_path).name}")
    print("-"*80)
    
    # Extract text
    print("\n1️⃣ Extracting text...")
    text_data = extractor.extract_text(Path(pdf_path))
    
    print(f"   Extraction method: {text_data.get('extraction_method', 'unknown')}")
    print(f"   Text length: {text_data['char_count']:,} chars")
    print(f"   Page count: {text_data['page_count']}")
    print(f"   Multi-column: {text_data.get('is_multi_column', False)}")
    
    # Check sections
    sections = text_data.get('sections', {})
    print(f"\n2️⃣ Sections detected: {len(sections)}")
    for section_name, content in sections.items():
        print(f"   - {section_name:20s}: {len(content):,} chars")
    
    # Check tables
    tables = text_data.get('tables', [])
    print(f"\n3️⃣ Tables detected: {len(tables)}")
    for i, table in enumerate(tables[:3], 1):
        print(f"   Table {i}: {table.get('n_rows', 0)} rows × {table.get('n_cols', 0)} cols")
    
    # Extract parameters (basic test without LLM)
    print("\n4️⃣ Extracting parameters...")
    
    # Use detect_sections with pre-extracted
    full_text = text_data['full_text']
    detected_sections = extractor.detect_sections(full_text, pre_extracted_sections=sections)
    
    print(f"   Sections used for extraction: {list(detected_sections.keys())}")
    
    # Extract from methods section if available
    if 'methods' in detected_sections:
        methods_text = detected_sections['methods']
        params = extractor.extract_parameters_from_text(methods_text, 'methods')
        
        print(f"\n   Parameters found in Methods section: {len(params)}")
        for param, data in list(params.items())[:10]:
            print(f"     {param:30s}: {data.get('value')} (conf={data.get('confidence', 0):.2f})")
        
        if len(params) > 10:
            print(f"     ... and {len(params)-10} more")
    
    # Summary
    print("\n" + "="*80)
    print("✅ INTEGRATION TEST COMPLETE")
    print("="*80)
    
    # Return summary
    return {
        'extraction_method': text_data.get('extraction_method'),
        'sections_count': len(sections),
        'tables_count': len(tables),
        'text_length': text_data['char_count'],
        'success': True
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_integration.py <pdf_path>")
        print("\nExample:")
        print('  python test_integration.py "../papers/Parvin et al. - 2018 - Credit Assignment.pdf"')
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)
    
    try:
        result = test_integration(pdf_path)
        
        # Check if improvements achieved
        if result['extraction_method'] == 'pymupdf4llm' and result['sections_count'] >= 3:
            print("\n🎉 SUCCESS: Enhanced extraction working!")
            print(f"   - {result['sections_count']} sections detected")
            print(f"   - {result['tables_count']} tables detected")
            print(f"   - {result['text_length']:,} chars extracted")
            sys.exit(0)
        elif result['extraction_method'] == 'pypdf_fallback':
            print("\n⚠️  WARNING: Fell back to pypdf (pymupdf4llm may not be installed)")
            sys.exit(1)
        else:
            print("\n⚠️  WARNING: Unexpected result")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
