"""
Validation module for checking extracted parameters.
"""
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class ExperimentValidator:
    """Validates extracted experiment parameters."""
    
    def __init__(self, db):
        """
        Initialize validator.
        
        Args:
            db: Database instance
        """
        self.db = db
    
    def validate_experiment(self, exp_id: str) -> Dict[str, Any]:
        """
        Validate a single experiment.
        
        Args:
            exp_id: Experiment ID to validate
            
        Returns:
            Dictionary with validation results
        """
        logger.info(f"Validating experiment: {exp_id}")
        
        session = self.db.get_session()
        try:
            from database.models import Experiment
            
            exp = session.query(Experiment).filter_by(id=exp_id).first()
            if not exp:
                return {
                    'valid': False,
                    'errors': [f"Experiment not found: {exp_id}"],
                    'warnings': []
                }
            
            errors = []
            warnings = []
            
            # Check required fields
            if not exp.name:
                errors.append("Missing experiment name")
            
            if not exp.study_type:
                warnings.append("Study type not specified")
            
            # Check for conflicts
            if exp.conflict_flag:
                warnings.append("Experiment has unresolved conflicts")
            
            # TODO: Add more validation rules
            # - Check value ranges
            # - Check consistency across hierarchy
            # - Check for implausible values
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'experiment_id': exp_id
            }
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                'valid': False,
                'errors': [str(e)],
                'warnings': []
            }
        finally:
            session.close()
    
    def validate_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Validate all experiments in database.
        
        Returns:
            Dictionary mapping experiment IDs to validation results
        """
        session = self.db.get_session()
        try:
            from database.models import Experiment
            
            experiments = session.query(Experiment).all()
            results = {}
            
            for exp in experiments:
                results[exp.id] = self.validate_experiment(exp.id)
            
            return results
            
        finally:
            session.close()
