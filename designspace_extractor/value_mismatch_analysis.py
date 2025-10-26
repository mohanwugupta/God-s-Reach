#!/usr/bin/env python3
"""Show only VALUE MISMATCHES after name normalization."""
import json
import urllib.request
import csv
import re

# Parameter name mapping
PARAM_NAME_MAPPING = {
    'rotation_magnitude_deg': 'perturbation_magnitude',
    'sample_size_n': 'n_total',
    'force_field_type': 'perturbation_class',
}

def normalize_param_name(param_name):
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

print("="*100)
print("VALUE MISMATCHES ANALYSIS (After Name Normalization)")
print("="*100)
print("\nThese parameters are extracted but with WRONG VALUES:\n")

metadata = {'study_id', 'title', 'authors', 'year', 'notes', 'doi_or_url', 'lab', 'dataset_link'}

# Taylor 2014
for r in results:
    if '3023.full.pdf' in r['paper_name']:
        exp = r['extraction_result']
        auto_params = {}
        for name, data in exp.get('parameters', {}).items():
            value = data.get('value') if isinstance(data, dict) else data
            normalized_name = normalize_param_name(name)
            auto_params[normalized_name] = value
        
        gold_params = gold_data.get('Taylor2014_JNeuro_Endpoint', {})
        
        print("📄 TAYLOR 2014 (3023.full.pdf)")
        print("-" * 100)
        print(f"{'Parameter':<30} {'Gold Standard':<35} {'Automated Extraction':<35}")
        print("-" * 100)
        
        for param in sorted(set(gold_params.keys()) | set(auto_params.keys())):
            if param in metadata or param == 'lab':
                continue
            
            gold_val = gold_params.get(param)
            auto_val = auto_params.get(param)
            
            # Skip if not in gold or gold is empty
            if not gold_val or gold_val.lower() in ['null', 'none', '', 'n/a', '?']:
                continue
            
            # Only show VALUE MISMATCHES
            if auto_val and str(gold_val).lower().strip() != str(auto_val).lower().strip():
                print(f"{param:<30} {str(gold_val):<35} {str(auto_val):<35}")
        
        break

print("\n" + "="*100)

# Morehead 2017
for r in results:
    if 'Morehead' in r['paper_name'] and '2017' in r['paper_name']:
        exp_result = r['extraction_result']
        exps = exp_result.get('experiments', [exp_result])
        if exps:
            exp = exps[0]
            auto_params = {}
            for name, data in exp.get('parameters', {}).items():
                value = data.get('value') if isinstance(data, dict) else data
                normalized_name = normalize_param_name(name)
                auto_params[normalized_name] = value
            
            gold_params = gold_data.get('Morehead2017_Clamp', {})
            
            print("\n📄 MOREHEAD 2017")
            print("-" * 100)
            print(f"{'Parameter':<30} {'Gold Standard':<35} {'Automated Extraction':<35}")
            print("-" * 100)
            
            for param in sorted(set(gold_params.keys()) | set(auto_params.keys())):
                if param in metadata or param == 'lab':
                    continue
                
                gold_val = gold_params.get(param)
                auto_val = auto_params.get(param)
                
                if not gold_val or gold_val.lower() in ['null', 'none', '', 'n/a', '?']:
                    continue
                
                # Only show VALUE MISMATCHES
                if auto_val and str(gold_val).lower().strip() != str(auto_val).lower().strip():
                    print(f"{param:<30} {str(gold_val):<35} {str(auto_val):<35}")
        
        break

print("\n" + "="*100)
print("\n📊 SUMMARY OF VALUE MISMATCH CATEGORIES:\n")
print("1. TEXT FORMAT DIFFERENCES:")
print("   - perturbation_class: 'visuomotor_rotation' vs 'visuomotor rotation' (underscore)")
print("   - perturbation_magnitude: '45' vs '45.0' (decimal)")
print("\n2. SYNONYM/VOCABULARY ISSUES:")
print("   - effector: 'arm' vs 'horizontal reaching movements' / 'reaching'")
print("   - environment: 'tablet/mouse' vs 'virtual' / 'vr'")
print("   - population_type: 'healthy_adult' vs 'young adults' / 'Undergraduate'")
print("\n3. INCORRECT EXTRACTIONS (Wrong section/context):")
print("   - feedback_type: 'endpoint_only'/'clamped' vs 'knowledge of results'/'Visual feedback'")
print("   - perturbation_schedule: 'abrupt' vs 'random'")
print("   - instruction_awareness: 'aim_report'/'uninstructed' vs 'instructed'")
print("   - mechanism_focus: 'mixed' vs 'implicit'")
print("   - primary_outcomes: Wrong descriptions")
print("\n" + "="*100)
