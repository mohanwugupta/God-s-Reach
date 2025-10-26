#!/usr/bin/env python3
"""Detailed diagnostic to see exactly what's being compared."""
import json
import urllib.request
import csv
import re

# Parameter name mapping: automated_name -> gold_standard_name
PARAM_NAME_MAPPING = {
    'rotation_magnitude_deg': 'perturbation_magnitude',
    'sample_size_n': 'n_total',
    'force_field_type': 'perturbation_class',
}

def normalize_param_name(param_name):
    """Convert automated parameter name to gold standard name."""
    return PARAM_NAME_MAPPING.get(param_name, param_name)

# Load gold standard
spreadsheet_id = "1nc34GT31emdpVJw7Vq-1cRI7_TtJ8Tdj"
gid = "486594143"
csv_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"

with urllib.request.urlopen(csv_url) as response:
    content = response.read().decode('utf-8')

lines = content.splitlines()
reader = csv.DictReader(lines)
gold_data = {}
for row in reader:
    entry = {k: v.strip() if v else None for k, v in row.items()}
    study_id = entry.get('study_id')
    if study_id:
        gold_data[study_id] = entry

# Load automated results
with open('batch_processing_results.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

# Find Taylor2014 paper (3023.full.pdf)
taylor_result = None
for r in results:
    if '3023.full.pdf' in r['paper_name']:
        taylor_result = r
        break

print("="*80)
print("TAYLOR 2014 COMPARISON")
print("="*80)

if taylor_result and taylor_result['success']:
    exp = taylor_result['extraction_result']
    auto_params_raw = {}
    for name, data in exp.get('parameters', {}).items():
        auto_params_raw[name] = data.get('value') if isinstance(data, dict) else data
    
    # Normalize parameter names
    auto_params = {}
    for name, value in auto_params_raw.items():
        normalized_name = normalize_param_name(name)
        auto_params[normalized_name] = value
    
    gold_params = gold_data.get('Taylor2014_JNeuro_Endpoint', {})
    
    # Compare parameter by parameter
    print("\nGOLD STANDARD PARAMETERS:")
    for key in sorted(gold_params.keys()):
        val = gold_params[key]
        if val and val.lower() not in ['', 'null', 'none', '?']:
            print(f"  {key}: {val}")
    
    print("\n" + "-"*80)
    print("AUTOMATED EXTRACTION PARAMETERS:")
    for key in sorted(auto_params.keys()):
        val = auto_params[key]
        if val:
            print(f"  {key}: {val}")
    
    print("\n" + "-"*80)
    print("PARAMETER MATCHING:")
    
    # Show which match
    metadata = {'study_id', 'title', 'authors', 'year', 'notes', 'doi_or_url', 'lab', 'dataset_link'}
    all_params = set(gold_params.keys()) | set(auto_params.keys())
    for param in sorted(all_params):
        if param in metadata:
            continue
        
        gold_val = gold_params.get(param)
        auto_val = auto_params.get(param)
        
        # Skip if gold is null/empty or lab
        if param == 'lab' or not gold_val or gold_val.lower() in ['null', 'none', '', 'n/a', '?']:
            continue
        
        status = "❓"
        if auto_val is None or auto_val == '':
            status = "❌ FN (missing)"
        elif str(gold_val).lower().strip() == str(auto_val).lower().strip():
            status = "✅ TP (match)"
        else:
            status = f"⚠️  VM (gold: {gold_val}, auto: {auto_val})"
        
        print(f"  {param:<30} {status}")

print("\n" + "="*80)
print("MOREHEAD 2017 COMPARISON")
print("="*80)

# Find Morehead 2017 paper
morehead_result = None
for r in results:
    if 'Morehead' in r['paper_name'] and '2017' in r['paper_name']:
        morehead_result = r
        break

if morehead_result and morehead_result['success']:
    exp_result = morehead_result['extraction_result']
    # Get first experiment
    exps = exp_result.get('experiments', [exp_result])
    if exps:
        exp = exps[0]
        auto_params_raw = {}
        for name, data in exp.get('parameters', {}).items():
            auto_params_raw[name] = data.get('value') if isinstance(data, dict) else data
        
        # Normalize parameter names
        auto_params = {}
        for name, value in auto_params_raw.items():
            normalized_name = normalize_param_name(name)
            auto_params[normalized_name] = value
        
        gold_params = gold_data.get('Morehead2017_Clamp', {})
        
        print("\nGOLD STANDARD PARAMETERS:")
        for key in sorted(gold_params.keys()):
            val = gold_params[key]
            if val and val.lower() not in ['', 'null', 'none', '?']:
                print(f"  {key}: {val}")
        
        print("\n" + "-"*80)
        print("AUTOMATED EXTRACTION PARAMETERS:")
        for key in sorted(auto_params.keys()):
            val = auto_params[key]
            if val:
                print(f"  {key}: {val}")
        
        print("\n" + "-"*80)
        print("PARAMETER MATCHING:")
        
        all_params = set(gold_params.keys()) | set(auto_params.keys())
        for param in sorted(all_params):
            if param in metadata:
                continue
            
            gold_val = gold_params.get(param)
            auto_val = auto_params.get(param)
            
            if param == 'lab' or not gold_val or gold_val.lower() in ['null', 'none', '', 'n/a', '?']:
                continue
            
            status = "❓"
            if auto_val is None or auto_val == '':
                status = "❌ FN (missing)"
            elif str(gold_val).lower().strip() == str(auto_val).lower().strip():
                status = "✅ TP (match)"
            else:
                status = f"⚠️  VM (gold: {gold_val}, auto: {auto_val})"
            
            print(f"  {param:<30} {status}")
