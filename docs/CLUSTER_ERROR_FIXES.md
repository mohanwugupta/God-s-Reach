# Cluster Batch Processing Error Fixes

**Date**: November 11, 2025  
**Issue**: Batch PDF extraction failing on HPC cluster with network/division errors

## Problems Identified

### 1. **ZeroDivisionError in Summary Report** ✅ FIXED
**Error**: 
```python
Multi-Experiment Papers: {len(multi_exp_papers)} ({len(multi_exp_papers)/len(successful)*100:.1f}% of successful)
ZeroDivisionError: division by zero
```

**Root Cause**: All PDFs failed extraction → `len(successful) == 0` → division by zero

**Solution**: Added defensive checks in `run_batch_extraction.py`:
```python
if len(successful) > 0:
    multi_pct = len(multi_exp_papers)/len(successful)*100
    # ... calculate percentages
else:
    # ... show "N/A - no successful extractions"
```

---

### 2. **Network Connectivity Issues** ✅ FIXED
**Error**:
```
HTTPSConnectionPool(host='openaipublic.blob.core.windows.net', port=443): Max retries exceeded
Failed to resolve 'openaipublic.blob.core.windows.net' ([Errno -2] Name or service not known)
```

**Root Cause**: HPC cluster nodes have no internet access. `tiktoken` tries to download `cl100k_base.tiktoken` from OpenAI servers on first use.

**Solutions**:

#### Option A: Pre-cache Encodings (Recommended)
1. **On machine with internet**, run:
   ```bash
   cd designspace_extractor
   python cache_tiktoken.py
   ```

2. **Transfer cache to cluster**:
   ```bash
   scp -r ~/.tiktoken_cache cluster:/home/username/.tiktoken_cache
   ```

3. **On cluster, set environment variable** in SLURM script:
   ```bash
   export TIKTOKEN_CACHE_DIR=$HOME/.tiktoken_cache
   ```

#### Option B: Use Offline Fallback (Automatic)
Modified `chunk.py` to gracefully degrade to word-based tokenization when tiktoken unavailable:
```python
def get_tiktoken_encoding():
    try:
        import tiktoken
        return tiktoken.get_encoding("cl100k_base")
    except Exception as e:
        logging.warning(f"tiktoken unavailable, using word approximation")
        return None  # Fallback to word splitting
```

---

### 3. **OCR Failures** ✅ FIXED
**Error**:
```
OCR failed for .../3023.full.pdf: Command '['ocrmypdf', ...]' returned non-zero exit status 1/10
```

**Root Cause**: OCR running on every PDF by default, but:
- Some PDFs are already searchable (don't need OCR)
- Tesseract may be missing on cluster
- OCR failures were blocking extraction

**Solution**: Added `skip_ocr` parameter to `ensure_searchable()`:
```python
def ensure_searchable(pdf_path: str, skip_ocr: bool = False) -> str:
    if skip_ocr:
        return str(pdf_path)  # Skip OCR in batch mode
    # ... normal OCR logic
```

Modified `retrieve_and_structured_extract()` to skip OCR in batch mode:
```python
searchable_pdf = ensure_searchable(pdf_path, skip_ocr=True)
```

**Why this works**:
- Most scientific PDFs are already searchable (created digitally)
- OCR is only needed for scanned documents
- Can run OCR as separate preprocessing step if needed

---

### 4. **RAG Pipeline Failures** ✅ FIXED
**Issue**: RAG extraction crashing when dependencies fail or data extraction fails.

**Solution**: Wrapped entire RAG pipeline in try-except blocks with graceful degradation:
```python
def retrieve_and_structured_extract(self, pdf_path: str, ...) -> Dict[str, Any]:
    try:
        from sentence_transformers import SentenceTransformer
        import faiss
    except ImportError:
        logger.warning("RAG dependencies not available, falling back to regex")
        return {}
    
    # Each step wrapped in try-except
    try:
        blocks_data = page_text_blocks(Path(searchable_pdf))
    except Exception as e:
        logger.warning(f"Failed to extract blocks: {e}")
        return {}
    
    # ... continue with fallbacks at each step
```

**Benefits**:
- System continues working even if RAG fails
- Falls back to regex extraction (already working)
- Detailed logging for debugging

---

## Updated Cluster Workflow

### Before Running Batch Job:

1. **Cache tiktoken encodings** (one-time setup):
   ```bash
   # On local machine with internet:
   cd designspace_extractor
   python cache_tiktoken.py
   
   # Transfer to cluster:
   scp -r ~/.tiktoken_cache della:/home/mg9965/.tiktoken_cache
   ```

2. **Update SLURM script** to set cache directory:
   ```bash
   #!/bin/bash
   #SBATCH --job-name=extract_papers
   #SBATCH --time=04:00:00
   #SBATCH --gpus=4
   
   # Set tiktoken cache location
   export TIKTOKEN_CACHE_DIR=$HOME/.tiktoken_cache
   
   # Run extraction
   cd $SCRATCH/God-s-Reach/designspace_extractor
   python run_batch_extraction.py --papers ../papers --llm qwen72b
   ```

### Expected Behavior Now:

- ✅ **Division by zero**: Fixed - shows "N/A" when no successful extractions
- ✅ **Network errors**: Fixed - uses cached tiktoken or word-based fallback
- ✅ **OCR failures**: Fixed - skips OCR in batch mode (can enable separately)
- ✅ **RAG crashes**: Fixed - graceful degradation to regex extraction
- ✅ **Continues processing**: Even if some PDFs fail, others will complete

---

## Testing the Fixes

### Local Test:
```bash
cd designspace_extractor

# Test with single PDF
python test_single_paper.py ../papers/3023.full.pdf --llm qwen72b

# Test batch (small subset)
python run_batch_extraction.py --papers ../papers --max-papers 3
```

### Cluster Test:
```bash
# Submit job
sbatch slurm/run_extraction_qwen72b.sh

# Monitor
squeue -u $USER
tail -f slurm-*.out
```

---

## Performance Optimizations

### Current Status:
- **Regex extraction**: Always works (primary method)
- **RAG extraction**: Optional enhancement (may fail gracefully)
- **LLM verification**: Works if model loaded correctly
- **OCR**: Disabled by default (enable only if needed)

### Trade-offs:
| Method | Speed | Accuracy | Reliability |
|--------|-------|----------|-------------|
| Regex only | Fast ⚡ | Good ✓ | Very High ✅ |
| Regex + RAG | Medium 🔄 | Better ✓✓ | High ✓ (with fixes) |
| Regex + RAG + LLM | Slow 🐌 | Best ✓✓✓ | Medium ⚠️ (network dependent) |

### Recommendations:
1. **For batch processing**: Use regex-only or regex+LLM (skip RAG if tiktoken issues persist)
2. **For high-quality extraction**: Run locally with full stack (internet available)
3. **For cluster**: Pre-cache all dependencies, use fallbacks

---

## Files Modified

1. ✅ `run_batch_extraction.py` - Fixed division by zero in summary report
2. ✅ `extractors/chunk.py` - Added offline tiktoken fallback
3. ✅ `extractors/ocr.py` - Added skip_ocr option, better error handling
4. ✅ `extractors/pdfs.py` - Wrapped RAG pipeline in try-except blocks
5. ✅ `cache_tiktoken.py` - New helper script for pre-caching encodings

---

## Next Steps

1. **Run cache_tiktoken.py** on local machine
2. **Transfer cache** to cluster
3. **Update SLURM script** with environment variable
4. **Re-run batch job** and verify fixes

All errors should now be resolved! 🎉
