#!/usr/bin/env python3
"""
Test script to demonstrate PDF extraction improvements using pymupdf4llm.

Compares old vs new extraction methods on problematic papers.
"""

import sys
from pathlib import Path

def test_extraction_comparison(pdf_path: str):
    """Compare old PyMuPDF extraction vs new pymupdf4llm extraction"""
    
    print("="*80)
    print(f"TESTING: {Path(pdf_path).name}")
    print("="*80)
    
    # ===== OLD METHOD: Basic PyMuPDF =====
    print("\n📊 OLD METHOD (PyMuPDF get_text)")
    print("-"*80)
    
    import fitz
    doc = fitz.open(pdf_path)
    old_text = ""
    for page in doc:
        old_text += page.get_text()
    doc.close()
    
    print(f"Length: {len(old_text)} chars")
    print(f"\nFirst 500 chars:")
    print(repr(old_text[:500]))
    
    # Check for common issues
    issues = []
    if "participantsappeared" in old_text or "experimentswhich" in old_text:
        issues.append("❌ Words concatenated without spaces")
    if old_text.count("\n\n") / len(old_text.split("\n")) < 0.1:
        issues.append("❌ No paragraph breaks (wall of text)")
    if "\n1\n" in old_text[:1000] and "\n2\n" in old_text[:1000]:
        issues.append("❌ Line numbers polluting text")
    
    if issues:
        print(f"\n⚠️  Issues detected:")
        for issue in issues:
            print(f"   {issue}")
    
    # ===== NEW METHOD: pymupdf4llm =====
    print("\n\n✨ NEW METHOD (pymupdf4llm)")
    print("-"*80)
    
    try:
        import pymupdf4llm
        new_text = pymupdf4llm.to_markdown(pdf_path)
        
        print(f"Length: {len(new_text)} chars")
        print(f"\nFirst 500 chars:")
        print(new_text[:500])
        
        # Check for improvements
        improvements = []
        if "##" in new_text or "###" in new_text:
            improvements.append("✅ Section headers preserved")
        if "|" in new_text and "---" in new_text:
            improvements.append("✅ Tables extracted as Markdown")
        if new_text.count("\n\n") / len(new_text.split("\n")) > 0.2:
            improvements.append("✅ Proper paragraph breaks")
        
        if improvements:
            print(f"\n✨ Improvements:")
            for improvement in improvements:
                print(f"   {improvement}")
        
        # ===== COMPARISON =====
        print(f"\n\n📈 COMPARISON")
        print("-"*80)
        print(f"Old method: {len(old_text):,} chars")
        print(f"New method: {len(new_text):,} chars")
        print(f"Difference: {len(new_text) - len(old_text):+,} chars ({(len(new_text)/len(old_text)-1)*100:+.1f}%)")
        
        # Search for key terms
        print(f"\n\n🔍 KEY TERM DETECTION")
        print("-"*80)
        
        search_terms = [
            ("participants", "Participant count"),
            ("n = ", "Sample size notation"),
            ("age", "Age demographics"),
            ("apparatus", "Equipment description"),
            ("experiment", "Experiment mentions"),
            ("method", "Methods section"),
        ]
        
        for term, description in search_terms:
            old_count = old_text.lower().count(term.lower())
            new_count = new_text.lower().count(term.lower())
            status = "✅" if new_count >= old_count else "⚠️"
            print(f"{status} {description:30s}: Old={old_count:2d}, New={new_count:2d}")
        
        # Extract sections if available
        from extractors.layout_enhanced import extract_sections_from_markdown
        sections = extract_sections_from_markdown(new_text)
        
        print(f"\n\n📑 SECTIONS DETECTED")
        print("-"*80)
        if sections:
            for section_name, content in sections.items():
                print(f"   {section_name:20s}: {len(content):,} chars")
        else:
            print("   (No sections detected)")
        
        # Extract tables if available
        from extractors.layout_enhanced import extract_tables_from_markdown
        tables = extract_tables_from_markdown(new_text)
        
        print(f"\n\n📊 TABLES DETECTED")
        print("-"*80)
        if tables:
            for i, table in enumerate(tables, 1):
                print(f"   Table {i}: {table['n_rows']} rows × {table['n_cols']} cols")
                print(f"      Headers: {', '.join(table['headers'][:5])}{'...' if len(table['headers']) > 5 else ''}")
        else:
            print("   (No tables detected)")
        
        # Show methods section if found
        if 'methods' in sections:
            print(f"\n\n📋 METHODS SECTION PREVIEW")
            print("-"*80)
            methods_text = sections['methods']
            print(methods_text[:800])
            if len(methods_text) > 800:
                print(f"\n   ... ({len(methods_text)-800:,} more chars)")
        
    except ImportError:
        print("❌ pymupdf4llm not installed")
        print("\nInstall with: pip install pymupdf4llm")
        return
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_extraction_improvements.py <pdf_path>")
        print("\nExample:")
        print('  python test_extraction_improvements.py "papers/Parvin et al. - 2018 - Credit Assignment.pdf"')
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)
    
    test_extraction_comparison(pdf_path)
    
    print("\n\n" + "="*80)
    print("✅ TEST COMPLETE")
    print("="*80)
