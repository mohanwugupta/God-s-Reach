"""
Conflict resolution module for reconciling parameter conflicts.
Implements the policies defined in conflict_resolution.yaml
"""
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

from utils.io_helpers import load_yaml

logger = logging.getLogger(__name__)


class ConflictResolver:
    """Resolves conflicts between parameter values from different sources."""
    
    def __init__(self, policy_path: str = './mapping/conflict_resolution.yaml'):
        """
        Initialize conflict resolver.
        
        Args:
            policy_path: Path to conflict resolution policy file
        """
        self.policies = load_yaml(policy_path)
        self.default_policy = self.policies.get('default_policy', 'precedence')
        self.source_precedence = self.policies.get('source_precedence', [])
        self.parameter_overrides = self.policies.get('parameter_overrides', {})
    
    def resolve_conflict(self, parameter_name: str, values: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Resolve a conflict for a parameter with multiple values.
        
        Args:
            parameter_name: Name of the parameter
            values: List of value dictionaries with keys: value, source_type, confidence, source_file
            
        Returns:
            Dictionary with resolved value and metadata
        """
        if len(values) <= 1:
            # No conflict
            return values[0] if values else None
        
        logger.info(f"Resolving conflict for {parameter_name} with {len(values)} values")
        
        # Get policy for this parameter
        param_policy = self.parameter_overrides.get(parameter_name, {})
        policy_name = param_policy.get('policy', self.default_policy)
        
        # Apply policy
        if policy_name == 'precedence':
            resolved = self._resolve_by_precedence(values, param_policy)
        elif policy_name == 'manual':
            resolved = self._flag_for_manual_review(values)
        elif policy_name == 'tolerance':
            resolved = self._resolve_with_tolerance(values, param_policy)
        elif policy_name == 'consensus':
            resolved = self._resolve_by_consensus(values, param_policy)
        else:
            logger.warning(f"Unknown policy {policy_name}, using precedence")
            resolved = self._resolve_by_precedence(values, {})
        
        # Add conflict metadata
        resolved['conflict_detected'] = True
        resolved['alternative_values'] = [
            {'value': v['value'], 'source': v['source_type'], 'confidence': v['confidence']}
            for v in values if v['value'] != resolved['value']
        ]
        resolved['resolution_policy'] = policy_name
        
        return resolved
    
    def _resolve_by_precedence(self, values: List[Dict[str, Any]], param_policy: Dict) -> Dict[str, Any]:
        """Resolve conflict using source precedence."""
        # Get precedence list (parameter-specific or default)
        precedence = param_policy.get('source_precedence', self.source_precedence)
        
        # Sort values by precedence
        def get_precedence_order(value):
            source_type = value['source_type']
            try:
                return precedence.index(source_type)
            except ValueError:
                return len(precedence)  # Unknown sources go to end
        
        sorted_values = sorted(values, key=get_precedence_order)
        
        # Return highest-precedence value
        return sorted_values[0]
    
    def _resolve_with_tolerance(self, values: List[Dict[str, Any]], param_policy: Dict) -> Dict[str, Any]:
        """Resolve conflict by checking if values are within tolerance."""
        tolerance_percent = param_policy.get('tolerance_percent', 5)
        
        # Check if all values are numeric and within tolerance
        numeric_values = []
        for v in values:
            try:
                numeric_values.append(float(v['value']))
            except (ValueError, TypeError):
                # Not numeric, fall back to precedence
                return self._resolve_by_precedence(values, {})
        
        if not numeric_values:
            return self._resolve_by_precedence(values, {})
        
        # Calculate mean and check tolerance
        mean_value = sum(numeric_values) / len(numeric_values)
        tolerance = mean_value * (tolerance_percent / 100)
        
        all_within_tolerance = all(
            abs(v - mean_value) <= tolerance
            for v in numeric_values
        )
        
        if all_within_tolerance:
            # Use mean value
            result = values[0].copy()
            result['value'] = mean_value
            result['resolution_method'] = 'tolerance_mean'
            return result
        else:
            # Values differ too much, use precedence
            return self._resolve_by_precedence(values, {})
    
    def _resolve_by_consensus(self, values: List[Dict[str, Any]], param_policy: Dict) -> Dict[str, Any]:
        """Resolve conflict by requiring consensus."""
        min_agreement = param_policy.get('min_agreement', 2)
        
        # Count occurrences of each value
        value_counts = {}
        value_records = {}
        
        for v in values:
            val_str = str(v['value'])
            value_counts[val_str] = value_counts.get(val_str, 0) + 1
            if val_str not in value_records:
                value_records[val_str] = v
        
        # Find most common value
        max_count = max(value_counts.values())
        
        if max_count >= min_agreement:
            # Consensus reached
            for val_str, count in value_counts.items():
                if count == max_count:
                    result = value_records[val_str].copy()
                    result['resolution_method'] = 'consensus'
                    result['agreement_count'] = count
                    return result
        
        # No consensus, flag for manual review
        return self._flag_for_manual_review(values)
    
    def _flag_for_manual_review(self, values: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Flag parameter for manual review."""
        # Return first value but mark for review
        result = values[0].copy()
        result['requires_manual_review'] = True
        result['resolution_method'] = 'manual_review_required'
        return result


# Convenience function
def resolve_conflicts(parameters: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    """
    Resolve conflicts for all parameters.
    
    Args:
        parameters: Dictionary mapping parameter names to lists of value dictionaries
        
    Returns:
        Dictionary mapping parameter names to resolved values
    """
    resolver = ConflictResolver()
    resolved = {}
    
    for param_name, values in parameters.items():
        if isinstance(values, list) and len(values) > 1:
            resolved[param_name] = resolver.resolve_conflict(param_name, values)
        elif isinstance(values, list) and len(values) == 1:
            resolved[param_name] = values[0]
        else:
            resolved[param_name] = values
    
    return resolved
