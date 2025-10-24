# Complete Command Reference

## 🔬 Validation System (NEW!)

### Run Validation Against Gold Standard
```bash
cd designspace_extractor

python validation/validator_simple.py \
  --spreadsheet-id "1nc34GT31emdpVJw7Vq-1cRI7_TtJ8Tdj" \
  --worksheet "Sheet1" \
  --results "./batch_processing_results.json"
```

**Prerequisites**:
1. Google Cloud service account created
2. `credentials.json` downloaded to workspace root
3. Spreadsheet shared with service account email

**See**: `docs/VALIDATION_GUIDE.md` for setup instructions

**What it shows**:
- Overall precision, recall, F1 scores
- Per-parameter metrics
- Top/bottom performing parameters
- Discrepancy counts (TP, FP, FN, VM)

---

## 🗄️ Database Integration

### Load Results into Database
```bash
cd designspace_extractor
python database_integration.py
```

### Query Database (Python)
```python
from database.models import Database, Experiment

db = Database('./designspace.db')
session = db.get_session()

# Get all experiments
experiments = session.query(Experiment).all()

# Get multi-experiment papers
multi = session.query(Experiment).filter(Experiment.is_multi_experiment == True).all()
```

---

## 🧪 Testing

### Run All Tests
```bash
cd designspace_extractor
pytest validation/tests/ -v
```

### Run Specific Tests
```bash
# PDF extraction tests
pytest validation/tests/test_pdf_extraction.py::TestPDFExtraction -v

# Pattern matching tests
pytest validation/tests/test_pdf_extraction.py::TestPatternMatching -v

# Multi-experiment detection tests
pytest validation/tests/test_pdf_extraction.py::TestMultiExperimentDetection -v
```

---

## 📊 Coverage Analytics

### Basic Coverage
```bash
python analyze_coverage.py
```

### With LLM Parameter Discovery
```bash
python analyze_coverage.py --discover-new
```

Shows new parameters not in current schema that the LLM recommends tracking.

---

## 🔄 Iterative Improvement Workflow

### 1. Run Validation
```bash
python validation/validator_simple.py \
  --spreadsheet-id "1nc34GT31emdpVJw7Vq-1cRI7_TtJ8Tdj" \
  --worksheet "Sheet1"
```

### 2. Identify Low-Performing Parameters
Look for F1 < 0.70 in validation report

### 3. Analyze Discrepancies
- **High FN** (false negatives): Add patterns to `mapping/patterns.yaml`
- **High FP** (false positives): Tighten patterns, add exclusions
- **High VM** (value mismatches): Add synonyms to `mapping/synonyms.yaml`

### 4. Edit Patterns/Synonyms
Edit `mapping/patterns.yaml` and `mapping/synonyms.yaml`

### 5. Re-extract and Re-integrate
```bash
python run_batch_extraction.py
python database_integration.py
```

### 6. Re-validate
```bash
python validation/validator_simple.py \
  --spreadsheet-id "1nc34GT31emdpVJw7Vq-1cRI7_TtJ8Tdj" \
  --worksheet "Sheet1"
```

### 7. Compare Results
Did F1 improve? Repeat until targets met (Overall F1 ≥0.85)

---

## 📁 Key Files

### Implementation
- `validation/validator_simple.py` - Validation engine
- `database_integration.py` - DB loader
- `analyze_coverage.py` - Coverage analytics
- `validation/tests/test_pdf_extraction.py` - Test suite

### Configuration
- `mapping/patterns.yaml` - Extraction patterns
- `mapping/synonyms.yaml` - Value synonyms
- `database/schema.sql` - Database schema
- `credentials.json` - Google Sheets credentials (create yourself)

### Documentation
- `docs/VALIDATION_GUIDE.md` - Validation setup and usage
- `docs/VALIDATION_IMPLEMENTATION_SUMMARY.md` - Technical details
- `docs/FEATURE_IMPLEMENTATION_SUMMARY.md` - Features #1, #3, #5
- `docs/GOLD_STANDARD_GUIDE.md` - Gold standard format

### Data
- `batch_processing_results.json` - Automated extraction results (46 experiments)
- `designspace.db` - SQLite database (48 experiments)
- Google Sheets - Gold standard (ID: `1nc34GT31emdpVJw7Vq-1cRI7_TtJ8Tdj`)

---

## 🎯 Quick Diagnostics

### Check Database Status
```bash
python database_integration.py
# Shows count of integrated experiments
```

### Check Test Status
```bash
pytest validation/tests/ -v
# Should show 12 tests passing
```

### Check Coverage Status
```bash
python analyze_coverage.py
# Shows parameter extraction percentages
```

### Check Validation Status (requires credentials)
```bash
python validation/validator_simple.py \
  --spreadsheet-id "1nc34GT31emdpVJw7Vq-1cRI7_TtJ8Tdj" \
  --worksheet "Sheet1"
# Shows F1 scores vs gold standard
```

---

## 🚀 Next Steps

1. **Set up Google Sheets credentials** (see `docs/VALIDATION_GUIDE.md`)
2. **Run baseline validation** to get current F1 scores
3. **Identify parameters** with F1 < 0.70
4. **Improve patterns** based on discrepancy analysis
5. **Re-validate** to measure improvement
6. **Iterate** until Overall F1 ≥0.85 (PRD target)
