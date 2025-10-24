"""
Code and data extraction module for Python and JSON files.
Uses AST parsing for Python and direct parsing for JSON/YAML configs.
"""
import ast
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging

from utils.io_helpers import load_json, load_yaml, compute_file_hash
from database.models import Database, Experiment, Provenance
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

__version__ = "1.0.0"


class ParameterExtractor:
    """Base class for parameter extraction."""
    
    def __init__(self, schema_map_path: str = None, synonyms_path: str = None, patterns_path: str = None):
        """
        Initialize extractor with mapping configurations.
        
        Args:
            schema_map_path: Path to schema_map.yaml
            synonyms_path: Path to synonyms.yaml
            patterns_path: Path to patterns.yaml
        """
        # Load mapping configurations
        self.schema_map = load_yaml(schema_map_path or './mapping/schema_map.yaml')
        self.synonyms = load_yaml(synonyms_path or './mapping/synonyms.yaml')
        self.patterns = load_yaml(patterns_path or './mapping/patterns.yaml')
        
        # Build reverse synonym lookup (alias -> canonical)
        self.alias_to_canonical = {}
        for canonical, aliases in self.synonyms.items():
            self.alias_to_canonical[canonical] = canonical
            for alias in aliases:
                self.alias_to_canonical[alias] = canonical
    
    def normalize_parameter_name(self, name: str) -> Optional[str]:
        """
        Normalize a parameter name to its canonical form.
        
        Args:
            name: Parameter name to normalize
            
        Returns:
            Canonical parameter name or None if not recognized
        """
        name_lower = name.lower()
        return self.alias_to_canonical.get(name_lower)
    
    def normalize_value(self, canonical_name: str, value: Any, unit: str = None) -> Tuple[Any, float]:
        """
        Normalize a parameter value (unit conversion, type casting, etc.).
        
        Args:
            canonical_name: Canonical parameter name
            value: Value to normalize
            unit: Unit of the value (if applicable)
            
        Returns:
            Tuple of (normalized_value, confidence_score)
        """
        confidence = 1.0
        
        # Find parameter spec in schema_map
        param_spec = None
        for category in self.schema_map.values():
            if isinstance(category, dict):
                for param_key, spec in category.items():
                    if isinstance(spec, dict) and spec.get('canonical') == canonical_name:
                        param_spec = spec
                        break
        
        if not param_spec:
            logger.warning(f"No schema specification found for {canonical_name}")
            return value, 0.5
        
        # Type casting
        expected_type = param_spec.get('type', 'string')
        try:
            if expected_type == 'integer':
                value = int(float(value))
            elif expected_type == 'float':
                value = float(value)
            elif expected_type == 'boolean':
                if isinstance(value, str):
                    value = value.lower() in ('true', 'yes', '1', 'on')
                else:
                    value = bool(value)
            elif expected_type == 'string':
                value = str(value)
                # Normalize string values
                if 'normalize' in param_spec:
                    value = param_spec['normalize'].get(value.lower(), value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Type conversion failed for {canonical_name}: {e}")
            confidence = 0.5
        
        # Unit conversion
        if unit and 'unit_conversions' in param_spec:
            unit_lower = unit.lower()
            if unit_lower in param_spec['unit_conversions']:
                conversion_factor = param_spec['unit_conversions'][unit_lower]
                if expected_type in ('float', 'integer'):
                    value = float(value) * conversion_factor
                    if expected_type == 'integer':
                        value = int(value)
        
        return value, confidence


class PythonExtractor(ParameterExtractor):
    """Extract parameters from Python source files using AST."""
    
    def extract_from_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract parameters from a Python file.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Dictionary of extracted parameters with confidence scores
        """
        logger.info(f"Extracting from Python file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source, filename=str(file_path))
            extracted = {}
            
            # Extract assignments
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            var_name = target.id
                            value = self._extract_value(node.value)
                            
                            if value is not None:
                                canonical = self.normalize_parameter_name(var_name)
                                if canonical:
                                    normalized_value, confidence = self.normalize_value(canonical, value)
                                    extracted[canonical] = {
                                        'value': normalized_value,
                                        'confidence': confidence,
                                        'source_name': var_name,
                                        'method': 'ast_extraction'
                                    }
            
            # Also try regex patterns for cases AST misses
            regex_params = self._extract_with_regex(source)
            for param, data in regex_params.items():
                if param not in extracted:
                    extracted[param] = data
            
            return extracted
            
        except Exception as e:
            logger.error(f"Failed to extract from {file_path}: {e}")
            return {}
    
    def _extract_value(self, node) -> Any:
        """Extract value from an AST node."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Num):  # Python < 3.8
            return node.n
        elif isinstance(node, ast.Str):  # Python < 3.8
            return node.s
        elif isinstance(node, ast.NameConstant):  # Python < 3.8
            return node.value
        elif isinstance(node, ast.List):
            return [self._extract_value(elem) for elem in node.elts]
        elif isinstance(node, ast.Dict):
            return {
                self._extract_value(k): self._extract_value(v)
                for k, v in zip(node.keys, node.values)
            }
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            val = self._extract_value(node.operand)
            return -val if isinstance(node.op, ast.USub) else val
        return None
    
    def _extract_with_regex(self, source: str) -> Dict[str, Any]:
        """Extract parameters using regex patterns."""
        extracted = {}
        
        # Try each pattern category
        for category, patterns_dict in self.patterns.items():
            if isinstance(patterns_dict, dict):
                for pattern_name, pattern in patterns_dict.items():
                    if isinstance(pattern, str):
                        matches = re.finditer(pattern, source, re.IGNORECASE | re.MULTILINE)
                        for match in matches:
                            # Pattern name often corresponds to parameter
                            canonical = self.normalize_parameter_name(pattern_name)
                            if canonical and match.groups():
                                value = match.group(1)
                                normalized_value, confidence = self.normalize_value(canonical, value)
                                extracted[canonical] = {
                                    'value': normalized_value,
                                    'confidence': confidence * 0.8,  # Regex less reliable
                                    'source_name': pattern_name,
                                    'method': 'pattern_match'
                                }
        
        return extracted


class JSONExtractor(ParameterExtractor):
    """Extract parameters from JSON configuration files."""
    
    def extract_from_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract parameters from a JSON file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Dictionary of extracted parameters
        """
        logger.info(f"Extracting from JSON file: {file_path}")
        
        try:
            data = load_json(str(file_path))
            extracted = {}
            
            # Recursively search for parameters
            self._extract_from_dict(data, extracted)
            
            return extracted
            
        except Exception as e:
            logger.error(f"Failed to extract from {file_path}: {e}")
            return {}
    
    def _extract_from_dict(self, data: Dict[str, Any], extracted: Dict[str, Any], prefix: str = ''):
        """Recursively extract parameters from nested dictionaries."""
        for key, value in data.items():
            # Try to normalize the key
            canonical = self.normalize_parameter_name(key)
            
            if canonical:
                # Found a recognized parameter
                if not isinstance(value, (dict, list)):
                    normalized_value, confidence = self.normalize_value(canonical, value)
                    extracted[canonical] = {
                        'value': normalized_value,
                        'confidence': confidence,
                        'source_name': key,
                        'method': 'json_extraction'
                    }
            
            # Recurse into nested structures
            if isinstance(value, dict):
                self._extract_from_dict(value, extracted, f"{prefix}{key}.")


class YAMLExtractor(ParameterExtractor):
    """Extract parameters from YAML configuration files."""
    
    def extract_from_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract parameters from a YAML file.
        
        Args:
            file_path: Path to YAML file
            
        Returns:
            Dictionary of extracted parameters
        """
        logger.info(f"Extracting from YAML file: {file_path}")
        
        try:
            data = load_yaml(str(file_path))
            extracted = {}
            
            # Recursively search for parameters
            self._extract_from_dict(data, extracted)
            
            return extracted
            
        except Exception as e:
            logger.error(f"Failed to extract from {file_path}: {e}")
            return {}
    
    def _extract_from_dict(self, data: Dict[str, Any], extracted: Dict[str, Any], prefix: str = ''):
        """Recursively extract parameters from nested dictionaries."""
        for key, value in data.items():
            canonical = self.normalize_parameter_name(key)
            
            if canonical:
                if not isinstance(value, (dict, list)):
                    normalized_value, confidence = self.normalize_value(canonical, value)
                    extracted[canonical] = {
                        'value': normalized_value,
                        'confidence': confidence,
                        'source_name': key,
                        'method': 'yaml_extraction'
                    }
            
            if isinstance(value, dict):
                self._extract_from_dict(value, extracted, f"{prefix}{key}.")


class CodeExtractor:
    """Main code extraction orchestrator."""
    
    def __init__(self, db: Database, use_llm: bool = False, llm_provider: str = 'claude'):
        """
        Initialize code extractor.
        
        Args:
            db: Database instance
            use_llm: Whether to use LLM assistance
            llm_provider: LLM provider to use
        """
        self.db = db
        self.use_llm = use_llm
        self.llm_provider = llm_provider
        
        # Initialize specific extractors
        self.python_extractor = PythonExtractor()
        self.json_extractor = JSONExtractor()
        self.yaml_extractor = YAMLExtractor()
    
    def extract_from_repo(self, repo_path: str, discovered_files: Dict[str, List[Path]], 
                         exp_id: Optional[str] = None) -> Experiment:
        """
        Extract parameters from an entire repository.
        
        Args:
            repo_path: Path to repository
            discovered_files: Dictionary of discovered files by category
            exp_id: Optional experiment ID
            
        Returns:
            Experiment object
        """
        logger.info(f"Extracting from repository: {repo_path}")
        
        all_parameters = {}
        provenance_records = []
        
        # Extract from Python files
        for py_file in discovered_files.get('python', []):
            params = self.python_extractor.extract_from_file(py_file)
            self._merge_parameters(all_parameters, params, 'code', py_file)
            
            # Create provenance record
            provenance_records.append({
                'file_path': str(py_file),
                'file_content_hash': compute_file_hash(str(py_file)),
                'source_type': 'code',
                'extractor_version': __version__
            })
        
        # Extract from JSON files
        for json_file in discovered_files.get('json', []):
            params = self.json_extractor.extract_from_file(json_file)
            self._merge_parameters(all_parameters, params, 'config', json_file)
            
            provenance_records.append({
                'file_path': str(json_file),
                'file_content_hash': compute_file_hash(str(json_file)),
                'source_type': 'config',
                'extractor_version': __version__
            })
        
        # Extract from YAML files
        for yaml_file in discovered_files.get('yaml', []):
            params = self.yaml_extractor.extract_from_file(yaml_file)
            self._merge_parameters(all_parameters, params, 'config', yaml_file)
            
            provenance_records.append({
                'file_path': str(yaml_file),
                'file_content_hash': compute_file_hash(str(yaml_file)),
                'source_type': 'config',
                'extractor_version': __version__
            })
        
        # Create experiment record
        experiment = self._create_experiment_record(all_parameters, exp_id, repo_path)
        
        # TODO: LLM assistance for low-confidence parameters
        if self.use_llm:
            logger.info("LLM assistance enabled but not yet implemented")
        
        # Store in database
        session = self.db.get_session()
        try:
            session.add(experiment)
            
            # Add provenance records
            for prov_data in provenance_records:
                prov = Provenance(
                    experiment_id=experiment.id,
                    **prov_data
                )
                session.add(prov)
            
            session.commit()
            logger.info(f"Experiment {experiment.id} saved to database")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save to database: {e}")
            raise
        finally:
            session.close()
        
        return experiment
    
    def _merge_parameters(self, all_params: Dict, new_params: Dict, source_type: str, file_path: Path):
        """Merge newly extracted parameters with existing ones."""
        for param, data in new_params.items():
            if param not in all_params:
                all_params[param] = {
                    'value': data['value'],
                    'confidence': data['confidence'],
                    'source_type': source_type,
                    'source_file': str(file_path),
                    'method': data['method']
                }
            else:
                # Parameter conflict - will be handled by conflict resolution module
                # For now, keep the higher confidence value
                if data['confidence'] > all_params[param]['confidence']:
                    all_params[param] = {
                        'value': data['value'],
                        'confidence': data['confidence'],
                        'source_type': source_type,
                        'source_file': str(file_path),
                        'method': data['method'],
                        'conflict': True
                    }
    
    def _create_experiment_record(self, parameters: Dict, exp_id: Optional[str], repo_path: str) -> Experiment:
        """Create an Experiment database record from extracted parameters."""
        if not exp_id:
            # Generate experiment ID
            exp_id = f"EXP{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Map extracted parameters to database fields
        exp_data = {
            'id': exp_id,
            'name': Path(repo_path).name,
            'description': f"Extracted from {repo_path}",
            'extractor_version': __version__,
            'schema_version': '1.3',
        }
        
        # Map parameters to experiment fields
        field_mapping = {
            'rotation_magnitude_deg': 'rotation_magnitude_deg',
            'sample_size_n': 'sample_size_n',
            'age_mean': 'age_mean',
            'age_sd': 'age_sd',
            'handedness_criteria': 'handedness_criteria',
            'equipment_manipulandum_type': 'equipment_manipulandum_type',
            'equipment_workspace_width_cm': 'equipment_workspace_width_cm',
            'equipment_workspace_height_cm': 'equipment_workspace_height_cm',
            'equipment_sampling_rate_hz': 'equipment_sampling_rate_hz',
        }
        
        # Check for conflicts
        has_conflicts = any(p.get('conflict', False) for p in parameters.values())
        exp_data['conflict_flag'] = has_conflicts
        
        # Extract field values
        for param, db_field in field_mapping.items():
            if param in parameters:
                exp_data[db_field] = parameters[param]['value']
        
        # Store provenance sources as JSON
        provenance_sources = [
            {
                'parameter': param,
                'source_file': data['source_file'],
                'source_type': data['source_type'],
                'confidence': data['confidence']
            }
            for param, data in parameters.items()
        ]
        exp_data['provenance_sources'] = json.dumps(provenance_sources)
        
        return Experiment(**exp_data)
