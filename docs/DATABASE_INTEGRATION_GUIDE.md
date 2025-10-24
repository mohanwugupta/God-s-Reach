# Database Integration Guide for Multi-Experiment Extraction

## Overview

This guide documents how to integrate the batch extraction results with the SQLite database using the multi-experiment schema (v1.4).

---

## 1. Database Schema v1.4 Structure

### Core Tables

#### `experiments` Table
```sql
CREATE TABLE experiments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    
    -- Multi-experiment support
    parent_experiment_id TEXT REFERENCES experiments(id),
    experiment_number INTEGER,  -- 1, 2, 3... within a paper
    paper_id TEXT,             -- Shared ID for all experiments from same paper
    is_multi_experiment BOOLEAN DEFAULT FALSE,
    
    -- Experiment metadata
    study_type TEXT,
    publication_doi TEXT,
    lab_name TEXT,
    principal_investigator TEXT,
    
    -- Sample information
    sample_size_n INTEGER,
    age_mean REAL,
    age_sd REAL,
    handedness_criteria TEXT,
    
    -- [Additional fields...]
    
    -- Provenance
    schema_version TEXT DEFAULT '1.4',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### `multi_experiment_groups` Table
```sql
CREATE TABLE multi_experiment_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT UNIQUE NOT NULL,
    total_experiments INTEGER NOT NULL,
    shared_parameters TEXT,  -- JSON
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Database Views

#### `v_multi_experiment_groups`
Shows papers with multiple experiments grouped together:
```sql
CREATE VIEW v_multi_experiment_groups AS
SELECT 
    paper_id,
    COUNT(*) as experiment_count,
    GROUP_CONCAT(id) as experiment_ids
FROM experiments
WHERE is_multi_experiment = TRUE
GROUP BY paper_id;
```

#### `v_experiment_hierarchy`
Shows parent-child relationships:
```sql
CREATE VIEW v_experiment_hierarchy AS
SELECT 
    e1.id as parent_id,
    e1.name as parent_name,
    e2.id as child_id,
    e2.name as child_name,
    e2.experiment_number
FROM experiments e1
LEFT JOIN experiments e2 ON e1.id = e2.parent_experiment_id
WHERE e1.parent_experiment_id IS NULL;
```

---

## 2. Integration Architecture

### Data Flow

```
PDF Files
    ↓
batch_process_papers.py
    ↓
batch_processing_results.json
    ↓
database_integration.py
    ↓
SQLite Database (designspace.db)
```

### Current Batch Results Structure

```json
{
  "paper_name": "McDougle and Taylor - 2019.pdf",
  "success": true,
  "is_multi_experiment": true,
  "num_experiments": 4,
  "param_counts": [25, 25, 25, 25],
  "unique_params": 25,
  "all_params": ["authors", "year", ...],
  "extraction_result": {
    "experiments": [
      {
        "experiment_number": 1,
        "parameters": {...},
        "confidence_scores": {...}
      },
      ...
    ],
    "shared_parameters": {...}
  }
}
```

---

## 3. Database Integration Script

### Implementation: `database_integration.py`

```python
#!/usr/bin/env python3
"""
Database Integration Script
Loads batch extraction results into SQLite database with multi-experiment support.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from database.models import Database, Experiment, MultiExperimentGroup


def generate_experiment_id(paper_name, exp_number=None):
    """Generate unique experiment ID."""
    # Extract first author and year
    parts = paper_name.replace('.pdf', '').split(' - ')
    author = parts[0].split(' ')[0] if parts else 'Unknown'
    year = parts[1] if len(parts) > 1 else datetime.now().year
    
    if exp_number is not None:
        return f"{author}{year}_E{exp_number}"
    else:
        return f"{author}{year}"


def create_experiment_record(paper_name, exp_data, exp_number, paper_id, is_multi):
    """Create an Experiment database record from extraction data."""
    
    params = exp_data.get('parameters', {})
    confidence = exp_data.get('confidence_scores', {})
    
    # Generate unique ID
    exp_id = generate_experiment_id(paper_name, exp_number if is_multi else None)
    
    # Create experiment record
    experiment = {
        'id': exp_id,
        'name': f"{paper_name} - Experiment {exp_number}" if is_multi else paper_name,
        'description': f"Extracted from {paper_name}",
        
        # Multi-experiment fields
        'parent_experiment_id': None,  # Set later if needed
        'experiment_number': exp_number if is_multi else None,
        'paper_id': paper_id,
        'is_multi_experiment': is_multi,
        
        # Extracted parameters
        'study_type': params.get('perturbation_class'),
        'publication_doi': params.get('doi_or_url'),
        'lab_name': params.get('lab'),
        'principal_investigator': None,  # Rarely extracted
        
        'sample_size_n': params.get('sample_size_n') or params.get('n_total'),
        'age_mean': params.get('age_mean'),
        'age_sd': params.get('age_sd'),
        'handedness_criteria': params.get('handedness'),
        
        # Store full extraction as JSON
        'extracted_params': json.dumps(params),
        'metadata': json.dumps({
            'confidence_scores': confidence,
            'extraction_date': datetime.now().isoformat(),
            'source': 'pdf_batch_extraction',
            'paper_name': paper_name
        }),
        
        'schema_version': '1.4',
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    return experiment


def integrate_batch_results(results_file, database_path='./out/designspace.db'):
    """
    Integrate batch processing results into database.
    
    Args:
        results_file: Path to batch_processing_results.json
        database_path: Path to SQLite database
    """
    
    # Initialize database
    db = Database(database_path)
    db.create_tables()
    session = db.get_session()
    
    # Load batch results
    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    print(f"Loading {len(results)} papers into database...")
    
    inserted_count = 0
    multi_exp_count = 0
    
    for result in results:
        if not result['success']:
            print(f"  Skipping failed: {result['paper_name']}")
            continue
        
        paper_name = result['paper_name']
        is_multi = result['is_multi_experiment']
        paper_id = generate_experiment_id(paper_name)
        
        # Get experiments
        extraction = result['extraction_result']
        experiments = extraction.get('experiments', [extraction])
        
        # Create multi-experiment group if needed
        if is_multi:
            try:
                group = MultiExperimentGroup(
                    paper_id=paper_id,
                    total_experiments=len(experiments),
                    shared_parameters=json.dumps(extraction.get('shared_parameters', {}))
                )
                session.add(group)
                session.flush()
                multi_exp_count += 1
            except Exception as e:
                print(f"  Warning: Could not create group for {paper_name}: {e}")
        
        # Insert each experiment
        parent_id = None
        for idx, exp_data in enumerate(experiments, 1):
            try:
                exp_record = create_experiment_record(
                    paper_name, exp_data, idx, paper_id, is_multi
                )
                
                # Set parent relationship (first experiment is parent)
                if is_multi:
                    if idx == 1:
                        parent_id = exp_record['id']
                    else:
                        exp_record['parent_experiment_id'] = parent_id
                
                # Create Experiment object
                experiment = Experiment(**exp_record)
                session.add(experiment)
                inserted_count += 1
                
            except Exception as e:
                print(f"  Error inserting {paper_name} Exp {idx}: {e}")
        
        print(f"  ✓ {paper_name}: {len(experiments)} experiment(s)")
    
    # Commit all changes
    try:
        session.commit()
        print(f"\n✓ Successfully integrated:")
        print(f"  - {inserted_count} experiments")
        print(f"  - {multi_exp_count} multi-experiment groups")
    except Exception as e:
        session.rollback()
        print(f"\n✗ Database commit failed: {e}")
    finally:
        session.close()


def query_multi_experiment_papers(database_path='./out/designspace.db'):
    """Query and display multi-experiment papers from database."""
    
    db = Database(database_path)
    session = db.get_session()
    
    # Query multi-experiment papers
    results = session.query(Experiment)\
        .filter(Experiment.is_multi_experiment == True)\
        .order_by(Experiment.paper_id, Experiment.experiment_number)\
        .all()
    
    # Group by paper
    papers = {}
    for exp in results:
        if exp.paper_id not in papers:
            papers[exp.paper_id] = []
        papers[exp.paper_id].append(exp)
    
    print(f"\nMulti-Experiment Papers in Database: {len(papers)}")
    print("="*80)
    
    for paper_id, experiments in papers.items():
        print(f"\n{paper_id}")
        print(f"  Total Experiments: {len(experiments)}")
        for exp in experiments:
            print(f"    Exp {exp.experiment_number}: {exp.id}")
            params = json.loads(exp.extracted_params) if exp.extracted_params else {}
            print(f"      Parameters: {len(params)}")
    
    session.close()


if __name__ == '__main__':
    # Integrate batch results
    results_file = Path(__file__).parent / 'batch_processing_results.json'
    integrate_batch_results(results_file)
    
    # Query results
    query_multi_experiment_papers()
```

---

## 4. Usage Instructions

### Step 1: Run Batch Extraction
```bash
python run_batch_extraction.py
```
Generates: `batch_processing_results.json`

### Step 2: Integrate with Database
```bash
python database_integration.py
```

### Step 3: Verify Integration
```python
from database.models import Database

db = Database('./out/designspace.db')
session = db.get_session()

# Count total experiments
total = session.query(Experiment).count()
print(f"Total experiments: {total}")

# Count multi-experiment papers
multi = session.query(Experiment)\
    .filter(Experiment.is_multi_experiment == True)\
    .count()
print(f"Multi-experiment entries: {multi}")

# Get a specific paper
paper = session.query(Experiment)\
    .filter(Experiment.paper_id == "McDougle2019")\
    .all()
for exp in paper:
    print(f"{exp.name}: Exp {exp.experiment_number}")
```

---

## 5. Query Examples

### Get All Multi-Experiment Papers
```python
multi_papers = session.query(MultiExperimentGroup).all()
for group in multi_papers:
    print(f"{group.paper_id}: {group.total_experiments} experiments")
```

### Get Experiment Hierarchy
```python
parents = session.query(Experiment)\
    .filter(Experiment.parent_experiment_id == None)\
    .filter(Experiment.is_multi_experiment == True)\
    .all()

for parent in parents:
    children = session.query(Experiment)\
        .filter(Experiment.parent_experiment_id == parent.id)\
        .all()
    print(f"{parent.name}:")
    for child in children:
        print(f"  - Exp {child.experiment_number}")
```

### Get Papers by Parameter Coverage
```python
# Papers with sample size
with_sample = session.query(Experiment)\
    .filter(Experiment.sample_size_n != None)\
    .count()
print(f"Papers with sample size: {with_sample}")

# Papers with DOI
with_doi = session.query(Experiment)\
    .filter(Experiment.publication_doi != None)\
    .count()
print(f"Papers with DOI: {with_doi}")
```

### Export Experiment Parameters
```python
import json

experiments = session.query(Experiment).all()
for exp in experiments:
    params = json.loads(exp.extracted_params)
    metadata = json.loads(exp.metadata)
    
    print(f"\n{exp.name}")
    print(f"  Sample size: {params.get('sample_size_n', 'N/A')}")
    print(f"  Perturbation: {params.get('perturbation_class', 'N/A')}")
    print(f"  Confidence: {metadata.get('confidence_scores', {})}")
```

---

## 6. Database Maintenance

### Backup Database
```bash
# Create backup
cp ./out/designspace.db ./out/designspace_backup_$(date +%Y%m%d).db

# Restore backup
cp ./out/designspace_backup_20251024.db ./out/designspace.db
```

### Update Existing Records
```python
# Update experiment description
exp = session.query(Experiment).filter_by(id="McDougle2019_E1").first()
exp.description = "Updated description"
session.commit()

# Add missing parameters
exp = session.query(Experiment).filter_by(id="Taylor2013_E2").first()
params = json.loads(exp.extracted_params)
params['new_parameter'] = 'value'
exp.extracted_params = json.dumps(params)
session.commit()
```

### Delete and Re-import
```python
# Delete all experiments from a specific paper
session.query(Experiment)\
    .filter(Experiment.paper_id == "McDougle2019")\
    .delete()
session.commit()

# Then re-run integration for that paper
```

---

## 7. Current Integration Status

### Batch Results Available
- ✅ `batch_processing_results.json` - 19 papers, 49 experiments
- ✅ `BATCH_PROCESSING_REPORT.txt` - Summary report
- ✅ `COMPREHENSIVE_CORPUS_ANALYSIS.md` - Detailed analysis

### Database Status
- ⚠️ Not yet integrated (integration script provided above)
- Database schema v1.4 ready
- Multi-experiment support fully implemented

### To Complete Integration
1. Run `database_integration.py` (script provided above)
2. Verify experiment count: Should be 49 experiments
3. Verify multi-experiment groups: Should be 13 groups
4. Query and validate sample records

---

## 8. Benefits of Database Integration

### Research Capabilities
1. **Cross-Paper Queries:** Find all papers using rotation perturbations
2. **Parameter Analysis:** Analyze distribution of sample sizes, rotation magnitudes
3. **Trend Analysis:** Study design choices over time (requires year data)
4. **Quality Assessment:** Identify papers with missing parameters

### Data Management
1. **Structured Storage:** Relational database vs. flat JSON
2. **Easy Updates:** Modify individual parameters without reprocessing
3. **Provenance Tracking:** Know when/how each parameter was extracted
4. **Version Control:** Track schema versions and changes

### Future Extensions
1. **Manual Overrides Table:** Correct extraction errors
2. **Validation Flags:** Mark validated vs. unvalidated parameters
3. **Confidence Thresholds:** Filter by extraction confidence
4. **Export Functions:** Generate CSV, Excel, or JSON exports for analysis

---

## 9. Next Steps

### Immediate (Week 1)
- [ ] Run `database_integration.py` on batch results
- [ ] Verify 49 experiments inserted correctly
- [ ] Spot-check 3-5 papers for accuracy
- [ ] Document any integration issues

### Short-Term (Week 2-3)
- [ ] Add manual validation table
- [ ] Create export functions (CSV, Excel)
- [ ] Build parameter coverage dashboard
- [ ] Implement confidence filtering queries

### Long-Term (Month 1-2)
- [ ] Manual validation of all 49 experiments
- [ ] Parameter distribution analysis
- [ ] Identify missing/rare parameters
- [ ] Cross-paper meta-analysis

---

## 10. Troubleshooting

### Common Issues

**Issue:** Duplicate primary key errors
```python
# Solution: Use unique IDs or check for existing
existing = session.query(Experiment).filter_by(id=exp_id).first()
if existing:
    session.merge(experiment)  # Update existing
else:
    session.add(experiment)  # Insert new
```

**Issue:** JSON decoding errors in parameters
```python
# Solution: Validate JSON before storage
import json
try:
    params = json.loads(exp.extracted_params)
except json.JSONDecodeError:
    print(f"Invalid JSON in {exp.id}")
    exp.extracted_params = "{}"  # Reset to empty
```

**Issue:** Missing parent experiment relationships
```python
# Solution: Query and fix relationships
children = session.query(Experiment)\
    .filter(Experiment.experiment_number > 1)\
    .filter(Experiment.parent_experiment_id == None)\
    .all()

for child in children:
    parent = session.query(Experiment)\
        .filter(Experiment.paper_id == child.paper_id)\
        .filter(Experiment.experiment_number == 1)\
        .first()
    if parent:
        child.parent_experiment_id = parent.id
session.commit()
```

---

**Document Version:** 1.0  
**Last Updated:** October 24, 2025  
**Related Documentation:** 
- `MULTI_EXPERIMENT_IMPLEMENTATION.md`
- `COMPREHENSIVE_CORPUS_ANALYSIS.md`
- `database/schema.sql`
