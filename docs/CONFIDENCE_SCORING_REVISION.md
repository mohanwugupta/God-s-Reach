# Confidence Scoring for Regex Extractions - Analysis & Revision

## 🔍 Current System Analysis

### How Confidence is Currently Calculated

The current regex confidence scoring uses a **multi-factor model** based on:

1. **Base Confidence** (from `normalize_value()`)
2. **Section Multiplier** (where the match was found)
3. **Pattern Source** (schema patterns vs fallback patterns)

### Current Confidence Values

#### Base Confidence (Type-Based)
```python
# From normalize_value() in pdfs.py:
- Integer conversion: 0.9
- Float conversion: 0.9  
- Boolean conversion: 0.85
- Enum (exact match): 0.9
- Enum (fuzzy match): 0.6
- String (general): 0.75
- Fallback (error): 0.5
```

#### Section Multipliers
```python
# From extract_from_section() in pdfs.py:
- Methods section: × 1.0 (no change)
- Participants section: × 0.95
- Results section: × 0.7
- Other sections: × 0.8
```

#### Pattern Source Multipliers
```python
# Schema patterns (patterns.yaml): base confidence
# Common/fallback patterns: × 0.7 (30% penalty)
```

### Example Calculation

**Scenario:** Extract "30" for `rotation_degrees` from Methods section

```python
1. Pattern matches: "30°"
2. normalize_value('rotation_degrees', '30'):
   - Detected as integer → base_confidence = 0.9
3. Section adjustment (Methods): 0.9 × 1.0 = 0.9
4. Final confidence: 0.9
```

---

## ❌ Problems with Current System

### 1. **Arbitrary Multipliers**
The section multipliers (0.95, 0.7, 0.8) have no empirical justification. Why is Results 0.7 vs Methods 1.0?

### 2. **No Pattern Quality Assessment**
All patterns are treated equally regardless of:
- Specificity (e.g., "30 degrees" vs "30")
- Context keywords (e.g., "rotation of 30" vs just "30")
- Units presence ("30°" vs "30")

### 3. **Type-Based Confidence Too High**
A successful integer parse doesn't mean the value is correct:
- "30" could be rotation, participants, trials, age, etc.
- Type conversion confidence (0.9) is often higher than it should be

### 4. **No Match Quality Metrics**
Doesn't consider:
- Number of matches (1 match vs 10 matches)
- Match specificity (exact phrase vs loose pattern)
- Proximity to relevant keywords

### 5. **Section Detection is Unreliable**
PDF section headers vary widely. Misclassified sections lead to wrong multipliers.

---

## ✅ Proposed Revision: Evidence-Based Confidence

### New Multi-Factor Model

```python
confidence = base × pattern_quality × context_quality × uniqueness × section_boost
```

### Factor 1: Base Confidence (Unchanged)
Keep type-based confidence as-is:
- Integer/Float: 0.9
- Boolean: 0.85
- Enum exact: 0.9
- Enum fuzzy: 0.6
- String: 0.75

### Factor 2: Pattern Quality (NEW)
Based on pattern specificity:

```python
if has_units and has_parameter_name:
    pattern_quality = 1.0  # "rotation of 30°" or "30° rotation"
elif has_units or has_parameter_name:
    pattern_quality = 0.9  # "30 degrees" or "rotation: 30"
elif has_strong_context:
    pattern_quality = 0.8  # "perturbation was 30"
else:
    pattern_quality = 0.6  # bare "30"
```

**Implementation:**
```python
def assess_pattern_quality(match_text: str, param_name: str) -> float:
    """
    Assess pattern quality based on context and specificity.
    
    Args:
        match_text: The full matched text (with context)
        param_name: Canonical parameter name
        
    Returns:
        Quality multiplier (0.6 - 1.0)
    """
    score = 0.6  # Base
    
    # Check for units
    unit_patterns = {
        'rotation': [r'°', r'deg', r'degrees'],
        'age': [r'years?', r'yrs?', r'y\.o\.'],
        'trials': [r'trials?'],
        'distance': [r'cm', r'mm', r'm\b'],
    }
    for param_type, units in unit_patterns.items():
        if param_type in param_name:
            for unit in units:
                if re.search(unit, match_text, re.I):
                    score += 0.2
                    break
    
    # Check for parameter keywords
    param_keywords = param_name.replace('_', ' ').split()
    for keyword in param_keywords:
        if len(keyword) > 3 and keyword in match_text.lower():
            score += 0.15
    
    # Check for strong context verbs
    strong_verbs = ['was', 'were', 'consisted', 'included', 'performed']
    if any(verb in match_text.lower() for verb in strong_verbs):
        score += 0.05
    
    return min(score, 1.0)
```

### Factor 3: Context Quality (NEW)
Based on sentence structure and keywords:

```python
def assess_context_quality(sentence: str, param_name: str) -> float:
    """
    Assess the quality of the context sentence.
    
    Returns:
        Quality multiplier (0.7 - 1.0)
    """
    score = 0.7
    
    # Bonus for clear statements
    if re.search(r'(participants?|subjects?|n\s*=)', sentence, re.I):
        score += 0.1
    
    # Bonus for methods-like language
    methods_keywords = ['performed', 'completed', 'received', 'underwent', 'exposed']
    if any(kw in sentence.lower() for kw in methods_keywords):
        score += 0.1
    
    # Penalty for ambiguous language
    if re.search(r'(approximately|~|around|about|roughly)', sentence, re.I):
        score -= 0.1
    
    # Bonus for exact values (not ranges)
    if not re.search(r'(\d+\s*-\s*\d+|to|between)', sentence):
        score += 0.1
    
    return max(min(score, 1.0), 0.5)
```

### Factor 4: Uniqueness (NEW)
Penalize when multiple different values are found:

```python
def assess_uniqueness(all_matches: List[str]) -> float:
    """
    Assess uniqueness of the match.
    
    Returns:
        Uniqueness multiplier (0.5 - 1.0)
    """
    unique_values = set(all_matches)
    
    if len(unique_values) == 1:
        return 1.0  # Perfect - one unique value
    elif len(unique_values) == 2:
        return 0.8  # Two different values - ambiguous
    elif len(unique_values) <= 4:
        return 0.6  # Multiple values - very ambiguous
    else:
        return 0.5  # Too many values - flag for review
```

### Factor 5: Section Boost (REVISED)
Replace arbitrary multipliers with empirically-derived boosts:

```python
# Based on validation data (to be calibrated against gold standard)
section_boosts = {
    'methods': 1.0,        # Neutral (baseline)
    'participants': 1.0,   # Equally reliable
    'abstract': 0.95,      # Slightly less detailed
    'procedure': 1.0,      # Equally reliable
    'results': 0.85,       # Often summary values, not exact
    'discussion': 0.7,     # Interpretive, not exact
    'introduction': 0.6,   # Background, not exact
    'unknown': 0.9,        # Slight penalty for unknown
}
```

---

## 📊 Comparison: Old vs New

### Example 1: "Rotation was 30°" (Methods section)

**Old System:**
```
base = 0.9 (integer)
section = 1.0 (methods)
final = 0.9 × 1.0 = 0.9
```

**New System:**
```
base = 0.9 (integer)
pattern_quality = 1.0 (has units + keyword "rotation")
context_quality = 1.0 (clear statement with "was")
uniqueness = 1.0 (single match)
section_boost = 1.0 (methods)
final = 0.9 × 1.0 × 1.0 × 1.0 × 1.0 = 0.9
```
✅ Same result, but justified

### Example 2: Bare "30" in Results section

**Old System:**
```
base = 0.9 (integer)
section = 0.7 (results)
final = 0.9 × 0.7 = 0.63
```

**New System:**
```
base = 0.9 (integer)
pattern_quality = 0.6 (bare number, no context)
context_quality = 0.7 (neutral sentence)
uniqueness = 0.8 (assume 2 different "30"s found)
section_boost = 0.85 (results)
final = 0.9 × 0.6 × 0.7 × 0.8 × 0.85 = 0.26
```
✅ **Much lower** - correctly flags as unreliable

### Example 3: "24 participants" (Participants section)

**Old System:**
```
base = 0.9 (integer)
section = 0.95 (participants)
final = 0.9 × 0.95 = 0.855
```

**New System:**
```
base = 0.9 (integer)
pattern_quality = 0.9 (has keyword "participants")
context_quality = 1.0 (clear noun phrase)
uniqueness = 1.0 (single match)
section_boost = 1.0 (participants)
final = 0.9 × 0.9 × 1.0 × 1.0 × 1.0 = 0.81
```
✅ Slightly lower but still high confidence

---

## 🛠️ Implementation Plan

### Phase 1: Add Pattern Quality Assessment (Week 1)
1. Implement `assess_pattern_quality()` function
2. Integrate into `extract_from_section()`
3. Test on 10-20 papers
4. Calibrate thresholds

### Phase 2: Add Context & Uniqueness (Week 2)
1. Implement `assess_context_quality()` and `assess_uniqueness()`
2. Integrate into extraction pipeline
3. Compare old vs new confidence on corpus
4. Document changes

### Phase 3: Calibrate Section Boosts (Week 3)
1. Extract from 50+ papers with gold standard
2. Measure accuracy by section
3. Calculate empirical section boosts
4. Update boosts based on data

### Phase 4: Validation (Week 4)
1. Run on full corpus with new confidence
2. Compare F1 scores (old vs new)
3. Analyze false positives/negatives by confidence range
4. Adjust thresholds for optimal precision/recall

---

## 📈 Expected Improvements

### Better Calibration
- **High confidence (≥ 0.9)**: Should achieve 95%+ accuracy
- **Medium confidence (0.7-0.9)**: Should achieve 85%+ accuracy
- **Low confidence (< 0.7)**: Should achieve 60%+ accuracy (flag for review)

### Fewer False Positives
Current system often assigns 0.8-0.9 to ambiguous matches. New system will more accurately reflect uncertainty.

### Actionable Thresholds
Can set auto-accept threshold at 0.85 with high confidence that parameters are correct.

### Traceable Decisions
Each confidence score includes breakdown:
```python
'confidence': 0.72,
'confidence_breakdown': {
    'base': 0.9,
    'pattern_quality': 0.8,
    'context_quality': 1.0,
    'uniqueness': 1.0,
    'section_boost': 1.0
}
```

---

## 🧪 Validation Methodology

### Gold Standard Comparison

```python
# For each parameter in gold standard
for param in gold_standard:
    extracted = regex_extract(param)
    
    if extracted:
        confidence = extracted['confidence']
        is_correct = (extracted['value'] == gold_standard[param]['value'])
        
        # Track accuracy by confidence bin
        confidence_bins[get_bin(confidence)].append(is_correct)

# Calculate calibration curve
for bin_name, results in confidence_bins.items():
    accuracy = sum(results) / len(results)
    print(f"{bin_name}: confidence vs accuracy")
    # Ideal: confidence ≈ accuracy
```

### Calibration Curve Example

```
Confidence Range  |  Old Accuracy  |  New Accuracy  |  Improvement
------------------|----------------|----------------|-------------
0.90 - 1.00      |     82%        |     94%        |    +12%
0.80 - 0.90      |     74%        |     86%        |    +12%
0.70 - 0.80      |     68%        |     77%        |     +9%
0.60 - 0.70      |     55%        |     64%        |     +9%
< 0.60           |     41%        |     48%        |     +7%
```

---

## 📝 Revised `normalize_value()` Function

```python
def normalize_value_v2(self, parameter: str, value: str, 
                       match_text: str = '', sentence: str = '',
                       all_matches: List[str] = None) -> Tuple[Any, float, Dict]:
    """
    Normalize parameter value and assign evidence-based confidence score.
    
    Args:
        parameter: Canonical parameter name
        value: Raw extracted value
        match_text: Full matched text with context (±50 chars)
        sentence: Full sentence containing the match
        all_matches: All values found for this parameter
        
    Returns:
        Tuple of (normalized_value, confidence_score, breakdown_dict)
    """
    # [Keep existing type conversion logic]
    
    # Calculate base confidence (type-based)
    if param_type == 'integer':
        normalized = int(float(re.sub(r'[^\d.-]', '', str(value))))
        base_confidence = 0.9
    # ... [rest of type logic]
    
    # NEW: Assess pattern quality
    pattern_quality = self.assess_pattern_quality(match_text, parameter)
    
    # NEW: Assess context quality
    context_quality = self.assess_context_quality(sentence, parameter)
    
    # NEW: Assess uniqueness
    uniqueness = self.assess_uniqueness(all_matches or [value])
    
    # Calculate final confidence
    final_confidence = (base_confidence * pattern_quality * 
                       context_quality * uniqueness)
    
    # Breakdown for debugging/transparency
    breakdown = {
        'base': base_confidence,
        'pattern_quality': pattern_quality,
        'context_quality': context_quality,
        'uniqueness': uniqueness,
        'final': final_confidence
    }
    
    return normalized, final_confidence, breakdown
```

---

## 🎯 Recommended Actions

### Immediate (This Week)
1. ✅ Remove arbitrary section multipliers from code
2. ✅ Implement basic pattern quality assessment
3. ✅ Add confidence breakdown to extraction output

### Short-term (Next 2 Weeks)
1. Implement full multi-factor confidence model
2. Extract from 50 papers and compare with gold standard
3. Calibrate section boosts empirically

### Long-term (Next Month)
1. Train a simple ML model for confidence prediction
2. Use features: pattern type, context words, section, uniqueness
3. Achieve calibrated confidence (confidence ≈ accuracy)

---

## 📌 Summary

### Current System Issues
- ❌ Arbitrary multipliers with no justification
- ❌ No pattern or context quality assessment
- ❌ Overconfident on ambiguous matches
- ❌ Can't explain why confidence is X

### Proposed System Benefits
- ✅ Evidence-based, multi-factor scoring
- ✅ Transparent confidence breakdowns
- ✅ Calibrated to match actual accuracy
- ✅ Can be validated and improved iteratively

### Next Steps
1. Review this proposal
2. Decide on implementation timeline
3. Start with Phase 1 (pattern quality)
4. Validate on gold standard corpus

---

**Date:** October 28, 2025  
**Status:** 📋 Proposal - awaiting approval  
**Impact:** Better confidence calibration → higher auto-acceptance → less manual review
