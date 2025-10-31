# Qwen Model Loading - Freeze/Hang Debugging Guide

## Problem

The LLM initialization freezes/hangs for 2+ hours without completing or showing errors.

## Root Causes Identified

1. **Model loading timeout** - `device_map="cuda:0"` can hang if CUDA has issues
2. **Corrupted model files** - Incomplete downloads cause silent hangs
3. **CUDA driver incompatibility** - PyTorch/CUDA version mismatch
4. **GPU memory fragmentation** - Previous processes left GPU in bad state

## 🔧 Quick Fix Steps

### Step 1: Run Diagnostic Script

**Option A: Using SLURM (Recommended for cluster)**
```bash
cd /scratch/gpfs/JORDANAT/mg9965/God-s-Reach

# Submit diagnostic job (completes in 5-15 min)
sbatch slurm/test_qwen_loading.sh

# Monitor progress
tail -f logs/qwen_diagnostic_*.out

# Check results when done
cat logs/qwen_diagnostic_*.out
```

**Option B: Interactive (for quick tests on login node)**
```bash
cd /scratch/gpfs/JORDANAT/mg9965/God-s-Reach/designspace_extractor

# Set model path
export QWEN_MODEL_PATH=/scratch/gpfs/JORDANAT/mg9965/models/Qwen--Qwen3-32B

# Run diagnostic (10-15 min max)
python test_qwen_loading.py
```

**What it does:**
- ✅ Checks model files exist and are complete
- ✅ Verifies CUDA is available
- ✅ Tests vLLM loading (5 min timeout)
- ✅ Tests transformers loading (10 min timeout)
- ✅ Runs quick inference test
- ❌ Times out and gives specific error if it hangs

### Step 2: Interpret Results

#### ✅ If diagnostic passes:
```
✅ DIAGNOSTIC COMPLETE - ALL TESTS PASSED
Your model is ready for extraction!
```
**Action:** Proceed with normal extraction.

#### ❌ If it hangs on "Loading tokenizer":
```
Step 4a: Loading tokenizer (timeout: 2 minutes)...
[HANGS HERE]
```
**Cause:** Corrupted tokenizer files or network issues
**Fix:**
```bash
# Re-download tokenizer files
cd /scratch/gpfs/JORDANAT/mg9965/models/Qwen--Qwen3-32B
rm tokenizer*.json
huggingface-cli download Qwen/Qwen3-32B --include "tokenizer*"
```

#### ❌ If it hangs on "Loading model":
```
Step 4b: Loading model (timeout: 10 minutes)...
[HANGS HERE FOR 10+ MIN, THEN TIMES OUT]
```
**Cause:** CUDA driver issue, GPU fragmentation, or device_map problem
**Fixes:**

**Option 1: Reset GPU**
```bash
# Kill stuck processes
pkill -9 python

# Check GPU status
nvidia-smi

# If stuck, reset GPU (requires sudo)
sudo nvidia-smi --gpu-reset
```

**Option 2: Try device_map='auto'**

Edit `llm/llm_assist.py` line ~148:
```python
# Change from:
device_map="cuda:0",

# To:
device_map="auto",
```

**Option 3: Use vLLM instead**
```bash
# Install vLLM (much more reliable)
pip install vllm

# vLLM will be used automatically
```

**Option 4: Verify CUDA compatibility**
```bash
# Check PyTorch CUDA version
python -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.version.cuda}')"

# Check system CUDA version
nvcc --version

# Should match! If not:
pip install torch --index-url https://download.pytorch.org/whl/cu121  # or cu118, etc.
```

#### ❌ If it shows "GPU Out of Memory":
```
❌ GPU Out of Memory
```
**Cause:** Not enough free GPU memory
**Fix:**
```bash
# Check what's using GPU
nvidia-smi

# Kill other processes
pkill -9 python

# Or reduce model memory allocation in llm_assist.py:
max_memory={0: "68GiB"}  # Instead of 72GiB
```

## 🚀 Enhanced Code Changes

The updated `llm/llm_assist.py` now includes:

1. **File validation** - Checks model files exist before loading
2. **Progressive logging** - Shows exactly where it's stuck
3. **Memory reporting** - Shows free GPU memory
4. **Better error messages** - Explains what went wrong
5. **Timeout handling** - In diagnostic script (signal-based)
6. **local_files_only** - Prevents network hangs

## 📊 Expected Loading Times

| Step | vLLM | Transformers |
|------|------|--------------|
| Model file check | < 1 sec | < 1 sec |
| Tokenizer load | 5-10 sec | 5-10 sec |
| Model load | 1-2 min | 3-5 min |
| Total | **1-2 min** | **3-5 min** |

**If it takes >10 minutes, something is wrong!**

## 🔍 Monitoring During Load

In another terminal:
```bash
# Watch GPU memory usage
watch -n 1 nvidia-smi

# Watch process
watch -n 1 'ps aux | grep python'
```

**Normal behavior:**
- GPU memory gradually increases from 0 → 64GB
- Process shows 100% CPU briefly, then goes to 0-5%
- Completes in 1-5 minutes

**Problem behavior:**
- GPU memory stuck at 0% or partial value
- Process shows 0% CPU (completely frozen)
- No progress after 10+ minutes

## 📝 Common Issues & Solutions

### Issue: "Model incomplete, missing: ['tokenizer.json']"
**Solution:**
```bash
cd $QWEN_MODEL_PATH
huggingface-cli download Qwen/Qwen3-32B --include "*.json"
```

### Issue: "CUDA not available"
**Solution:**
```bash
# Check CUDA setup
nvidia-smi
nvcc --version

# Reinstall PyTorch with CUDA
pip install torch --force-reinstall --index-url https://download.pytorch.org/whl/cu121
```

### Issue: Diagnostic passes but extraction still hangs
**Solution:**
- The hang is likely in PDFExtractor, not LLM loading
- Check `llm_enable` flag is being passed correctly
- Add debugging: `logger.info(f"LLM enabled: {llm.enabled}")`

### Issue: "Only XX GB free (need ~64GB)"
**Solution:**
```bash
# Free GPU memory
pkill -9 python
torch.cuda.empty_cache()

# Or use smaller batch size in extraction
```

## 🎯 Testing After Fix

Once diagnostic passes:

```bash
# Test single paper
cd /scratch/gpfs/JORDANAT/mg9965/God-s-Reach/designspace_extractor

export LLM_ENABLE=true
export LLM_PROVIDER=qwen
export QWEN_MODEL_PATH=/scratch/gpfs/JORDANAT/mg9965/models/Qwen--Qwen3-32B

python -m designspace_extractor extract \
    --pdf ../papers/test_paper.pdf \
    --llm-enable \
    --output test_results.json
```

**Expected:**
- Model loads in 1-5 minutes
- Extraction completes
- No hangs or timeouts

## 📞 If All Else Fails

1. **Use smaller model:**
   ```bash
   export QWEN_MODEL_PATH=/path/to/Qwen2.5-7B-Instruct
   ```

2. **Use API instead:**
   ```bash
   export LLM_ENABLE=true
   export LLM_PROVIDER=claude  # or openai
   export ANTHROPIC_API_KEY=your_key
   ```

3. **Skip LLM entirely:**
   ```bash
   export LLM_ENABLE=false
   # Use regex-only extraction
   ```

## 📚 Related Documentation

- `QWEN3_32B_MIGRATION.md` - Migration from 72B model
- `LLM_SETUP_GUIDE.md` - Full LLM setup guide
- `LLM_MEMORY_FIX.md` - Previous memory issues (72B-specific)
- `SLURM_CONFIGURATION.md` - Cluster job setup

---

**Last Updated:** October 31, 2025  
**Status:** Enhanced with timeout detection and diagnostics
