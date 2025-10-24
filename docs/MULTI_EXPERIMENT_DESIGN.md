# Multi-Experiment Extraction Design

## Overview

This document outlines the architecture for extracting parameters from papers and code repositories containing multiple experiments.

## Use Cases

### PDF Papers with Multiple Experiments
Many motor adaptation papers include multiple experiments:
- **Experiment 1**: Tests baseline effect
- **Experiment 2**: Tests variant with different parameters
- **Experiment 3**: Follow-up or control condition

Each experiment has distinct:
- Sample sizes
- Parameter configurations
- Perturbation schedules
- Demographics
- Equipment settings

### Code Repositories with Multiple Experiment Configs
Research code often contains multiple experiment configurations:
```python
experiments = {
    'exp1_baseline': {...},
    'exp2_adaptation': {...},
    'exp3_transfer': {...}
}
```

## Architecture

### 1. Database Schema Changes

#### Parent-Child Experiment Relationship
```sql
ALTER TABLE experiments ADD COLUMN parent_experiment_id VARCHAR;
ALTER TABLE experiments ADD COLUMN experiment_number INTEGER;
ALTER TABLE experiments ADD COLUMN paper_id VARCHAR;
ALTER TABLE experiments ADD COLUMN is_multi_experiment BOOLEAN DEFAULT FALSE;
```

**Fields:**
- `parent_experiment_id`: Links to parent experiment (NULL for standalone or parent)
- `experiment_number`: Sequential number within paper (1, 2, 3, etc.)
- `paper_id`: Shared ID for all experiments from same paper
- `is_multi_experiment`: Flag indicating this is part of a multi-experiment set

**Relationship Types:**
1. **Standalone Experiment**: `parent_experiment_id = NULL`, `experiment_number = NULL`
2. **Parent Experiment**: `parent_experiment_id = NULL`, `experiment_number = NULL`, `is_multi_experiment = TRUE`
3. **Child Experiment**: `parent_experiment_id = <parent_id>`, `experiment_number = 1, 2, 3...`

### 2. PDF Extraction Strategy

#### Section Detection Patterns
Add patterns to detect experiment boundaries:
```regex
- '^Experiment\s+(\d+|[IVX]+|one|two|three)'
- '^Study\s+(\d+|[IVX]+|one|two|three)'
- '^(?:Behavioral\s+)?Task\s+(\d+|[IVX]+|one|two|three)'
```

#### Extraction Flow
```
1. Extract full text from PDF
2. Detect experiment boundaries using patterns
3. If multiple experiments detected:
   a. Split text by experiment sections
   b. Extract parameters from each section separately
   c. Create parent experiment record
   d. Create child experiment records for each
4. Else:
   a. Extract as single experiment (current behavior)
```

#### Shared vs. Experiment-Specific Parameters
Some parameters may be shared across experiments:
- Equipment (if same robot used)
- Demographics (if same participant pool)
- General methods

Strategy:
1. Extract common parameters into parent experiment
2. Extract experiment-specific parameters into child experiments
3. Use provenance to track which parameters came from which section

### 3. Code Extraction Strategy

#### Detection Patterns
Identify multi-experiment configurations:

**Python:**
```python
# Dictionary of experiments
experiments = {'exp1': {...}, 'exp2': {...}}
experiment_configs = [...]
EXPERIMENTS = {...}

# Separate files
exp1_config.json, exp2_config.json
exp1_params.py, exp2_params.py
```

**JSON/YAML:**
```json
{
  "experiments": [
    {"id": "exp1", ...},
    {"id": "exp2", ...}
  ]
}
```

#### Extraction Flow
```
1. Discover files in repository
2. Check for multi-experiment patterns:
   - Multiple config files with experiment numbers
   - Dictionary/array of experiment configs
   - Experiment loop structures
3. If multi-experiment detected:
   a. Extract each experiment configuration separately
   b. Create parent record for repository
   c. Create child records for each experiment
4. Else:
   a. Extract as single experiment
```

### 4. Provenance Tracking

Each parameter extraction must track:
- `experiment_id`: Which specific experiment it belongs to
- `section_name`: Which section/experiment number (e.g., "Experiment 1", "exp2_config")
- `is_shared`: Whether parameter is shared across experiments

This enables:
- Conflict resolution within and across experiments
- Understanding which parameters are study-wide vs. experiment-specific

### 5. API Changes

#### PDFExtractor.extract_from_file()
```python
def extract_from_file(self, pdf_path: Path, 
                     detect_multi_experiment: bool = True,
                     use_llm_fallback: bool = None) -> Dict[str, Any]:
    """
    Returns:
    {
        'is_multi_experiment': bool,
        'experiments': [
            {
                'experiment_number': 1,
                'parameters': {...},
                'metadata': {...}
            },
            ...
        ],
        'shared_parameters': {...},  # Parameters common to all experiments
        'metadata': {...}
    }
    """
```

#### CodeExtractor.extract_from_repo()
```python
def extract_from_repo(self, repo_path: str, 
                     discovered_files: Dict[str, List[Path]],
                     detect_multi_experiment: bool = True,
                     exp_id: Optional[str] = None) -> List[Experiment]:
    """
    Returns:
        List of Experiment objects (one if single experiment, multiple if multi-experiment)
    """
```

### 6. Conflict Resolution

Conflicts can occur:
1. **Within-experiment**: Same parameter appears multiple times in same experiment
2. **Across-experiment**: Same parameter differs between experiments (expected!)
3. **Shared vs. specific**: Parameter appears in both shared section and experiment-specific section

Resolution Strategy:
- Within-experiment: Apply existing conflict resolution (highest confidence)
- Across-experiment: No conflict (expected variation)
- Shared vs. specific: Specific overrides shared for that experiment

### 7. Validation

#### Schema Validation
- Parent experiments must have `is_multi_experiment = TRUE`
- Child experiments must reference valid parent
- Experiment numbers must be sequential (1, 2, 3...)
- All experiments in same paper must share same `paper_id`

#### Data Validation
- At least one parameter differs between experiments (else why multiple?)
- Shared parameters have same values across children
- No orphaned child experiments

### 8. Export Formats

#### Google Sheets
Each experiment gets its own row, with additional columns:
- `paper_id`: Links experiments from same paper
- `experiment_number`: Distinguishes experiments
- `is_parent`: Indicates parent record with shared parameters

#### Psych-DS
Create separate experiment files:
```
dataset_description.json
study.json
experiment_1/
    experiment.json
    sessions/
experiment_2/
    experiment.json
    sessions/
```

#### HED Tags
Add experiment-level tags:
```
(Experiment-ID, (Experiment-Number, 1))
(Experiment-ID, (Experiment-Number, 2))
```

### 9. UI Considerations

#### CLI Flags
```bash
# Auto-detect multi-experiment
designspace_extractor extract paper.pdf

# Force single experiment mode
designspace_extractor extract paper.pdf --single-experiment

# Extract specific experiment only
designspace_extractor extract paper.pdf --experiment-number 2
```

#### Output Display
```
Found 3 experiments in paper.pdf:

Experiment 1: "Baseline Adaptation"
  - 15 participants
  - 30° rotation
  - 320 trials
  
Experiment 2: "Transfer Test"
  - 12 participants (subset of Exp 1)
  - 45° rotation
  - 160 trials
  
Experiment 3: "Retention"
  - 15 participants (same as Exp 1)
  - 30° rotation
  - 80 trials
```

## Implementation Plan

### Phase 1: Database & Models (30 min)
- [ ] Add new columns to schema.sql
- [ ] Update models.py with new fields
- [ ] Add migration script
- [ ] Update Database class methods

### Phase 2: PDF Extraction (1-2 hours)
- [ ] Add experiment boundary detection patterns
- [ ] Implement text splitting by experiment
- [ ] Update extract_from_file() to return multi-experiment structure
- [ ] Add shared vs. specific parameter logic
- [ ] Update provenance tracking

### Phase 3: Code Extraction (1-2 hours)
- [ ] Add multi-config detection patterns
- [ ] Update PythonExtractor for experiment dictionaries
- [ ] Update JSONExtractor for experiment arrays
- [ ] Update CodeExtractor.extract_from_repo()

### Phase 4: Patterns & Validation (30 min)
- [ ] Add patterns.yaml entries for experiment detection
- [ ] Update validation.py with multi-experiment checks
- [ ] Add unit tests for multi-experiment scenarios

### Phase 5: Integration & CLI (1 hour)
- [ ] Update CLI commands
- [ ] Add multi-experiment examples to docs
- [ ] Update README.md
- [ ] Create demo with multi-experiment paper

## Testing Strategy

### Test Cases

1. **Single Experiment PDF**: Should extract as before (backward compatibility)
2. **Multi-Experiment PDF (3023.full.pdf if applicable)**: Extract all experiments
3. **Python with experiment dict**: Extract each configuration
4. **JSON with experiment array**: Extract each element
5. **Mixed sources**: PDF + code both multi-experiment

### Test Data
- Create `papers/multi_experiment_sample.pdf` (or use existing paper)
- Create `validation/test_repo_multi/` with multi-experiment configs

## Benefits

1. **Accuracy**: Correctly attribute parameters to specific experiments
2. **Completeness**: Extract all experiments from a paper, not just first one
3. **Reusability**: Papers often reuse equipment/demographics - capture shared info once
4. **Analysis**: Enable meta-analysis across experiments within same paper
5. **Provenance**: Clear tracking of which experiment each parameter came from

## Future Enhancements

1. **Automatic Experiment Grouping**: Use LLM to group related experiments
2. **Cross-Experiment Analysis**: Detect patterns across experiments (e.g., dose-response)
3. **Experiment Summarization**: Generate summary of how experiments differ
4. **Visual Comparison**: Side-by-side comparison UI for experiments
5. **Smart Defaults**: When creating new experiment, inherit shared parameters from parent
