#!/usr/bin/env python3
"""Show what was extracted from 3023.full.pdf"""
import json

with open('batch_processing_results.json', encoding='utf-8') as f:
    results = json.load(f)

for r in results:
    if '3023.full.pdf' in r['paper_name']:
        print(f"Paper: {r['paper_name']}")
        print(f"Success: {r['success']}\n")
        
        if r['success']:
            exp = r['extraction_result']
            params = exp.get('parameters', {})
            
            # Show key identifying parameters
            print("Key parameters:")
            for key in ['authors', 'year', 'title', 'doi_or_url']:
                if key in params:
                    val = params[key]['value'] if isinstance(params[key], dict) else params[key]
                    print(f"  {key}: {val}")
        break
