# Test Suite for Design-Space Parameter Extractor

## Overview

This directory contains the formal test suite for validating PDF extraction, pattern matching, and multi-experiment detection functionality.

## Structure

```
validation/tests/
├── fixtures/                    # Known-good test data
│   └── bond_taylor_2017_expected.json
├── test_pdf_extraction.py       # PDF extraction tests
└── README.md                    # This file
```

## Running Tests

### Install pytest

```bash
pip install pytest pytest-cov
```

### Run All Tests

```bash
cd designspace_extractor
pytest validation/tests/ -v
```

### Run Specific Test File

```bash
pytest validation/tests/test_pdf_extraction.py -v
```

### Run Specific Test

```bash
pytest validation/tests/test_pdf_extraction.py::TestPDFExtraction::test_multi_experiment_detection -v
```

### Run with Coverage

```bash
pytest validation/tests/ --cov=extractors --cov-report=html
```

## Test Categories

### 1. PDF Extraction Tests (`TestPDFExtraction`)

**test_pdf_text_extraction**
- Verifies PDF text can be extracted
- Checks for minimum text length
- Validates expected content

**test_section_detection**
- Tests Methods/Participants section detection
- Validates section boundaries

**test_multi_experiment_detection**
- Verifies multi-experiment papers are detected
- Checks experiment count accuracy

**test_shared_methods_detection**
- Ensures shared Methods sections are distributed to all experiments
- Critical for balanced parameter extraction

**test_parameter_extraction_quality**
- Validates parameter counts are in expected ranges
- Checks required parameters are extracted
- Ensures minimum quality standards

**test_multi_experiment_balance**
- Tests that experiments have similar parameter counts
- Prevents regression of Bond & Taylor Exp 1 issue
- Max variance: 5 parameters

### 2. Pattern Matching Tests (`TestPatternMatching`)

**test_demographics_patterns**
- Tests age_mean, age_sd, gender_distribution, sample_size patterns
- Validates pattern matching on known text

**test_rotation_patterns**
- Tests rotation_magnitude_deg and rotation_direction extraction
- Handles various formats (45°, 45 degrees, etc.)

**test_trial_count_patterns**
- Tests adaptation_trials extraction
- Validates number parsing

### 3. Multi-Experiment Detection Tests (`TestMultiExperimentDetection`)

**test_experiment_header_detection**
- Tests "Experiment 1", "Experiment 2" detection
- Validates boundary detection

**test_roman_numeral_headers**
- Tests "Experiment I", "Experiment II" formats

**test_written_number_headers**
- Tests "Experiment One", "Experiment Two" formats

## Adding New Tests

### 1. Create Fixture

Add expected results to `fixtures/`:

```json
{
  "paper_name": "YourPaper.pdf",
  "is_multi_experiment": true,
  "num_experiments": 3,
  "experiments": [
    {
      "experiment_number": 1,
      "min_parameters": 20,
      "max_parameters": 30,
      "required_parameters": ["param1", "param2"]
    }
  ]
}
```

### 2. Write Test

```python
def test_your_feature(self, extractor):
    """Test description."""
    result = extractor.extract_from_file('path/to/paper.pdf')
    assert result['something'] == expected_value
```

### 3. Run Test

```bash
pytest validation/tests/test_pdf_extraction.py::TestPDFExtraction::test_your_feature -v
```

## Current Test Coverage

- ✅ PDF text extraction
- ✅ Section detection
- ✅ Multi-experiment detection
- ✅ Shared methods distribution
- ✅ Parameter extraction quality
- ✅ Multi-experiment balance
- ✅ Demographics patterns
- ✅ Rotation patterns
- ✅ Trial count patterns
- ✅ Experiment header formats

## Known Issues

- Tests require actual PDF files in `../../../papers/` directory
- Some tests may fail if pattern files are modified
- Fixtures need updating when extraction logic improves

## CI/CD Integration

To integrate with CI/CD:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest validation/tests/ --cov=extractors --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```
