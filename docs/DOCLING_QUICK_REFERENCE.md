# Docling Preprocessor - Quick Reference

## 🚀 Quick Start

### Cluster Execution (Recommended)
```bash
cd designspace_extractor
sbatch slurm/run_batch_qwen72b.sh
```

### Local Testing
```bash
cd designspace_extractor
python run_batch_extraction.py --preprocessor auto --cache-dir .pdf_cache
```

---

## 📋 Command-Line Options

| Flag | Options | Default | Description |
|------|---------|---------|-------------|
| `--preprocessor` | `auto`, `pymupdf4llm`, `docling` | `auto` | PDF preprocessor to use |
| `--cache-dir` | Any path | `.pdf_cache` | Cache directory for preprocessed PDFs |
| `--llm-enable` | flag | disabled | Enable LLM assistance |
| `--llm-provider` | `qwen`, `claude`, `openai` | `qwen` | LLM provider |
| `--llm-mode` | `verify`, `fallback` | `verify` | LLM mode |

---

## 🔀 Routing Logic

### Auto-Routing Criteria (preprocessor='auto')

**Docling is used when:**
- PDF has tables (detected)
- PDF has figures (detected)
- PDF has scanned pages
- PDF is multi-column layout
- Complexity score ≥ 5

**Complexity Score Formula:**
```
score = tables*3 + figures*2 + scanned_pages*4 + multi_column*2
```

**pymupdf4llm is used when:**
- Complexity score < 5
- Simple text-only PDFs
- Single-column layouts

---

## 📊 Common Use Cases

### 1. Auto-Routing (Intelligent Default)
```bash
python run_batch_extraction.py --preprocessor auto
```
- **When:** You want the system to decide
- **Best for:** Mixed corpus (simple + complex PDFs)
- **Speed:** Fast for simple, thorough for complex

### 2. Force Docling (Maximum Quality)
```bash
python run_batch_extraction.py --preprocessor docling
```
- **When:** PDFs have tables/figures
- **Best for:** Methods-heavy papers, data-rich documents
- **Speed:** Slower but more thorough

### 3. Force pymupdf4llm (Maximum Speed)
```bash
python run_batch_extraction.py --preprocessor pymupdf4llm
```
- **When:** Simple text PDFs only
- **Best for:** Review papers, theoretical papers
- **Speed:** Fastest option

### 4. With LLM Assistance
```bash
python run_batch_extraction.py \
    --preprocessor auto \
    --llm-enable \
    --llm-provider qwen \
    --llm-mode verify
```
- **When:** Need parameter recovery from implicit/ambiguous text
- **Best for:** Full extraction pipeline with validation
- **Speed:** Slower (LLM inference overhead)

---

## 🗂️ Cache Management

### Check Cache
```bash
# View cached files
ls -lh .pdf_cache/

# Count cached PDFs
ls .pdf_cache/*.json | wc -l

# Check cache size
du -sh .pdf_cache/
```

### Clear Cache
```bash
# Delete all cached files
rm -rf .pdf_cache/

# Or delete specific file (by hash)
rm .pdf_cache/a3f4e2c1d5b6.json
```

### Cache Behavior
- **Cached:** When PDF exists and mtime unchanged
- **Re-cached:** When PDF modified (mtime changed)
- **Invalidated:** When preprocessor mode changed (auto→docling)

---

## 📝 Logging & Monitoring

### Key Log Messages to Watch

**Routing Decision:**
```
INFO: Routing papers/complex.pdf to docling (complexity=7.0)
INFO: Routing papers/simple.pdf to pymupdf4llm (complexity=0.0)
```

**Cache Hit:**
```
INFO: Using cached preprocessed PDF: complex.pdf
```

**Cache Miss:**
```
INFO: Preprocessing PDF with mode 'auto': complex.pdf
INFO: Cached preprocessed PDF: a3f4e2c1d5b6.json
```

**Fallback:**
```
ERROR: Preprocessing failed for broken.pdf
INFO: Falling back to basic text extraction
```

### Check Routing Decisions
```bash
# View all routing decisions
grep "Routing" logs/batch_extraction_qwen72b_*.out

# Count Docling vs pymupdf4llm usage
grep "Routing.*docling" logs/batch_extraction_qwen72b_*.out | wc -l
grep "Routing.*pymupdf4llm" logs/batch_extraction_qwen72b_*.out | wc -l
```

---

## 🐛 Troubleshooting

### Problem: Docling not installed
**Error:** `ImportError: No module named 'docling'`

**Fix:**
```bash
pip install docling
```
*(SLURM script auto-installs)*

### Problem: Cache not working
**Symptom:** PDFs re-processed every time

**Fix:**
```bash
# Check cache directory exists
ls .pdf_cache/

# Create if missing
mkdir -p .pdf_cache
```

### Problem: Wrong preprocessor selected
**Symptom:** Simple PDF using Docling (slow)

**Fix:**
```bash
# Force pymupdf4llm for this run
python run_batch_extraction.py --preprocessor pymupdf4llm

# Or analyze PDF to debug
python -c "
from extractors.preprocessors import PDFPreprocessorRouter
router = PDFPreprocessorRouter()
chars = router._analyze_pdf_characteristics('papers/problem.pdf')
print(f'Complexity: {chars.complexity_score}')
print(f'Tables: {chars.has_tables}, Figures: {chars.has_figures}')
"
```

### Problem: Docling extraction fails
**Error:** Docling crashes or empty output

**Fix:**
```bash
# Use pymupdf4llm as fallback
python run_batch_extraction.py --preprocessor pymupdf4llm

# System auto-falls back if Docling fails
```

---

## 📈 Performance Expectations

### Speed Comparison (per PDF)

| Preprocessor | First Run | Cached |
|--------------|-----------|--------|
| pymupdf4llm | 2-5 sec | <1 sec |
| Docling | 8-15 sec | <1 sec |

### Quality Comparison

| Feature | pymupdf4llm | Docling |
|---------|-------------|---------|
| Text extraction | ✅ Good | ✅ Good |
| Table extraction | ⚠️ Basic | ✅✅ Excellent |
| Figure detection | ❌ No | ✅ Yes |
| Multi-column | ✅ Good | ✅✅ Better |
| Scanned PDFs | ❌ Poor | ✅ OCR |

---

## 🔧 Advanced Configuration

### Python API
```python
from extractors.pdfs import PDFExtractor
from pathlib import Path

# Custom configuration
extractor = PDFExtractor(
    preprocessor='auto',           # or 'docling', 'pymupdf4llm'
    cache_dir=Path('/scratch/cache'),
    use_llm=True,
    llm_provider='qwen',
    llm_mode='verify'
)

# Extract with auto-routing
result = extractor.extract_text('papers/sample.pdf')
print(f"Method: {result['extraction_method']}")
```

### Analyze PDF Characteristics
```python
from extractors.preprocessors import PDFPreprocessorRouter

router = PDFPreprocessorRouter()
chars = router._analyze_pdf_characteristics('papers/complex.pdf')

print(f"Tables: {chars.has_tables}")
print(f"Figures: {chars.has_figures}")
print(f"Scanned: {chars.has_scanned_pages}")
print(f"Multi-column: {chars.is_multi_column}")
print(f"Complexity: {chars.complexity_score}")
```

### Force Specific Preprocessor
```python
# Always use Docling
extractor = PDFExtractor(preprocessor='docling')

# Always use pymupdf4llm
extractor = PDFExtractor(preprocessor='pymupdf4llm')
```

---

## 📚 Related Documentation

- **Full Implementation:** `docs/DOCLING_INTEGRATION_SUMMARY.md`
- **FN Reduction:** `docs/COMPREHENSIVE_FN_REDUCTION_IMPROVEMENTS.md`
- **LLM Setup:** `docs/LLM_SETUP_GUIDE.md`
- **Multi-Experiment:** `docs/MULTI_EXPERIMENT_IMPLEMENTATION.md`

---

## ✅ Quick Checklist

Before running on cluster:

- [ ] SLURM script updated (`slurm/run_batch_qwen72b.sh`)
- [ ] PDFs in `papers/` directory
- [ ] Conda environment activated (`godsreach2`)
- [ ] Sufficient disk space for cache (~10 MB per 50 PDFs)
- [ ] LLM model available (if using `--llm-enable`)

Run command:
```bash
sbatch slurm/run_batch_qwen72b.sh
```

Check logs:
```bash
tail -f logs/batch_extraction_qwen72b_*.out
```

---

**Status:** ✅ Ready for testing  
**Next Action:** Run on cluster and validate routing decisions!
