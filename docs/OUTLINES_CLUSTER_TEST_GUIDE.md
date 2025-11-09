# Outlines Structured Generation - Cluster Testing Guide

## Overview

This guide explains how to test the Outlines integration for structured JSON generation on your cluster. The integration fixes JSON parsing failures in Qwen2.5-72B batch extraction by enforcing schema compliance.

## What Was Implemented

### 1. **JSON Schemas** (`llm/schemas.py`)
   - `VERIFICATION_BATCH_SCHEMA`: For batch parameter verification
   - `VERIFICATION_SINGLE_SCHEMA`: For single parameter verification
   - `MISSED_PARAMS_SCHEMA`: For finding missed library parameters (Task 1)
   - `NEW_PARAMS_SCHEMA`: For discovering new parameters (Task 2)

### 2. **Provider Updates** (`llm/providers.py`)
   - Modified `Qwen72BProvider.generate()` to accept `schema` parameter
   - When schema provided, uses Outlines for structured JSON generation
   - Falls back to regular generation if Outlines unavailable or schema not provided
   - Returns valid JSON string that can be parsed without errors

### 3. **Engine Integration**
   - `VerificationEngine` (`llm/inference.py`): Passes schemas for verification tasks
   - `DiscoveryEngine` (`llm/discovery.py`): Passes schema for discovery tasks
   - All LLM calls now enforce JSON structure automatically

## Prerequisites

Before running tests on the cluster, ensure:

1. **Outlines library installed**:
   ```bash
   pip install outlines>=0.0.34
   ```

2. **Model available**: Qwen2.5-72B model downloaded and accessible
   - Path should be set in `QWEN_MODEL_PATH` environment variable
   - Or default path: `/scratch/gpfs/JORDANAT/mg9965/models/Qwen--Qwen2.5-72B-Instruct`

3. **GPU access**: At least 2 GPUs with sufficient memory for 72B model

4. **Dependencies installed**: All requirements from `requirements.txt`

## Running Tests on Cluster

### Step 1: Upload Code to Cluster

```bash
# From your local machine, sync code to cluster
rsync -avz --exclude='*.pyc' --exclude='__pycache__' \
    designspace_extractor/ username@cluster:/path/to/designspace_extractor/
```

### Step 2: Run Test Script

```bash
# SSH to cluster
ssh username@cluster

# Navigate to project directory
cd /path/to/designspace_extractor

# Activate Python environment (if using virtual env)
source venv/bin/activate

# Run the comprehensive test suite
python test_outlines_cluster.py
```

### Expected Output

The test script will:
1. ✅ Verify imports (Outlines, schemas, providers, engines)
2. ✅ Validate schema structures
3. ✅ Initialize Qwen72B provider (takes 2-3 minutes)
4. ✅ Test single parameter verification with schema
5. ✅ Test batch parameter verification with schema
6. ✅ Test missed parameters discovery with schema
7. ✅ Test engine integration (schema passing)

**Success looks like:**
```
================================================================================
TEST SUMMARY
================================================================================
✓ PASS   - imports
✓ PASS   - schemas
✓ PASS   - provider_init
✓ PASS   - single_schema
✓ PASS   - batch_schema
✓ PASS   - missed_params_schema
✓ PASS   - engine_integration

Results: 7/7 tests passed

🎉 ALL TESTS PASSED! 🎉
Outlines structured generation is working correctly on this cluster.
```

### Step 3: Test Single Paper Extraction

After cluster tests pass:

```bash
# Test on a single paper
python -m designspace_extractor --test-single-paper --model qwen72b --paper-id 1
```

**What to look for:**
- No "Expecting property name" JSON parsing errors
- Valid JSON responses from LLM
- Successful parameter extraction

### Step 4: Submit Batch Job

If single paper works, submit full batch extraction:

```bash
# Navigate to slurm directory
cd slurm

# Submit batch job (adjust as needed for your cluster)
sbatch batch_extract_qwen72b.slurm
```

**Monitor the job:**
```bash
# Check job status
squeue -u $USER

# Monitor logs (replace JOBID with actual job ID)
tail -f slurm-JOBID.out

# Check for JSON errors (should be zero)
grep "Expecting property name" slurm-*.out
```

## Troubleshooting

### Test 1 Fails: Import Error for Outlines

**Problem**: `Outlines library not available`

**Solution**:
```bash
pip install outlines>=0.0.34
# Or if using conda:
conda install -c conda-forge outlines
```

### Test 3 Fails: Provider Initialization

**Problem**: `Model path does not exist` or `Failed to load model`

**Solutions**:
1. Check model path:
   ```bash
   echo $QWEN_MODEL_PATH
   ls -la $QWEN_MODEL_PATH
   ```

2. Set correct path:
   ```bash
   export QWEN_MODEL_PATH=/path/to/Qwen2.5-72B-Instruct
   ```

3. Verify GPU availability:
   ```bash
   nvidia-smi
   ```

### Test 4-6 Fail: Structured Generation

**Problem**: Response is not valid JSON or missing fields

**Possible causes**:
1. Outlines version incompatibility - update to latest
2. Model compatibility issues - check Outlines docs
3. Schema definition errors - review `llm/schemas.py`

**Debug**:
```python
# Add this to test script for more details
import logging
logging.getLogger('outlines').setLevel(logging.DEBUG)
```

### Batch Job Fails with Memory Errors

**Problem**: `CUDA out of memory` during batch processing

**Solutions**:
1. Request more GPUs in SLURM script:
   ```bash
   #SBATCH --gres=gpu:4  # Increase from 2 to 4
   ```

2. Reduce batch size in extraction code

3. Use gradient checkpointing (if available)

## Validation Checklist

Before considering deployment successful:

- [ ] All 7 cluster tests pass
- [ ] Single paper extraction works without JSON errors
- [ ] Batch job completes without JSON parsing failures
- [ ] Extracted parameters have proper evidence and confidence scores
- [ ] No regression in extraction quality (F1 scores stable/improved)

## Key Files Modified

| File | Changes |
|------|---------|
| `llm/schemas.py` | ✨ New file with JSON schemas |
| `llm/providers.py` | 🔧 Added schema parameter to `Qwen72BProvider.generate()` |
| `llm/inference.py` | 🔧 Added schema imports and passing to provider |
| `llm/discovery.py` | 🔧 Added schema import and passing to provider |
| `requirements.txt` | 📦 Added `outlines>=0.0.34` |

## Performance Impact

**Expected changes:**
- ✅ **Elimination** of JSON parsing errors
- ✅ **Consistent** JSON structure in all responses
- ⚠️ **Slightly slower** generation (schema enforcement overhead ~5-10%)
- ✅ **No manual** JSON cleaning needed
- ✅ **Better** reliability for batch processing

## Next Steps After Successful Testing

1. **Monitor production runs**: Track JSON parsing error rates (should be 0%)
2. **Compare extraction quality**: Run gold standard evaluation
3. **Optimize schemas**: Refine if certain fields cause issues
4. **Extend to other providers**: Add schema support to DeepSeek if needed
5. **Document findings**: Update project docs with results

## Contact

If you encounter issues not covered here:
1. Check detailed error messages in test output
2. Review Outlines documentation: https://github.com/outlines-dev/outlines
3. Check provider logs for specific error details
