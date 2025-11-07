"""
Test script for refactored LLM modules.

Tests the modular structure without actually calling LLMs.
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules import correctly."""
    print("Testing imports...")
    
    try:
        from llm.base import ParameterProposal, LLMInferenceResult
        print("✓ base.py imports")
    except Exception as e:
        print(f"✗ base.py import failed: {e}")
        return False
    
    try:
        from llm.providers import create_provider, LLMProvider
        print("✓ providers.py imports")
    except Exception as e:
        print(f"✗ providers.py import failed: {e}")
        return False
    
    try:
        from llm.prompt_builder import PromptBuilder
        print("✓ prompt_builder.py imports")
    except Exception as e:
        print(f"✗ prompt_builder.py import failed: {e}")
        return False
    
    try:
        from llm.response_parser import ResponseParser
        print("✓ response_parser.py imports")
    except Exception as e:
        print(f"✗ response_parser.py import failed: {e}")
        return False
    
    try:
        from llm.inference import VerificationEngine
        print("✓ inference.py imports")
    except Exception as e:
        print(f"✗ inference.py import failed: {e}")
        return False
    
    try:
        from llm.discovery import DiscoveryEngine
        print("✓ discovery.py imports")
    except Exception as e:
        print(f"✗ discovery.py import failed: {e}")
        return False
    
    try:
        from llm.llm_assist_refactored import LLMAssistant
        print("✓ llm_assist_refactored.py imports")
    except Exception as e:
        print(f"✗ llm_assist_refactored.py import failed: {e}")
        return False
    
    return True


def test_dataclasses():
    """Test dataclass instantiation."""
    print("\nTesting dataclasses...")
    
    from llm.base import ParameterProposal, LLMInferenceResult
    
    try:
        proposal = ParameterProposal(
            parameter_name="test_param",
            description="Test parameter",
            category="task_design",
            evidence="This is evidence from the paper",
            evidence_location="Page 5",
            example_values=["value1", "value2"],
            units="ms",
            prevalence="high",
            importance="medium",
            mapping_suggestion="new",
            hed_hint=None,
            confidence=0.85
        )
        print(f"✓ ParameterProposal created: {proposal.parameter_name}")
        
        prop_dict = proposal.to_dict()
        print(f"✓ ParameterProposal.to_dict() works: {len(prop_dict)} fields")
        
    except Exception as e:
        print(f"✗ ParameterProposal failed: {e}")
        return False
    
    try:
        result = LLMInferenceResult(
            value="test_value",
            confidence=0.8,
            evidence="Evidence quote",
            evidence_location="Page 3",
            reasoning="Because X",
            llm_provider="claude",
            llm_model="claude-3-5-sonnet"
        )
        print(f"✓ LLMInferenceResult created: {result.value}")
        
        result_dict = result.to_dict()
        print(f"✓ LLMInferenceResult.to_dict() works: {len(result_dict)} fields")
        
    except Exception as e:
        print(f"✗ LLMInferenceResult failed: {e}")
        return False
    
    return True


def test_llm_assistant_disabled():
    """Test LLMAssistant with LLM disabled."""
    print("\nTesting LLMAssistant (disabled)...")
    
    # Ensure LLM is disabled
    os.environ['LLM_ENABLE'] = 'false'
    
    from llm.llm_assist_refactored import LLMAssistant
    
    try:
        assistant = LLMAssistant(provider_name='claude')
        print(f"✓ LLMAssistant created (enabled={assistant.enabled})")
        
        # Test should_verify gate
        should_run = assistant.should_verify(
            extracted_params={'param1': 'value1'},
            missing_params=['param2', 'param3']
        )
        print(f"✓ should_verify() works: {should_run}")
        
        # Test verify_and_infer (should return empty when disabled)
        results = assistant.verify_and_infer(
            extracted_params={'param1': 'value1'},
            missing_params=['param2'],
            context="Paper text",
            study_type="between",
            num_experiments=1
        )
        print(f"✓ verify_and_infer() works: {len(results)} results")
        
        # Test discover_new_parameters (should return empty when disabled)
        proposals = assistant.discover_new_parameters(
            context="Paper text",
            study_type="between",
            num_experiments=1
        )
        print(f"✓ discover_new_parameters() works: {len(proposals)} proposals")
        
    except Exception as e:
        print(f"✗ LLMAssistant failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("Testing Refactored LLM Modules")
    print("=" * 60)
    
    all_passed = True
    
    if not test_imports():
        all_passed = False
    
    if not test_dataclasses():
        all_passed = False
    
    if not test_llm_assistant_disabled():
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 60)
        sys.exit(1)
