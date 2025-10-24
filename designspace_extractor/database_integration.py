#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Integration Script
Loads batch extraction results into SQLite database with multi-experiment support.
"""

import json
import sys
import io
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Set UTF-8 encoding for console output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from database.models import Database, Base, Experiment
from sqlalchemy import text


def generate_experiment_id(paper_name: str, exp_number: int = None) -> str:
    """Generate unique experiment ID from paper name."""
    # Extract first author and year
    parts = paper_name.replace('.pdf', '').split(' - ')
    author = parts[0].split(' ')[0] if parts else 'Unknown'
    
    # Try to extract year
    year = None
    for part in parts:
        if part.strip().isdigit() and len(part.strip()) == 4:
            year = part.strip()
            break
    
    if not year:
        year = str(datetime.now().year)
    
    base_id = f"{author}{year}"
    
    if exp_number is not None:
        return f"{base_id}_E{exp_number}"
    else:
        return base_id


def create_experiment_record(paper_name: str, exp_data: Dict, exp_number: int, 
                            paper_id: str, is_multi: bool, parent_id: str = None) -> Experiment:
    """Create an Experiment database record from extraction data."""
    
    params = exp_data.get('parameters', {})
    metadata = exp_data.get('metadata', {})
    
    # Generate unique ID
    exp_id = generate_experiment_id(paper_name, exp_number if is_multi else None)
    
    # Extract parameter values
    def get_param_value(key: str, default=None):
        """Helper to extract value from parameter dict."""
        if key in params and isinstance(params[key], dict):
            return params[key].get('value', default)
        return default
    
    # Create experiment record using ORM model
    experiment = Experiment(
        id=exp_id,
        name=f"{paper_name.replace('.pdf', '')} - Experiment {exp_number}" if is_multi else paper_name.replace('.pdf', ''),
        description=f"Extracted from {paper_name}",
        
        # Multi-experiment fields
        parent_experiment_id=parent_id,
        experiment_number=exp_number if is_multi else None,
        paper_id=paper_id,
        is_multi_experiment=is_multi,
        
        # Study metadata
        study_type=get_param_value('perturbation_class'),
        publication_doi=get_param_value('doi_or_url'),
        lab_name=get_param_value('lab'),
        
        # Sample information
        sample_size_n=get_param_value('sample_size_n') or get_param_value('n_total'),
        age_mean=get_param_value('age_mean'),
        age_sd=get_param_value('age_sd'),
        handedness_criteria=get_param_value('handedness'),
        
        # Store all parameters as JSON
        extracted_params=json.dumps(params),
        provenance_sources=json.dumps({
            'extraction_date': datetime.now().isoformat(),
            'source': 'pdf_batch_extraction',
            'paper_name': paper_name,
            'file_path': metadata.get('file_path'),
            'parameter_count': len(params)
        }),
        
        schema_version='1.4',
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    return experiment


def integrate_batch_results(results_file: Path, database_path: str = './out/designspace.db'):
    """
    Integrate batch processing results into database.
    
    Args:
        results_file: Path to batch_processing_results.json
        database_path: Path to SQLite database
    """
    
    print("="*80)
    print("DATABASE INTEGRATION: Batch Extraction Results")
    print("="*80)
    
    # Initialize database
    db = Database(database_path)
    
    # Create tables
    print(f"\nInitializing database: {database_path}")
    db.create_tables()
    
    # Create session
    session = db.get_session()
    
    # Load batch results
    print(f"\nLoading results from: {results_file}")
    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    print(f"Found {len(results)} papers in batch results")
    
    inserted_experiments = 0
    inserted_papers = 0
    skipped = 0
    
    for result in results:
        if not result['success']:
            print(f"  Skipping failed: {result['paper_name']}")
            skipped += 1
            continue
        
        paper_name = result['paper_name']
        is_multi = result['is_multi_experiment']
        paper_id = generate_experiment_id(paper_name)
        
        # Get experiments
        extraction = result['extraction_result']
        experiments = extraction.get('experiments', [extraction])
        
        print(f"\n  Processing: {paper_name}")
        print(f"    Multi-experiment: {is_multi}")
        print(f"    Experiments: {len(experiments)}")
        
        # Insert each experiment
        parent_id = None
        for idx, exp_data in enumerate(experiments, 1):
            try:
                # Set parent ID for child experiments
                if is_multi and idx > 1:
                    current_parent_id = parent_id
                else:
                    current_parent_id = None
                
                exp_record = create_experiment_record(
                    paper_name, exp_data, idx, paper_id, is_multi, current_parent_id
                )
                
                # Track parent ID (first experiment is parent for multi-exp)
                if is_multi and idx == 1:
                    parent_id = exp_record.id
                
                # Add to session
                session.merge(exp_record)  # Use merge to handle duplicate IDs
                session.flush()  # Flush to catch errors early
                
                inserted_experiments += 1
                params_count = len(json.loads(exp_record.extracted_params)) if exp_record.extracted_params else 0
                print(f"      Experiment {idx}: {exp_record.id} ({params_count} params)")
                
            except Exception as e:
                print(f"      ERROR inserting Exp {idx}: {e}")
                session.rollback()
                raise
        
        inserted_papers += 1
    
    # Commit all changes
    try:
        session.commit()
        print("\n" + "="*80)
        print("INTEGRATION COMPLETE")
        print("="*80)
        print(f"\nSuccessfully integrated:")
        print(f"  Papers: {inserted_papers}")
        print(f"  Experiments: {inserted_experiments}")
        print(f"  Skipped: {skipped}")
        print(f"\nDatabase: {database_path}")
        
    except Exception as e:
        session.rollback()
        print(f"\nERROR: Database commit failed: {e}")
        raise
    finally:
        session.close()


def query_database_statistics(database_path: str = './out/designspace.db'):
    """Query and display database statistics."""
    
    print("\n" + "="*80)
    print("DATABASE STATISTICS")
    print("="*80)
    
    db = Database(database_path)
    session = db.get_session()
    
    try:
        # Total experiments
        total = session.execute(text("SELECT COUNT(*) FROM experiments")).scalar()
        print(f"\nTotal Experiments: {total}")
        
        # Multi-experiment papers
        multi = session.execute(
            text("SELECT COUNT(DISTINCT paper_id) FROM experiments WHERE is_multi_experiment = 1")
        ).scalar()
        print(f"Multi-Experiment Papers: {multi}")
        
        # Single-experiment papers
        single = session.execute(
            text("SELECT COUNT(*) FROM experiments WHERE is_multi_experiment = 0")
        ).scalar()
        print(f"Single-Experiment Papers: {single}")
        
        # Experiments per paper distribution
        print("\nExperiments per Paper:")
        results = session.execute(text("""
            SELECT paper_id, COUNT(*) as exp_count
            FROM experiments
            WHERE is_multi_experiment = 1
            GROUP BY paper_id
            ORDER BY exp_count DESC
        """)).fetchall()
        
        exp_counts = {}
        for paper_id, count in results:
            exp_counts[count] = exp_counts.get(count, 0) + 1
        
        for count in sorted(exp_counts.keys()):
            print(f"  {count} experiments: {exp_counts[count]} papers")
        
        # Parameter coverage
        print("\nParameter Coverage:")
        results = session.execute(text("""
            SELECT 
                COUNT(CASE WHEN sample_size_n IS NOT NULL THEN 1 END) as with_sample_size,
                COUNT(CASE WHEN publication_doi IS NOT NULL THEN 1 END) as with_doi,
                COUNT(CASE WHEN age_mean IS NOT NULL THEN 1 END) as with_age,
                COUNT(CASE WHEN lab_name IS NOT NULL THEN 1 END) as with_lab
            FROM experiments
        """)).fetchone()
        
        total_float = float(total) if total > 0 else 1.0
        print(f"  Sample Size: {results[0]} ({results[0]/total_float*100:.1f}%)")
        print(f"  DOI: {results[1]} ({results[1]/total_float*100:.1f}%)")
        print(f"  Age: {results[2]} ({results[2]/total_float*100:.1f}%)")
        print(f"  Lab: {results[3]} ({results[3]/total_float*100:.1f}%)")
        
    finally:
        session.close()


def main():
    """Main integration function."""
    # Setup paths
    project_root = Path(__file__).parent
    results_file = project_root / 'batch_processing_results.json'
    database_path = str(project_root / 'out' / 'designspace.db')
    
    if not results_file.exists():
        print(f"ERROR: Results file not found: {results_file}")
        print("Please run batch_process_papers.py first")
        return
    
    # Create output directory
    (project_root / 'out').mkdir(exist_ok=True)
    
    # Integrate results
    integrate_batch_results(results_file, database_path)
    
    # Display statistics
    query_database_statistics(database_path)
    
    print("\n" + "="*80)
    print("Database integration complete!")
    print("="*80)


if __name__ == '__main__':
    main()
