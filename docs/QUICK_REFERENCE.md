# Quick Reference: New Features

## 🎯 Three Features Implemented

1. **Database Integration** - Store 48 experiments in SQLite
2. **Formal Test Suite** - Automated validation with pytest  
3. **Coverage Analytics** - Identify gaps + LLM parameter discovery

---

## 🗄️ Feature #1: Database Integration

### Run Integration
```bash
cd designspace_extractor
python database_integration.py
```

### Query Database
```python
from database.models import Database, Experiment

db = Database('./out/designspace.db')
session = db.get_session()

# Get all experiments
experiments = session.query(Experiment).all()

# Get multi-experiment papers
multi = session.query(Experiment).filter(Experiment.is_multi_experiment == True).all()

# Get experiments with DOI
with_doi = session.query(Experiment).filter(Experiment.publication_doi != None).all()
```

### Status
- ✅ 48 experiments integrated
- ✅ Multi-experiment hierarchy working
- ✅ 100% success rate

---

## 🧪 Feature #2: Formal Test Suite

### Run Tests
```bash
cd designspace_extractor

# All tests
pytest validation/tests/ -v

# With coverage
pytest validation/tests/ --cov=extractors

# Specific test
pytest validation/tests/test_pdf_extraction.py::TestPDFExtraction::test_shared_methods_detection -v
```

### What's Tested
- ✅ PDF text extraction
- ✅ Section detection
- ✅ Multi-experiment detection
- ✅ Shared methods distribution
- ✅ Parameter extraction quality
- ✅ Demographics/rotation/trial patterns
- ✅ Multi-experiment balance (prevents Bond & Taylor regression)

---

## 📊 Feature #3: Coverage Analytics + LLM Discovery

### Basic Usage
```bash
cd designspace_extractor

# Coverage report
python analyze_coverage.py

# Custom threshold
python analyze_coverage.py --threshold 70

# Save to file
python analyze_coverage.py --output coverage.json
```

### LLM Parameter Discovery ⭐
```bash
# Set API key (in .env or export)
export ANTHROPIC_API_KEY="sk-ant-..."
export LLM_ENABLE=true

# Discover new parameters
python analyze_coverage.py --discover-new

# Use OpenAI
python analyze_coverage.py --discover-new --llm-provider openai
```

### What You Get
1. **Coverage Report**
   - 38 parameters analyzed
   - Coverage tiers (Excellent/Good/Poor/Critical)
   - Top 10 and bottom 10 parameters
   - Category-based analysis

2. **Improvement Suggestions**
   - 19 parameters flagged for improvement
   - Prioritized (CRITICAL/HIGH/MEDIUM)
   - Actionable recommendations

3. **LLM Discoveries** (with --discover-new)
   - New parameters not in current schema
   - Descriptions and example values
   - Importance and prevalence ratings
   - Evidence quotes from papers

---

## 📈 Current Coverage Highlights

### ✅ Excellent (≥80%)
- authors, effector, environment (100%)
- perturbation_class, schedule_blocking (98%)
- sample_size_n (92%)

### 👍 Good (50-80%)
- age_sd (74%), doi_or_url (79%)
- gender_distribution (68%)
- outcome_measures (56%)

### ⚠️ Needs Improvement (<50%)
- age_mean (19%), handedness (0%)
- dataset_link (6%), lab (0%)
- primary_outcomes (2%)

---

## 🎓 Examples

### Example 1: Find All Visuomotor Rotation Experiments
```python
from database.models import Database, Experiment

db = Database('./out/designspace.db')
session = db.get_session()

visuomotor = session.query(Experiment).filter(
    Experiment.study_type == 'visual'
).all()

print(f"Found {len(visuomotor)} visuomotor experiments")
for exp in visuomotor:
    print(f"  - {exp.name} (n={exp.sample_size_n})")
```

### Example 2: Run Tests Before Making Changes
```bash
# Before modifying patterns
pytest validation/tests/ -v

# Make changes to patterns.yaml
vim mapping/patterns.yaml

# Run tests again
pytest validation/tests/ -v

# If tests pass, changes are safe!
```

### Example 3: Discover New Parameters from Papers
```bash
# Enable LLM
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
echo "LLM_ENABLE=true" >> .env

# Run discovery
python analyze_coverage.py --discover-new --output new_params.json

# Review suggestions
cat new_params.json | jq '.new_parameter_suggestions'
```

---

## 📁 New Files Reference

```
designspace_extractor/
├── analyze_coverage.py                          # Coverage analytics script
├── database_integration.py                      # Database integration (updated)
├── database/
│   ├── models.py                                # Added extracted_params column
│   └── schema.sql                               # Added extracted_params column
├── llm/
│   └── llm_assist.py                            # Added discover_new_parameters()
└── validation/
    └── tests/
        ├── test_pdf_extraction.py               # Test suite
        ├── README.md                            # Testing docs
        └── fixtures/
            └── bond_taylor_2017_expected.json   # Test fixtures

docs/
├── FEATURE_IMPLEMENTATION_SUMMARY.md            # Full implementation details
└── QUICK_REFERENCE.md                           # This file
```

---

## 💡 Tips

1. **Before pattern changes:** Run tests to establish baseline
2. **After extraction:** Check database with `database_integration.py`
3. **Weekly:** Run `analyze_coverage.py` to track progress
4. **Monthly:** Run with `--discover-new` to find schema gaps
5. **For CI/CD:** Use `pytest validation/tests/ --cov=extractors --cov-report=xml`

---

## 🚀 What's Next?

Based on coverage analysis:

1. **Improve demographics patterns** (age_mean 19%, handedness 0%)
2. **Add dataset_link patterns** (currently 6%)
3. **Test LLM discovery** on full corpus for new parameters
4. **Set up GitHub Actions** with pytest integration

See `docs/FEATURE_IMPLEMENTATION_SUMMARY.md` for detailed next steps.
