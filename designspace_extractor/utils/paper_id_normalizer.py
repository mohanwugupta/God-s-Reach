"""
Paper ID Normalizer
Utility for normalizing paper identifiers and deduplicating batch processing results.
"""

import re
from typing import Dict, List, Any
from pathlib import Path


class PaperIDNormalizer:
    """Normalize paper IDs to canonical form for deduplication."""
    
    @staticmethod
    def normalize(paper_id: str) -> str:
        """
        Normalize a paper ID to canonical form.
        
        Handles variations like:
        - "Paper.pdf" -> "paper"
        - "Paper.PDF" -> "paper"
        - "Paper_v2.pdf" -> "paper_v2"
        - "Author2023EXP1" -> "author2023exp1"
        - "Author_2023_exp1.pdf" -> "author_2023_exp1"
        
        Args:
            paper_id: Raw paper identifier (filename, study ID, etc.)
            
        Returns:
            Normalized ID (lowercase, no .pdf extension)
        """
        if not paper_id:
            return ""
        
        # Remove common file extensions
        normalized = paper_id
        for ext in ['.pdf', '.PDF', '.txt', '.TXT']:
            if normalized.endswith(ext):
                normalized = normalized[:-len(ext)]
                break
        
        # Convert to lowercase for case-insensitive matching
        normalized = normalized.lower()
        
        # Remove extra whitespace
        normalized = normalized.strip()
        
        # Replace multiple underscores/spaces with single underscore
        normalized = re.sub(r'[_\s]+', '_', normalized)
        
        return normalized
    
    @staticmethod
    def extract_author_year(paper_id: str) -> tuple:
        """
        Extract author and year from paper ID.
        
        Args:
            paper_id: Paper identifier
            
        Returns:
            (author, year) tuple, or (None, None) if not found
        """
        # Pattern: AuthorYYYY or Author_YYYY or Author2023EXP1
        match = re.search(r'([A-Za-z]+)[_\s]*(\d{4})', paper_id)
        if match:
            return match.group(1).lower(), match.group(2)
        return None, None
    
    @staticmethod
    def are_likely_same_paper(id1: str, id2: str) -> bool:
        """
        Check if two paper IDs likely refer to the same paper.
        
        Args:
            id1: First paper ID
            id2: Second paper ID
            
        Returns:
            True if likely the same paper
        """
        # Normalize both IDs
        norm1 = PaperIDNormalizer.normalize(id1)
        norm2 = PaperIDNormalizer.normalize(id2)
        
        # Exact match after normalization
        if norm1 == norm2:
            return True
        
        # Check author/year match
        author1, year1 = PaperIDNormalizer.extract_author_year(id1)
        author2, year2 = PaperIDNormalizer.extract_author_year(id2)
        
        if author1 and year1 and author2 and year2:
            if author1 == author2 and year1 == year2:
                return True
        
        return False


def deduplicate_results(results: List[Dict[str, Any]], 
                       keep_strategy: str = 'most_params') -> List[Dict[str, Any]]:
    """
    Deduplicate batch processing results by paper ID.
    
    Args:
        results: List of batch processing result dicts
        keep_strategy: Strategy for choosing which duplicate to keep:
            - 'most_params': Keep the version with most extracted parameters
            - 'first': Keep the first occurrence
            - 'last': Keep the last occurrence
            
    Returns:
        Deduplicated list of results
    """
    # Group by normalized paper ID
    paper_groups = {}
    
    for result in results:
        paper_name = result.get('paper_name', '')
        normalized_id = PaperIDNormalizer.normalize(paper_name)
        
        if normalized_id not in paper_groups:
            paper_groups[normalized_id] = []
        
        paper_groups[normalized_id].append(result)
    
    # Select best version from each group
    deduplicated = []
    duplicates_removed = 0
    
    for normalized_id, group in paper_groups.items():
        if len(group) == 1:
            # No duplicates
            deduplicated.append(group[0])
        else:
            # Multiple versions - choose based on strategy
            duplicates_removed += len(group) - 1
            
            if keep_strategy == 'most_params':
                # Choose the one with most parameters
                def count_params(result):
                    if not result.get('success'):
                        return 0
                    extraction = result.get('extraction_result', {})
                    experiments = extraction.get('experiments', [extraction])
                    total_params = 0
                    for exp in experiments:
                        total_params += len(exp.get('parameters', {}))
                    return total_params
                
                best = max(group, key=count_params)
                deduplicated.append(best)
                
            elif keep_strategy == 'first':
                deduplicated.append(group[0])
                
            elif keep_strategy == 'last':
                deduplicated.append(group[-1])
            
            else:
                raise ValueError(f"Unknown keep_strategy: {keep_strategy}")
    
    print(f"🔧 Deduplication complete:")
    print(f"   Original: {len(results)} results")
    print(f"   Deduplicated: {len(deduplicated)} results")
    print(f"   Removed: {duplicates_removed} duplicates")
    
    return deduplicated


def deduplicate_json_file(input_path: str, output_path: str = None, 
                         keep_strategy: str = 'most_params'):
    """
    Deduplicate a batch processing results JSON file.
    
    Args:
        input_path: Path to input JSON file
        output_path: Path to output JSON file (default: overwrite input)
        keep_strategy: Strategy for keeping duplicates
    """
    import json
    
    input_file = Path(input_path)
    output_file = Path(output_path) if output_path else input_file
    
    print(f"📥 Loading: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    print(f"   Loaded {len(results)} results")
    
    # Deduplicate
    deduplicated = deduplicate_results(results, keep_strategy=keep_strategy)
    
    # Save
    print(f"💾 Saving to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(deduplicated, f, indent=2, ensure_ascii=False)
    
    print("✅ Deduplication complete!")


def main():
    """Main function for command-line usage."""
    import sys
    from pathlib import Path
    
    if len(sys.argv) < 2:
        print("Usage: python paper_id_normalizer.py <input_json> [output_json] [strategy]")
        print("Strategy options: most_params (default), first, last")
        return
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    strategy = sys.argv[3] if len(sys.argv) > 3 else 'most_params'
    
    deduplicate_json_file(input_path, output_path, keep_strategy=strategy)


if __name__ == '__main__':
    main()
