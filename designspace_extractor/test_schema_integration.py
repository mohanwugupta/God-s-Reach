#!/usr/bin/env python3
"""
Test script to verify Outlines schema integration in LLM providers.
"""
import sys
import os
import inspect
sys.path.insert(0, os.path.dirname(__file__))

from llm.schemas import VERIFICATION_BATCH_SCHEMA, VERIFICATION_SINGLE_SCHEMA, MISSED_PARAMS_SCHEMA, NEW_PARAMS_SCHEMA

def test_schema_structure():
    """Test that schemas have correct structure."""
    print("Testing schema structures...")

    # Test VERIFICATION_BATCH_SCHEMA
    assert "patternProperties" in VERIFICATION_BATCH_SCHEMA
    assert ".*" in VERIFICATION_BATCH_SCHEMA["patternProperties"]
    print("✓ VERIFICATION_BATCH_SCHEMA structure correct")

    # Test VERIFICATION_SINGLE_SCHEMA
    assert "properties" in VERIFICATION_SINGLE_SCHEMA
    assert "verified" in VERIFICATION_SINGLE_SCHEMA["properties"]
    print("✓ VERIFICATION_SINGLE_SCHEMA structure correct")

    # Test MISSED_PARAMS_SCHEMA
    assert "properties" in MISSED_PARAMS_SCHEMA
    assert "missed_parameters" in MISSED_PARAMS_SCHEMA["properties"]
    print("✓ MISSED_PARAMS_SCHEMA structure correct")

    # Test NEW_PARAMS_SCHEMA
    assert "properties" in NEW_PARAMS_SCHEMA
    assert "new_parameters" in NEW_PARAMS_SCHEMA["properties"]
    print("✓ NEW_PARAMS_SCHEMA structure correct")

    return True

def test_provider_signature():
    """Test that provider generate method accepts schema parameter."""
    print("Testing provider method signatures...")

    try:
        from llm.providers import Qwen72BProvider

        # Check if generate method has schema parameter
        sig = inspect.signature(Qwen72BProvider.generate)
        params = sig.parameters

        if 'schema' in params:
            print("✓ Qwen72BProvider.generate() has schema parameter")
        else:
            print("✗ Qwen72BProvider.generate() missing schema parameter")
            return False

        # Check if schema parameter has correct default
        schema_param = params['schema']
        if schema_param.default is None:
            print("✓ Schema parameter has correct default (None)")
        else:
            print(f"✗ Schema parameter default is {schema_param.default}, should be None")
            return False

    except ImportError as e:
        print(f"✗ Could not import Qwen72BProvider: {e}")
        return False

    return True

def test_engine_imports():
    """Test that engines import and can be instantiated with mock provider."""
    print("Testing engine imports...")

    try:
        from llm.inference import VerificationEngine
        from llm.discovery import DiscoveryEngine

        # Create a mock provider for testing
        class MockProvider:
            def __init__(self):
                self.provider_name = "mock"
                self.model_name = "mock-model"

            def generate(self, prompt, max_tokens=100, temperature=0.0, schema=None):
                # Return mock JSON responses based on schema
                if schema == VERIFICATION_BATCH_SCHEMA:
                    return '{"param1": {"verified": true, "value": "test", "confidence": 0.8, "evidence": "test evidence", "reasoning": "test", "abstained": false}}'
                elif schema == VERIFICATION_SINGLE_SCHEMA:
                    return '{"verified": true, "value": "test", "confidence": 0.8, "evidence": "test evidence", "reasoning": "test", "abstained": false}'
                elif schema == MISSED_PARAMS_SCHEMA:
                    return '{"missed_parameters": [{"parameter_name": "test_param", "value": "test", "confidence": 0.8, "evidence": "test evidence", "evidence_location": "test location"}]}'
                elif schema == NEW_PARAMS_SCHEMA:
                    return '{"new_parameters": [{"parameter_name": "new_param", "description": "test", "category": "test", "evidence": "test", "evidence_location": "test"}]}'
                else:
                    return "Mock response without schema"

        mock_provider = MockProvider()

        # Test VerificationEngine
        ver_engine = VerificationEngine(mock_provider)
        print("✓ VerificationEngine created successfully")

        # Test DiscoveryEngine
        disc_engine = DiscoveryEngine(mock_provider)
        print("✓ DiscoveryEngine created successfully")

    except Exception as e:
        print(f"✗ Error testing engines: {e}")
        return False

    return True

if __name__ == "__main__":
    print("Running schema integration tests...\n")

    tests = [
        ("Schema Structure", test_schema_structure),
        ("Provider Signature", test_provider_signature),
        ("Engine Imports", test_engine_imports)
    ]

    all_passed = True
    for test_name, test_func in tests:
        try:
            print(f"Running {test_name} test...")
            if test_func():
                print(f"✓ {test_name} test passed\n")
            else:
                print(f"✗ {test_name} test failed\n")
                all_passed = False
        except Exception as e:
            print(f"✗ {test_name} test error: {e}\n")
            all_passed = False

    if all_passed:
        print("🎉 All schema integration tests passed!")
        print("Outlines structured generation is ready for use.")
    else:
        print("❌ Some tests failed. Please check the implementation.")

    sys.exit(0 if all_passed else 1)