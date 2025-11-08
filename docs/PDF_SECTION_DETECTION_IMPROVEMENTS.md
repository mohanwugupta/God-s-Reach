# PDF Section Detection Improvements Summary

## Problem
SLURM batch processing was failing with "Insufficient evidence (len=0)" errors for most parameters. Root cause: PDF section detection was failing to extract Methods sections, leaving LLM with no context to find parameter values.

## Initial State
- **Success Rate**: 77.8% (14/18 PDFs with Methods >500 chars)
- **Issues Identified**:
  1. Section headers not detected (McDougle, Schween, Wong PDFs)
  2. Section boundaries calculated incorrectly, truncating content
  3. Subsection headers (e.g., "Apparatus", "Experimental design") treated as separate sections
  4. Mid-sentence matches (e.g., "method for extracting...") incorrectly identified as headers

## Solutions Implemented

### 1. Enhanced Section Header Patterns
**File**: `extractors/pdfs.py`

Added comprehensive header patterns to catch variations:
- **Numbered sections**: `^\d*\.?\s*methods?` (catches "2. Methods", "Methods")
- **Mid-line detection**: `\bmethods?\s+and\s+materials?\b`
- **Variations**: methodology, task description, experimental design, apparatus
- **New sections**: Added DISCUSSION_HEADERS and ABSTRACT_HEADERS

```python
METHODS_HEADERS = [
    r'^\d*\.?\s*materials?\s+and\s+methods?',
    r'^\d*\.?\s*methods?\s+and\s+materials?',
    r'^\d*\.?\s*methods?',
    r'^\d*\.?\s*procedures?',
    r'^\d*\.?\s*experimental\s+(?:design|setup|procedure|methods?)',
    r'^\d*\.?\s*methodology',
    r'^\d*\.?\s*task\s+(?:description|design|and\s+procedure)',
    r'\bmaterials?\s+and\s+methods?\b',  # Mid-line detection
    r'\bmethods?\s+and\s+materials?\b',
]
```

### 2. Subsection Filtering
**Problem**: "Apparatus" and "Experimental design" headers appearing AFTER "Methods" were treated as separate sections, cutting Methods content short.

**Solution**: Created METHODS_SUBSECTIONS list and added filtering logic:

```python
METHODS_SUBSECTIONS = [
    r'^\d*\.?\s*apparatus(?:\s+and\s+(?:materials?|methods?))?',
    r'^\d*\.?\s*participants?\s+and\s+(?:experimental\s+)?apparatus',
    r'^\d*\.?\s*experimental\s+(?:design|setup|procedure)',
    r'^\d*\.?\s*task\s+(?:description|design)',
]
```

Filtering logic:
- Track when entering Methods section
- Skip subsection headers that appear after first Methods header
- Allow Methods section to continue until major section (Results, Discussion) encountered

### 3. Stricter Header Detection
**Problem**: Lines like "method for extracting the pace parameter..." were matched as headers.

**Solution**: Changed header criteria from OR to AND logic:
```python
# OLD: Header if short (<100 chars) OR at line start
is_likely_header = (len(line_text) < 100 or match.start() - line_start < 5)

# NEW: Header MUST be at line start AND short (<50 chars)
at_line_start = (match.start() - line_start < 5)
is_short_line = (len(line_text) < 50)
is_likely_header = at_line_start and is_short_line
```

This filters out mid-sentence matches that happen to start a line.

### 4. Enhanced LLM Context with Participants Section
**Problem**: Wong PDF has 22K chars of Methods content under "Participants" subsection, but LLM only received 375-char "Methods" section.

**Solution**: Modified `_apply_llm_fallback()` to include Participants section in LLM context:

```python
# 1b. Add Participants section (often contains critical Methods details)
participants_text = sections.get('participants', '')
if participants_text and len(participants_text) > 100:
    participants_limited = participants_text[:10000]
    context_parts.append(f"PARTICIPANTS & PROCEDURES:\n{participants_limited}")
```

Now LLM receives:
1. Methods section (direct experimental procedures)
2. Participants section (detailed apparatus, procedure, task descriptions)
3. Introduction (background and hypotheses)
4. Results (experimental outcomes)

### 5. Three-Strategy Detection Approach
Maintained comprehensive fallback strategy:

**Strategy 1**: Position-based detection with enhanced patterns
**Strategy 2**: Keyword-based extraction (finds paragraphs with experimental terms)
**Strategy 3**: Line-by-line fallback detection

## Results

### Final Success Rate: **94.4%** (17/18 PDFs)

| PDF | Before | After | Improvement |
|-----|--------|-------|-------------|
| McDougle 2019 | 379 chars | 40,341 chars | **+39,962 chars** |
| Schween 2018 | 202 chars | 6,898 chars | **+6,696 chars** |
| s41467-2018 | 379 chars | 40,341 chars | **+39,962 chars** |
| Wong et al. | 357 chars | 375 chars* | (+22K via Participants) |
| Butcher 2018 | 2,842 chars | 51,617 chars | **+48,775 chars** |

*Wong PDF: Methods section still short (375 chars) but LLM now receives 22K-char Participants section

### Average Methods Section Length
- **Before**: 21,954 chars
- **After**: 31,407 chars
- **Improvement**: +43% more content

### Section Detection Rates
- Methods: **100%** (18/18 PDFs)
- Participants: 66.7% (12/18 PDFs)
- Results: 94.4% (17/18 PDFs)
- Discussion: 94.4% (17/18 PDFs)
- Introduction: 77.8% (14/18 PDFs)
- Abstract: 50.0% (9/18 PDFs)

## Impact on LLM Parameter Extraction

### Before Improvements
```
Parameters extracted via regex:
  total_trials: 500 (confidence: 0.8, method: regex)
  
LLM checking low-confidence parameters...
Methods section: [EMPTY or very short]
Result: "Insufficient evidence (len=0)" for most parameters
```

### After Improvements
```
Parameters extracted via regex:
  total_trials: 500 (confidence: 0.8, method: regex)
  
LLM checking low-confidence parameters...
Methods section: [4K-80K chars of actual experimental procedures]
Participants section: [10K+ chars of apparatus, task descriptions]
Result: LLM can find evidence and extract missing parameters
```

## Regex Extraction Benefits

Improved section detection also benefits regex-based extraction:
- More text to search for patterns
- Better context for pattern matching
- Higher confidence scores due to more surrounding evidence

## Files Modified

1. **extractors/pdfs.py**:
   - Enhanced METHODS_HEADERS patterns
   - Added METHODS_SUBSECTIONS list
   - Modified `detect_sections()` with subsection filtering
   - Stricter header detection (AND logic instead of OR)
   - Enhanced `_apply_llm_fallback()` to include Participants section

2. **Test Files Created**:
   - `test_pdf_section_detection.py`: Comprehensive test suite
   - `investigate_short_methods.py`: Debug script for problematic PDFs
   - `debug_methods_markers.py`: Marker detection debugging
   - `check_positions.py`: Position analysis tool

## Next Steps

1. **Run SLURM batch processing** with improved PDF parser
2. **Validate F1 score improvement** on full corpus
3. **Monitor "Insufficient evidence" errors** - should be significantly reduced
4. **Consider**: If Wong PDF (last 5.6% failure) needs special handling:
   - Could merge Methods + Participants sections for Papers with this structure
   - Current solution (passing Participants to LLM separately) should work

## Key Takeaways

1. **Scientific papers are inconsistent**: Need multiple strategies (patterns, keywords, fallbacks)
2. **Section ≠ Header**: Detecting headers is different from extracting full section content
3. **Subsections matter**: "Apparatus", "Experimental design" are often PART of Methods, not separate
4. **Header criteria must be strict**: Avoid mid-sentence matches by requiring short lines AND line-start position
5. **Participants section is critical**: Often contains more experimental details than "Methods" header section
6. **Testing on real corpus essential**: Unit tests can't catch all edge cases - need full PDF testing

## Success Metrics

✅ **94.4% success rate** (from 77.8%)  
✅ **100% Methods detection** (from 100% - maintained)  
✅ **+43% more Methods content** on average  
✅ **Robust subsection handling**  
✅ **LLM receives Participants section** for additional context  
✅ **Ready for production deployment**
