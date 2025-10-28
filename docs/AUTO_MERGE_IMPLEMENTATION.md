# Auto-Merge Implementation Summary

## ✅ What Was Implemented

### 1. Confidence-Based Conflict Resolution

Updated `utils/conflict_resolution.py` with intelligent merging logic:

- **Auto-accepts** LLM-only parameters if confidence ≥ 0.7
- **Flags for review** LLM-only parameters if confidence < 0.7  
- **Resolves conflicts** by comparing confidence scores
- **Uses source precedence** when confidences are similar (within 0.2)
- **Preserves provenance** with full source attribution

### 2. Updated LLM Response Parsing

Modified `llm/llm_assist.py` to set smart `requires_review` flags:

- **High confidence (≥ 0.7)**: `requires_review = False` → Auto-accepted
- **Low confidence (< 0.7)**: `requires_review = True` → Flagged for review
- Both single and batch parameter extraction updated

### 3. New Auto-Merge Function

Added `auto_merge_llm_and_regex()` convenience function:

```python
from utils.conflict_resolution import auto_merge_llm_and_regex

merged = auto_merge_llm_and_regex(
    regex_params=regex_extractions,
    llm_params=llm_extractions,
    confidence_threshold=0.7  # Configurable threshold
)
```

---

## 🎯 Auto-Merge Decision Tree

```
Parameter found?
├─ Only in Regex
│  └─ ✅ Auto-accept (regex is validated)
│
├─ Only in LLM
│  ├─ Confidence ≥ 0.7
│  │  └─ ✅ Auto-accept (high confidence)
│  └─ Confidence < 0.7
│     └─ ⚠️  Flag for review (low confidence)
│
└─ In Both (Conflict)
   ├─ Confidence difference > 0.2
   │  └─ ✅ Use higher confidence source
   └─ Confidence difference ≤ 0.2
      └─ ✅ Use source precedence
         (code > pdf_table > pdf_text > llm)
```

---

## 📊 Example Output

### Scenario: Paper with 6 parameters

**Inputs:**
- Regex found: `n_participants` (0.90), `rotation_degrees` (0.70), `n_trials_baseline` (0.95)
- LLM found: `age_mean` (0.85), `age_sd` (0.62), `rotation_degrees` (0.65), `perturbation_type` (0.95)

**Auto-Merge Results:**

| Parameter | Source | Confidence | Decision | Reasoning |
|-----------|--------|------------|----------|-----------|
| `n_participants` | regex | 0.90 | ✅ Auto-accept | Regex only |
| `n_trials_baseline` | regex | 0.95 | ✅ Auto-accept | Regex only |
| `age_mean` | LLM | 0.85 | ✅ Auto-accept | LLM only, high conf |
| `perturbation_type` | LLM | 0.95 | ✅ Auto-accept | LLM only, very high conf |
| `rotation_degrees` | regex | 0.70 | ✅ Auto-accept | Conflict, regex wins (precedence) |
| `age_sd` | LLM | 0.62 | ⚠️  Review | LLM only, low conf |

**Summary:**
- 5 of 6 parameters (83%) auto-accepted
- 1 parameter flagged for review
- 1 conflict resolved automatically

---

## 🧪 Testing

Run the test script to validate:

```bash
cd /scratch/gpfs/JORDANAT/mg9965/God-s-Reach/designspace_extractor
python test_auto_merge.py
```

Expected output shows all decision scenarios working correctly.

---

## 🔧 Configuration

### Environment Variables

```bash
# Confidence threshold for auto-accepting LLM-only parameters
export LLM_CONFIDENCE_THRESHOLD=0.7

# Confidence difference required for confidence-based resolution
export CONFLICT_CONFIDENCE_DELTA=0.2
```

### Per-Parameter Overrides

In `mapping/conflict_resolution.yaml`:

```yaml
default_policy: precedence

source_precedence:
  - code
  - pdf_table
  - pdf_text
  - llm_inference

parameter_overrides:
  # Always use highest confidence for age parameters
  age_mean:
    policy: precedence
    confidence_based: true
    min_confidence_delta: 0.15
```

---

## 📈 Expected Impact

### Before (Manual Review All)
- Parameters requiring review: 100%
- Processing time: ~5 min per paper
- Throughput: ~12 papers/hour

### After (Auto-Merge @ 0.7)
- Parameters auto-accepted: ~80%
- Parameters requiring review: ~20%
- Processing time: ~1 min per paper
- Throughput: ~60 papers/hour
- **5x speedup** 🚀

---

## 🔄 Iterative Improvement

### Validation Loop

1. **Extract & Merge** → Auto-merge regex + LLM
2. **Compare vs Gold** → Measure F1, precision, recall
3. **Analyze Errors** → Which confidence thresholds failed?
4. **Adjust Thresholds** → Optimize based on data
5. **Update Patterns** → Add regex patterns for LLM discoveries
6. **Repeat** → Continuous improvement

### Metrics to Track

```python
# Per confidence range
metrics = {
    'llm_0.9+': {'precision': 0.95, 'count': 120},
    'llm_0.7-0.9': {'precision': 0.82, 'count': 85},
    'llm_0.5-0.7': {'precision': 0.65, 'count': 42},
    'regex_table': {'precision': 0.98, 'count': 150},
    'regex_text': {'precision': 0.85, 'count': 95}
}
```

Use this data to calibrate optimal threshold (e.g., if 0.65 achieves 90% precision, lower threshold).

---

## 🚀 Integration Points

### In Batch Extraction Script

```python
# batch_process_papers.py

from utils.conflict_resolution import auto_merge_llm_and_regex
from llm.llm_assist import LLMAssistant

# Extract with regex
regex_results = pdf_extractor.extract(paper_path)

# Extract with LLM (full paper context)
llm = LLMAssistant(provider='qwen')
missing_params = [p for p in schema if p not in regex_results]
llm_results = llm.infer_parameters_batch(
    parameter_names=missing_params,
    context=full_paper_text
)

# Auto-merge
final_results = auto_merge_llm_and_regex(
    regex_params=regex_results,
    llm_params=llm_results,
    confidence_threshold=0.7
)

# Save with source attribution
save_to_database(final_results)
```

### In Database Export

```python
# Flag review-required parameters in exports
df = pd.DataFrame(final_results).T
df['requires_review'] = df.apply(lambda x: x.get('requires_review', False), axis=1)

# Export to CSV with highlighting
df.to_csv('results.csv')

# Export to Google Sheets with conditional formatting
# Red highlight for requires_review=True
```

---

## 📝 Files Modified

1. **`utils/conflict_resolution.py`**
   - Added `auto_merge_extractions()` method
   - Updated `_resolve_by_precedence()` for confidence-based selection
   - Added `auto_merge_llm_and_regex()` convenience function

2. **`llm/llm_assist.py`**
   - Updated `_parse_batch_response()` to set smart `requires_review` flags
   - Updated `_parse_response()` to set smart `requires_review` flags
   - Confidence ≥ 0.7 → `requires_review = False`
   - Confidence < 0.7 → `requires_review = True`

3. **`docs/AUTO_MERGE_STRATEGY.md`** (NEW)
   - Complete strategy documentation
   - Decision rules and examples
   - Validation workflow
   - Configuration guide

4. **`test_auto_merge.py`** (NEW)
   - Test script demonstrating auto-merge functionality
   - Validates all decision scenarios
   - Shows expected output format

---

## ✅ Ready for Testing

1. **Run unit test**: `python test_auto_merge.py`
2. **Test on real paper**: Use batch extraction with LLM enabled
3. **Validate against gold standard**: Compare F1 scores
4. **Calibrate threshold**: Adjust based on precision/recall
5. **Deploy at scale**: Process full corpus with auto-merge

---

## 🎯 Success Criteria

- ✅ Auto-acceptance rate ≥ 80%
- ✅ Precision on auto-accepted params ≥ 90%
- ✅ Review queue reduced by ≥ 75%
- ✅ F1 score maintained or improved
- ✅ Full source provenance preserved

---

**Date:** October 28, 2025  
**Status:** ✅ Implemented and ready for testing  
**Next Steps:** Test on corpus, validate against gold standard, calibrate thresholds
