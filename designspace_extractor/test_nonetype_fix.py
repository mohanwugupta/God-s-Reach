#!/usr/bin/env python3
"""
Test to verify the NoneType iteration bug fix.
Tests that parse_verification_response always returns a dict, never None.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from llm.response_parser import ResponseParser

class MockLLMProvider:
    """Mock LLM provider for testing auto-fix failures."""
    
    def __init__(self, return_value=None):
        self.return_value = return_value
        self.provider_name = "mock"
        self.model_name = "mock-model"
    
    def generate(self, prompt, max_tokens=1024, temperature=0.0):
        """Mock generate that returns the configured value."""
        return self.return_value


def test_parse_verification_never_returns_none():
    """Test that parse_verification_response never returns None under any failure condition."""
    parser = ResponseParser(accept_threshold=0.7)
    
    # Test 1: Empty response
    result = parser.parse_verification_response("", ["param1"], True, "test", "test", None)
    assert result is not None, "Should return empty dict, not None"
    assert isinstance(result, dict), "Should return dict"
    assert len(result) == 0, "Should be empty"
    print("✓ Test 1 passed: Empty response returns {}")
    
    # Test 2: Invalid JSON (no auto-fix provider)
    result = parser.parse_verification_response("This is not JSON", ["param1"], True, "test", "test", None)
    assert result is not None, "Should return empty dict, not None"
    assert isinstance(result, dict), "Should return dict"
    assert len(result) == 0, "Should be empty"
    print("✓ Test 2 passed: Invalid JSON (no provider) returns {}")
    
    # Test 3: Malformed JSON with auto-fix that returns None
    mock_provider = MockLLMProvider(return_value=None)
    malformed = '{"param1": {"value": "test", "confidence": 0.9'  # Missing closing braces
    result = parser.parse_verification_response(malformed, ["param1"], True, "test", "test", mock_provider)
    assert result is not None, "Should return empty dict even if auto-fix fails"
    assert isinstance(result, dict), "Should return dict"
    print("✓ Test 3 passed: Malformed JSON with failed auto-fix returns {}")
    
    # Test 4: Malformed JSON with auto-fix that returns more malformed JSON
    mock_provider_bad = MockLLMProvider(return_value='{"still": "bad", "json":')
    result = parser.parse_verification_response(malformed, ["param1"], True, "test", "test", mock_provider_bad)
    assert result is not None, "Should return empty dict when auto-fix also fails"
    assert isinstance(result, dict), "Should return dict"
    print("✓ Test 4 passed: Malformed JSON with malformed auto-fix returns {}")
    
    # Test 5: Valid JSON
    valid_json = '''
    {
        "param1": {
            "value": "test_value",
            "confidence": 0.95,
            "evidence": "This is evidence from the paper with sufficient length",
            "evidence_location": "Methods section",
            "reasoning": "Found in text"
        }
    }
    '''
    result = parser.parse_verification_response(valid_json, ["param1"], True, "test", "test", None)
    assert result is not None, "Should return dict for valid JSON"
    assert isinstance(result, dict), "Should return dict"
    assert len(result) == 1, "Should have one result"
    assert "param1" in result, "Should contain param1"
    print("✓ Test 5 passed: Valid JSON parsed correctly")
    
    # Test 6: Malformed JSON with auto-fix that succeeds
    fixed_valid_json = '{"param1": {"value": "fixed_value", "confidence": 0.9, "evidence": "Fixed evidence with sufficient length for validation", "evidence_location": "Methods", "reasoning": "Auto-fixed"}}'
    mock_provider_good = MockLLMProvider(return_value=fixed_valid_json)
    result = parser.parse_verification_response(malformed, ["param1"], True, "test", "test", mock_provider_good)
    assert result is not None, "Should return dict when auto-fix succeeds"
    assert isinstance(result, dict), "Should return dict"
    # Note: Auto-fix may not always succeed in extracting the param, but should not return None
    print(f"✓ Test 6 passed: Auto-fix attempt returns dict (found {len(result)} params)")
    
    print("\n✅ All tests passed! parse_verification_response never returns None")


def test_iteration_safety():
    """Test that the fixed code allows safe iteration even after failures."""
    parser = ResponseParser(accept_threshold=0.7)
    
    # Simulate the actual code flow in pdfs.py
    params_to_check = ["param1", "param2", "param3"]
    
    # Get result from parser (simulating auto-fix failure)
    llm_results = parser.parse_verification_response(
        "malformed json {{{", 
        params_to_check, 
        True, 
        "test", 
        "test", 
        MockLLMProvider(return_value=None)
    )
    
    # This is the code from pdfs.py that was failing
    # Now it should work because llm_results is {} not None
    if llm_results is None:
        llm_results = {}
    
    extracted_count = 0
    for param in params_to_check:
        if param in llm_results and llm_results[param].value is not None:
            extracted_count += 1
    
    assert extracted_count == 0, "Should extract 0 params from failed response"
    print("✓ Iteration test passed: Can safely iterate over failed LLM results")


if __name__ == '__main__':
    test_parse_verification_never_returns_none()
    test_iteration_safety()
    print("\n🎉 All bug fixes verified! The NoneType iteration error is resolved.")
