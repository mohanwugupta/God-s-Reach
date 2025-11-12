#!/usr/bin/env python3
"""
Debug Parvin paper extraction to understand why only 2 parameters are found.
"""
from pathlib import Path
from extractors.preprocessors import PDFPreprocessorRouter

# Parvin paper path
pdf_path = Path('../papers/Parvin et al. - 2018 - Credit Assignment in a Motor Decision Making Task Is Influenced by Agency and Not Sensory Prediction.pdf')

print('='*80)
print('PARVIN PAPER EXTRACTION DEBUG')
print('='*80)

# Initialize router
router = PDFPreprocessorRouter()

# Check routing decision
print('\n1. ROUTING DECISION')
print('-'*80)
preprocessor = router.route_pdf(pdf_path, force_preprocessor=None)
print(f'Auto-selected preprocessor: {preprocessor}')

# Force pymupdf4llm extraction
print('\n2. PYMUPDF4LLM EXTRACTION')
print('-'*80)
result = router.preprocess_pdf(pdf_path, preprocessor='pymupdf4llm')
print(f'Extraction method: {result["extraction_method"]}')
print(f'Full text length: {len(result["full_text"]):,} chars')
print(f'Sections found: {list(result["sections"].keys())}')
print(f'Multi-column detected: {result["is_multi_column"]}')
print(f'Tables found: {len(result.get("tables", []))}')

# Check Methods section specifically
print('\n3. METHODS SECTION ANALYSIS')
print('-'*80)
if 'methods' in result['sections']:
    methods_text = result['sections']['methods']
    print(f'✓ Methods section found!')
    print(f'  Length: {len(methods_text):,} chars')
    print(f'  Word count: {len(methods_text.split()):,} words')
    print(f'\n  First 800 characters:')
    print('  ' + '-'*76)
    print('  ' + methods_text[:800].replace('\n', '\n  '))
    print('  ' + '-'*76)
    
    # Check for key parameter indicators
    print(f'\n  Parameter keyword search:')
    keywords = ['participant', 'subject', 'trial', 'rotation', 'degree', 
                'target', 'reach', 'feedback', 'cursor', 'perturbation']
    for kw in keywords:
        count = methods_text.lower().count(kw)
        if count > 0:
            print(f'    - "{kw}": {count} occurrences')
else:
    print('✗ NO METHODS SECTION FOUND!')
    print(f'  Available sections: {list(result["sections"].keys())}')
    
    # Check if it's in a different section
    for section_name, section_text in result['sections'].items():
        if len(section_text) > 1000:  # Substantial section
            print(f'\n  Checking "{section_name}" ({len(section_text):,} chars)...')
            if 'participant' in section_text.lower() or 'subject' in section_text.lower():
                print(f'    → Found participant/subject mentions!')
                print(f'    Preview: {section_text[:300]}...')

# Compare with full text
print('\n4. FULL TEXT KEYWORD SEARCH')
print('-'*80)
full_text = result['full_text']
print(f'Full text length: {len(full_text):,} chars')
keywords = ['Materials and Methods', 'Materials & Methods', 'Methods', 
            'Participants', 'Subjects', 'Experimental Design']
for kw in keywords:
    if kw in full_text:
        idx = full_text.index(kw)
        print(f'✓ Found "{kw}" at position {idx:,}')
        print(f'  Context: ...{full_text[max(0,idx-50):idx+len(kw)+100]}...')
    else:
        print(f'✗ "{kw}" not found')

print('\n' + '='*80)
