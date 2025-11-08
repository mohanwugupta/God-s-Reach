# F1 Score Analysis - Regex Improvements Tested

## Test Results Summary

### **✅ Enhanced Regex Patterns Working**
**Batch extraction completed successfully** with improved metadata extraction:

- **Authors**: 18/18 papers (100%) ✅
- **Year**: 17/18 papers (94.4%) ✅  
- **DOI/URL**: 8/18 papers (44.4%) ✅

**Pattern counts verified**:
- Authors: 8 patterns loaded
- Year: 11 patterns loaded  
- DOI/URL: 20 patterns loaded
- **Total: 39 metadata patterns** (up from ~12 before)

### **❌ F1 Score Unchanged (0.171)**
**Root cause identified**: The F1 score bottleneck is NOT metadata extraction, but core parameter extraction logic.

**Validation results**:
- Precision: 0.218
- Recall: 0.140  
- F1: 0.171 (same as before)

**Top performing parameters** (by F1):
1. effector: 0.500 ✅
2. perturbation_magnitude: 0.429 ✅
3. perturbation_class: 0.364 ✅

**Poor performing parameters** (F1 = 0.000):
- adaptation_trials, num_trials, age_mean, target_hit_criteria, etc.

## **Key Findings**

### **1. Metadata Extraction Fixed ✅**
The enhanced regex patterns successfully improved metadata parameter extraction:
- Authors extraction: 100% coverage
- Year extraction: 94.4% coverage
- DOI/URL extraction: 44.4% coverage

### **2. Core Parameter Logic Needs Work ❌**
The F1 score stagnation indicates that the main issue is in the core parameter extraction and matching logic, not metadata patterns.

**Evidence**: Even with perfect metadata extraction, F1 remains low because:
- Many core parameters (adaptation_trials, num_trials, age_mean) have F1 = 0.000
- False negatives: 147 (high)
- Value mismatches: 46 (high)

### **3. JSON Auto-Fix Not Tested ❌**
LLM verification couldn't be enabled locally due to model loading requirements, so the JSON auto-fix mechanism remains untested.

## **Next Steps**

### **Immediate Actions**
1. **Deploy to cluster** - Test JSON auto-fix mechanism with actual LLM
2. **Analyze parameter extraction logic** - Investigate why core parameters fail
3. **Review gold standard matching** - Check if parameter definitions align

### **Technical Investigation**
1. **Examine parameter extraction pipeline** - Debug why core parameters aren't found
2. **Compare gold standard vs extracted** - Identify specific mismatches
3. **Test individual parameter patterns** - Verify regex effectiveness

### **Expected Outcomes**
- **JSON auto-fix**: Should reduce parsing failures and recover lost extractions
- **Parameter logic fixes**: Should improve F1 score beyond metadata improvements
- **Combined impact**: Target F1 > 0.25 with both fixes

## **Current Status**
- ✅ Enhanced regex patterns implemented and tested
- ✅ Metadata extraction significantly improved
- ❌ JSON auto-fix mechanism untested (needs cluster deployment)
- ❌ Core parameter extraction logic needs investigation
- 🔄 F1 score improvement pending parameter logic fixes</content>
<parameter name="filePath">C:/Users/sheik/Box/ResearchProjects/God-s-Reach/docs/F1_REGEX_TEST_RESULTS.md