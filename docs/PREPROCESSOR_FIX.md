# Preprocessor Integration Fixes

**Date:** 2025-11-12  
**Issue:** PDF preprocessing failing with "Unknown preprocessor: auto" error, causing fallback to basic pypdf extraction

## Root Cause

Two critical bugs in `extractors/preprocessors.py`:

1. **'auto' mode not handled** - When `preprocessor='auto'`, the code checked if `'auto'` was in the preprocessors dict before routing, causing ValueError
2. **Output format mismatch** - Preprocessors returned wrong data structure (list of sections instead of dict)

## Symptoms

```
ERROR - Enhanced extraction failed for ... : Unknown preprocessor: auto, falling back to basic pypdf
```

Result: All PDFs used fallback extraction instead of enhanced pymupdf4llm/Docling, causing poor parameter extraction (e.g., Parvin paper only got 2 parameters instead of expected ~15).

## Fixes Applied

### 1. Fixed Auto-Routing Logic

**File:** `extractors/preprocessors.py` (line ~287)

**Before:**
```python
def preprocess_pdf(self, pdf_path: Path, preprocessor: Optional[str] = None) -> Dict[str, Any]:
    preprocessor = preprocessor or self.route_pdf(pdf_path)  # ❌ Doesn't handle 'auto'
    
    if preprocessor not in self.preprocessors:  # ❌ Fails for 'auto'
        raise ValueError(f"Unknown preprocessor: {preprocessor}")
```

**After:**
```python
def preprocess_pdf(self, pdf_path: Path, preprocessor: Optional[str] = None) -> Dict[str, Any]:
    # Handle 'auto' or None -> route based on PDF characteristics
    if preprocessor is None or preprocessor == 'auto':
        preprocessor = self.route_pdf(pdf_path)  # ✅ Route first
    
    if preprocessor not in self.preprocessors:  # ✅ Now checks actual preprocessor name
        raise ValueError(f"Unknown preprocessor: {preprocessor}")
```

### 2. Fixed Pymupdf4llmPreprocessor Output Format

**File:** `extractors/preprocessors.py` (line ~40)

**Before:**
```python
normalized = {
    "sections": [{"name": name, "content": content} for name, content in sections.items()],  # ❌ List
    "full_text": markdown,
    "preprocessor": "pymupdf4llm",
    "metadata": {...}
}
```

**After:**
```python
normalized = {
    "full_text": markdown,
    "markdown_text": markdown,
    "sections": sections,  # ✅ Dict (as returned by extract_sections_from_markdown)
    "tables": tables,      # ✅ List (as returned by extract_tables_from_markdown)
    "page_count": page_count,
    "metadata": metadata,
    "extraction_method": "pymupdf4llm",
    "is_multi_column": is_multi_column
}
```

### 3. Fixed DoclingPreprocessor Output Format

**File:** `extractors/preprocessors.py` (line ~127)

**Before:**
```python
normalized = {
    "sections": [],        # ❌ Empty list
    "tables": [...]        # ❌ Complex nested structure
    "full_text": "",
    "preprocessor": "docling"
}
```

**After:**
```python
normalized = {
    "full_text": full_text,
    "markdown_text": full_text,
    "sections": {"full_document": full_text},  # ✅ Dict format
    "tables": tables,      # ✅ Simple list with content/page
    "page_count": page_count,
    "metadata": metadata,
    "extraction_method": "docling",
    "is_multi_column": True
}
```

## Expected Results

### Before Fix
```
[24/33] Processing: Parvin et al. - 2018...
   ERROR - Enhanced extraction failed: Unknown preprocessor: auto
   Parameters: [2]  ← Only basic metadata extracted
```

### After Fix
```
[18/19] Processing: Parvin et al. - 2018...
   INFO - Routing Parvin et al. - 2018... to pymupdf4llm (complexity=2.0)
   INFO - Preprocessing Parvin et al. - 2018... with pymupdf4llm
   Parameters: [15+]  ← Full parameter extraction with LLM
```

## Testing

### Verify Fix Locally
```python
from extractors.pdfs import PDFExtractor
from pathlib import Path

# Test with auto mode
extractor = PDFExtractor(preprocessor='auto', use_llm=False)
result = extractor.extract_text('papers/Parvin et al. - 2018 - Credit Assignment.pdf')

print(f"Method: {result['extraction_method']}")  # Should be 'pymupdf4llm'
print(f"Sections: {list(result['sections'].keys())}")
print(f"Tables: {len(result['tables'])}")
print(f"Text length: {len(result['full_text'])}")
```

### Check Cluster Logs
After re-running, look for:
```bash
grep "Routing" logs/batch_extraction_qwen72b_*.out
grep "Preprocessing.*with" logs/batch_extraction_qwen72b_*.out
```

Should see:
```
INFO - Routing Parvin et al. - 2018... to pymupdf4llm (complexity=2.0)
INFO - Preprocessing Parvin et al. - 2018... with pymupdf4llm
```

NOT:
```
ERROR - Enhanced extraction failed: Unknown preprocessor: auto
```

## Impact

✅ **Fixed:** Auto-routing now works correctly  
✅ **Fixed:** Preprocessor output format matches PDFExtractor expectations  
✅ **Expected:** Full parameter extraction instead of 2 parameters  
✅ **Expected:** LLM verification will now work with proper text extraction  
✅ **Expected:** Parvin paper should extract ~15 parameters

## Next Steps

1. **Re-run on cluster:** `sbatch slurm/run_batch_qwen72b.sh`
2. **Check logs** for "Routing" and "Preprocessing" messages
3. **Verify** Parvin paper extracts more than 2 parameters
4. **Validate** other papers also show improvement

## Files Changed

- ✅ `extractors/preprocessors.py` - Fixed auto-routing logic
- ✅ `extractors/preprocessors.py` - Fixed Pymupdf4llmPreprocessor output format
- ✅ `extractors/preprocessors.py` - Fixed DoclingPreprocessor output format

**Total changes:** 3 critical bug fixes in 1 file
