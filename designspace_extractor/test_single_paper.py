#!/usr/bin/env python3
"""
Test single paper extraction with simplified prompts
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from extractors.pdfs import PDFExtractor

def test_single_paper():
    """Test extraction on a single paper to verify prompt improvements."""

    # Use a small paper for testing
    pdf_path = Path("../papers/Taylor and Ivry - 2012 - The role of strategies in motor learning.pdf")

    if not pdf_path.exists():
        print(f"❌ Test paper not found: {pdf_path}")
        return

    print(f"🧪 Testing single paper extraction: {pdf_path.name}")
    print("   Using simplified JSON prompts...")

    try:
        # Initialize extractor with LLM enabled
        extractor = PDFExtractor(use_llm=True, llm_provider='qwen')

        # Process the paper
        result = extractor.extract_from_file(pdf_path, detect_multi_experiment=True)

        # Check results
        experiments = result.get('experiments', [result])
        num_experiments = len(experiments)

        print(f"✅ SUCCESS: {num_experiments} experiment(s) extracted")

        for i, exp in enumerate(experiments):
            params = exp.get('parameters', {})
            print(f"   Experiment {i+1}: {len(params)} parameters")

        print("🎉 Test completed successfully - no JSON parsing crashes!")

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_single_paper()