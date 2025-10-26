#!/usr/bin/env python3
"""Test enhanced fuzzy matching capabilities."""

import sys
sys.path.insert(0, '.')

from validation.validator_public import fuzzy_match, values_are_synonyms

# Test cases: (gold_value, auto_value, param_name, should_match)
test_cases = [
    # Exact matches
    ("horizontal", "horizontal", "coordinate_frame", True),
    ("continuous", "continuous", "feedback_type", True),
    
    # Typo tolerance
    ("horizontal", "horiztonal", "coordinate_frame", True),
    ("continuous", "continous", "feedback_type", True),
    
    # Abbreviations
    ("counterclockwise", "CCW", "perturbation_direction", True),
    ("visuomotor rotation", "vmr", "perturbation_class", True),
    
    # Synonyms
    ("endpoint_only", "endpoint", "feedback_type", True),
    ("endpoint_only", "terminal feedback", "feedback_type", True),
    ("error_clamped", "clamped", "feedback_type", True),
    ("error_clamped", "error clamp", "feedback_type", True),
    
    # Multi-value fields
    ("endpoint, continuous", "endpoint_only, continuous", "feedback_type", True),
    ("endpoint, clamped, continous", "error clamp", "feedback_type", True),
    
    # Numeric tolerance
    ("45", "45.0", "perturbation_magnitude", True),
    ("30°", "30", "perturbation_magnitude", True),
    ("1.5s", "1.5", "feedback_delay", True),
    
    # Word-based matching
    ("aim_report", "reported aiming direction", "instruction_awareness", True),
    ("visuomotor_rotation", "visuomotor rotation", "perturbation_class", True),
    
    # Should NOT match
    ("abrupt", "gradual", "perturbation_schedule", False),
    ("endpoint_only", "continuous", "feedback_type", False),
    ("45", "90", "perturbation_magnitude", False),
]

def run_tests():
    """Run all fuzzy matching test cases."""
    print("=" * 80)
    print("FUZZY MATCHING TEST SUITE")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for gold, auto, param, expected in test_cases:
        result = fuzzy_match(gold, auto, param)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status}")
        print(f"  Gold: '{gold}'")
        print(f"  Auto: '{auto}'")
        print(f"  Param: {param}")
        print(f"  Expected: {expected}, Got: {result}")
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return failed == 0

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
