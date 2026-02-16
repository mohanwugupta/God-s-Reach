# Gold Standard Immediate Action Items

## 🚨 CRITICAL FIXES NEEDED

Based on analysis of your current gold standard data, here are **specific corrections** that should be made immediately:

---

## 1️⃣ SPELLING ERRORS (17 instances)

### `coordinate_frame`: "horiztonal" → "horizontal"

**Fix in these rows:**
- Taylor2010
- Wang2025
- Evans2025
- Mcdougle2025
- Wong2019
- Poh2019
- Schween2019
- (and all Butcher2018, Hutter2018, Parvin2018, Schween2018 experiments)

**❌ Current:** `horiztonal`  
**✅ Fix to:** `horizontal`

---

## 2️⃣ TYPO IN `feedback_type` (10+ instances)

### "continous" → "continuous"

**Fix in these rows:**
- Mcdougle2025
- Wong2019
- Poh2019
- Schween2019
- Hutter2018EXP1
- Hutter2018EXP2
- Schween2018EXP1
- Schween2018EXP2
- Schween2018EXP3
- Schween2018EXP4

**❌ Current:** `continous` (missing 'u')  
**✅ Fix to:** `continuous`

**Example fixes:**
- "endpoint, continous" → "endpoint, continuous"
- "continous" → "continuous"

---

## 3️⃣ STANDARDIZE `perturbation_schedule` FORMAT

### Row 2 (Wang2025): 
**Current:** `gradual_abrupt`  
**Status:** ✅ CORRECT - this is the right format for mixed schedules

### Row 13-14 (Hutter2018):
**Current:** `consistensy of 1/2/3/7 in a row`  
**Issue:** This describes *consistency* of errors, NOT the perturbation schedule  
**Fix needed:** Determine if rotation was `abrupt` (step), `gradual` (ramp), or `random`

**Guidance:** Read the methods section to determine:
- Was rotation introduced suddenly? → `abrupt`
- Was rotation progressively increased? → `gradual`
- Was rotation magnitude varied trial-to-trial? → `random`

---

## 4️⃣ ADD UNITS TO `perturbation_magnitude`

### Current issues in multiple rows:

**Examples that need fixing:**
- Row 6 (Poh2019): `30` → should be `30°`
- Row 4 (Mcdougle2025): `25, 45, 75, 90` → should be `25°, 45°, 75°, 90°`
- Row 5 (Wong2019): `45` → should be `45°`

**Rule:** ALWAYS include the degree symbol `°` for rotations

**Format examples:**
- Single value: `45°`
- Multiple values: `45°, 90°`
- With direction: `45° CCW`
- Range: `0° to 45°`

---

## 5️⃣ STANDARDIZE `feedback_type` TERMINOLOGY

### Row 1 (Taylor2010):
**Current:** `endpoint_only`  
**Status:** ✅ CORRECT - good use of standardized term

### Row 5 (Wong2019):
**Current:** `No hand, continous view of hand`  
**Issue:** Mixed format and typo  
**Suggested fix:** `no_cursor, continuous` (standardized terms, separated by comma)

### Row 6 (Poh2019):
**Current:** `endpoint, clamped, continous`  
**Issues:** 
1. Typo: "continous" → "continuous"
2. Consider: "clamped" → "error_clamped" for consistency

**Suggested fix:** `endpoint, error_clamped, continuous`

### Row 8-12 (Butcher2018 series):
**Current examples:**
- `cursor, scalar point`
- `directional line feedback, magnitude line feedback, magnitude & direction line feedback`

**Issue:** Very specific terminology that may not match automated extraction  
**Suggested standardization:** 
- `cursor` (keep if cursor feedback was provided)
- Consider adding: `endpoint` or `continuous` to clarify timing

---

## 6️⃣ INCONSISTENT `perturbation_schedule` ENTRIES

### Row 2 (Wang2025):
**Current:** `gradual_abrupt`  
**Notes field:** "Gradual increases and decreases in some experiments"  
**Status:** ✅ GOOD - using mixed schedule format correctly

### Rows 13-14 (Hutter2018EXP1/2):
**Current:** `consistensy of 1/2/3/7 in a row` and `consistensy of 2/7 in a row`  
**Problem:** This is describing error *consistency*, not perturbation *schedule*

**Action needed:**
1. Check paper methods: Was rotation introduced abruptly or gradually?
2. Replace with: `abrupt`, `gradual`, or `random`
3. Move consistency info to `notes` field if important

---

## 7️⃣ STANDARDIZE `primary_outcomes` FORMAT

### Current issues:
Some rows have very specific technical descriptions, others are vague

### Examples to review:

**Row 8 (Butcher2018EXP1):**
**Current:** `Only cursor group showed aftereffect`  
**Status:** ✅ GOOD - clear, specific outcome

**Row 9 (Butcher2018EXP2):**
**Current:** `Minimal aftereffect when magnitude only feedback`  
**Status:** ✅ GOOD - clear finding

**Row 12 (Butcher2018EXP5):**
**Current:** `Need direction information to have implicit adaptation. If magnitude only, it only drives explicit reporting.`  
**Status:** ✅ EXCELLENT - specific mechanistic finding

**Template to follow:**
- Start with the KEY finding
- Be specific about conditions
- Focus on adaptation outcomes (not demographics)

---

## 📝 QUICK FIXES SPREADSHEET BATCH EDITS

### Find & Replace Operations:

1. **Fix coordinate_frame typo:**
   - Find: `horiztonal`
   - Replace with: `horizontal`
   - Expected: ~17 replacements

2. **Fix feedback_type typo:**
   - Find: `continous`
   - Replace with: `continuous`
   - Expected: ~10 replacements

3. **Add degree symbols to perturbation_magnitude:**
   - This requires manual review per row
   - Add `°` after numeric values in perturbation_magnitude column
   - For multiple values, ensure commas separate: `45°, 90°`

---

## 🎯 PRIORITY ORDER

### Immediate (Do First):
1. ✅ Fix "horiztonal" → "horizontal" (17 instances)
2. ✅ Fix "continous" → "continuous" (10+ instances)

### High Priority (Do Soon):
3. 🔄 Add degree symbols to perturbation_magnitude
4. 🔄 Fix Hutter2018 `perturbation_schedule` entries
5. 🔄 Standardize Wong2019 and Poh2019 `feedback_type`

### Medium Priority (Review):
6. 📋 Review all `primary_outcomes` for specificity
7. 📋 Ensure all multi-experiment studies have consistent study_id format

---

## ✅ VALIDATION AFTER FIXES

After making corrections, we should see:
- **Improved F1 scores** for `coordinate_frame` and `feedback_type`
- **Better matching** between gold standard and automated extraction
- **More consistent** terminology across all studies

**Next steps after corrections:**
1. Re-run validation: `python validation/validator_public.py`
2. Check new F1 scores
3. Identify remaining mismatches for pattern improvement

---

## 📊 EXPECTED IMPACT

Current F1 scores (19 matched studies):
- Overall F1: **0.217**
- `effector`: 0.895 ✅
- `number_of_locations`: 0.643 ✅
- Many parameters: 0.000 ❌

**After typo fixes**, we expect:
- `coordinate_frame` F1 to improve from 0.000 to ~0.80+
- `feedback_type` fuzzy matching to work better
- Overall F1 to increase to ~0.30-0.35

**These quick fixes will improve ~27 instances across 17+ rows!**
