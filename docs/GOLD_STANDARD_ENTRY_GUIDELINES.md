# Gold Standard Data Entry Guidelines

## Overview
Based on analysis of 18 matched studies from the gold standard, we've identified **7 key parameters** where human raters need better alignment with automated extraction patterns.

## 🔍 Current Issues Found

### 1. **Typos & Spelling**
- `coordinate_frame`: "horiztonal" → should be "horizontal"
- `feedback_type`: "continous" → should be "continuous"

### 2. **Terminology Misalignment**
| Parameter | Gold Standard Entry | Automated Extraction | Issue |
|-----------|---------------------|---------------------|-------|
| `perturbation_class` | "visuomotor_rotation" | "visuomotor" | Need consistency on abbreviation |
| `environment` | "kinarm" | "virtual" | Equipment name vs. type |
| `coordinate_frame` | "horiztonal" [typo] | "Cartesian" | Different terminology |
| `population_type` | "healthy_adult" | "older adults" | Different granularity |

### 3. **Format Issues**
- `perturbation_magnitude`: "30" should be "30°" (missing unit)
- `feedback_type`: Multiple formats ("endpoint, clamped, continous" vs "error clamp")

---

## ✅ RATER GUIDELINES BY PARAMETER

### 🎯 HIGH-PRIORITY PARAMETERS (Common Issues)

#### **perturbation_schedule**
**Use ONLY these values:**
- `abrupt` = sudden onset (step function)
- `gradual` = progressive increase/decrease (ramp)
- `random` = stochastic/variable
- `gradual_abrupt` = combination (some gradual, some abrupt)

**❌ AVOID:**
- "consistensy of X in a row" (this describes consistency, not schedule)
- Performance descriptions (e.g., "rapid improvement")

**✅ EXAMPLES:**
- "The 45° rotation was introduced in a single trial" → `abrupt`
- "Rotation increased 1° per trial from 0° to 45°" → `gradual`
- "Experiment 1 used gradual; Experiment 2 used abrupt" → `gradual_abrupt`

---

#### **feedback_type**
**Use ONLY these values:**
- `endpoint_only` or `endpoint` = cursor shown only at target
- `continuous` = cursor visible throughout movement
- `error_clamped` or `clamped` = fixed error feedback
- `delayed` = feedback presented after delay
- `cursor` = cursor feedback present
- `no_cursor` = no cursor shown

**RULES:**
- Separate multiple types with commas: `endpoint_only, continuous`
- Use "continuous" not "continous" (common typo!)
- Both "error_clamped" and "clamped" are acceptable

**✅ EXAMPLES:**
- "Cursor visible during reach" → `continuous`
- "Cursor appeared at end of movement" → `endpoint_only`
- "15° error clamp" → `error_clamped`
- "Groups received endpoint or continuous feedback" → `endpoint_only, continuous`

---

#### **perturbation_magnitude**
**ALWAYS include units!**

**FORMAT:** `NUMBER + UNIT`
- Degrees: `45°`, `30°`, `90°`
- Milliseconds: `500ms`
- Seconds: `1.5s`

**Multiple values:** Use commas: `45°, 90°`  
**Ranges:** Use "to": `0° to 45°`  
**With direction:** `45° CCW`, `30° CW`

**❌ BAD:** `30`, `45`, `1.5`  
**✅ GOOD:** `30°`, `45° CCW`, `1.5s`

---

#### **instruction_awareness**
**Use ONLY:**
- `aim_report` = participants report aiming direction
- `strategy_report` = participants report strategy used
- `none` = no explicit awareness measurement

**✅ EXAMPLES:**
- "Participants reported aiming angle on each trial" → `aim_report`
- "Post-experiment questionnaire about strategies" → `strategy_report`
- "No awareness measures collected" → `none`

---

#### **primary_outcomes**
**Be specific about KEY findings!**

**FOCUS ON:**
- Adaptation-related outcomes (not demographics)
- Main result, not methodology
- Observable effects, not interpretations

**✅ GOOD EXAMPLES:**
- "Implicit adaptation reduced in cerebellar patients"
- "Direction information required for implicit learning"
- "Aftereffects present only with cursor feedback"
- "No generalization between left and right workspaces"

**❌ AVOID:**
- "Mean age was 24.8 years" (not an outcome)
- "Used 45° rotation" (methodology, not outcome)
- Generic: "Adaptation occurred" (too vague)

---

#### **feedback_delay**
**FORMAT:** `NUMBER + UNIT`
- `0s` = immediate (not just "0")
- `1.5s` = 1.5 seconds
- `500ms` = 500 milliseconds

**Multiple delays:** `0s, 2s`

---

#### **target_hit_criteria**
**Use ONLY:**
- `shooting` = ballistic reach through target
- `stop_at_target` = controlled stop at target location
- `predetermined` = pre-programmed trajectory
- `via_point` = must pass through intermediate point

---

#### **cue_modalities**
**Use ONLY:** `visual`, `auditory`, `spatial`, `text`, `color`

**RULES:**
- Capitalize first letter: `Visual`, `Text`, `Spatial`
- Multiple modalities: separate with commas: `Visual, Auditory`

---

### 📊 OTHER PARAMETERS

#### **perturbation_class**
Prefer full term: `visuomotor_rotation` rather than `visuomotor`

#### **coordinate_frame**
Check spelling! "horizontal" not "horiztonal"

#### **environment**
Be consistent: use equipment type (`virtual`, `physical`) OR specific device (`KINARM`, `tablet`)

#### **population_type**
Use standardized terms:
- `healthy_adult`
- `older_adult`
- `cerebellar_patient`
- `stroke_patient`

---

## 🎨 GENERAL FORMATTING STANDARDS

### Numbers with Units
```
✅ CORRECT:
   45°, 30° CCW, 1.5s, 500ms, 15 cm

❌ INCORRECT:
   45, 30, 1.5, 500
```

### Multiple Values
```
✅ Use commas: 45°, 90°, 135°
✅ Use "to" for ranges: 0° to 45°
```

### Unknown Values
```
✅ Use '?' for unknown (don't leave blank)
✅ Add notes if needed: "? (not reported in paper)"
```

### Multi-Experiment Studies
```
✅ study_id format:
   - Butcher2018EXP1
   - Butcher2018EXP2
   - Butcher2018EXP3

✅ Each experiment gets its own row
✅ Include "EXP1", "EXP2" in title if helpful
```

---

## 🚦 QUALITY CHECKLIST

Before submitting your gold standard entry:

- [ ] **Spelling:** Check for typos (especially "continuous" not "continous")
- [ ] **Units:** All numbers have units (°, s, ms, cm, etc.)
- [ ] **Controlled Vocabulary:** Parameter values match allowed terms exactly
- [ ] **Consistency:** Same terminology as previous similar studies
- [ ] **study_id:** Format is AuthorYearEXPN (e.g., Taylor2014EXP1)
- [ ] **Uncertainty:** Unknown values marked with '?' not left blank
- [ ] **Primary Outcomes:** Specific, adaptation-related findings

---

## 📈 Parameters Most Often Missing in Automated Extraction

These parameters are hard for the system to extract automatically, so **manual gold standard entries are especially valuable**:

1. `perturbation_schedule` (16 instances missing)
2. `feedback_delay` (15 instances missing)
3. `target_hit_criteria` (14 instances missing)
4. `cue_modalities` (10+ instances missing)
5. `primary_outcomes` (frequently incomplete)

**Impact:** Your accurate manual coding of these parameters directly improves the training data for pattern improvements!

---

## 🔄 Workflow Recommendations

### For Each Paper:

1. **Read Methods Section** carefully for:
   - Perturbation type and schedule
   - Feedback conditions
   - Awareness measures

2. **Check Results Section** for:
   - Primary outcomes
   - Key findings

3. **Cross-reference** with automated extraction:
   - Does your entry match the automated suggestion?
   - If not, is the automated extraction wrong, or should you align?

4. **Use Controlled Vocabularies** (see parameter guidelines above)

5. **Review** entry against this checklist before saving

---

## 📞 Questions?

If you encounter:
- **Ambiguous cases:** Mark with '?' and add note explaining ambiguity
- **Missing information:** Use '?' rather than guessing
- **Novel parameters:** Check with team before creating new vocabulary terms

**Remember:** Consistency across raters is more valuable than individual interpretation!
