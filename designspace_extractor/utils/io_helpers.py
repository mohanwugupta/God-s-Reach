"""I/O helper utilities."""
import json
import yaml
from pathlib import Path
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)


def load_yaml(file_path: str) -> Dict[str, Any]:
    """
    Load a YAML file.
    
    Args:
        file_path: Path to YAML file
        
    Returns:
        Dictionary with YAML contents
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_json(file_path: str) -> Dict[str, Any]:
    """
    Load a JSON file.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Dictionary with JSON contents
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Dict[str, Any], file_path: str, indent: int = 2):
    """
    Save data to JSON file.
    
    Args:
        data: Data to save
        file_path: Output file path
        indent: JSON indentation
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent)


def compute_file_hash(file_path: str) -> str:
    """
    Compute SHA256 hash of a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Hex digest of file hash
    """
    import hashlib
    
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()
