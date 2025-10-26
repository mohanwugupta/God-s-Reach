#!/usr/bin/env python3
"""Check study IDs in automated results."""
import json

with open('batch_processing_results.json', encoding='utf-8') as f:
    results = json.load(f)

print("Paper names in automated results:\n")
for i, r in enumerate(results[:15], 1):
    paper_name = r['paper_name']
    success = r['success']
    
    if success:
        extraction = r['extraction_result']
        num_exps = len(extraction.get('experiments', [extraction]))
        print(f"{i:2}. {paper_name:<50} ({num_exps} exp)")
    else:
        print(f"{i:2}. {paper_name:<50} (FAILED)")
