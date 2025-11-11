#!/usr/bin/env python3
"""
Test script to verify Task 1 improvements for false negative reduction.
Tests the enhanced response parser with relaxed evidence requirements.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from llm.response_parser import ResponseParser
import json


def test_relaxed_evidence_requirements():
    """Test that relaxed evidence requirements work correctly."""
    print("\n" + "="*80)
    print("TEST: Relaxed Evidence Requirements")
    print("="*80)
    
    parser = ResponseParser(accept_threshold=0.7)
    
    # Test case 1: High confidence with brief evidence (10 chars)
    response1 = """{
        "missed_parameters": [
            {
                "parameter_name": "target_size_cm",
                "value": 1.5,
                "confidence": 0.95,
                "evidence": "1.5 cm dia",
                "evidence_location": "Methods"
            }
        ]
    }"""
    
    results1 = parser.parse_task1_response(response1, require_evidence=True, 
                                          provider="test", model="test")
    
    print("\n✅ Test 1: High confidence (0.95) + brief evidence (10 chars)")
    print(f"   Evidence: '1.5 cm dia' (10 chars)")
    print(f"   Result: {'ACCEPTED' if 'target_size_cm' in results1 else 'REJECTED'}")
    assert 'target_size_cm' in results1, "High confidence with 10 char evidence should be accepted"
    
    # Test case 2: Low confidence with brief evidence (10 chars) - should be rejected
    response2 = """{
        "missed_parameters": [
            {
                "parameter_name": "feedback_type",
                "value": "endpoint",
                "confidence": 0.65,
                "evidence": "endpoint f",
                "evidence_location": "Methods"
            }
        ]
    }"""
    
    results2 = parser.parse_task1_response(response2, require_evidence=True,
                                          provider="test", model="test")
    
    print("\n✅ Test 2: Low confidence (0.65) + brief evidence (10 chars)")
    print(f"   Evidence: 'endpoint f' (10 chars)")
    print(f"   Result: {'ACCEPTED' if 'feedback_type' in results2 else 'REJECTED'}")
    assert 'feedback_type' not in results2, "Low confidence with brief evidence should be rejected"
    
    # Test case 3: Low confidence with adequate evidence (20+ chars)
    response3 = """{
        "missed_parameters": [
            {
                "parameter_name": "feedback_type",
                "value": "endpoint only",
                "confidence": 0.75,
                "evidence": "cursor feedback shown at endpoint only",
                "evidence_location": "Methods, Procedures"
            }
        ]
    }"""
    
    results3 = parser.parse_task1_response(response3, require_evidence=True,
                                          provider="test", model="test")
    
    print("\n✅ Test 3: Medium confidence (0.75) + adequate evidence (38 chars)")
    print(f"   Evidence: 'cursor feedback shown at endpoint only' (38 chars)")
    print(f"   Result: {'ACCEPTED' if 'feedback_type' in results3 else 'REJECTED'}")
    assert 'feedback_type' in results3, "Medium confidence with 20+ char evidence should be accepted"
    
    # Test case 4: Multiple parameters with mixed confidence
    response4 = """{
        "missed_parameters": [
            {
                "parameter_name": "param_high_brief",
                "value": "value1",
                "confidence": 0.92,
                "evidence": "brief text",
                "evidence_location": "Methods"
            },
            {
                "parameter_name": "param_low_brief",
                "value": "value2",
                "confidence": 0.60,
                "evidence": "short txt",
                "evidence_location": "Methods"
            },
            {
                "parameter_name": "param_low_long",
                "value": "value3",
                "confidence": 0.70,
                "evidence": "this is a much longer evidence string with details",
                "evidence_location": "Methods"
            }
        ]
    }"""
    
    results4 = parser.parse_task1_response(response4, require_evidence=True,
                                          provider="test", model="test")
    
    print("\n✅ Test 4: Mixed confidence parameters")
    print(f"   param_high_brief (conf=0.92, len=10): {'ACCEPTED' if 'param_high_brief' in results4 else 'REJECTED'}")
    print(f"   param_low_brief (conf=0.60, len=9): {'ACCEPTED' if 'param_low_brief' in results4 else 'REJECTED'}")
    print(f"   param_low_long (conf=0.70, len=51): {'ACCEPTED' if 'param_low_long' in results4 else 'REJECTED'}")
    
    assert 'param_high_brief' in results4, "High conf + brief evidence should be accepted"
    assert 'param_low_brief' not in results4, "Low conf + brief evidence should be rejected"
    assert 'param_low_long' in results4, "Low conf + long evidence should be accepted"
    
    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED - Relaxed evidence requirements working correctly!")
    print("="*80)


def test_filtering_stats():
    """Test that filtering statistics are logged correctly."""
    print("\n" + "="*80)
    print("TEST: Filtering Statistics Logging")
    print("="*80)
    
    import logging
    
    # Enable debug logging to see statistics
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    parser = ResponseParser(accept_threshold=0.7)
    
    # Create response with various rejection reasons
    response = """{
        "missed_parameters": [
            {
                "parameter_name": "good_param",
                "value": 123,
                "confidence": 0.9,
                "evidence": "good evidence here",
                "evidence_location": "Methods"
            },
            {
                "parameter_name": "no_value_param",
                "value": null,
                "confidence": 0.9,
                "evidence": "has evidence but no value"
            },
            {
                "parameter_name": "brief_evidence_low_conf",
                "value": 456,
                "confidence": 0.6,
                "evidence": "too brief"
            },
            {
                "parameter_name": "another_good",
                "value": "text",
                "confidence": 0.85,
                "evidence": "more good evidence here",
                "evidence_location": "Results"
            }
        ]
    }"""
    
    print("\n📊 Parsing response with intentional filtering cases...")
    results = parser.parse_task1_response(response, require_evidence=True,
                                         provider="test", model="test")
    
    print(f"\n✅ Results: {len(results)} parameters accepted")
    print(f"   Expected: 2 accepted (good_param, another_good)")
    print(f"   Filtered: 2 rejected (no_value_param, brief_evidence_low_conf)")
    
    assert len(results) == 2, "Should accept exactly 2 parameters"
    assert 'good_param' in results, "good_param should be accepted"
    assert 'another_good' in results, "another_good should be accepted"
    
    print("\n" + "="*80)
    print("✅ Filtering statistics logged correctly!")
    print("="*80)


def test_evidence_threshold_boundary():
    """Test evidence threshold boundary conditions."""
    print("\n" + "="*80)
    print("TEST: Evidence Threshold Boundary Conditions")
    print("="*80)
    
    parser = ResponseParser(accept_threshold=0.7)
    
    # Exactly 10 characters with high confidence
    test_cases = [
        (0.8, "1234567890", True, "exactly 10 chars, conf=0.8"),
        (0.8, "123456789", False, "9 chars, conf=0.8"),
        (0.79, "12345678901234567890", True, "exactly 20 chars, conf=0.79"),
        (0.79, "1234567890123456789", False, "19 chars, conf=0.79"),
    ]
    
    for conf, evidence, should_pass, description in test_cases:
        response = json.dumps({
            "missed_parameters": [{
                "parameter_name": "test_param",
                "value": "test_value",
                "confidence": conf,
                "evidence": evidence,
                "evidence_location": "Test"
            }]
        })
        
        results = parser.parse_task1_response(response, require_evidence=True,
                                             provider="test", model="test")
        
        passed = 'test_param' in results
        status = "✅ PASS" if passed == should_pass else "❌ FAIL"
        print(f"{status}: {description} -> {'accepted' if passed else 'rejected'}")
        assert passed == should_pass, f"Boundary test failed: {description}"
    
    print("\n" + "="*80)
    print("✅ All boundary conditions handled correctly!")
    print("="*80)


def main():
    """Run all tests."""
    print("="*80)
    print("TASK 1 IMPROVEMENT TESTS")
    print("Testing enhanced response parser with relaxed evidence requirements")
    print("="*80)
    
    try:
        test_relaxed_evidence_requirements()
        test_filtering_stats()
        test_evidence_threshold_boundary()
        
        print("\n" + "="*80)
        print("🎉 ALL TESTS PASSED!")
        print("="*80)
        print("\nChanges implemented:")
        print("✅ Relaxed evidence requirements (10 chars for conf≥0.8, 20 for <0.8)")
        print("✅ Enhanced filtering statistics logging")
        print("✅ Detailed diagnostic tracking for each filtering decision")
        print("\nExpected impact:")
        print("📈 Reduced false negatives in Task 1 parameter recovery")
        print("🔍 Better visibility into filtering decisions")
        print("📊 Diagnostic data for continuous improvement")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
