# Group-Level Extraction: Quick Reference

## Quick Start (3 Commands)

```bash
# 1. Upgrade database
python -m database.migrations.add_groups_v1_5 out/designspace.db

# 2. Extract groups
python run_batch_extraction.py --pdf-dir papers/ --extract-level group --output-dir out/

# 3. Launch dashboard
streamlit run analysis/dashboard.py
```

## CLI Reference

### Extraction
```bash
# Experiment-level (default)
python run_batch_extraction.py --pdf-dir papers/ --output-dir out/

# Group-level
python run_batch_extraction.py --pdf-dir papers/ --extract-level group --output-dir out/
```

### Validation
```bash
# Experiment-level
python validation/validator_public.py \
  --local-file standards/gold_standard.csv \
  --results out/batch_processing_results.json

# Group-level
python validation/validator_public.py \
  --local-groups-file standards/gold_standard_groups.csv \
  --results out/batch_processing_results.json \
  --level group

# Both
python validation/validator_public.py \
  --local-file standards/gold_standard.csv \
  --local-groups-file standards/gold_standard_groups.csv \
  --results out/batch_processing_results.json \
  --level both
```

### Migration
```bash
# Upgrade to v1.5
python -m database.migrations.add_groups_v1_5 out/designspace.db

# Rollback
python -m database.migrations.add_groups_v1_5 out/designspace.db --rollback

# Verify
sqlite3 out/designspace.db "SELECT name FROM sqlite_master WHERE type='table';"
```

## Python API Reference

### Load and Analyze Data

```python
from analysis.design_space import DesignSpaceAnalyzer

# Initialize
analyzer = DesignSpaceAnalyzer(level='group')  # or 'experiment'

# Load from database
analyzer.load_from_database('out/designspace.db')

# Load from JSON
analyzer.load_from_json('out/batch_processing_results.json')

# Create parameter matrix
analyzer.create_parameter_matrix(
    missing_strategy='median',  # 'median', 'mean', 'zero', 'drop'
    scale=True  # Standardize features
)
```

### Dimensionality Reduction

```python
# PCA
pca = analyzer.run_pca(n_components=3)
print(pca['explained_variance'])  # Variance per component
print(pca['loadings'])            # Feature contributions

# t-SNE
tsne = analyzer.run_tsne(n_components=2, perplexity=30)

# UMAP (requires umap-learn)
umap = analyzer.run_umap(n_components=2, n_neighbors=15)
```

### Visualization

```python
# 2D PCA plot
analyzer.plot_pca_2d(
    pca,
    color_by='perturbation_class',  # Color by parameter
    save_path='pca_2d.png'
)

# 3D PCA plot
analyzer.plot_pca_3d(pca, color_by='rotation_magnitude_deg')

# Scree plot
analyzer.plot_scree(pca, save_path='scree.png')
```

### Clustering

```python
# K-means
kmeans = analyzer.cluster_kmeans(n_clusters=5)
print(f"Silhouette: {kmeans['silhouette_score']:.3f}")
print(f"Labels: {kmeans['labels']}")

# Hierarchical
hier = analyzer.cluster_hierarchical(
    n_clusters=5,
    linkage='ward'  # 'ward', 'complete', 'average', 'single'
)
```

### Feature Analysis

```python
# Top contributing features to PC1
top_features = analyzer.get_top_features(pca, component=0, n_top=10)
for feature, loading in top_features:
    print(f"{feature}: {loading:.3f}")

# Parameter matrix access
df = analyzer.parameter_matrix
print(df.columns)
print(df.describe())
```

## Database Schema (v1.5)

### Group Model
```python
class Group(Base):
    __tablename__ = 'groups'
    
    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey('experiments.id'))
    group_name = Column(String)
    
    # Demographics
    sample_size_n = Column(Integer)
    age_mean = Column(Float)
    age_sd = Column(Float)
    sex_distribution = Column(String)
    
    # Perturbation
    rotation_magnitude_deg = Column(Float)
    force_field_type = Column(String)
    perturbation_schedule = Column(String)
    
    # Feedback
    feedback_type = Column(String)
    cursor_size_mm = Column(Float)
    error_clamp_angle_deg = Column(Float)
    
    # Results (JSON)
    results = Column(JSON)
```

### Query Examples
```python
from database.models import Session, Experiment, Group

session = Session()

# Get all groups
groups = session.query(Group).all()

# Get groups for specific study
exp = session.query(Experiment).filter_by(study_id='Butcher2018').first()
groups = exp.groups

# Filter by perturbation type
rotation_groups = session.query(Group).filter_by(
    force_field_type='visuomotor_rotation'
).all()
```

## Gold Standard Format

### Experiment-level (existing)
`standards/gold_standard.csv`
```csv
study_id,parameter_name,parameter_value,notes
Butcher2018,perturbation_class,visuomotor_rotation,
Butcher2018,rotation_magnitude_deg,30,
```

### Group-level (new)
`standards/gold_standard_groups.csv`
```csv
study_id,group_name,group_n,age_mean,age_sd,perturbation_type,rotation_deg,feedback_type,adaptation_mean,adaptation_sd,retention_mean,retention_sd,p_value,effect_size,notes
Butcher2018,control,12,24.5,3.2,none,0,continuous,5.2,2.1,4.8,1.9,,,No perturbation
Butcher2018,rotation_30,12,23.8,2.9,visuomotor_rotation,30,continuous,18.5,4.2,12.3,3.8,0.001,0.85,30° rotation
```

## Key Files

| File | Purpose |
|------|---------|
| `database/models.py` | Group model definition |
| `database/migrations/add_groups_v1_5.py` | Migration script |
| `mapping/patterns.yaml` | Group detection patterns |
| `extractors/group_extractor.py` | Group extraction logic |
| `extractors/pdfs.py` | Modified PDFExtractor |
| `run_batch_extraction.py` | CLI with --extract-level |
| `analysis/design_space.py` | PCA/clustering backend |
| `analysis/dashboard.py` | Streamlit frontend |
| `analysis/requirements.txt` | Analysis dependencies |
| `validation/validator_public.py` | Enhanced validator |
| `standards/gold_standard_groups.csv` | Group gold standard |

## Common Patterns

### Compare Groups Across Studies
```python
# Filter rotation studies
rotation_groups = analyzer.parameter_matrix[
    analyzer.parameter_matrix['perturbation_class'] == 'visuomotor_rotation'
]

# Group by rotation magnitude
import pandas as pd
rotation_summary = rotation_groups.groupby('rotation_magnitude_deg').agg({
    'sample_size_n': 'sum',
    'age_mean': 'mean'
})
print(rotation_summary)
```

### Find Similar Studies
```python
# Run PCA
pca = analyzer.run_pca(n_components=10)

# Cluster
clusters = analyzer.cluster_kmeans(n_clusters=8)

# Find studies in same cluster
analyzer.parameter_matrix['cluster'] = clusters['labels']
cluster_0 = analyzer.parameter_matrix[analyzer.parameter_matrix['cluster'] == 0]
print(cluster_0[['study_id', 'group_name', 'perturbation_class']])
```

### Export for External Analysis
```python
# Save parameter matrix
analyzer.parameter_matrix.to_csv('parameter_matrix.csv', index=False)

# Save PCA results
pca_df = pd.DataFrame(
    pca['components'],
    columns=[f'PC{i+1}' for i in range(pca['components'].shape[1])]
)
pca_df.to_csv('pca_components.csv', index=False)

# Save loadings
loadings_df = pd.DataFrame(
    pca['loadings'],
    columns=[f'PC{i+1}' for i in range(pca['loadings'].shape[1])],
    index=analyzer.feature_names
)
loadings_df.to_csv('pca_loadings.csv')
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No groups detected | Check patterns in `mapping/patterns.yaml` |
| Wrong group count | Update group identification patterns |
| Missing parameters | Verify parameter inheritance logic |
| Low validation F1 | Check gold standard format matching |
| Dashboard won't start | `pip install -r analysis/requirements.txt` |
| UMAP not available | `pip install umap-learn` |
| Database locked | Close other connections, check permissions |

## Next Steps

1. **Run migration**: Upgrade database schema
2. **Test extraction**: Process 1-2 papers with `--extract-level group`
3. **Validate results**: Compare against gold standard
4. **Explore dashboard**: Launch Streamlit app
5. **Analyze design space**: Run PCA, identify clusters
6. **Iterate patterns**: Improve group detection patterns based on results

---

**Full Documentation**: `docs/GROUP_LEVEL_EXTRACTION_GUIDE.md`
