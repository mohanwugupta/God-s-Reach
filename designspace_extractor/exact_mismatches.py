#!/usr/bin/env python3
"""Show EXACT mismatches with current fuzzy matching applied."""
import json
import urllib.request
import csv
import re

# Use the same matching logic as validator
PARAM_NAME_MAPPING = {
    'rotation_magnitude_deg': 'perturbation_magnitude',
    'sample_size_n': 'n_total',
    'force_field_type': 'perturbation_class',
}

VALUE_SYNONYMS = {
    'effector': {
        'arm': ['reaching', 'horizontal reaching movements', 'upper limb', 'hand', 'wrist'],
    },
    'environment': {
        'tablet/mouse': ['virtual', 'vr', '2d display', 'computer screen', 'monitor'],
    },
    'population_type': {
        'healthy_adult': ['young adults', 'undergraduate', 'adults', 'healthy young adults'],
    },
    'perturbation_class': {
        'visuomotor_rotation': ['visuomotor rotation', 'visual rotation', 'cursor rotation'],
    },
}

def normalize_param_name(param_name):
    return PARAM_NAME_MAPPING.get(param_name, param_name)

def values_are_synonyms(param_name, gold_val, auto_val):
    if param_name not in VALUE_SYNONYMS:
        return False
    g_lower = str(gold_val).lower().strip()
    a_lower = str(auto_val).lower().strip()
    for standard_val, synonyms in VALUE_SYNONYMS[param_name].items():
        if standard_val.lower() == g_lower:
            if a_lower in [s.lower() for s in synonyms]:
                return True
            if a_lower == standard_val.lower():
                return True
    return False

def fuzzy_match(gold_val, auto_val, param_name=None):
    if gold_val is None or auto_val is None:
        return False
    g, a = str(gold_val).lower().strip(), str(auto_val).lower().strip()
    if g == a:
        return True
    if param_name and values_are_synonyms(param_name, gold_val, auto_val):
        return True
    g_norm = re.sub(r'[_\s]+', ' ', g).strip()
    a_norm = re.sub(r'[_\s]+', ' ', a).strip()
    if g_norm == a_norm:
        return True
    if g in a or a in g:
        return True
    try:
        g_num = float(re.search(r'[-+]?\d*\.?\d+', g).group())
        a_num = float(re.search(r'[-+]?\d*\.?\d+', a).group())
        return abs(g_num - a_num) / max(abs(g_num), 0.001) < 0.01
    except:
        pass
    return False

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

# Load automated
with open('batch_processing_results.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

print("="*100)
print("EXACT VALUE MISMATCHES (After All Fuzzy Matching)")
print("="*100)

metadata = {'study_id', 'title', 'authors', 'year', 'notes', 'doi_or_url', 'lab', 'dataset_link'}

# Process both papers
papers = [
    ('3023.full.pdf', 'Taylor2014_JNeuro_Endpoint', 'TAYLOR 2014'),
    ('Morehead', 'Morehead2017_Clamp', 'MOREHEAD 2017')
]

for search_term, gold_id, display_name in papers:
    # Find result
    result = None
    for r in results:
        if search_term in r['paper_name']:
            result = r
            break
    
    if not result or not result['success']:
        continue
    
    # Get automated params
    exp_result = result['extraction_result']
    exps = exp_result.get('experiments', [exp_result])
    exp = exps[0] if exps else exp_result
    
    auto_params_raw = {}
    for name, data in exp.get('parameters', {}).items():
        value = data.get('value') if isinstance(data, dict) else data
        auto_params_raw[name] = value
    
    # Normalize names
    auto_params = {}
    for name, value in auto_params_raw.items():
        normalized_name = normalize_param_name(name)
        auto_params[normalized_name] = value
    
    gold_params = gold_data.get(gold_id, {})
    
    # Find mismatches
    mismatches = []
    for param in sorted(set(gold_params.keys()) | set(auto_params.keys())):
        if param in metadata or param == 'lab':
            continue
        
        gold_val = gold_params.get(param)
        auto_val = auto_params.get(param)
        
        # Skip if not in gold or empty
        if not gold_val or gold_val.lower() in ['null', 'none', '', 'n/a', '?']:
            continue
        
        # Check if it's a mismatch
        if auto_val and not fuzzy_match(gold_val, auto_val, param):
            mismatches.append({
                'param': param,
                'gold': gold_val,
                'auto': auto_val
            })
    
    if mismatches:
        print(f"\n📄 {display_name}")
        print("-" * 100)
        print(f"{'Parameter':<30} {'Gold Standard':<35} {'Automated Extraction':<35}")
        print("-" * 100)
        for m in mismatches:
            print(f"{m['param']:<30} {m['gold']:<35} {m['auto']:<35}")

print("\n" + "="*100)
print("\n📊 MISMATCH ANALYSIS:\n")

# Count by parameter across all papers
mismatch_counts = {}
for search_term, gold_id, _ in papers:
    result = None
    for r in results:
        if search_term in r['paper_name']:
            result = r
            break
    
    if not result or not result['success']:
        continue
    
    exp_result = result['extraction_result']
    exps = exp_result.get('experiments', [exp_result])
    exp = exps[0] if exps else exp_result
    
    auto_params = {}
    for name, data in exp.get('parameters', {}).items():
        value = data.get('value') if isinstance(data, dict) else data
        normalized_name = normalize_param_name(name)
        auto_params[normalized_name] = value
    
    gold_params = gold_data.get(gold_id, {})
    
    for param in set(gold_params.keys()) | set(auto_params.keys()):
        if param in metadata or param == 'lab':
            continue
        gold_val = gold_params.get(param)
        auto_val = auto_params.get(param)
        
        if not gold_val or gold_val.lower() in ['null', 'none', '', 'n/a', '?']:
            continue
        
        if auto_val and not fuzzy_match(gold_val, auto_val, param):
            if param not in mismatch_counts:
                mismatch_counts[param] = 0
            mismatch_counts[param] += 1

print("Parameters with mismatches:")
for param, count in sorted(mismatch_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {param}: {count} paper(s)")

print("\n" + "="*100)
