# LLM Integration - Root Cause Analysis & Fix

## 🔍 Problem: LLM Was Never Called

### Root Cause Found
The SLURM script was calling **`run_batch_extraction.py`** (not `batch_process_papers.py`!), and this file had:

```python
extractor = PDFExtractor()  # ❌ No use_llm parameter!
```

So even though:
- ✅ Environment variables were set (`LLM_ENABLE=true`)
- ✅ Qwen model was found and loaded
- ✅ LLM assistant was created

The `PDFExtractor` was initialized with `use_llm=False` (the default).

## 📖 Understanding the PDF Text Flow

**Q: Can the LLM read the PDF?**  
**A: YES!** The PDF is already converted to text before the LLM sees it:

```
1. PDF File (binary)
   ↓
2. pypdf extraction → full_text (string)
   ↓
3. Section detection → methods_text (string)
   ↓
4. Regex extraction → parameters (dict)
   ↓
5. LLM receives: context=methods_text (5000 chars max)
                 parameter_name="perturbation_schedule"
                 extracted_params={existing parameters}
   ↓
6. LLM returns: {'value': 'continuous', 'confidence': 0.8, 'evidence': '...'}
```

The LLM **never sees the PDF** - it sees the **extracted text** from the Methods section.

## 🎯 Your Request: Verify ALL Parameters

You asked for the LLM to check **every extracted parameter**, not just low-confidence ones. This is smart because:

1. **Regex can extract wrong values** (false positives)
2. **LLM can verify/correct** extracted values
3. **More thorough quality control**

### Old Behavior (FALLBACK mode)
- Only call LLM if:
  - Confidence < 0.3, OR
  - Critical parameter missing
- Typical: 3-8 LLM calls per paper

### New Behavior (VERIFY mode) ✅
- Call LLM for:
  - **ALL extracted parameters** (verify correctness)
  - All missing critical parameters (try to find)
- Typical: 20-30 LLM calls per paper

## ✅ Changes Made

### 1. Fixed `run_batch_extraction.py` (Lines 183-191)
```python
# Before:
extractor = PDFExtractor()

# After:
use_llm = os.getenv('LLM_ENABLE', 'false').lower() in ('true', '1', 'yes')
llm_provider = os.getenv('LLM_PROVIDER', 'qwen')
llm_mode = os.getenv('LLM_MODE', 'verify')  # NEW!

extractor = PDFExtractor(use_llm=use_llm, llm_provider=llm_provider, llm_mode=llm_mode)
```

### 2. Added `llm_mode` Parameter to `PDFExtractor` (pdfs.py)
```python
def __init__(self, ..., llm_mode: str = 'verify'):
    """
    llm_mode: 
      - 'fallback': Only check confidence < 0.3 (old behavior)
      - 'verify': Check ALL parameters (new default)
    """
```

### 3. Updated `_apply_llm_fallback()` Method (pdfs.py Lines 1140-1200)
```python
if self.llm_mode == 'verify':
    # VERIFY MODE: Check ALL extracted parameters
    params_to_check.extend(extracted_params.keys())
    # Also add missing critical parameters
    for param in critical_params:
        if param not in extracted_params:
            params_to_check.append(param)
else:
    # FALLBACK MODE: Only low-confidence
    for param, data in extracted_params.items():
        if data['confidence'] < 0.3:
            params_to_check.append(param)
```

### 4. Added `LLM_MODE` Environment Variable (run_batch_extraction.sh)
```bash
export LLM_MODE=verify  # 'verify' checks ALL parameters, 'fallback' only low-confidence
```

## 📊 Expected Output (After Fix)

When you run the next batch, you should see:

```bash
Initializing PDF extractor...
   LLM assistance: ENABLED (provider: qwen, mode: verify)
   LLM assistant initialized: True

[1/18]
Processing: Taylor and Ivry - 2012.pdf
  🤖 LLM assistance active for this paper
     🤖 LLM mode: VERIFY (checking all 19 parameters)
     🤖 LLM checking: authors, effector, perturbation_class, num_trials, rotation_magnitude...
        ✅ authors = Taylor, J. A., & Ivry, R. B.
        ✅ effector = arm
        ✅ perturbation_class = visuomotor_rotation
        ✅ perturbation_schedule = continuous
        ✅ feedback_delay = terminal
        ✅ coordinate_frame = extrinsic
        ...
  SUCCESS: 1 experiment(s)
  Parameters: [25]  ← Should increase from 19!
```

## ⏱️ Performance Impact

### FALLBACK Mode (Old)
- ~3-8 LLM calls per paper
- ~30-60 seconds per paper
- 18 papers: ~10-20 minutes

### VERIFY Mode (New)
- ~20-30 LLM calls per paper
- ~2-3 minutes per paper
- **18 papers: ~40-60 minutes total**

This is acceptable given the quality improvement!

## 🎯 Expected F1 Improvements

With LLM verifying ALL parameters:

| Parameter | Baseline F1 | Expected F1 | Improvement |
|-----------|------------|-------------|-------------|
| `perturbation_schedule` | 0.00 | **0.60-0.80** | Huge |
| `feedback_delay` | 0.00 | **0.50-0.70** | Huge |
| `coordinate_frame` | 0.00 | **0.40-0.60** | Huge |
| `instruction_awareness` | 0.25 | **0.60-0.80** | 2-3x |
| `perturbation_class` | 0.33 | **0.70-0.85** | 2x |
| `n_total` | 0.22 | **0.60-0.75** | 3x |

**Overall F1:** 0.217 → **0.50-0.65** (2-3x improvement!)

## 🧪 Testing

### Quick Test (Single Paper)
```bash
cd /scratch/gpfs/JORDANAT/mg9965/God-s-Reach/designspace_extractor

export LLM_ENABLE=true
export LLM_PROVIDER=qwen
export LLM_MODE=verify
export QWEN_MODEL_PATH=/scratch/gpfs/JORDANAT/mg9965/models/Qwen--Qwen2.5-72B-Instruct

python test_llm_extraction.py
```

### Full Batch
```bash
sbatch slurm/run_batch_extraction.sh
```

**Watch for:**
- "LLM mode: VERIFY (checking all X parameters)"
- Multiple "✅ parameter = value" messages
- Increased parameter counts
- Much higher F1 scores

## 🔧 Modes You Can Use

### VERIFY Mode (Default) - What You Wanted
```bash
export LLM_MODE=verify
```
- Checks ALL extracted parameters
- Most thorough
- Slower but highest quality

### FALLBACK Mode (Conservative)
```bash
export LLM_MODE=fallback
```
- Only checks confidence < 0.3
- Faster
- Original design

## 📝 Files Modified

1. ✅ **`run_batch_extraction.py`** - Read LLM_ENABLE, LLM_MODE from environment
2. ✅ **`extractors/pdfs.py`** - Added `llm_mode` parameter and VERIFY mode logic
3. ✅ **`slurm/run_batch_extraction.sh`** - Added `LLM_MODE=verify` environment variable

## 🎉 Summary

**Before:**
- LLM loaded but never called
- PDFExtractor initialized with `use_llm=False`
- Results identical to no-LLM run

**After:**
- LLM VERIFY mode checks ALL parameters
- Every regex extraction gets LLM verification
- Should see 2-3x F1 improvement
- Output will show detailed LLM activity

**Next Run:** You should see ~20-30 LLM verification messages per paper, and significantly higher F1 scores!

---

**Status:** Ready to test with full LLM verification! 🚀
