# Duplicate PDF Files Fix

**Issue:** Batch processing found 33 PDFs instead of expected 19, including duplicates like:
- `Taylor and Ivry - 2012 - The role of strategies in motor learning.pdf`
- `Taylor and Ivry - 2012 - The role of strategies in motor learning.ocr.pdf` ← **Duplicate**

## Root Cause

1. **`.ocr.pdf` duplicates** - OCR-processed versions of PDFs were saved alongside originals
2. **Invalid CLI arguments** - SLURM script used `--papers` and `--output` flags that don't exist

## Fixes Applied

### 1. Auto-Skip .ocr.pdf Duplicates in Script

**File:** `run_batch_extraction.py`

Added intelligent filtering that:
- Detects `.ocr.pdf` files
- Checks if non-OCR version (`paper.pdf`) exists
- Skips `.ocr.pdf` if original exists
- Logs skipped duplicates

**Example output:**
```
⚠️  Skipped 14 .ocr.pdf duplicates:
   - Taylor and Ivry - 2012 - The role of strategies in motor learning.ocr.pdf
   - Bond and Taylor - 2017 - Structural Learning.ocr.pdf
   ...

Found 19 PDF files in papers/
```

### 2. Fixed SLURM Script Arguments

**File:** `slurm/run_batch_qwen72b.sh`

**Before:**
```bash
python run_batch_extraction.py \
    --papers "../papers" \          # ❌ Invalid argument
    --output "batch_processing_results_qwen72b.json" \  # ❌ Invalid
    --preprocessor auto \
    --cache-dir .pdf_cache
```

**After:**
```bash
python run_batch_extraction.py \
    --preprocessor auto \
    --cache-dir .pdf_cache
# Script auto-detects papers folder at ../papers
# Outputs to batch_processing_results.json (default)
```

Also updated result checking to use correct filename:
- Changed: `batch_processing_results_qwen72b.json` 
- To: `batch_processing_results.json`

### 3. Manual Cleanup Script

**File:** `remove_ocr_duplicates.sh`

Created a script to manually remove `.ocr.pdf` files on the cluster:

```bash
cd designspace_extractor
bash remove_ocr_duplicates.sh
```

This will:
- List all `.ocr.pdf` files found
- Ask for confirmation before deletion
- Remove duplicates
- Show before/after counts

## What Changed

| File | Change | Status |
|------|--------|--------|
| `run_batch_extraction.py` | Added .ocr.pdf filtering logic | ✅ Fixed |
| `slurm/run_batch_qwen72b.sh` | Removed invalid `--papers`, `--output` args | ✅ Fixed |
| `slurm/run_batch_qwen72b.sh` | Updated result filename references | ✅ Fixed |
| `remove_ocr_duplicates.sh` | Created cleanup script (optional) | ✅ New |

## Next Steps

### Automatic Fix (Recommended)
The script now automatically skips `.ocr.pdf` duplicates. Just re-run:

```bash
sbatch slurm/run_batch_qwen72b.sh
```

You should see:
```
⚠️  Skipped 14 .ocr.pdf duplicates:
   - Taylor and Ivry - 2012 - The role of strategies in motor learning.ocr.pdf
   ...
Found 19 PDF files in papers/
```

### Manual Cleanup (Optional)
If you want to permanently delete the `.ocr.pdf` files:

```bash
cd designspace_extractor
bash remove_ocr_duplicates.sh
```

This will reduce disk usage and prevent confusion.

## Verification

After running, check the log:

```bash
tail -100 logs/batch_extraction_qwen72b_*.out
```

Look for:
- **Before:** `[24/33]`, `[25/33]` with duplicates
- **After:** `[18/19]`, `[19/19]` with no duplicates
- **Skipped message:** `⚠️  Skipped X .ocr.pdf duplicates`

## Why .ocr.pdf Files Exist

These files were likely created by:
1. OCR processing tool (trying to make PDFs searchable)
2. PDF viewer with OCR functionality
3. Backup/sync tool that created OCR versions
4. Previous extraction attempt that saved OCR'd versions

The `.ocr.pdf` files are redundant if the original `.pdf` files are already searchable (which they appear to be, based on successful extractions).

## Summary

✅ **Fixed:** Auto-skip .ocr.pdf duplicates in `run_batch_extraction.py`  
✅ **Fixed:** Invalid CLI arguments in `slurm/run_batch_qwen72b.sh`  
✅ **Created:** Manual cleanup script `remove_ocr_duplicates.sh`  
✅ **Expected:** Next run will process 19 PDFs instead of 33  
✅ **No duplicates:** Each paper processed only once
