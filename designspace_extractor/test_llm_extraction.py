#!/usr/bin/env python3
"""
Quick test to verify LLM-assisted extraction is working.
Tests on a single paper to see LLM invocation.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from extractors.pdfs import PDFExtractor


def main():
    print("="*80)
    print("LLM EXTRACTION TEST")
    print("="*80)
    
    # Check environment
    llm_enable = os.getenv('LLM_ENABLE', 'false')
    llm_provider = os.getenv('LLM_PROVIDER', 'qwen')
    model_path = os.getenv('QWEN_MODEL_PATH', '')
    
    print(f"\n📋 Environment:")
    print(f"   LLM_ENABLE: {llm_enable}")
    print(f"   LLM_PROVIDER: {llm_provider}")
    print(f"   QWEN_MODEL_PATH: {model_path}")
    print(f"   Model exists: {Path(model_path).exists() if model_path else 'N/A'}")
    
    # Initialize extractor with LLM
    use_llm = llm_enable.lower() in ('true', '1', 'yes')
    
    print(f"\n🔧 Initializing PDFExtractor with use_llm={use_llm}")
    extractor = PDFExtractor(use_llm=use_llm, llm_provider=llm_provider)
    
    print(f"   Extractor.use_llm: {extractor.use_llm}")
    print(f"   Extractor.llm_assistant: {extractor.llm_assistant}")
    if extractor.llm_assistant:
        print(f"   LLM enabled: {extractor.llm_assistant.enabled}")
    
    # Test on a single paper
    papers_dir = Path(__file__).parent.parent / 'papers'
    pdf_files = sorted(papers_dir.glob('*.pdf'))
    
    if not pdf_files:
        print("\n❌ No PDF files found in papers directory")
        return
    
    # Use Taylor 2012 - it has low F1 scores
    test_paper = None
    for pdf in pdf_files:
        if 'Taylor' in pdf.name and '2012' in pdf.name:
            test_paper = pdf
            break
    
    if not test_paper:
        test_paper = pdf_files[0]  # Fallback to first paper
    
    print(f"\n📄 Testing on: {test_paper.name}")
    print("\n" + "="*80)
    
    # Extract with LLM
    result = extractor.extract_from_file(test_paper, detect_multi_experiment=True)
    
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    
    # Check if LLM was used
    experiments = result.get('experiments', [result])
    for i, exp in enumerate(experiments, 1):
        metadata = exp.get('metadata', {})
        llm_used = metadata.get('llm_used', False)
        
        print(f"\nExperiment {i}:")
        print(f"   LLM used: {llm_used}")
        
        # Check for LLM-assisted parameters
        params = exp.get('parameters', {})
        llm_params = {k: v for k, v in params.items() if v.get('method') == 'llm_assisted'}
        
        print(f"   Total parameters: {len(params)}")
        print(f"   LLM-assisted parameters: {len(llm_params)}")
        
        if llm_params:
            print(f"\n   LLM-inferred values:")
            for param, data in llm_params.items():
                print(f"      • {param} = {data['value']} (confidence: {data.get('confidence', 0):.2f})")
        else:
            # Show low-confidence parameters that could use LLM
            low_conf = {k: v for k, v in params.items() if v.get('confidence', 1.0) < 0.3}
            if low_conf:
                print(f"\n   Low-confidence parameters (< 0.3) that could benefit from LLM:")
                for param, data in sorted(low_conf.items(), key=lambda x: x[1].get('confidence', 0)):
                    print(f"      • {param}: confidence={data.get('confidence', 0):.2f}, value={data.get('value', 'None')}")
    
    print("\n✅ Test complete!")


if __name__ == '__main__':
    main()
