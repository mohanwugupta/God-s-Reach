# Task 1 Investigation and Fix Plan

## Problem Summary
Task 1 (LLM finding missed library parameters) has **0% recovery rate** - the LLM found ZERO parameters that regex missed, despite 169 parameters being in gold standard but not extracted.

## Investigation Findings

### 1. Code Flow Analysis ✅
- Task 1 is properly implemented in `llm/inference.py::find_missed_library_params()`
- It's called from `extractors/pdfs.py::_find_missed_parameters()` at line 1247
- Condition: `if use_llm and self.llm_assistant and self.llm_mode == 'verify'`
- Response parser has relaxed evidence requirements (5 chars for conf≥0.5)

### 2. Batch Results Analysis ❌
- All 18 papers show `"llm_used": true` in metadata
- **ZERO** parameters have `source_type: "llm_task1"` or `method: "llm_missed_params"`
- All parameters are `source_type: "library_extraction"` (regex only)

### 3. Top Failing Parameters
Based on diagnostic report:
1. `perturbation_schedule` - 18 failures
2. `perturbation_magnitude` - 17 failures  
3. `population_type` - 17 failures
4. `feedback_delay` - 14 failures
5. `age_mean` - 14 failures
6. `target_hit_criteria` - 13 failures
7. `environment` - 12 failures
8. `effector` - 12 failures

These are common,  straightforward parameters that should be easily found!

## Root Cause Hypotheses

### Hypothesis 1: LLM Returning Empty Arrays ⭐ **MOST LIKELY**
- LLM generates `{"missed_parameters": []}`  every time
- Reasons:
  - Context truncation (not enough paper text)
  - Prompt too conservative ("don't repeat")
  - LLM being overly cautious
  - Temperature 0.0 making it deterministically conservative

### Hypothesis 2: Response Parsing Issues
- JSON parsing failures (but logs would show this)
- Evidence filtering too strict (but we relaxed it to 5 chars)

### Hypothesis 3: Context Issues  
- Full text not being passed correctly
- Text cleaning removing critical information
- Paper structure confusing the LLM

## Comprehensive Fix Plan

### Fix 1: Enhanced Diagnostic Logging 🔍
**Location**: `llm/inference.py::find_missed_library_params()`

Add logging to capture:
- Full prompt being sent
- Raw LLM response (first 1000 chars)
- Parsed JSON structure
- Number of candidates before filtering

### Fix 2: Improve Prompt with Examples 📝
**Location**: `llm/prompts/task1_missed_params.txt`

Add:
- Explicit examples of the top failing parameters
- More encouraging language ("be thorough", "err on the side of inclusion")
- Clarify that brief evidence is OK for high confidence
- Add context about what regex typically misses

### Fix 3: Increase Temperature for Diversity 🎲
**Location**: `llm/inference.py::find_missed_library_params()`

Change from `temperature=0.0` to `temperature=0.3`:
- Allows more varied responses
- Reduces overly conservative behavior
- Still deterministic enough for consistency

### Fix 4: Add LLM Response Logging Utility 📊
**Location**: New file `llm/response_logger.py`

Create utility to:
- Log every Task 1 request/response pair
- Save to `task1_responses.jsonl` for analysis
- Include paper name, prompt, response, parsed results

### Fix 5: Fallback Retry Logic 🔄
**Location**: `extractors/pdfs.py::_find_missed_parameters()`

If Task 1 returns empty:
- Log warning with paper name
- Optionally retry with higher temperature (0.5)
- Track retry statistics

### Fix 6: Context Validation 📄
**Location**: `extractors/pdfs.py::_find_missed_parameters()`

Before calling Task 1:
- Log context length
- Warn if context <5000 chars (too short)
- Ensure Methods section is included

## Implementation Priority

### Phase 1: Diagnostics (Immediate) 🚨
1. ✅ Add logging to `find_missed_library_params()` to capture raw responses
2. ✅ Add response logger utility
3. ✅ Add context length validation

### Phase 2: Prompt Improvements (High Priority) 📈
1. ✅ Add examples of top failing parameters to prompt
2. ✅ Make language more encouraging
3. ✅ Clarify evidence requirements explicitly

### Phase 3: Algorithm Tuning (Medium Priority) ⚙️
1. ✅ Increase temperature to 0.3
2. ✅ Add retry logic for empty responses
3. ✅ Adjust confidence thresholds

### Phase 4: Testing & Validation (Final) ✅
1. ⏳ Re-run batch processing on cluster with fixes
2. ⏳ Run diagnostics to measure improvement
3. ⏳ Compare before/after recovery rates
4. ⏳ Target: >30% recovery rate (from 0%)

## Expected Outcomes

### Quantitative Targets
- **Current**: 0% Task 1 recovery rate (0/169 regex misses)
- **Target**: >30% Task 1 recovery rate (>50/169)
- **Stretch**: >50% recovery rate (>85/169)

### Qualitative Improvements
- Visibility into why LLM returns empty
- Data-driven prompt optimization
- Diagnostic tools for continuous improvement

## Files to Modify

1. `llm/inference.py` - Add logging, increase temperature
2. `llm/prompts/task1_missed_params.txt` - Add examples, improve language
3. `extractors/pdfs.py` - Add context validation, retry logic
4. `llm/response_logger.py` - NEW: Response logging utility

## Testing Strategy

1. **Local Test**: Run on 1-2 papers with enhanced logging
2. **Cluster Test**: Run full batch with fixes
3. **Diagnostic Analysis**: Use `task1_diagnostics.py` to measure improvement
4. **Iterative Refinement**: Adjust based on logged responses

---
**Status**: Plan Complete, Ready for Implementation
**Date**: 2024-11-11
**Expected Impact**: 0% → 30-50% Task 1 recovery rate
