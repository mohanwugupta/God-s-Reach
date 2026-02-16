# Group-Level Parameter Extraction Guide

## Overview

The design space extractor now supports **dual-mode extraction** at both experiment-level and group-level granularity. This enhancement enables analysis of within-study experimental groups, capturing group-specific demographics, perturbation parameters, and outcome results.

## Features

### Database Schema (v1.5)

New `Group` model with fields:
- **Demographics**: `sample_size_n`, `age_mean`, `age_sd`, `sex_distribution`
- **Perturbation Parameters**: `rotation_magnitude_deg`, `force_field_type`, `perturbation_schedule`
- **Feedback Parameters**: `feedback_type`, `cursor_size_mm`, `error_clamp_angle_deg`
- **Results**: JSON field storing means, SDs, statistical tests, effect sizes

Migration script: `database/migrations/add_groups_v1_5.py`

### Extraction Modes

1. **Experiment-level** (default): One record per study
2. **Group-level**: Multiple records per study, one per experimental group

### Pattern Library

Added 100+ regex patterns to `mapping/patterns.yaml`:
- Group identification (e.g., "control group", "rotation group")
- Group names and labels
- Sample sizes per group
- Statistical results (means, SDs, t-tests, ANOVAs, effect sizes)

### Extraction Architecture

**Mixin-based design** for clean separation:
- `GroupExtractionMixin` (530 lines) - Group detection and parameter extraction logic
- `PDFExtractor` inherits from mixin for dual-mode support

Key methods:
- `_detect_groups()` - Identifies number of groups and names
- `_extract_group_parameters()` - Extracts group-specific parameters
- `_extract_group_results()` - Parses outcome metrics and statistics
- `extract_group_level()` - Main orchestration method

### Analysis Tools

**Design Space Analyzer** (`analysis/design_space.py`):
- PCA, t-SNE, UMAP dimensionality reduction
- Hierarchical and k-means clustering
- 2D/3D visualization with parameter color-coding
- Scree plots and feature importance
- Supports both experiment-level and group-level matrices

**Interactive Dashboard** (`analysis/dashboard.py`):
- Streamlit app for design space exploration
- Interactive Plotly visualizations
- Parameter distribution analysis
- Clustering quality metrics
- Export to CSV

### Validation

Enhanced validator supports:
- `validate_groups()` - Group-level comparison
- `compare_study_with_groups()` - Dual-level validation
- Group-level F1 scores per parameter
- Gold standard: `standards/gold_standard_groups.csv`

## Usage

### 1. Run Migration

Upgrade database to schema v1.5:

```bash
python -m database.migrations.add_groups_v1_5 out/designspace.db
```

Verify migration:
```bash
sqlite3 out/designspace.db "SELECT name FROM sqlite_master WHERE type='table';"
# Should show: experiments, groups
```

### 2. Extract at Group Level

Run batch extraction with `--extract-level group`:

```bash
python run_batch_extraction.py \
  --pdf-dir papers/ \
  --output-dir out/ \
  --batch-size 10 \
  --extract-level group
```

This will:
- Detect groups in each study
- Extract group-specific parameters
- Parse group-level results (means, SDs, statistics)
- Store in `Group` table with foreign key to parent `Experiment`

### 3. Validate Extraction

Compare against gold standard:

```bash
# Experiment-level validation (existing)
python validation/validator_public.py \
  --local-file standards/gold_standard.csv \
  --results out/batch_processing_results.json \
  --level experiment

# Group-level validation (new)
python validation/validator_public.py \
  --local-groups-file standards/gold_standard_groups.csv \
  --results out/batch_processing_results.json \
  --level group

# Both levels
python validation/validator_public.py \
  --local-file standards/gold_standard.csv \
  --local-groups-file standards/gold_standard_groups.csv \
  --results out/batch_processing_results.json \
  --level both
```

### 4. Analyze Design Space

**Python API**:

```python
from analysis.design_space import DesignSpaceAnalyzer

# Initialize analyzer
analyzer = DesignSpaceAnalyzer(
    db_path='out/designspace.db',
    level='group'  # or 'experiment'
)

# Load data
analyzer.load_from_database('out/designspace.db')

# Create parameter matrix
analyzer.create_parameter_matrix(
    missing_strategy='median',  # 'median', 'mean', 'zero', or 'drop'
    scale=True  # Standardize features
)

# Run PCA
pca_results = analyzer.run_pca(n_components=3)
print(f"Explained variance: {pca_results['explained_variance']}")

# Plot 2D
analyzer.plot_pca_2d(
    pca_results,
    color_by='perturbation_class',
    save_path='pca_plot.png'
)

# Clustering
clusters = analyzer.cluster_kmeans(n_clusters=5)
print(f"Silhouette score: {clusters['silhouette_score']:.3f}")

# Top features
top_features = analyzer.get_top_features(pca_results, component=0, n_top=10)
for feature, loading in top_features:
    print(f"{feature}: {loading:.3f}")
```

**Dashboard**:

```bash
# Install dependencies
pip install -r analysis/requirements.txt

# Launch dashboard
streamlit run analysis/dashboard.py
```

Dashboard features:
- Load data from database or JSON
- Select analysis level (experiment/group)
- Interactive PCA/t-SNE/UMAP plots with parameter color-coding
- Hierarchical and k-means clustering with quality metrics
- Parameter distribution histograms
- Export parameter matrix to CSV

### 5. Create Gold Standard

Template in `standards/gold_standard_groups.csv`:

```csv
study_id,group_name,group_n,age_mean,age_sd,perturbation_type,rotation_deg,feedback_type,adaptation_mean,adaptation_sd,retention_mean,retention_sd,p_value,effect_size,notes
Butcher2018,control,12,24.5,3.2,none,0,continuous,5.2,2.1,4.8,1.9,,,No perturbation
Butcher2018,rotation_30,12,23.8,2.9,visuomotor_rotation,30,continuous,18.5,4.2,12.3,3.8,0.001,0.85,30° rotation
```

Columns:
- **study_id**: Author+Year (e.g., Butcher2018)
- **group_name**: Label (e.g., "control", "rotation_30")
- **group_n**: Sample size
- **age_mean**, **age_sd**: Demographics
- **perturbation_type**, **rotation_deg**: Perturbation parameters
- **feedback_type**: Feedback condition
- **adaptation_mean**, **adaptation_sd**: Adaptation phase results
- **retention_mean**, **retention_sd**: Retention phase results
- **p_value**, **effect_size**: Statistical comparisons
- **notes**: Additional context

## Implementation Details

### Group Detection Logic

1. **Pattern Matching**: Searches for phrases like:
   - "participants were divided into N groups"
   - "control group vs experimental group"
   - "Group 1 (n=20) and Group 2 (n=18)"

2. **Name Extraction**: Parses group labels:
   - "control", "rotation", "force field"
   - "Group A", "Group B"
   - Numbered groups (Group 1, Group 2)

3. **Sample Size Extraction**: Regex patterns for:
   - "n = 12", "N=20"
   - "12 participants", "20 subjects"
   - Inline notation: "control group (n=15)"

### Parameter Inheritance

Groups inherit experiment-level defaults, then override with group-specific values:

```python
# Example: Experiment has rotation_magnitude_deg = 30
# Group 1 inherits 30° rotation
# Group 2 overrides with 60° rotation
```

This handles cases where:
- Common parameters are specified once at experiment level
- Specific groups modify certain parameters
- Not all parameters are repeated per group

### Results Parsing

Regex patterns extract:
- **Means and SDs**: "mean ± SD", "M = X, SD = Y"
- **T-tests**: "t(df) = X, p < 0.05"
- **ANOVAs**: "F(df1, df2) = X, p = Y"
- **Effect sizes**: "Cohen's d = 0.8", "η² = 0.25"

Structured JSON storage:
```json
{
  "adaptation": {"mean": 18.5, "sd": 4.2},
  "retention": {"mean": 12.3, "sd": 3.8},
  "statistical_tests": [
    {
      "test_type": "t_test",
      "t_value": 3.45,
      "df": 22,
      "p_value": 0.001
    }
  ],
  "effect_sizes": [
    {"metric": "cohen_d", "value": 0.85}
  ]
}
```

### Backward Compatibility

- Default `extract_level='experiment'` preserves existing behavior
- Migration creates default groups for existing experiments
- Experiment-level gold standard still works
- No breaking changes to existing API

## File Structure

```
designspace_extractor/
├── database/
│   ├── models.py                    # Added Group model
│   └── migrations/
│       └── add_groups_v1_5.py       # Migration script
├── mapping/
│   └── patterns.yaml                # Added 100+ group patterns
├── extractors/
│   ├── group_extractor.py           # NEW: GroupExtractionMixin
│   └── pdfs.py                      # Modified: Inherits mixin
├── analysis/                        # NEW: Analysis module
│   ├── __init__.py
│   ├── design_space.py              # PCA, clustering, visualization
│   ├── dashboard.py                 # Streamlit app
│   └── requirements.txt             # Analysis dependencies
├── validation/
│   └── validator_public.py          # Enhanced: Group validation
├── standards/
│   └── gold_standard_groups.csv     # NEW: Group-level gold standard
└── run_batch_extraction.py          # Added --extract-level flag
```

## Examples

### Example 1: Compare Rotation Magnitudes

Extract groups with different rotation angles:

```python
analyzer = DesignSpaceAnalyzer(level='group')
analyzer.load_from_database('out/designspace.db')
analyzer.create_parameter_matrix()

# Filter to rotation studies
rotation_mask = analyzer.parameter_matrix['perturbation_class'] == 'visuomotor_rotation'
rotation_data = analyzer.parameter_matrix[rotation_mask]

# Group by rotation magnitude
import matplotlib.pyplot as plt
rotation_data.groupby('rotation_magnitude_deg')['sample_size_n'].sum().plot(kind='bar')
plt.xlabel('Rotation Magnitude (deg)')
plt.ylabel('Total Participants')
plt.title('Distribution of Sample Sizes by Rotation Magnitude')
plt.show()
```

### Example 2: Cluster Studies by Parameters

Find natural groupings in design space:

```python
# Run hierarchical clustering
clusters = analyzer.cluster_hierarchical(n_clusters=5, linkage='ward')

# Add cluster labels to data
analyzer.parameter_matrix['cluster'] = clusters['labels']

# Run PCA and color by cluster
pca_results = analyzer.run_pca(n_components=2)
analyzer.plot_pca_2d(pca_results, color_by='cluster', save_path='clusters.png')

# Analyze cluster characteristics
for cluster_id in range(5):
    cluster_data = analyzer.parameter_matrix[analyzer.parameter_matrix['cluster'] == cluster_id]
    print(f"\nCluster {cluster_id}:")
    print(cluster_data[['perturbation_class', 'rotation_magnitude_deg', 'feedback_type']].describe())
```

### Example 3: Interactive Dashboard Exploration

```bash
streamlit run analysis/dashboard.py
```

1. Load database: `out/designspace.db`
2. Select analysis level: `group`
3. Navigate to **Dimensionality Reduction** tab
4. Select PCA, 2D, color by `perturbation_class`
5. Click **Run Analysis**
6. Explore clusters in **Clustering** tab
7. Check parameter distributions in **Parameter Distributions** tab
8. Export matrix from **Sample Details** tab

## Troubleshooting

### Group Detection Issues

**Problem**: No groups detected for a study
- **Check**: Pattern matches in `mapping/patterns.yaml`
- **Solution**: Add study-specific patterns, review methods section

**Problem**: Wrong number of groups
- **Check**: Group identification patterns
- **Solution**: Update regex patterns for edge cases

### Validation Issues

**Problem**: Low F1 scores for group-level validation
- **Check**: Gold standard format matches extraction output
- **Solution**: Review parameter name mappings in validator

**Problem**: Groups not matching between gold and automated
- **Check**: Group name consistency
- **Solution**: Add name normalization logic

### Analysis Issues

**Problem**: Missing data in parameter matrix
- **Solution**: Use `missing_strategy='median'` or `'drop'`

**Problem**: Dashboard won't load
- **Check**: Dependencies installed (`pip install -r analysis/requirements.txt`)
- **Solution**: Verify database path, check for UMAP installation

## Future Enhancements

1. **LLM-based group detection** for complex experimental designs
2. **Multi-level models** for nested group structures
3. **Temporal analysis** of adaptation curves per group
4. **Meta-analysis** aggregation across studies
5. **Interactive filters** in dashboard (by year, population, etc.)

## References

- Database schema: `database/models.py`
- Patterns library: `mapping/patterns.yaml`
- Extraction logic: `extractors/group_extractor.py`
- Analysis tools: `analysis/design_space.py`
- Dashboard: `analysis/dashboard.py`
- Validation: `validation/validator_public.py`

---

**Version**: 1.5  
**Last Updated**: 2024  
**Maintainer**: Design Space Extraction Team
