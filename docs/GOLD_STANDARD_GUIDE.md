# Gold Standard Annotation in Google Sheets

## Overview

Gold standard annotations are stored in Google Sheets for easy collaborative annotation by domain experts. The validation system compares automated extraction results against this ground truth.

## Google Sheets Structure

### Sheet 1: "Gold_Standard_Annotations"

| Column | Type | Required | Description | Example |
|--------|------|----------|-------------|---------|
| `paper_name` | Text | Yes | Exact filename of PDF | "Bond and Taylor - 2017.pdf" |
| `experiment_number` | Number | No | Experiment number (1, 2, 3) or blank for single-exp | 1 |
| `parameter_name` | Text | Yes | Parameter name (must match schema) | "rotation_magnitude_deg" |
| `ground_truth_value` | Text/Number | Yes | Correct value according to paper | "45" |
| `value_type` | Dropdown | Yes | Data type: numeric, text, boolean, null | "numeric" |
| `confidence` | Dropdown | Yes | Annotator confidence | "certain", "likely", "inferred", "ambiguous" |
| `evidence_section` | Dropdown | No | Where value appears | "methods", "participants", "results" |
| `evidence_quote` | Text | Recommended | Exact quote from paper | "participants learned a 45° rotation" |
| `evidence_page` | Number | No | Page number in PDF | 3 |
| `annotator` | Text | Yes | Annotator initials/name | "MG", "JT" |
| `annotation_date` | Date | Yes | Date annotated | "2025-10-24" |
| `notes` | Text | No | Additional context | "Value inferred from figure" |
| `review_status` | Dropdown | Yes | Status | "draft", "reviewed", "validated", "final" |

### Sheet 2: "Missing_Parameters"

Documents parameters that are explicitly NOT reported in papers:

| Column | Type | Description |
|--------|------|-------------|
| `paper_name` | Text | Paper filename |
| `experiment_number` | Number | Experiment number or blank |
| `parameter_name` | Text | Parameter that is missing |
| `confirmed_missing` | Checkbox | Thoroughly checked and confirmed absent |
| `annotator` | Text | Who confirmed it's missing |
| `notes` | Text | Why it's missing or alternative info |

### Sheet 3: "Annotation_Metadata"

Tracks annotation progress and inter-rater agreement:

| Column | Type | Description |
|--------|------|-------------|
| `paper_name` | Text | Paper filename |
| `total_experiments` | Number | Number of experiments in paper |
| `parameters_annotated` | Number | How many parameters have ground truth |
| `annotators` | Text | List of annotators (comma-separated) |
| `completion_status` | Dropdown | "not_started", "in_progress", "complete", "reviewed" |
| `inter_rater_kappa` | Number | Cohen's kappa if multiple raters |
| `last_updated` | Date | Last annotation date |
| `notes` | Text | General notes about this paper |

## Data Validation Rules

**parameter_name** dropdown should include:
- All parameters from `mapping/schema_map.yaml`
- Prevents typos and ensures consistency

**confidence** dropdown:
- `certain`: Explicitly stated in paper, no ambiguity
- `likely`: Strongly implied but not explicit
- `inferred`: Reasoned from context or figures
- `ambiguous`: Multiple valid interpretations

**value_type** dropdown:
- `numeric`: Numbers (45, 3.2, 100)
- `text`: Text values ("visuomotor", "explicit")
- `boolean`: True/False
- `null`: Parameter not reported

**evidence_section** dropdown:
- `methods`, `participants`, `results`, `introduction`, `discussion`, `abstract`, `supplementary`

**review_status** dropdown:
- `draft`: Initial annotation, not reviewed
- `reviewed`: Reviewed by second annotator
- `validated`: Checked against extraction results
- `final`: Approved for benchmarking

## Annotation Guidelines

### 1. What to Annotate

Annotate **all experiments** from a selected subset of papers:
- Start with 10-20 papers for initial validation
- Include variety: single-exp, multi-exp, different perturbation types
- Prioritize papers with poor automated extraction

### 2. How to Annotate

**Step 1: Read the paper**
- Focus on Methods, Participants, Procedure sections
- Note experiment structure (single vs multi-experiment)

**Step 2: Extract each parameter**
- Find exact value in text
- Copy direct quote as evidence
- Note section and page number

**Step 3: Set confidence**
- `certain`: "Participants (n=15) learned a 45° rotation"
- `likely`: "Each group had the same sample size" (n mentioned earlier)
- `inferred`: From a figure or calculation
- `ambiguous`: Conflicting information or unclear wording

**Step 4: Document missing parameters**
- Add to Missing_Parameters sheet
- Only mark as missing if thoroughly searched

### 3. Handling Edge Cases

**Multi-experiment papers:**
- Create separate row for each experiment
- Use experiment_number column (1, 2, 3...)
- Check if parameters are shared or experiment-specific

**Ambiguous values:**
- Choose most likely interpretation
- Document alternatives in notes
- Set confidence = "ambiguous"

**Inferred values:**
- OK to infer from context, figures, or calculations
- Set confidence = "inferred"
- Explain reasoning in notes

**Range values:**
- If paper gives range (e.g., "18-30 years"), calculate mean
- Document in notes: "Range 18-30, using midpoint 24"

**Missing in paper but expected:**
- Add to Missing_Parameters sheet
- Helps distinguish true negatives from extraction failures

## Example Annotations

### Example 1: Certain Value
```
paper_name: Bond and Taylor - 2017.pdf
experiment_number: 1
parameter_name: rotation_magnitude_deg
ground_truth_value: 45
value_type: numeric
confidence: certain
evidence_section: methods
evidence_quote: "participants learned a 45° counterclockwise visuomotor rotation"
evidence_page: 3
annotator: MG
annotation_date: 2025-10-24
notes: 
review_status: draft
```

### Example 2: Inferred Value
```
paper_name: McDougle et al - 2017.pdf
experiment_number: 
parameter_name: age_mean
ground_truth_value: 24
value_type: numeric
confidence: inferred
evidence_section: participants
evidence_quote: "young adults aged 18-30 years"
evidence_page: 2
annotator: MG
annotation_date: 2025-10-24
notes: Range given, using midpoint (18+30)/2 = 24
review_status: draft
```

### Example 3: Missing Parameter
```
Missing_Parameters sheet:
paper_name: Taylor et al - 2013.pdf
experiment_number: 1
parameter_name: handedness
confirmed_missing: ✓
annotator: MG
notes: Not reported anywhere in paper. Only mentions "healthy participants"
```

## Inter-Rater Reliability

For critical benchmarking, have 2-3 raters annotate the same papers:

1. **Independent annotation**: Each rater annotates without seeing others' work
2. **Calculate agreement**: Use Cohen's kappa or Fleiss' kappa
3. **Resolve disagreements**: Discuss and reach consensus
4. **Update Annotation_Metadata**: Record kappa score

Target: κ ≥ 0.75 (substantial agreement)

## Sheet Setup Instructions

### 1. Create Google Sheet
```
Name: "Design-Space Extractor - Gold Standard Annotations"
Share with: Service account email from credentials.json
Permissions: Editor
```

### 2. Create Sheets
- Sheet 1: "Gold_Standard_Annotations"
- Sheet 2: "Missing_Parameters"  
- Sheet 3: "Annotation_Metadata"

### 3. Add Headers
Copy headers from tables above

### 4. Set Up Data Validation

**For Gold_Standard_Annotations:**
- `parameter_name`: List from range (create hidden sheet with all param names)
- `value_type`: List: numeric, text, boolean, null
- `confidence`: List: certain, likely, inferred, ambiguous
- `evidence_section`: List: methods, participants, results, introduction, discussion
- `review_status`: List: draft, reviewed, validated, final

**For Missing_Parameters:**
- `confirmed_missing`: Checkbox

**For Annotation_Metadata:**
- `completion_status`: List: not_started, in_progress, complete, reviewed

### 5. Format
- Freeze top row (headers)
- Apply filters to all columns
- Conditional formatting:
  - review_status = "final" → Green background
  - confidence = "ambiguous" → Yellow background
  - confidence = "certain" → Light green text

## Integration with Validation

The validation system loads this Google Sheet and compares to `batch_processing_results.json`:

```bash
# Run validation
python validation/validator.py --gold-standard-sheet "Gold_Standard_Annotations"

# Output:
# - Precision, Recall, F1 per parameter
# - Discrepancy report (FP, FN, value mismatches)
# - Pattern improvement suggestions
```

See `validation/validator.py` documentation for details.
