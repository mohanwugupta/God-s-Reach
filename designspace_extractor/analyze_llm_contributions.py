#!/usr/bin/env python3
"""
Analyze LLM contributions to parameter extraction.

This script analyzes batch_processing_results.json to determine:
1. How many parameters were extracted by LLM vs regex
2. Percentage of LLM-assisted parameters
3. Breakdown by paper and experiment
"""

import json
from pathlib import Path
from collections import defaultdict, Counter


def analyze_llm_contributions(json_file: str):
    """Analyze LLM contributions from batch processing results."""
    
    with open(json_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Statistics
    total_params = 0
    llm_assisted_params = 0
    regex_params = 0
    
    # Breakdown by method
    method_counts = Counter()
    
    # Per-paper statistics
    paper_stats = []
    
    for paper in results:
        if not paper.get('success'):
            continue
        
        paper_name = paper['paper_name']
        paper_llm_count = 0
        paper_total_count = 0
        
        # Handle both single and multi-experiment papers
        extraction_result = paper['extraction_result']
        
        if extraction_result.get('is_multi_experiment'):
            # Multi-experiment paper
            experiments = extraction_result.get('experiments', [])
            for exp in experiments:
                params = exp.get('parameters', {})
                for param_name, param_data in params.items():
                    method = param_data.get('method', 'unknown')
                    method_counts[method] += 1
                    paper_total_count += 1
                    total_params += 1
                    
                    if method == 'llm_assisted':
                        llm_assisted_params += 1
                        paper_llm_count += 1
                    else:
                        regex_params += 1
        else:
            # Single-experiment paper
            params = extraction_result.get('parameters', {})
            for param_name, param_data in params.items():
                method = param_data.get('method', 'unknown')
                method_counts[method] += 1
                paper_total_count += 1
                total_params += 1
                
                if method == 'llm_assisted':
                    llm_assisted_params += 1
                    paper_llm_count += 1
                else:
                    regex_params += 1
        
        # Store paper stats
        if paper_total_count > 0:
            paper_stats.append({
                'name': paper_name,
                'total': paper_total_count,
                'llm_assisted': paper_llm_count,
                'percent_llm': (paper_llm_count / paper_total_count) * 100
            })
    
    # Print results
    print("=" * 80)
    print("LLM CONTRIBUTION ANALYSIS")
    print("=" * 80)
    print()
    
    print("OVERALL STATISTICS")
    print("-" * 80)
    print(f"Total parameters extracted: {total_params}")
    print(f"LLM-assisted parameters:    {llm_assisted_params} ({(llm_assisted_params/total_params)*100:.1f}%)")
    print(f"Regex-based parameters:     {regex_params} ({(regex_params/total_params)*100:.1f}%)")
    print()
    
    print("BREAKDOWN BY EXTRACTION METHOD")
    print("-" * 80)
    for method, count in sorted(method_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_params) * 100
        print(f"{method:30s}: {count:4d} ({percentage:5.1f}%)")
    print()
    
    print("PER-PAPER LLM ASSISTANCE")
    print("-" * 80)
    print(f"{'Paper':<70s} {'Total':>6s} {'LLM':>6s} {'%':>6s}")
    print("-" * 80)
    
    # Sort by percentage descending
    paper_stats.sort(key=lambda x: x['percent_llm'], reverse=True)
    
    for stat in paper_stats:
        name = stat['name'][:67] + '...' if len(stat['name']) > 70 else stat['name']
        print(f"{name:<70s} {stat['total']:6d} {stat['llm_assisted']:6d} {stat['percent_llm']:5.1f}%")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"The LLM assisted with {llm_assisted_params}/{total_params} parameters")
    print(f"({(llm_assisted_params/total_params)*100:.1f}% of all extracted parameters)")
    print()
    print("This represents parameters that were:")
    print("  • Completely missed by regex (found by LLM)")
    print("  • Found by regex but corrected/enhanced by LLM")
    print("  • Had values filled in/verified by LLM")
    print("=" * 80)


if __name__ == '__main__':
    json_file = Path(__file__).parent / 'batch_processing_results.json'
    
    if not json_file.exists():
        print(f"Error: {json_file} not found!")
        print("Please run this script from the designspace_extractor directory")
        exit(1)
    
    analyze_llm_contributions(json_file)
