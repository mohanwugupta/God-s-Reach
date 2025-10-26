#!/usr/bin/env python3
"""Check what's actually extracted for Taylor 2014."""
import json

with open('batch_processing_results.json', encoding='utf-8') as f:
    results = json.load(f)

# Find Taylor 2014
for r in results:
    if '3023' in r['paper_name']:
        params = r['extraction_result']['parameters']
        print('Taylor 2014 extraction:')
        print(f"  instruction_awareness: {params.get('instruction_awareness', {}).get('value', 'NOT FOUND')}")
        print(f"  mechanism_focus: {params.get('mechanism_focus', {}).get('value', 'NOT FOUND')}")
        print(f"  perturbation_schedule: {params.get('perturbation_schedule', {}).get('value', 'NOT FOUND')}")
        print(f"  feedback_type: {params.get('feedback_type', {}).get('value', 'NOT FOUND')}")
        print(f"  primary_outcomes: {params.get('primary_outcomes', {}).get('value', 'NOT FOUND')}")
        
        print("\n  Evidence snippets:")
        for key in ['instruction_awareness', 'mechanism_focus', 'perturbation_schedule', 'feedback_type', 'primary_outcomes']:
            if key in params:
                evidence = params[key].get('evidence', '')[:100]
                print(f"    {key}: {evidence}")
        break

# Find Morehead 2017
print("\n" + "="*80)
for r in results:
    if 'Morehead' in r['paper_name'] and '2017' in r['paper_name']:
        exp = r['extraction_result'].get('experiments', [r['extraction_result']])[0]
        params = exp['parameters']
        print('Morehead 2017 extraction:')
        print(f"  perturbation_schedule: {params.get('perturbation_schedule', {}).get('value', 'NOT FOUND')}")
        if 'perturbation_schedule' in params:
            evidence = params['perturbation_schedule'].get('evidence', '')[:100]
            print(f"    Evidence: {evidence}")
        break
