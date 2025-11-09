#!/usr/bin/env python3
"""
Quick test to verify the missed params bug fix.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from llm.response_parser import ResponseParser
from llm.base import LLMInferenceResult

def test_parse_task1_with_none():
    """Test that parse_task1_response never returns None."""
    parser = ResponseParser(accept_threshold=0.7)
    
    # Test 1: Empty response
    result = parser.parse_task1_response("", True, "test", "test")
    assert result is not None, "Should return empty dict, not None"
    assert isinstance(result, dict), "Should return dict"
    print("✓ Test 1 passed: Empty response returns {}")
    
    # Test 2: Invalid JSON
    result = parser.parse_task1_response("This is not JSON", True, "test", "test")
    assert result is not None, "Should return empty dict, not None"
    assert isinstance(result, dict), "Should return dict"
    print("✓ Test 2 passed: Invalid JSON returns {}")
    
    # Test 3: Malformed JSON
    result = parser.parse_task1_response('{"missed_parameters": [{"name":', True, "test", "test")
    assert result is not None, "Should return empty dict, not None"
    assert isinstance(result, dict), "Should return dict"
    print("✓ Test 3 passed: Malformed JSON returns {}")
    
    # Test 4: Valid but empty result
    result = parser.parse_task1_response('{"missed_parameters": []}', True, "test", "test")
    assert result is not None, "Should return empty dict, not None"
    assert isinstance(result, dict), "Should return dict"
    assert len(result) == 0, "Should be empty"
    print("✓ Test 4 passed: Empty array returns {}")
    
    # Test 5: Valid result
    valid_response = '''
    {
      "missed_parameters": [
        {
          "parameter_name": "sample_size_n",
          "value": 20,
          "confidence": 0.95,
          "evidence": "Twenty participants were recruited for this study",
          "evidence_location": "Methods, Participants"
        }
      ]
    }
    '''
    result = parser.parse_task1_response(valid_response, True, "test", "test")
    assert result is not None, "Should return dict, not None"
    assert isinstance(result, dict), "Should return dict"
    assert len(result) == 1, "Should have one result"
    assert 'sample_size_n' in result, "Should contain sample_size_n"
    assert isinstance(result['sample_size_n'], LLMInferenceResult), "Should be LLMInferenceResult"
    print("✓ Test 5 passed: Valid response parsed correctly")
    
    print("\n✅ All tests passed! parse_task1_response never returns None")

if __name__ == '__main__':
    test_parse_task1_with_none()
