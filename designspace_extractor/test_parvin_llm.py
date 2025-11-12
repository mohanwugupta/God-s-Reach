#!/usr/bin/env python3
"""
Test what the LLM is seeing for the Parvin paper.
"""
from pathlib import Path
from extractors.pdfs import PDFExtractor

# Initialize extractor WITHOUT LLM to see base extraction
print('='*80)
print('PARVIN PAPER - BASE EXTRACTION (NO LLM)')
print('='*80)

pdf_path = Path('../papers/Parvin et al. - 2018 - Credit Assignment in a Motor Decision Making Task Is Influenced by Agency and Not Sensory Prediction.pdf')

# Extract without LLM
extractor_no_llm = PDFExtractor(use_llm=False, preprocessor='pymupdf4llm')
result_no_llm = extractor_no_llm.extract_from_file(pdf_path, detect_multi_experiment=True)

print(f'\nExperiments found: {len(result_no_llm.get("experiments", [result_no_llm]))}')

for i, exp in enumerate(result_no_llm.get('experiments', [result_no_llm])):
    params = exp.get('parameters', {})
    print(f'\nExperiment {i+1}: {len(params)} parameters (NO LLM)')
    for key in sorted(params.keys()):
        value = params[key].get('value')
        method = params[key].get('method')
        confidence = params[key].get('confidence', 0)
        print(f'  - {key}: {value} (method={method}, conf={confidence:.2f})')

# Now check what text is being sent for LLM inference
print('\n' + '='*80)
print('TEXT BEING SENT TO LLM')
print('='*80)

# Get the text_data that would be sent to LLM
text_data = extractor_no_llm.extract_text(pdf_path)
sections = text_data.get('sections', {})

if 'methods' in sections:
    methods_text = sections['methods']
    print(f'\nMethods section for LLM: {len(methods_text):,} chars')
    print('\nFirst 1500 characters that LLM sees:')
    print('-'*80)
    print(methods_text[:1500])
    print('-'*80)
    
    # Check for specific parameters
    print('\nSearching for key information in Methods section:')
    
    # Sample size
    import re
    n_patterns = [
        r'(\d+)\s+participants?',
        r'n\s*=\s*(\d+)',
        r'sample\s+size[:\s]+(\d+)',
        r'(\d+)\s+right[- ]handed'
    ]
    for pattern in n_patterns:
        matches = re.findall(pattern, methods_text, re.IGNORECASE)
        if matches:
            print(f'  Sample size pattern "{pattern}": {matches[:3]}')
    
    # Rotation magnitude
    rot_patterns = [
        r'(\d+)[°\s]*(?:deg|degree)s?\s*(?:rotation|perturbation|visuomotor)',
        r'(?:rotation|perturbation)[:\s]+(\d+)[°\s]*(?:deg|degree)',
        r'rotated[:\s]+(\d+)[°\s]*(?:deg|degree)'
    ]
    for pattern in rot_patterns:
        matches = re.findall(pattern, methods_text, re.IGNORECASE)
        if matches:
            print(f'  Rotation pattern "{pattern[:40]}...": {matches[:3]}')
    
    # Number of trials
    trial_patterns = [
        r'(\d+)\s+trials?',
        r'trial[s\s]+(?:consisted|comprised)[:\s]+(\d+)',
        r'each\s+(?:block|phase|session)[:\s]+(\d+)\s+trials?'
    ]
    for pattern in trial_patterns:
        matches = re.findall(pattern, methods_text, re.IGNORECASE)
        if matches:
            print(f'  Trial pattern "{pattern[:40]}...": {matches[:3]}')

else:
    print('\n⚠️ NO METHODS SECTION AVAILABLE FOR LLM!')

print('\n' + '='*80)
