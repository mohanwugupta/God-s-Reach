#!/usr/bin/env python3
"""
Cluster test script for Outlines structured generation integration.

This script is designed to run on the cluster where the Qwen2.5-72B model is available.
It tests:
1. Schema definitions are correct
2. Outlines library is available and working
3. Qwen72BProvider accepts schema parameter and generates valid JSON
4. All LLM engines (verification, discovery) pass schemas correctly
5. End-to-end integration with real model

Usage:
    python test_outlines_cluster.py

Requirements:
    - Qwen2.5-72B model downloaded and available
    - Outlines library installed (pip install outlines)
    - Sufficient GPU memory for model loading
"""
import sys
import os
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test 1: Verify all required modules can be imported."""
    logger.info("=" * 80)
    logger.info("TEST 1: Import Verification")
    logger.info("=" * 80)
    
    try:
        # Test Outlines availability
        try:
            import outlines
            logger.info(f"✓ Outlines library available (version: {outlines.__version__ if hasattr(outlines, '__version__') else 'unknown'})")
        except ImportError:
            logger.error("✗ Outlines library not available - this is REQUIRED for structured generation")
            logger.error("  Install with: pip install outlines")
            return False
        
        # Test schema imports
        from llm.schemas import (
            VERIFICATION_BATCH_SCHEMA,
            VERIFICATION_SINGLE_SCHEMA,
            MISSED_PARAMS_SCHEMA,
            NEW_PARAMS_SCHEMA
        )
        logger.info("✓ All schemas imported successfully")
        
        # Test provider imports
        from llm.providers import Qwen72BProvider, create_provider
        logger.info("✓ Provider classes imported successfully")
        
        # Test engine imports
        from llm.inference import VerificationEngine
        from llm.discovery import DiscoveryEngine
        logger.info("✓ Engine classes imported successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Import test failed: {e}")
        return False


def test_schema_structure():
    """Test 2: Verify JSON schemas have correct structure."""
    logger.info("=" * 80)
    logger.info("TEST 2: Schema Structure Validation")
    logger.info("=" * 80)
    
    try:
        from llm.schemas import (
            VERIFICATION_BATCH_SCHEMA,
            VERIFICATION_SINGLE_SCHEMA,
            MISSED_PARAMS_SCHEMA,
            NEW_PARAMS_SCHEMA
        )
        
        # Verify VERIFICATION_BATCH_SCHEMA
        assert "patternProperties" in VERIFICATION_BATCH_SCHEMA, "VERIFICATION_BATCH_SCHEMA missing patternProperties"
        assert ".*" in VERIFICATION_BATCH_SCHEMA["patternProperties"], "VERIFICATION_BATCH_SCHEMA missing .* pattern"
        logger.info("✓ VERIFICATION_BATCH_SCHEMA structure correct")
        
        # Verify VERIFICATION_SINGLE_SCHEMA
        assert "properties" in VERIFICATION_SINGLE_SCHEMA, "VERIFICATION_SINGLE_SCHEMA missing properties"
        assert "verified" in VERIFICATION_SINGLE_SCHEMA["properties"], "VERIFICATION_SINGLE_SCHEMA missing verified field"
        assert "confidence" in VERIFICATION_SINGLE_SCHEMA["properties"], "VERIFICATION_SINGLE_SCHEMA missing confidence field"
        logger.info("✓ VERIFICATION_SINGLE_SCHEMA structure correct")
        
        # Verify MISSED_PARAMS_SCHEMA
        assert "properties" in MISSED_PARAMS_SCHEMA, "MISSED_PARAMS_SCHEMA missing properties"
        assert "missed_parameters" in MISSED_PARAMS_SCHEMA["properties"], "MISSED_PARAMS_SCHEMA missing missed_parameters"
        logger.info("✓ MISSED_PARAMS_SCHEMA structure correct")
        
        # Verify NEW_PARAMS_SCHEMA
        assert "properties" in NEW_PARAMS_SCHEMA, "NEW_PARAMS_SCHEMA missing properties"
        assert "new_parameters" in NEW_PARAMS_SCHEMA["properties"], "NEW_PARAMS_SCHEMA missing new_parameters"
        logger.info("✓ NEW_PARAMS_SCHEMA structure correct")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Schema structure test failed: {e}")
        return False


def test_provider_initialization():
    """Test 3: Verify Qwen72BProvider can be initialized."""
    logger.info("=" * 80)
    logger.info("TEST 3: Provider Initialization")
    logger.info("=" * 80)
    
    try:
        from llm.providers import create_provider
        
        # Try to create Qwen72B provider
        logger.info("Attempting to create Qwen72B provider...")
        logger.info("NOTE: This will take several minutes as the model loads into GPU memory")
        
        provider = create_provider('qwen72b')
        
        if provider is None:
            logger.error("✗ Failed to create Qwen72B provider")
            logger.error("  Check that QWEN_MODEL_PATH is set correctly")
            logger.error("  Check that model files exist in the specified path")
            return False
        
        logger.info(f"✓ Qwen72B provider created successfully")
        logger.info(f"  Provider name: {provider.provider_name}")
        logger.info(f"  Model name/path: {provider.model_name}")
        
        # Verify provider has generate method with schema parameter
        import inspect
        sig = inspect.signature(provider.generate)
        params = sig.parameters
        
        if 'schema' not in params:
            logger.error("✗ Provider.generate() missing schema parameter")
            return False
        
        logger.info("✓ Provider.generate() has schema parameter")
        
        return provider
        
    except Exception as e:
        logger.error(f"✗ Provider initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_structured_generation(provider):
    """Test 4: Verify structured generation produces valid JSON."""
    logger.info("=" * 80)
    logger.info("TEST 4: Structured Generation with Schema")
    logger.info("=" * 80)
    
    try:
        from llm.schemas import VERIFICATION_SINGLE_SCHEMA
        
        # Simple test prompt
        test_prompt = """Given the following information:
Parameter: sample_size_n = 12
Context: "The study included 12 participants who completed the adaptation protocol."

Verify if this parameter extraction is correct. Respond in JSON format with:
- verified: true/false
- value: the extracted value
- confidence: 0.0 to 1.0
- evidence: quote from context
- reasoning: brief explanation
- abstained: true/false (if you cannot determine)
"""
        
        logger.info("Generating with VERIFICATION_SINGLE_SCHEMA...")
        logger.info("This tests that Outlines enforces JSON structure")
        
        response = provider.generate(
            prompt=test_prompt,
            max_tokens=256,
            temperature=0.0,
            schema=VERIFICATION_SINGLE_SCHEMA
        )
        
        if response is None:
            logger.error("✗ Provider returned None")
            return False
        
        logger.info(f"✓ Received response (length: {len(response)} chars)")
        
        # Try to parse as JSON
        try:
            parsed = json.loads(response)
            logger.info("✓ Response is valid JSON")
            
            # Verify required fields exist
            required_fields = ['verified', 'confidence', 'evidence', 'reasoning', 'abstained']
            missing_fields = [f for f in required_fields if f not in parsed]
            
            if missing_fields:
                logger.error(f"✗ Response missing required fields: {missing_fields}")
                logger.error(f"  Response: {response}")
                return False
            
            logger.info("✓ Response has all required fields")
            logger.info(f"  Sample response: {json.dumps(parsed, indent=2)[:200]}...")
            
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"✗ Response is not valid JSON: {e}")
            logger.error(f"  Response: {response[:500]}")
            return False
        
    except Exception as e:
        logger.error(f"✗ Structured generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_verification_schema(provider):
    """Test 5: Verify batch verification schema works."""
    logger.info("=" * 80)
    logger.info("TEST 5: Batch Verification Schema")
    logger.info("=" * 80)
    
    try:
        from llm.schemas import VERIFICATION_BATCH_SCHEMA
        
        test_prompt = """Verify the following extracted parameters:
1. sample_size_n = 12 (from "12 participants completed the study")
2. perturbation_class = "visual" (from "visual field perturbation was applied")

For each parameter, respond with:
- verified: true/false
- value: the value
- confidence: 0.0 to 1.0
- evidence: quote
- reasoning: explanation
- abstained: true/false

Return as JSON object with parameter names as keys.
"""
        
        logger.info("Generating with VERIFICATION_BATCH_SCHEMA...")
        
        response = provider.generate(
            prompt=test_prompt,
            max_tokens=512,
            temperature=0.0,
            schema=VERIFICATION_BATCH_SCHEMA
        )
        
        if response is None:
            logger.error("✗ Provider returned None")
            return False
        
        logger.info(f"✓ Received response (length: {len(response)} chars)")
        
        # Parse and validate
        try:
            parsed = json.loads(response)
            logger.info("✓ Response is valid JSON")
            
            # Should be a dict with parameter names as keys
            if not isinstance(parsed, dict):
                logger.error(f"✗ Response is not a dict: {type(parsed)}")
                return False
            
            logger.info(f"✓ Response is a dict with {len(parsed)} parameters")
            
            # Check one parameter has correct structure
            for param_name, param_data in list(parsed.items())[:1]:
                required_fields = ['verified', 'confidence', 'evidence', 'reasoning', 'abstained']
                missing = [f for f in required_fields if f not in param_data]
                
                if missing:
                    logger.error(f"✗ Parameter '{param_name}' missing fields: {missing}")
                    return False
                
                logger.info(f"✓ Parameter '{param_name}' has correct structure")
            
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"✗ Response is not valid JSON: {e}")
            logger.error(f"  Response: {response[:500]}")
            return False
        
    except Exception as e:
        logger.error(f"✗ Batch verification test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_missed_params_schema(provider):
    """Test 6: Verify missed parameters schema works."""
    logger.info("=" * 80)
    logger.info("TEST 6: Missed Parameters Schema")
    logger.info("=" * 80)
    
    try:
        from llm.schemas import MISSED_PARAMS_SCHEMA
        
        test_prompt = """From this text, find any motor adaptation parameters that were missed:
"Participants performed 100 reaching movements to visual targets. A 30-degree 
visuomotor rotation was applied unexpectedly after 20 baseline trials. The 
adaptation phase consisted of 60 trials with the rotation, followed by 20 
washout trials without rotation."

Already extracted: baseline_trials = 20

Find any other parameters mentioned. Return as JSON with "missed_parameters" array.
Each item should have: parameter_name, value, confidence, evidence, evidence_location.
"""
        
        logger.info("Generating with MISSED_PARAMS_SCHEMA...")
        
        response = provider.generate(
            prompt=test_prompt,
            max_tokens=512,
            temperature=0.0,
            schema=MISSED_PARAMS_SCHEMA
        )
        
        if response is None:
            logger.error("✗ Provider returned None")
            return False
        
        logger.info(f"✓ Received response (length: {len(response)} chars)")
        
        # Parse and validate
        try:
            parsed = json.loads(response)
            logger.info("✓ Response is valid JSON")
            
            if "missed_parameters" not in parsed:
                logger.error("✗ Response missing 'missed_parameters' key")
                return False
            
            logger.info(f"✓ Response has 'missed_parameters' array with {len(parsed['missed_parameters'])} items")
            
            # Check structure of first item
            if len(parsed['missed_parameters']) > 0:
                item = parsed['missed_parameters'][0]
                required = ['parameter_name', 'confidence', 'evidence', 'evidence_location']
                missing = [f for f in required if f not in item]
                
                if missing:
                    logger.error(f"✗ First item missing fields: {missing}")
                    return False
                
                logger.info(f"✓ First item has correct structure: {item['parameter_name']}")
            
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"✗ Response is not valid JSON: {e}")
            logger.error(f"  Response: {response[:500]}")
            return False
        
    except Exception as e:
        logger.error(f"✗ Missed parameters test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_engine_integration():
    """Test 7: Verify engines pass schemas to provider correctly."""
    logger.info("=" * 80)
    logger.info("TEST 7: Engine Integration")
    logger.info("=" * 80)
    
    try:
        # This test uses a mock provider to verify schemas are passed correctly
        from llm.inference import VerificationEngine
        from llm.discovery import DiscoveryEngine
        from llm.schemas import (
            VERIFICATION_BATCH_SCHEMA,
            VERIFICATION_SINGLE_SCHEMA,
            MISSED_PARAMS_SCHEMA,
            NEW_PARAMS_SCHEMA
        )
        
        # Mock provider that tracks schema usage
        class MockProvider:
            def __init__(self):
                self.provider_name = "mock"
                self.model_name = "mock-model"
                self.last_schema = None
            
            def generate(self, prompt, max_tokens=100, temperature=0.0, schema=None):
                self.last_schema = schema
                
                # Return appropriate mock JSON based on schema
                if schema == VERIFICATION_BATCH_SCHEMA:
                    return '{"param1": {"verified": true, "value": "test", "confidence": 0.8, "evidence": "test", "reasoning": "test", "abstained": false}}'
                elif schema == VERIFICATION_SINGLE_SCHEMA:
                    return '{"verified": true, "value": "test", "confidence": 0.8, "evidence": "test", "reasoning": "test", "abstained": false}'
                elif schema == MISSED_PARAMS_SCHEMA:
                    return '{"missed_parameters": [{"parameter_name": "test", "value": "test", "confidence": 0.8, "evidence": "test", "evidence_location": "test"}]}'
                elif schema == NEW_PARAMS_SCHEMA:
                    return '{"new_parameters": [{"parameter_name": "test", "description": "test", "category": "test", "evidence": "test", "evidence_location": "test"}]}'
                else:
                    return '{"result": "no schema provided"}'
        
        mock = MockProvider()
        
        # Test VerificationEngine passes schema for batch verification
        ver_engine = VerificationEngine(mock)
        ver_engine.verify_batch({'param1': 'value1'}, 'test context', 'between', 1)
        
        if mock.last_schema != VERIFICATION_BATCH_SCHEMA:
            logger.error("✗ VerificationEngine.verify_batch() did not pass VERIFICATION_BATCH_SCHEMA")
            return False
        logger.info("✓ VerificationEngine.verify_batch() passes correct schema")
        
        # Test VerificationEngine passes schema for single parameter
        ver_engine.infer_single('test_param', 'test context', 'test description')
        
        if mock.last_schema != VERIFICATION_SINGLE_SCHEMA:
            logger.error("✗ VerificationEngine.infer_single() did not pass VERIFICATION_SINGLE_SCHEMA")
            return False
        logger.info("✓ VerificationEngine.infer_single() passes correct schema")
        
        # Test VerificationEngine passes schema for missed params
        ver_engine.find_missed_library_params({'param1': 'desc1'}, {'param2': 'val2'}, 'test context')
        
        if mock.last_schema != MISSED_PARAMS_SCHEMA:
            logger.error("✗ VerificationEngine.find_missed_library_params() did not pass MISSED_PARAMS_SCHEMA")
            return False
        logger.info("✓ VerificationEngine.find_missed_library_params() passes correct schema")
        
        # Test DiscoveryEngine passes schema
        disc_engine = DiscoveryEngine(mock)
        disc_engine.discover_parameters('test context', {'param1': 'desc1'}, {'param2': 'val2'})
        
        if mock.last_schema != NEW_PARAMS_SCHEMA:
            logger.error("✗ DiscoveryEngine.discover_parameters() did not pass NEW_PARAMS_SCHEMA")
            return False
        logger.info("✓ DiscoveryEngine.discover_parameters() passes correct schema")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Engine integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all cluster tests."""
    logger.info("=" * 80)
    logger.info("OUTLINES STRUCTURED GENERATION - CLUSTER TEST SUITE")
    logger.info("=" * 80)
    logger.info("")
    
    results = {}
    
    # Test 1: Imports
    results['imports'] = test_imports()
    if not results['imports']:
        logger.error("\n❌ CRITICAL: Import test failed. Cannot continue.")
        logger.error("Please install required dependencies and ensure model is available.")
        return False
    
    # Test 2: Schema structure
    results['schemas'] = test_schema_structure()
    
    # Test 3: Provider initialization (this takes time)
    provider = test_provider_initialization()
    results['provider_init'] = provider is not None
    
    if not results['provider_init']:
        logger.warning("\n⚠️  Provider initialization failed. Skipping provider-dependent tests.")
        logger.warning("This may be due to:")
        logger.warning("  - Model not downloaded or incorrect path")
        logger.warning("  - Insufficient GPU memory")
        logger.warning("  - QWEN_MODEL_PATH environment variable not set")
    else:
        # Tests 4-6: Provider-dependent tests
        results['single_schema'] = test_structured_generation(provider)
        results['batch_schema'] = test_batch_verification_schema(provider)
        results['missed_params_schema'] = test_missed_params_schema(provider)
    
    # Test 7: Engine integration (doesn't need real provider)
    results['engine_integration'] = test_engine_integration()
    
    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status:8} - {test_name}")
    
    logger.info("")
    logger.info(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("")
        logger.info("🎉 ALL TESTS PASSED! 🎉")
        logger.info("Outlines structured generation is working correctly on this cluster.")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Run single paper extraction: python -m designspace_extractor --test-single-paper --model qwen72b")
        logger.info("2. Submit batch job with SLURM to test at scale")
        logger.info("3. Monitor extraction logs for absence of JSON parsing errors")
        return True
    else:
        logger.error("")
        logger.error("❌ SOME TESTS FAILED")
        logger.error("Please review the errors above and fix issues before deploying.")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
