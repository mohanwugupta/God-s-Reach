"""
File discovery utilities for finding relevant files in repositories.
"""
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class FileDiscovery:
    """Discovers relevant files in a repository for extraction."""
    
    # File extensions to look for
    EXTENSIONS = {
        'code': {
            'python': ['.py'],
            'matlab': ['.m'],
            'javascript': ['.js', '.jsx', '.ts', '.tsx'],
            'r': ['.R', '.r'],
        },
        'config': {
            'json': ['.json'],
            'yaml': ['.yaml', '.yml'],
            'xml': ['.xml'],
            'ini': ['.ini'],
            'txt': ['.txt', '.cfg', '.conf'],
        },
        'data': {
            'csv': ['.csv', '.tsv'],
            'mat': ['.mat'],
            'hdf5': ['.h5', '.hdf5'],
        },
        'docs': {
            'pdf': ['.pdf'],
            'markdown': ['.md'],
            'tex': ['.tex'],
        }
    }
    
    # Directories to exclude
    EXCLUDE_DIRS = {
        '.git', '.svn', '.hg',  # Version control
        '__pycache__', '.pytest_cache', '.mypy_cache',  # Python caches
        'node_modules', 'bower_components',  # JavaScript
        'venv', 'env', '.env', 'virtualenv',  # Python virtual environments
        'dist', 'build', 'out', 'target',  # Build outputs
        '.vscode', '.idea', '.eclipse',  # IDE directories
    }
    
    # Files to exclude
    EXCLUDE_FILES = {
        '.DS_Store', 'Thumbs.db',  # OS files
        'package-lock.json', 'yarn.lock',  # JavaScript lock files
        'requirements.lock',  # Python lock files (usually duplicates info)
    }
    
    def __init__(self, root_path: str):
        """
        Initialize file discovery.
        
        Args:
            root_path: Root directory to search
        """
        self.root_path = Path(root_path)
        if not self.root_path.exists():
            raise ValueError(f"Path does not exist: {root_path}")
    
    def discover(self) -> Dict[str, List[Path]]:
        """
        Discover all relevant files in the repository.
        
        Returns:
            Dictionary with file categories as keys and lists of file paths as values
        """
        logger.info(f"Discovering files in {self.root_path}")
        
        discovered = {
            'python': [],
            'matlab': [],
            'javascript': [],
            'r': [],
            'json': [],
            'yaml': [],
            'xml': [],
            'config': [],
            'csv': [],
            'mat': [],
            'hdf5': [],
            'pdf': [],
            'markdown': [],
        }
        
        # Walk the directory tree
        for path in self.root_path.rglob('*'):
            # Skip directories
            if path.is_dir():
                continue
            
            # Skip excluded directories
            if any(excluded in path.parts for excluded in self.EXCLUDE_DIRS):
                continue
            
            # Skip excluded files
            if path.name in self.EXCLUDE_FILES:
                continue
            
            # Categorize by extension
            suffix = path.suffix.lower()
            
            # Python files
            if suffix in self.EXTENSIONS['code']['python']:
                discovered['python'].append(path)
            
            # MATLAB files
            elif suffix in self.EXTENSIONS['code']['matlab']:
                discovered['matlab'].append(path)
            
            # JavaScript files
            elif suffix in self.EXTENSIONS['code']['javascript']:
                discovered['javascript'].append(path)
            
            # R files
            elif suffix in self.EXTENSIONS['code']['r']:
                discovered['r'].append(path)
            
            # JSON files
            elif suffix in self.EXTENSIONS['config']['json']:
                discovered['json'].append(path)
            
            # YAML files
            elif suffix in self.EXTENSIONS['config']['yaml']:
                discovered['yaml'].append(path)
            
            # XML files
            elif suffix in self.EXTENSIONS['config']['xml']:
                discovered['xml'].append(path)
            
            # Other config files
            elif suffix in self.EXTENSIONS['config']['ini'] or suffix in self.EXTENSIONS['config']['txt']:
                discovered['config'].append(path)
            
            # CSV/TSV files
            elif suffix in self.EXTENSIONS['data']['csv']:
                discovered['csv'].append(path)
            
            # MAT files
            elif suffix in self.EXTENSIONS['data']['mat']:
                discovered['mat'].append(path)
            
            # HDF5 files
            elif suffix in self.EXTENSIONS['data']['hdf5']:
                discovered['hdf5'].append(path)
            
            # PDF files
            elif suffix in self.EXTENSIONS['docs']['pdf']:
                discovered['pdf'].append(path)
            
            # Markdown files
            elif suffix in self.EXTENSIONS['docs']['markdown']:
                discovered['markdown'].append(path)
        
        # Log summary
        total_files = sum(len(files) for files in discovered.values())
        logger.info(f"Discovered {total_files} files:")
        for category, files in discovered.items():
            if files:
                logger.info(f"  {category}: {len(files)} files")
        
        return discovered
    
    def prioritize_files(self, discovered: Dict[str, List[Path]]) -> List[Path]:
        """
        Prioritize files for extraction based on likelihood of containing parameters.
        
        Args:
            discovered: Dictionary of discovered files by category
            
        Returns:
            Prioritized list of file paths
        """
        prioritized = []
        
        # Priority 1: Configuration files (most likely to contain parameters)
        prioritized.extend(discovered['json'])
        prioritized.extend(discovered['yaml'])
        prioritized.extend(discovered['xml'])
        
        # Priority 2: Code files (contain parameter definitions)
        prioritized.extend(discovered['python'])
        prioritized.extend(discovered['matlab'])
        prioritized.extend(discovered['javascript'])
        
        # Priority 3: Data files (might contain trial logs)
        prioritized.extend(discovered['csv'])
        prioritized.extend(discovered['mat'])
        prioritized.extend(discovered['hdf5'])
        
        # Priority 4: Documentation (papers, README)
        # Prioritize files with "paper", "methods", "manuscript" in name
        pdf_files = discovered['pdf']
        priority_pdfs = [f for f in pdf_files if any(
            keyword in f.name.lower() for keyword in ['paper', 'methods', 'manuscript', 'supplementary']
        )]
        other_pdfs = [f for f in pdf_files if f not in priority_pdfs]
        prioritized.extend(priority_pdfs)
        prioritized.extend(other_pdfs)
        
        # Priority 5: Markdown (README, documentation)
        readme_files = [f for f in discovered['markdown'] if 'readme' in f.name.lower()]
        other_md = [f for f in discovered['markdown'] if f not in readme_files]
        prioritized.extend(readme_files)
        prioritized.extend(other_md)
        
        return prioritized


def discover_files(repo_path: str) -> Dict[str, List[Path]]:
    """
    Convenience function to discover files in a repository.
    
    Args:
        repo_path: Path to repository root
        
    Returns:
        Dictionary of discovered files by category
    """
    discovery = FileDiscovery(repo_path)
    return discovery.discover()


def prioritize_files(discovered: Dict[str, List[Path]]) -> List[Path]:
    """
    Convenience function to prioritize discovered files.
    
    Args:
        discovered: Dictionary of discovered files
        
    Returns:
        Prioritized list of file paths
    """
    discovery = FileDiscovery(str(list(discovered.values())[0][0].parent) if discovered else '.')
    return discovery.prioritize_files(discovered)
