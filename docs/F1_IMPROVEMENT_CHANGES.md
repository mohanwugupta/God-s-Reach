# F1 Score Improvement - Comprehensive Context & Evidence Fixes

## Changes Implemented

### 1. Updated Verification Prompt (verify_batch.txt)
**Problem**: LLM only provided evidence when correcting parameters, causing verified parameters to be skipped
**Fix**: Updated prompt to **always require evidence** for verified parameters

```txt
INSTRUCTIONS:
1. For each parameter: scan context, verify value is correct
2. If value matches context → set "verified": true, provide concise evidence  # ← Always provide evidence
3. If value is WRONG → provide correct value + brief reasoning + concise evidence
4. If parameter NOT in context → set "abstained": true

OUTPUT:
"evidence": "concise quote or description supporting the value",  // ALWAYS required  # ← Key change
```

### 2. Expanded Context Coverage (extractors/pdfs.py)
**Problem**: Limited to Methods + Participants, missing parameters in other sections
**Fix**: Include Abstract, Introduction, Methods, Participants, Results, Discussion

```python
# New comprehensive context preparation:
1. Abstract (authors, year, DOI often here)
2. Introduction (background, outcomes, mechanisms)
3. Methods (primary parameter source)
4. Participants (sample sizes, demographics)
5. Results (outcomes, additional sample info)
6. Discussion (mechanisms, focus)
```

### 3. Increased Context Limits (prompt_builder.py)
**Problem**: 12K character limit too restrictive for comprehensive context
**Fix**: Increased batch limit from 12K → 25K characters

```python
base_limits = {
    'batch': 25000,     # Comprehensive verification (Abstract+Intro+Methods+Participants+Results+Discussion)
    'single': 15000,    # Expanded single parameter inference
}
```

## Expected Impact

### Before Fixes
- **F1: 0.184** (Precision: 0.236, Recall: 0.150)
- **Issue**: Hundreds of "No evidence provided" skips
- **Root Cause**: Evidence only required for corrections, limited context

### After Fixes
- **Higher Recall**: Verified parameters now have evidence → fewer skips
- **Higher Precision**: More context → better verification accuracy
- **Target F1**: 0.3-0.4 (significant improvement)

### Specific Parameter Improvements
- **authors/year/doi**: Now found in Abstract/Introduction
- **sample_size_n/n_total**: Found in Participants/Results
- **outcome_measures/primary_outcomes**: Found in Introduction/Results
- **mechanism_focus**: Found in Introduction/Discussion
- **age_mean/target_hit_criteria**: Found in Methods/Results

## Validation Plan

Run batch processing and check:
1. **Reduced "No evidence provided" warnings**
2. **Higher F1 score** (target: >0.3)
3. **Better parameter coverage** for previously missed parameters
4. **Improved precision** from comprehensive context

## Files Modified

1. `llm/prompts/verify_batch.txt` - Always require evidence
2. `extractors/pdfs.py` - Comprehensive context preparation
3. `prompt_builder.py` - Increased context limits

## Next Steps

Run the batch extraction:
```bash
sbatch slurm/batch_extract.sh
```

Monitor for:
- ✅ Fewer "No evidence provided" messages
- ✅ Higher F1 score in validation report
- ✅ Better coverage of parameters from all paper sections