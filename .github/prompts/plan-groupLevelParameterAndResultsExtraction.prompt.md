# Plan: Group-Level Parameter & Results Extraction

This plan extends your design space extraction system to support **group-level parameters** and **results/outcomes scraping** from motor learning papers, enabling richer analysis and maintaining compatibility with the existing gold standard during transition.

## Steps

### 1. Add Group model and database schema

Create `database/models.py` `Group` class with relationships to `Experiment`, fields for group-specific parameters (name, N, demographics, perturbation settings), and JSON `results` field for means/SDs/statistics. Write migration script to extend existing database without breaking current experiment-level data.

**Details:**
- New `Group` model with fields:
  - `id` (String, primary key, e.g., "EXP001_GRP01")
  - `experiment_id` (String, foreign key)
  - `group_number` (Integer)
  - `group_name` (String, e.g., "Control", "Experimental", "Gradual")
  - `group_type` (String, e.g., "control", "experimental", "baseline")
  - `sample_size_n` (Integer)
  - `age_mean`, `age_sd` (Float)
  - `gender_distribution` (String)
  - Group-specific perturbation parameters (rotation_magnitude_deg, perturbation_schedule, etc.)
  - Group-specific feedback parameters (feedback_type, instruction_awareness)
  - `results` (Text/JSON field for outcomes)
- Add relationship: `Experiment.groups = relationship("Group", back_populates="experiment")`
- Create migration script: `database/migrations/add_groups_v1_5.py`
- Ensure backward compatibility: existing experiment-level data remains intact

### 2. Implement dual-mode parameter extraction

Modify `extractors/pdfs.py` `PDFExtractor` to add `extract_level` parameter (`'experiment'` or `'group'`, default `'experiment'` for backward compatibility). Add `_detect_groups()` and `_extract_group_parameters()` methods. Create group detection patterns in `mapping/patterns.yaml` for identifying group names, per-group sample sizes, and group-specific parameter values.

**Details:**
- Add `extract_level` parameter to `PDFExtractor.__init__()` (default: `'experiment'`)
- Modify `extract_from_file()` to branch based on `extract_level`:
  - `'experiment'`: Current behavior (return experiment-level dict)
  - `'group'`: Return dict with `groups` list containing per-group parameters
- New methods in `PDFExtractor`:
  - `_detect_groups(text: str) -> int`: Detect number of groups
  - `_extract_group_names(text: str, num_groups: int) -> List[str]`: Extract group identifiers
  - `_extract_group_parameters(text: str, group_name: str) -> Dict`: Extract parameters for specific group
  - `_extract_group_results(text: str, group_name: str) -> Dict`: Extract results/outcomes for specific group
- Add to `mapping/patterns.yaml`:
  ```yaml
  groups:
    group_identification:
      - 'participants?\s+were\s+(?:randomly\s+)?assigned\s+to\s+(?:one\s+of\s+)?(\d+)\s+groups?'
      - '(\d+)\s+groups?:\s*([^.]+)'
      - 'divided\s+into\s+(\d+)\s+(?:experimental\s+)?(?:groups?|conditions?)'
    
    group_names:
      - '(?:Group|Condition)\s+(\d+):\s*([A-Za-z\s]+)'
      - '(?:control|experimental|baseline|test)\s+group'
    
    group_sample_size:
      - '([A-Z][a-z]+)\s+group\s*\(n\s*=\s*(\d+)\)'
      - 'n\s*=\s*(\d+)\s+(?:in\s+(?:the\s+)?)?([A-Z][a-z]+)\s+group'
    
    group_demographics:
      - '([A-Z][a-z]+)\s+group\s*\(.*?age[:\s]+(\d+\.?\d*)\s*±\s*(\d+\.?\d*)'
  ```
- Handle parameter inheritance: group-level parameters override experiment-level defaults

### 3. Add results extraction patterns and methods

Extend `mapping/patterns.yaml` with regex patterns for means/SDs (e.g., `"M=12.3±4.5"`), statistical tests (`"t(22)=3.45, p<0.01"`), and effect sizes. Implement `_extract_group_results()` method in `extractors/pdfs.py` to parse numeric results and statistical comparisons. Store results in normalized JSON format within `Group.results` field.

**Details:**
- Add to `mapping/patterns.yaml`:
  ```yaml
  results:
    mean_sd_extraction:
      - '(?:mean|M)\s*=\s*(\d+\.?\d*)\s*(?:deg|°)?\s*(?:,\s*)?(?:SD|s\.d\.|±)\s*=?\s*(\d+\.?\d*)'
      - '(\d+\.?\d*)\s*±\s*(\d+\.?\d*)\s*(?:deg|°|mm|ms)'
    
    statistical_tests:
      - 't\((\d+)\)\s*=\s*(-?\d+\.?\d*)\s*,\s*p\s*[=<]\s*(\d+\.?\d*)'
      - 'F\((\d+),\s*(\d+)\)\s*=\s*(\d+\.?\d*)\s*,\s*p\s*[=<]\s*(\d+\.?\d*)'
      - 'Cohen\'?s?\s+d\s*=\s*(\d+\.?\d*)'
      - 'η²\s*=\s*(\d+\.?\d*)'
    
    significance_markers:
      - 'significant(?:ly)?\s+(?:greater|larger|higher|lower|smaller)'
      - 'no\s+significant\s+(?:difference|effect)'
  ```
- Implement `_extract_group_results()`:
  - Parse means and standard deviations
  - Extract sample sizes if reported with results
  - Capture statistical test results (t-tests, ANOVAs, post-hocs)
  - Extract effect sizes when reported
  - Identify outcome types (adaptation, retention, aftereffect, learning rate)
- Normalize results to JSON structure:
  ```json
  {
    "adaptation": {
      "mean": 23.5,
      "sd": 4.2,
      "n": 15,
      "unit": "degrees"
    },
    "retention_24h": {
      "mean": 18.3,
      "sd": 5.1,
      "n": 15
    },
    "statistics": {
      "vs_control": {
        "test": "t-test",
        "t_value": 3.45,
        "df": 28,
        "p_value": 0.002,
        "effect_size": 1.23,
        "comparison": "Experimental vs Control"
      }
    }
  }
  ```
- Handle table extraction for results (many papers report means/SDs in tables):
  - Consider adding `camelot-py` or `pdfplumber` for table parsing
  - Match table rows to group names
  - Parse columns for Mean, SD, N, p-value

### 4. Update CLI and validation for dual-mode operation

Add `--extract-level {experiment,group}` flag to `run_batch_extraction.py`. Update `validation/validator.py` to support both experiment-level and group-level gold standards. Maintain backward compatibility with existing `standards/gold_standard.csv` for experiment-level comparison.

**Details:**
- Modify `run_batch_extraction.py`:
  - Add CLI argument: `--extract-level {experiment,group}` (default: `'experiment'`)
  - Pass `extract_level` to `PDFExtractor` initialization
  - Handle group-level results in output JSON:
    ```python
    if args.extract_level == 'group':
        result = {
            'paper_name': paper_name,
            'experiment_id': exp_id,
            'groups': [
                {
                    'group_id': grp_id,
                    'group_name': grp_name,
                    'parameters': {...},
                    'results': {...}
                }
            ]
        }
    ```
- Update `validation/validator.py`:
  - Add `validate_groups()` method for group-level comparison
  - Support both gold standard formats:
    - Experiment-level: existing `gold_standard.csv`
    - Group-level: new `gold_standard_groups.csv`
  - Calculate separate metrics:
    - Group detection accuracy (TP, FP, FN for group identification)
    - Per-group parameter F1 scores
    - Results extraction precision/recall
  - Comparison logic:
    ```python
    def compare_study_with_groups(gold_groups, auto_groups):
        metrics = {
            'group_detection': {'tp': 0, 'fp': 0, 'fn': 0},
            'group_parameters': {},
            'results_extraction': {}
        }
        # Match groups by name (fuzzy matching)
        for gold_group in gold_groups:
            matched = find_matching_group(gold_group, auto_groups)
            if matched:
                metrics['group_detection']['tp'] += 1
                # Compare parameters and results
            else:
                metrics['group_detection']['fn'] += 1
        return metrics
    ```
- Maintain backward compatibility:
  - Default behavior (`--extract-level experiment`) uses existing validation
  - Group-level mode requires explicit opt-in

### 5. Test with multi-group papers and create sample gold standard

Manually annotate 3-5 multi-group papers (e.g., Butcher2018, Benson2011) with group-level ground truth. Run extraction in both modes, validate that experiment-level extraction still matches existing gold standard. Measure group detection accuracy and results extraction precision on annotated subset.

**Details:**
- Select test papers (criteria: clear multi-group design, reported results):
  - Butcher2018 (2 groups: Control vs Cursor feedback)
  - Benson2011 (3 groups: Gradual, Abrupt, Control)
  - Taylor2014 (2 groups: Implicit vs Explicit instruction)
  - Heuer2011 (multiple perturbation schedules)
  - Krakauer2006 (visuomotor vs force-field groups)
- Create `standards/gold_standard_groups.csv`:
  ```csv
  study_id,group_name,group_n,age_mean,age_sd,perturbation_type,rotation_deg,feedback_type,adaptation_mean,adaptation_sd,retention_mean,retention_sd,p_value,effect_size
  Butcher2018EXP1_Control,Control,12,20.1,1.8,visuomotor_rotation,45,no_cursor,12.3,3.4,8.2,2.1,,
  Butcher2018EXP1_Cursor,Cursor,12,19.8,2.1,visuomotor_rotation,45,cursor,23.5,4.2,18.3,5.1,0.002,1.23
  ```
- Run both modes on test set:
  ```bash
  # Experiment-level (baseline)
  python run_batch_extraction.py --extract-level experiment
  
  # Group-level (new)
  python run_batch_extraction.py --extract-level group
  ```
- Validation metrics to track:
  - **Group detection**: TP, FP, FN (are all groups identified?)
  - **Parameter extraction**: F1 per parameter (same as existing validation)
  - **Results extraction**: 
    - Numeric accuracy (mean ± threshold, e.g., within 0.5 degrees)
    - Statistical test capture rate (% of reported p-values extracted)
    - Effect size extraction rate
- Success criteria:
  - Experiment-level mode: F1 score unchanged from baseline
  - Group detection: >80% recall (catch most groups)
  - Results extraction: >60% precision (what we extract is correct)
- Document findings in `docs/GROUP_LEVEL_VALIDATION_REPORT.md`

## Further Considerations

### 1. Gold standard transition strategy

Should we maintain separate `gold_standard_experiment.csv` and `gold_standard_groups.csv` files, or add a `has_groups` flag to unify them? 

**Recommendation**: Maintain separate files initially for clean migration:
- `standards/gold_standard.csv` - Existing experiment-level annotations (keep unchanged)
- `standards/gold_standard_groups.csv` - New group-level annotations
- Benefits:
  - Clear separation during development/validation
  - Existing validation pipeline unaffected
  - Easier to compare experiment-level vs group-level extraction quality
- Once group-level extraction is stable (F1 > 0.7), consider unified format with `has_groups` flag

Alternative approach: Add `has_groups` column to existing CSV:
```csv
study_id,has_groups,group_id,group_name,n_total,group_n,age_mean,...
Butcher2018EXP1,TRUE,Butcher2018EXP1_Control,Control,24,12,20.1,...
Butcher2018EXP1,TRUE,Butcher2018EXP1_Cursor,Cursor,24,12,19.8,...
Taylor2010EXP1,FALSE,,,18,18,22.3,...
```
- Pros: Single source of truth
- Cons: More complex validation logic, harder to maintain backward compatibility

### 2. Results extraction scope

Start with basic statistics (means, SDs, sample sizes, p-values) or immediately include effect sizes, confidence intervals, and complex ANOVA structures?

**Recommendation**: Phased approach starting minimal:

**Phase 1 (MVP)**: Basic descriptive statistics
- Means and standard deviations
- Sample sizes (if reported with results)
- Basic p-values from t-tests

**Phase 2**: Statistical tests
- t-test parameters (t-value, df, p-value)
- ANOVA F-tests (F-value, df1, df2, p-value)
- Post-hoc test indicators

**Phase 3**: Effect sizes and advanced metrics
- Cohen's d, partial η², confidence intervals
- Learning rate parameters (slope, asymptote)
- Retention indices (savings, washout rate)

Rationale:
- Establish extraction pipeline with high-precision basics first
- Validate that pattern matching works before adding complexity
- Later phases can use LLM for complex statistical prose
- Meta-analysis needs (Step 6 in user's plan) will guide which metrics to prioritize

### 3. PCA/visualization integration

Implement after extraction is stable, or build concurrently to validate that group-level data enables better design space clustering?

**Recommendation**: Sequential implementation (extraction first, then analysis)

**Why extraction first**:
- PCA requires complete parameter matrix (missing data problematic)
- Need sufficient group-level extractions (>30 groups) for meaningful clustering
- Visualization goals will inform which parameters to prioritize extracting
- Reduces scope creep and maintains focus on stable extraction

**Proposed timeline**:
1. **Weeks 1-4**: Implement Steps 1-3 (schema, extraction, results)
2. **Week 5**: Validate and refine extraction (Step 5)
3. **Weeks 6-8**: Build PCA/visualization module (user's original Step 6)

**PCA module requirements** (for later):
- Design space analyzer class
- Parameter matrix construction (handle missing data, mixed types)
- Dimensionality reduction (PCA, t-SNE, UMAP)
- Clustering analysis (hierarchical, k-means)
- Interactive visualization (Plotly/Streamlit dashboard)
- Color-coding by results (e.g., effect size heatmap on PCA plot)

**Early validation approach** (compromise):
- After completing Steps 1-3, run simple exploratory analysis:
  - Count groups per experiment (distribution)
  - Parameter co-occurrence matrix (which params vary by group?)
  - Results availability (how many groups have extractable means/SDs?)
- Use these insights to prioritize which parameters/results to improve extraction for
- Full PCA implementation after validation is stable

### 4. LLM integration for group and results extraction

When should LLM assistance be added for group detection and results parsing?

**Recommendation**: Rule-based first, LLM fallback later

**Rule-based approach** (Steps 1-5):
- Regex patterns for common formats
- High precision but lower recall
- Fast and deterministic
- Good for validation baseline

**LLM enhancement** (post-validation):
- For ambiguous group descriptions: "The first group received..."
- Complex statistical prose: "only the abrupt group showed savings..."
- Table interpretation when structure varies
- Resolving group name synonyms (fuzzy matching backup)

**Implementation strategy**:
- Add `llm_assist_groups` flag (default: False)
- LLM only called when rule-based extraction:
  - Finds 0 groups but text suggests multi-group design
  - Detects N groups but extracts N-1 (missing one)
  - Results section mentions group names not found in Methods
- Use same LLM integration pattern as existing parameter extraction:
  - Verify rule-based results
  - Infer missing information
  - Structured output for parsing

### 5. Database migration strategy

How to handle transition from existing experiment-only database to group-aware schema?

**Recommendation**: Additive migration with experiment-level defaults

**Migration approach**:
```python
# database/migrations/add_groups_v1_5.py

def migrate_experiment_to_groups(session):
    """Create default group for each existing experiment."""
    experiments = session.query(Experiment).all()
    
    for exp in experiments:
        # Create single "default" group inheriting experiment params
        default_group = Group(
            id=f"{exp.id}_DEFAULT",
            experiment_id=exp.id,
            group_number=1,
            group_name="Default",
            group_type="experiment_level",
            sample_size_n=exp.sample_size_n,
            age_mean=exp.age_mean,
            age_sd=exp.age_sd,
            # Inherit all experiment-level parameters
        )
        session.add(default_group)
    
    session.commit()
```

**Benefits**:
- Existing experiments automatically get 1 group (backward compatible)
- Queries can uniformly use `Experiment.groups` relationship
- Re-extraction can update from default to actual groups
- No data loss

**Alternative**: Leave existing experiments without groups
- Only new extractions populate groups
- Queries must handle `None` groups
- Simpler migration but inconsistent data model

### 6. Performance considerations for batch processing

How will group-level extraction affect processing time and parallelization?

**Current performance** (from optimization summary):
- 18 PDFs in ~8-15 minutes (4x parallel workers)
- ~27-50 seconds per PDF

**Group-level impact**:
- Additional regex patterns: +5-10% processing time
- Group detection: minimal (single pass)
- Results extraction (if scanning entire Results section): +20-30% time
- LLM assistance for groups (if enabled): +30-50% time per paper

**Mitigation strategies**:
1. **Targeted text extraction**:
   - Only scan Methods section for group detection
   - Only scan Results section for outcome extraction
   - Skip group extraction for papers with `n_total < 15` (likely single group)

2. **Parallel group processing**:
   - Once groups detected, extract parameters for each group in parallel (ThreadPoolExecutor)
   - Minimal overhead since groups share same PDF text

3. **Caching**:
   - Cache group detection results separately from parameters
   - Re-use preprocessed PDF text for both experiment and group modes

4. **Batch size tuning**:
   - Current: 4 parallel workers, 4 LLM batch size
   - Group mode: Consider reducing to 3 workers to account for +30% per-paper time
   - Keep total cluster time similar (~15-20 minutes for 18 PDFs)

**Testing plan**:
- Run group-level extraction on 5 papers, measure time increase
- If >50% slower, optimize by targeted text extraction
- Ensure total batch time stays under 30 minutes for 18 PDFs

### 7. Handling papers without clear groups

What to do with single-group experiments or papers that don't report group-level statistics?

**Scenarios**:
1. **Single-group experiment** (e.g., within-subject design, all participants same condition)
2. **Multi-group but no group-specific parameters** (only aggregate results)
3. **Groups mentioned but not clearly defined** (ambiguous descriptions)

**Recommended handling**:

**Scenario 1 - Single group**:
```python
# Create one group labeled "All participants"
group = Group(
    group_name="All participants",
    group_type="single_group",
    sample_size_n=experiment.sample_size_n,
    # Inherit all experiment parameters
)
```

**Scenario 2 - Aggregate results only**:
```python
# Create groups with parameters but minimal results
# Flag: results_level = "experiment" (not group-specific)
```

**Scenario 3 - Ambiguous groups**:
```python
# Use LLM fallback or flag for manual review
group.extraction_confidence = "low"
group.needs_manual_review = True
```

**Database flag**: Add `Experiment.extraction_level` field:
- `"experiment"` - Single group, all parameters at experiment level
- `"group"` - Multiple groups, parameters vary by group
- `"mixed"` - Some parameters at experiment level, some vary by group

This allows queries like:
```python
# Only analyze experiments with true group-level variation
multi_group_exps = session.query(Experiment).filter(
    Experiment.extraction_level == "group"
).all()
```

## Implementation Checklist

### Week 1: Database Schema
- [ ] Design `Group` model in `database/models.py`
- [ ] Add relationships to `Experiment` model
- [ ] Write migration script `database/migrations/add_groups_v1_5.py`
- [ ] Test migration on copy of existing database
- [ ] Update `database/schema.py` if needed

### Week 2: Group Detection Patterns
- [ ] Add group detection patterns to `mapping/patterns.yaml`
- [ ] Implement `_detect_groups()` in `extractors/pdfs.py`
- [ ] Implement `_extract_group_names()` in `extractors/pdfs.py`
- [ ] Test on 5 multi-group papers (manual inspection)
- [ ] Measure group detection recall

### Week 3: Group Parameter Extraction
- [ ] Implement `_extract_group_parameters()` in `extractors/pdfs.py`
- [ ] Add `extract_level` parameter to `PDFExtractor.__init__()`
- [ ] Modify `extract_from_file()` to branch on `extract_level`
- [ ] Handle parameter inheritance (group overrides experiment)
- [ ] Test parameter extraction accuracy

### Week 4: Results Extraction
- [ ] Add results patterns to `mapping/patterns.yaml`
- [ ] Implement `_extract_group_results()` in `extractors/pdfs.py`
- [ ] Parse means, SDs, statistical tests
- [ ] Normalize to JSON format
- [ ] Test numeric extraction precision

### Week 5: CLI and Validation
- [ ] Add `--extract-level` flag to `run_batch_extraction.py`
- [ ] Create `standards/gold_standard_groups.csv` with 5 papers
- [ ] Implement `validate_groups()` in `validation/validator.py`
- [ ] Run validation on test set
- [ ] Document results in `docs/GROUP_LEVEL_VALIDATION_REPORT.md`

### Week 6 (Optional): PCA Module
- [ ] Create `analysis/design_space.py`
- [ ] Implement parameter matrix construction
- [ ] Add PCA, clustering methods
- [ ] Build visualization functions
- [ ] Test with group-level data

### Week 7-8 (Optional): Visualization Dashboard
- [ ] Create `analysis/dashboard.py` (Streamlit app)
- [ ] Interactive PCA plot with group coloring
- [ ] Parameter distribution plots
- [ ] Clustering dendrogram
- [ ] Export design space report

## Success Metrics

### Group Detection
- **Recall**: >80% (catch most groups in multi-group papers)
- **Precision**: >85% (few false positive groups)
- **F1 Score**: >0.80

### Parameter Extraction (Group-level)
- **Overall F1**: >0.60 (comparable to current experiment-level ~0.70)
- **Key parameters F1**: 
  - `sample_size_n`: >0.70
  - `perturbation_magnitude`: >0.60
  - `feedback_type`: >0.65

### Results Extraction
- **Numeric precision**: >75% (extracted values within tolerance)
- **Statistical test capture**: >60% (p-values, effect sizes found)
- **Coverage**: >40% (% of groups with any results extracted)

### Performance
- **Processing time**: <50% increase vs experiment-level mode
- **Batch completion**: <30 minutes for 18 PDFs
- **Stability**: No OOM errors, consistent results

### Backward Compatibility
- **Experiment-level F1**: No regression (maintain current ~0.70)
- **Gold standard comparison**: Existing papers still validate
- **API compatibility**: Old scripts work without modification
