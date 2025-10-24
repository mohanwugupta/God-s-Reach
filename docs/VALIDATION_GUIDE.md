# Validation System Guide

## Overview

The validation system compares automated parameter extraction against a gold standard maintained in Google Sheets. It calculates precision, recall, and F1 scores to identify which parameters need pattern improvements.

## Status

✅ **COMPLETED**:
- Validation engine implementation (`validation/validator_simple.py`)
- Study ID matching logic (handles both single and multi-experiment papers)
- Parameter comparison with fuzzy value matching
- Metrics calculation (precision, recall, F1)
- Discrepancy categorization (TP, FP, FN, VM)
- Per-parameter and overall performance reporting

⏸️ **PENDING** (requires user setup):
- Google Sheets API credentials
- Service account email sharing with gold standard spreadsheet

## Setup Instructions

### 1. Create Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Enable Google Sheets API for your project
4. Go to **APIs & Services → Credentials**
5. Click **Create Credentials → Service Account**
6. Fill in service account details
7. Click **Keys → Add Key → Create New Key → JSON**
8. Save the JSON file as `credentials.json` in the workspace root:
   ```
   designspace_extractor/credentials.json
   ```

### 2. Share Spreadsheet with Service Account

1. Open your gold standard Google Sheet
2. Open the `credentials.json` file
3. Find the `client_email` field (looks like: `your-service@project-name.iam.gserviceaccount.com`)
4. In Google Sheets, click **Share** button
5. Paste the service account email
6. Give it **Viewer** permissions (read-only is sufficient)
7. Click **Send**

### 3. Verify Spreadsheet Format

Your gold standard sheet should have this structure:

**Row 1 (Headers)**:
```
study_id | title | authors | year | doi_or_url | lab | dataset_link | n_total | population_type | age_mean | age_sd | handedness | effector | environment | ...
```

**Row 2+ (Data)**:
- `study_id`: Unique identifier (e.g., "Taylor2014", "Butcher2018_EXP1")
- Parameter columns: Fill with values from papers, leave empty if not reported
- Partial annotations OK (validator only compares parameters that have values)

### 4. Run Validation

Once credentials are set up:

```bash
cd designspace_extractor

# Basic validation
python validation/validator_simple.py \
  --spreadsheet-id "1nc34GT31emdpVJw7Vq-1cRI7_TtJ8Tdj" \
  --worksheet "Sheet1" \
  --results "./batch_processing_results.json"
```

## How It Works

### Study ID Matching

The validator matches automated results to gold standard using `study_id`:

- **Single experiment papers**: Extracts "AuthorYear" from filename
  - `"Bond and Taylor - 2017 - Title.pdf"` → `"Bond2017"`
  - `"Taylor, Krakauer & Ivry - 2014.pdf"` → `"Taylor2014"`

- **Multi-experiment papers**: Appends experiment number
  - `"Butcher et al - 2018.pdf"` (3 experiments) → `"Butcher2018_EXP1"`, `"Butcher2018_EXP2"`, `"Butcher2018_EXP3"`

### Parameter Comparison

For each parameter:

1. **True Positive (TP)**: In both gold standard and automated, values match
2. **False Positive (FP)**: In automated but NOT in gold standard
3. **False Negative (FN)**: In gold standard but NOT in automated (missed)
4. **Value Mismatch (VM)**: In both but values don't match

### Fuzzy Value Matching

Values are considered a match if:
- Exact string match (case-insensitive)
- Substring match (one contains the other)
- Numeric match within 1% tolerance (e.g., "45°" matches "45")

### Metrics Calculation

- **Precision** = TP / (TP + FP + VM) - How many extracted values are correct?
- **Recall** = TP / (TP + FN + VM) - How many gold standard values were found?
- **F1 Score** = 2 × (Precision × Recall) / (Precision + Recall) - Harmonic mean

## Output

The validation report shows:

```
VALIDATION REPORT
================================================================================

OVERALL METRICS (48 studies matched)
  Precision: 0.723
  Recall: 0.651
  F1 Score: 0.685
  TP: 342, FP: 78, FN: 103, VM: 52

PER-PARAMETER METRICS
  title                          F1:0.98 P:1.00 R:0.96 (TP:46 FP:0 FN:2 VM:0)
  authors                        F1:0.96 P:0.98 R:0.94 (TP:45 FP:1 FN:3 VM:0)
  year                           F1:0.94 P:1.00 R:0.89 (TP:43 FP:0 FN:5 VM:0)
  n_total                        F1:0.85 P:0.88 R:0.82 (TP:38 FP:4 FN:8 VM:1)
  perturbation_class             F1:0.72 P:0.81 R:0.65 (TP:28 FP:5 FN:12 VM:3)
  ...
  rotation_magnitude             F1:0.45 P:0.52 R:0.40 (TP:15 FP:8 FN:18 VM:5)  ← Needs improvement
  coordinate_frame               F1:0.38 P:0.45 R:0.33 (TP:11 FP:9 FN:20 VM:4)  ← Needs improvement
```

## Interpretation

### High F1 (>0.80): Working Well
- Patterns are accurate
- No action needed unless aiming for >0.90

### Medium F1 (0.60-0.80): Needs Tuning
- Check discrepancies for pattern improvements
- High FN → Add more patterns (missing values)
- High FP → Tighten patterns (over-eager matching)
- High VM → Review synonyms/normalization

### Low F1 (<0.60): Priority Improvement
- Patterns may be missing or too specific
- Review gold standard examples
- Add new extraction patterns
- Check section targeting

## Iterative Improvement Workflow

1. **Run validation** → Get baseline metrics
2. **Identify low F1 parameters** → Focus on weakest areas
3. **Analyze discrepancies** → Understand failure modes
   - FN examples: What patterns would catch these?
   - VM examples: What synonyms are missing?
   - FP examples: Are patterns too permissive?
4. **Improve patterns** → Edit `mapping/patterns.yaml`, `mapping/synonyms.yaml`
5. **Re-extract** → Run batch processing again
6. **Re-validate** → Measure improvement
7. **Repeat** until F1 targets met (PRD: ≥0.85 overall, ≥0.70 per parameter)

## Current Status

- ✅ Validation engine implemented and tested
- ✅ 46 automated results ready for validation
- ⏸️ Awaiting Google Sheets API credentials setup
- ⏸️ Gold standard annotations in progress (~30 papers partially annotated)

## Next Steps

1. **User Action Required**:
   - Set up Google Cloud service account
   - Download `credentials.json`
   - Share spreadsheet with service account email

2. **Once credentials ready**:
   ```bash
   python validation/validator_simple.py \
     --spreadsheet-id "1nc34GT31emdpVJw7Vq-1cRI7_TtJ8Tdj" \
     --worksheet "Sheet1"
   ```

3. **Analyze results**:
   - Identify parameters with F1 < 0.70
   - Group failure modes (FN, FP, VM)
   - Prioritize by parameter importance

4. **Pattern improvements**:
   - Add patterns for high-FN parameters
   - Refine patterns for high-FP parameters
   - Add synonyms for high-VM parameters

## Files

- **Validator**: `validation/validator_simple.py` (220 lines, standalone)
- **Gold Standard**: Google Sheets (ID: `1nc34GT31emdpVJw7Vq-1cRI7_TtJ8Tdj`)
- **Automated Results**: `batch_processing_results.json` (46 results, 18 papers)
- **Credentials**: `credentials.json` (not created yet - user needs to set up)

## Troubleshooting

### "Credentials file not found"
- Create service account in Google Cloud Console
- Download JSON key as `credentials.json`
- Place in workspace root

### "Permission denied" or "403 Forbidden"
- Share spreadsheet with service account email
- Grant at least Viewer permissions

### "No studies matched"
- Check `study_id` format in gold standard matches automated IDs
- Verify study_id column is first column in sheet
- Check for typos in study IDs

### "Google API libraries not installed"
```bash
pip install google-api-python-client google-auth
```
