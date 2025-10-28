# Auto-Merge Strategy for LLM and Regex Extractions

## 🎯 Goal
Maximize automation while maintaining quality by intelligently merging LLM and regex extractions based on confidence scores, with iterative validation against gold standard.

## 🔄 Workflow

### 1. Extraction Phase
```
Paper → Regex Extraction → Parameters A
     → LLM Extraction → Parameters B
```

### 2. Auto-Merge Phase
```
Parameters A + Parameters B → Conflict Resolution → Final Parameters
```

### 3. Validation Phase
```
Final Parameters → Compare vs Gold Standard → Update Confidence
```

---

## 📋 Auto-Merge Rules

### Rule 1: No Conflict (Parameter in Only One Source)
**Condition:** Parameter found by regex OR LLM, but not both

#### Regex Only
```python
# Always accept - regex patterns are validated
result = regex_value
result['auto_accepted'] = True
result['source'] = 'regex'
```

#### LLM Only
```python
if llm_confidence >= 0.7:
    # High confidence - auto-accept
    result = llm_value
    result['auto_accepted'] = True
    result['source'] = 'llm_inference'
else:
    # Low confidence - flag for review
    result = llm_value
    result['requires_review'] = True
    result['reason'] = f'Low confidence ({llm_confidence:.2f})'
    result['source'] = 'llm_inference'
```

### Rule 2: Conflict (Parameter in Both Sources)
**Condition:** Parameter found by both regex AND LLM

#### Strategy: Confidence-Based Selection
```python
if abs(regex_confidence - llm_confidence) > 0.2:
    # Significant confidence difference (>20%)
    # Use higher confidence source
    result = max(regex_value, llm_value, key=lambda x: x['confidence'])
    result['resolution_method'] = 'confidence_based'
    result['winning_confidence'] = result['confidence']
    result['alternative_value'] = other_value
else:
    # Similar confidence - use source precedence
    # Default order: code > pdf_table > pdf_text > llm_inference
    result = apply_source_precedence([regex_value, llm_value])
    result['resolution_method'] = 'source_precedence'
    result['alternative_value'] = other_value
```

---

## 🎚️ Confidence Thresholds

| Threshold | Meaning | Action |
|-----------|---------|--------|
| **≥ 0.9** | Very High | Auto-accept, trusted like regex |
| **0.7 - 0.9** | High | Auto-accept, mark source |
| **0.5 - 0.7** | Medium | Flag for review |
| **< 0.5** | Low | Flag for manual review |

### Confidence Sources

**Regex Extractions:**
- Direct match in code: 0.95
- PDF table extraction: 0.90
- PDF text with units: 0.85
- PDF text without units: 0.70
- Inferred from context: 0.60

**LLM Extractions:**
- Explicit value with quote: 0.90-0.95
- Clear statement: 0.80-0.90
- Inferred from context: 0.60-0.80
- Weak inference: 0.40-0.60
- Uncertain: < 0.40

---

## 💻 Implementation

### Usage Example

```python
from utils.conflict_resolution import auto_merge_llm_and_regex

# Extract with both methods
regex_params = pdf_extractor.extract(paper_pdf)
llm_params = llm_assistant.infer_parameters_batch(
    parameter_names=['n_participants', 'age_mean', 'rotation_degrees'],
    context=paper_text
)

# Auto-merge with confidence threshold
merged_params = auto_merge_llm_and_regex(
    regex_params=regex_params,
    llm_params=llm_params,
    confidence_threshold=0.7  # Only auto-accept LLM if conf ≥ 0.7
)

# Results include source attribution
for param, value in merged_params.items():
    print(f"{param}: {value['value']}")
    print(f"  Source: {value['source_type']}")
    print(f"  Confidence: {value['confidence']:.2f}")
    print(f"  Resolution: {value.get('resolution_method', 'direct')}")
    if value.get('alternative_value'):
        print(f"  Alternative: {value['alternative_value']}")
    if value.get('requires_review'):
        print(f"  ⚠️  REVIEW REQUIRED: {value.get('reason', 'Low confidence')}")
```

### Output Example

```
n_participants: 24
  Source: pdf_table
  Confidence: 0.90
  Resolution: direct
  
age_mean: 22.3
  Source: llm_inference
  Confidence: 0.85
  Resolution: direct
  Auto-accepted: True
  
rotation_degrees: 30
  Source: pdf_text
  Confidence: 0.88
  Resolution: confidence_based
  Winning confidence: 0.88
  Alternative: {'value': 25, 'source': 'llm_inference', 'confidence': 0.65}
  
age_sd: 3.2
  Source: llm_inference
  Confidence: 0.62
  Resolution: direct
  ⚠️  REVIEW REQUIRED: Low confidence (0.62)
```

---

## 📊 Validation Against Gold Standard

### Iterative Improvement Loop

```
1. Extract → 2. Auto-Merge → 3. Compare vs Gold → 4. Update Patterns
    ↑                                                       ↓
    └───────────────────────────────────────────────────────┘
```

### Validation Metrics

```python
from validation.validator import validate_against_gold_standard

# Compare merged results against gold standard
validation_report = validate_against_gold_standard(
    extracted=merged_params,
    gold_standard_file='gold_standard.json',
    study_id='3023'
)

# Metrics tracked:
# - F1 score overall
# - F1 per parameter
# - F1 per source type (regex vs llm)
# - Precision/recall by confidence threshold
# - False positive rate
# - False negative rate
```

### Confidence Calibration

Track confidence vs accuracy to calibrate thresholds:

```python
# After validation
calibration = {
    'llm_conf_0.9+': {'accuracy': 0.95, 'count': 12},
    'llm_conf_0.7-0.9': {'accuracy': 0.82, 'count': 18},
    'llm_conf_0.5-0.7': {'accuracy': 0.65, 'count': 8},
    'regex_table': {'accuracy': 0.98, 'count': 25},
    'regex_text': {'accuracy': 0.85, 'count': 15}
}

# Adjust thresholds based on observed accuracy
# If llm_conf_0.7+ has 95% accuracy, can lower threshold to 0.65
```

---

## 🔍 Review Workflow

### Parameters Flagged for Review

All parameters with `requires_review=True` are exported with annotations:

**In CSV:**
```csv
parameter,value,source,confidence,requires_review,reason,alternative_value
age_sd,3.2,llm_inference,0.62,TRUE,Low confidence (0.62),
n_blocks,8,llm_inference,0.55,TRUE,Low confidence (0.55),5 (regex:0.50)
```

**In Google Sheets:**
- Red highlighting for `requires_review=True`
- Comment bubbles with alternative values
- Validation dropdown: Accept / Reject / Modify

### Review Priority

1. **High Impact Parameters** (demographics, core design)
2. **Conflicting Values** with similar confidence
3. **Low Confidence** (< 0.7) LLM extractions
4. **Novel Parameters** discovered by LLM but not in schema

---

## 📈 Expected Improvements

### Baseline (Regex Only)
- Coverage: 60% of parameters
- Precision: 90%
- Recall: 60%
- F1: 0.72

### With LLM (No Auto-Merge)
- Coverage: 85% of parameters
- Precision: 75% (false positives from LLM)
- Recall: 85%
- F1: 0.80

### With Auto-Merge (Confidence ≥ 0.7)
- Coverage: 85% of parameters
- Precision: 88% (filtered low-confidence LLM)
- Recall: 85%
- F1: 0.86

### With Iterative Calibration (5+ rounds)
- Coverage: 90% of parameters
- Precision: 92%
- Recall: 90%
- F1: 0.91

---

## 🛠️ Configuration

### Environment Variables

```bash
# LLM confidence threshold for auto-accept (LLM-only params)
LLM_CONFIDENCE_THRESHOLD=0.7

# Confidence difference for conflict resolution
CONFLICT_CONFIDENCE_DELTA=0.2

# Source precedence (if confidences are similar)
SOURCE_PRECEDENCE=code,pdf_table,pdf_text,llm_inference
```

### Per-Parameter Overrides

In `mapping/conflict_resolution.yaml`:

```yaml
parameter_overrides:
  n_participants:
    # Always prefer regex for participant count
    policy: precedence
    source_precedence: [code, pdf_table, pdf_text, llm_inference]
  
  age_mean:
    # Use confidence-based resolution
    policy: confidence
    min_confidence_delta: 0.15
  
  perturbation_schedule:
    # Complex parameter - always require manual review
    policy: manual
```

---

## 🚀 Rollout Plan

### Phase 1: Conservative (Week 1)
- Threshold: 0.8 (very conservative)
- Auto-accept only very high confidence LLM
- Flag all conflicts for review

### Phase 2: Calibration (Weeks 2-3)
- Validate against gold standard
- Measure precision/recall by confidence
- Adjust threshold based on data

### Phase 3: Optimized (Week 4+)
- Threshold: 0.7 (optimized)
- Auto-resolve high-confidence conflicts
- Focus review on edge cases

### Phase 4: Continuous Improvement
- Track validation metrics
- Update regex patterns from LLM discoveries
- Refine confidence models
- Expand gold standard

---

## 📝 Logging & Auditing

All merge decisions are logged:

```json
{
  "timestamp": "2025-10-28T14:30:00",
  "study_id": "3023",
  "parameter": "age_mean",
  "sources": {
    "regex": {"value": 22.5, "confidence": 0.70, "source_type": "pdf_text"},
    "llm": {"value": 22.3, "confidence": 0.85, "source_type": "llm_inference"}
  },
  "resolution": {
    "method": "confidence_based",
    "selected_source": "llm",
    "final_value": 22.3,
    "confidence_delta": 0.15,
    "auto_accepted": true
  }
}
```

Saved to: `./out/logs/merge_decisions.jsonl`

---

## ✅ Success Criteria

1. **Automation Rate:** ≥ 80% of parameters auto-merged without review
2. **Precision:** ≥ 90% on auto-accepted parameters
3. **Coverage:** ≥ 85% of gold standard parameters extracted
4. **F1 Score:** ≥ 0.85 overall
5. **Review Efficiency:** < 20% of parameters require manual review

---

**Date:** October 28, 2025
**Status:** ✅ Implemented
**Next:** Test on corpus and calibrate confidence thresholds
