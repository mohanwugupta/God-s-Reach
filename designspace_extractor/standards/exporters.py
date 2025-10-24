"""
Standards exporters for various formats.
"""
from typing import Dict, Any, Optional
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class PsychDSExporter:
    """Export to Psych-DS format."""
    
    def __init__(self, db):
        self.db = db
    
    def export(self, exp_id: Optional[str] = None, output_path: str = None) -> str:
        """
        Export experiments to Psych-DS format.
        
        Args:
            exp_id: Optional experiment ID (default: export all)
            output_path: Output directory path
            
        Returns:
            Path to exported file
        """
        logger.info(f"Exporting to Psych-DS format")
        
        output_path = output_path or './out/psychds_export'
        Path(output_path).mkdir(parents=True, exist_ok=True)
        
        # Create dataset_description.json
        dataset_desc = {
            "Name": "Motor Adaptation Design Parameters",
            "BIDSVersion": "1.0.0",
            "License": "CC0",
            "Authors": ["Mohan Gupta"],
            "Description": "Extracted design parameters from motor adaptation studies",
            "DatasetType": "raw"
        }
        
        with open(Path(output_path) / 'dataset_description.json', 'w') as f:
            json.dump(dataset_desc, f, indent=2)
        
        logger.info(f"Exported to {output_path}")
        return output_path


class CSVExporter:
    """Export to CSV format."""
    
    def __init__(self, db):
        self.db = db
    
    def export(self, exp_id: Optional[str] = None, output_path: str = None) -> str:
        """Export experiments to CSV."""
        import pandas as pd
        
        output_path = output_path or './out/export.csv'
        
        session = self.db.get_session()
        try:
            from database.models import Experiment
            
            if exp_id:
                experiments = session.query(Experiment).filter_by(id=exp_id).all()
            else:
                experiments = session.query(Experiment).all()
            
            # Convert to DataFrame
            data = [exp.to_dict() for exp in experiments]
            df = pd.DataFrame(data)
            
            # Save to CSV
            df.to_csv(output_path, index=False)
            logger.info(f"Exported {len(experiments)} experiments to {output_path}")
            
            return output_path
            
        finally:
            session.close()


class JSONExporter:
    """Export to JSON format."""
    
    def __init__(self, db):
        self.db = db
    
    def export(self, exp_id: Optional[str] = None, output_path: str = None) -> str:
        """Export experiments to JSON."""
        output_path = output_path or './out/export.json'
        
        session = self.db.get_session()
        try:
            from database.models import Experiment
            
            if exp_id:
                experiments = session.query(Experiment).filter_by(id=exp_id).all()
            else:
                experiments = session.query(Experiment).all()
            
            data = [exp.to_dict() for exp in experiments]
            
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Exported {len(experiments)} experiments to {output_path}")
            return output_path
            
        finally:
            session.close()


def get_exporter(format_name: str, db):
    """
    Get exporter for specified format.
    
    Args:
        format_name: Export format (psychds, csv, json, metalab)
        db: Database instance
        
    Returns:
        Exporter instance
    """
    exporters = {
        'psychds': PsychDSExporter,
        'csv': CSVExporter,
        'json': JSONExporter,
        'metalab': JSONExporter,  # Placeholder
    }
    
    if format_name not in exporters:
        raise ValueError(f"Unknown export format: {format_name}")
    
    return exporters[format_name](db)
