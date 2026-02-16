#!/usr/bin/env python3
"""
Analyze LLM contributions: Found vs Corrected parameters.

This script analyzes the log file to distinguish between:
1. Parameters completely FOUND by LLM (regex missed them)
2. Parameters CORRECTED/VERIFIED by LLM (regex found something, LLM improved it)
"""

import re
from pathlib import Path
from collections import defaultdict


def analyze_log_file(log_path: str):
    """Analyze the .out log file to categorize LLM contributions."""
    
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        log_content = f.read()
    
    # Find all "Found missed" parameters (completely new findings)
    found_pattern = r'✅ Found missed: (\w+)'
    found_params = re.findall(found_pattern, log_content)
    
    # Find all verified/corrected parameters (LLM provided value)
    verified_pattern = r'✅ (\w+) = (.+?)(?:\n|$)'
    verified_matches = re.findall(verified_pattern, log_content)
    
    # Count by parameter name
    found_counts = defaultdict(int)
    verified_counts = defaultdict(int)
    
    for param in found_params:
        found_counts[param] += 1
    
    for param, value in verified_matches:
        # Only count if it's not also in "found missed"
        if param not in found_params:
            verified_counts[param] += 1
    
    # Print results
    print("=" * 80)
    print("LLM CONTRIBUTIONS: FOUND vs VERIFIED/CORRECTED")
    print("=" * 80)
    print()
    
    print("PARAMETERS COMPLETELY FOUND BY LLM (Regex Missed Them)")
    print("-" * 80)
    if found_counts:
        for param, count in sorted(found_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {param:30s}: {count:3d} occurrences")
        print(f"\nTotal 'Found Missed': {sum(found_counts.values())} parameters")
        print(f"Unique parameters:    {len(found_counts)} types")
    else:
        print("  (None found in log)")
    
    print()
    print("PARAMETERS VERIFIED/CORRECTED BY LLM (Regex Found, LLM Enhanced)")
    print("-" * 80)
    if verified_counts:
        for param, count in sorted(verified_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {param:30s}: {count:3d} occurrences")
        print(f"\nTotal 'Verified':     {sum(verified_counts.values())} parameters")
        print(f"Unique parameters:    {len(verified_counts)} types")
    else:
        print("  (None found in log)")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    total_found = sum(found_counts.values())
    total_verified = sum(verified_counts.values())
    total_llm = total_found + total_verified
    
    if total_llm > 0:
        print(f"Total LLM contributions: {total_llm}")
        print(f"  Completely FOUND:      {total_found} ({(total_found/total_llm)*100:.1f}%)")
        print(f"  VERIFIED/CORRECTED:    {total_verified} ({(total_verified/total_llm)*100:.1f}%)")
    else:
        print("No LLM contributions found in log file.")
    
    print("=" * 80)
    print()
    print("Note: This analyzes the log file, which shows LLM actions during processing.")
    print("To get exact numbers, compare batch results with LLM vs without LLM.")
    print("=" * 80)


if __name__ == '__main__':
    # Try to find the most recent log file
    log_dir = Path(__file__).parent.parent / 'slurm' / 'logs'
    
    # Look for the specific log file
    log_files = list(log_dir.glob('batch_extraction_qwen72b_*.out'))
    
    if not log_files:
        print("Error: No log files found!")
        print(f"Searched in: {log_dir}")
        print("Please provide the path to the .out log file")
        exit(1)
    
    # Use the most recent one
    latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
    
    print(f"\nAnalyzing: {latest_log.name}\n")
    analyze_log_file(latest_log)
