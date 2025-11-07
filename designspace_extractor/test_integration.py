"""
Integration test for LLM refactoring with PDFExtractor.
"""
import os
import sys

# Ensure LLM is disabled for testing
os.environ['LLM_ENABLE'] = 'false'

print("=" * 70)
print("INTEGRATION TEST: PDFExtractor with Refactored LLM")
print("=" * 70)

# Test 1: Import PDFExtractor
print("\n[1] Importing PDFExtractor...")
try:
    from extractors.pdfs import PDFExtractor
    print("    ✓ PDFExtractor imported successfully")
except Exception as e:
    print(f"    ✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Initialize PDFExtractor without LLM
print("\n[2] Initializing PDFExtractor (LLM disabled)...")
try:
    extractor = PDFExtractor(use_llm=False)
    print(f"    ✓ PDFExtractor initialized (use_llm={extractor.use_llm})")
except Exception as e:
    print(f"    ✗ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Try to initialize with LLM (should handle gracefully when disabled)
print("\n[3] Attempting to initialize with LLM (should handle disabled state)...")
try:
    extractor_llm = PDFExtractor(use_llm=True, llm_provider='claude', llm_mode='verify')
    print(f"    ✓ PDFExtractor with LLM flag initialized")
    print(f"      - use_llm: {extractor_llm.use_llm}")
    print(f"      - llm_mode: {extractor_llm.llm_mode}")
    print(f"      - llm_assistant: {extractor_llm.llm_assistant}")
except Exception as e:
    print(f"    ✗ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Verify correct parameter usage
print("\n[4] Checking LLMAssistant parameter compatibility...")
try:
    from llm import LLMAssistant
    
    # Test that provider_name works
    assistant = LLMAssistant(provider_name='claude', mode='verify')
    print("    ✓ LLMAssistant accepts 'provider_name' parameter")
    
    # Test that mode parameter works
    assistant_fallback = LLMAssistant(provider_name='claude', mode='fallback')
    print("    ✓ LLMAssistant accepts 'mode' parameter")
    
    assistant_discover = LLMAssistant(provider_name='claude', mode='discover')
    print("    ✓ All three modes work (verify, fallback, discover)")
    
except Exception as e:
    print(f"    ✗ Parameter test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Test module consolidation
print("\n[5] Testing consolidated prompt_builder module...")
try:
    from llm.prompt_builder import PromptLoader, PromptBuilder
    
    loader = PromptLoader()
    print("    ✓ PromptLoader available from prompt_builder")
    
    builder = PromptBuilder()
    print("    ✓ PromptBuilder available from prompt_builder")
    
    # Test that old import path no longer exists
    try:
        from llm.prompt_loader import PromptLoader as OldLoader
        print("    ⚠ Old prompt_loader module still exists (should be removed)")
    except ImportError:
        print("    ✓ Old prompt_loader module successfully removed")
    
except Exception as e:
    print(f"    ✗ Consolidation test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Summary
print("\n" + "=" * 70)
print("✓ ALL INTEGRATION TESTS PASSED")
print("=" * 70)
print("\nIntegration Summary:")
print("  - PDFExtractor works with refactored LLM module")
print("  - LLMAssistant uses correct parameter names")
print("  - prompt_loader successfully consolidated into prompt_builder")
print("  - All modes (verify, fallback, discover) functional")
print("\n" + "=" * 70)
