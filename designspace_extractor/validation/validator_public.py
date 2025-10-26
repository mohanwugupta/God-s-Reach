#!/usr/bin/env python3
"""Validation Engine - Compare automated extraction to gold standard from public Google Sheet."""
import json
import sys
import re
import csv
from pathlib import Path
from collections import defaultdict
import urllib.request


# Parameter name mapping: automated_name -> gold_standard_name
PARAM_NAME_MAPPING = {
    # Magnitude/rotation parameters
    'rotation_magnitude_deg': 'perturbation_magnitude',
    
    # Sample size variations
    'sample_size_n': 'n_total',
    
    # Perturbation type
    'force_field_type': 'perturbation_class',
    
    # Add more mappings as needed
}

# Value synonym mapping: parameter -> {gold_value: [auto_synonyms]}
VALUE_SYNONYMS = {
    'effector': {
        'arm': ['reaching', 'horizontal reaching movements', 'upper limb', 'hand', 'wrist'],
        'leg': ['lower limb', 'foot', 'ankle'],
    },
    'environment': {
        'tablet/mouse': ['virtual', 'vr', '2d display', 'computer screen', 'monitor'],
        'vr': ['virtual reality', 'virtual environment', 'immersive'],
        'robotic manipulandum': ['robot', 'robotic device', 'manipulandum', 'haptic device'],
    },
    'population_type': {
        'healthy_adult': ['young adults', 'undergraduate', 'adults', 'healthy young adults', 'neurotypical'],
        'older_adult': ['elderly', 'seniors', 'aged', 'older adults'],
        'patient': ['clinical', 'neurological', 'stroke', 'cerebellar'],
    },
    'perturbation_class': {
        'visuomotor_rotation': ['visuomotor rotation', 'visual rotation', 'cursor rotation', 'vmr'],
        'force_field': ['curl field', 'velocity-dependent force field', 'dynamic perturbation'],
    },
    'feedback_type': {
        'endpoint_only': ['endpoint-only', 'endpoint feedback', 'endpoint', 'terminal feedback', 'terminal'],
        'clamped': ['error clamp', 'clamped feedback', 'clamp', 'error clamped', 'task-irrelevant feedback', 'clamped'],
        'concurrent': ['online feedback', 'continuous feedback', 'online'],
        'delayed': ['delayed feedback'],
    },
    'perturbation_schedule': {
        'abrupt': ['abruptly', 'sudden', 'suddenly', 'single-step', 'immediate', 'immediately'],
        'gradual': ['gradually', 'incremental', 'incrementally', 'ramp', 'ramped', 'slowly'],
    },
    'instruction_awareness': {
        'aim_report': ['aim reports', 'aim reporting', 'verbal report', 'verbal reports', 'reported angle', 'reported aiming', 'reported aiming direction', 'report aiming direction'],
        'instructed': ['informed', 'told', 'aware', 'explicit instruction', 'explicit group'],
        'uninstructed': ['naïve', 'unaware', 'no instruction', 'implicit learning', 'implicit group'],
    },
    'mechanism_focus': {
        'mixed': ['explicit and implicit', 'both explicit and implicit', 'implicit and explicit'],
        'implicit': ['implicit only', 'purely implicit', 'exclusively implicit', 'implicit adaptation', 'implicit learning'],
        'explicit': ['explicit only', 'purely explicit', 'exclusively explicit', 'explicit strategy'],
    },
}


def normalize_param_name(param_name):
    """Convert automated parameter name to gold standard name."""
    return PARAM_NAME_MAPPING.get(param_name, param_name)


def values_are_synonyms(param_name, gold_val, auto_val):
    """Check if two values are synonyms for a given parameter."""
    if param_name not in VALUE_SYNONYMS:
        return False
    
    g_lower = str(gold_val).lower().strip()
    a_lower = str(auto_val).lower().strip()
    
    # Check if gold value has synonyms and auto value matches one
    for standard_val, synonyms in VALUE_SYNONYMS[param_name].items():
        if standard_val.lower() == g_lower:
            # Gold matches a standard value, check if auto is a synonym
            if a_lower in [s.lower() for s in synonyms]:
                return True
            # Also check if auto matches the standard value
            if a_lower == standard_val.lower():
                return True
    
    return False


def load_gold_standard_csv(spreadsheet_id, gid='0'):
    """Load gold standard from public Google Sheet as CSV."""
    # Public CSV export URL
    csv_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
    
    print(f"📥 Fetching gold standard from Google Sheets...")
    print(f"   URL: {csv_url}")
    
    try:
        with urllib.request.urlopen(csv_url) as response:
            content = response.read().decode('utf-8')
        
        lines = content.splitlines()
        reader = csv.DictReader(lines)
        
        gold = {}
        for row in reader:
            # Clean up the row
            entry = {k: v.strip() if v else None for k, v in row.items()}
            
            study_id = entry.get('study_id')
            if study_id:
                gold[study_id] = entry
        
        print(f"✅ Loaded {len(gold)} gold standard entries")
        return gold
        
    except Exception as e:
        print(f"❌ ERROR loading Google Sheet: {e}")
        return {}


def load_automated_results(file_path):
    """Load automated results."""
    print(f"\n📥 Loading automated results from: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    auto = {}
    auto_by_doi = {}  # For DOI-based matching
    
    for res in results:
        if not res['success']:
            continue
        
        extraction = res['extraction_result']
        experiments = extraction.get('experiments', [extraction])
        
        for idx, exp in enumerate(experiments, 1):
            base_id = extract_id(res['paper_name'])
            study_id = f"{base_id}_EXP{idx}" if len(experiments) > 1 else base_id
            
            # Normalize parameter names to gold standard
            params = {}
            for name, data in exp.get('parameters', {}).items():
                value = data.get('value') if isinstance(data, dict) else data
                normalized_name = normalize_param_name(name)
                params[normalized_name] = value
            
            # Store by study_id
            auto[study_id] = params
            
            # Also store by DOI for flexible matching
            doi = params.get('doi_or_url', '')
            if doi and isinstance(doi, str):
                # Clean DOI (remove https://, dx.doi.org/, etc.)
                clean_doi = doi.replace('https://', '').replace('http://', '')
                clean_doi = clean_doi.replace('dx.doi.org/', '').replace('doi.org/', '')
                clean_doi = clean_doi.replace('DOI ', '').strip()
                if clean_doi:
                    auto_by_doi[clean_doi] = (study_id, params)
    
    print(f"✅ Loaded {len(auto)} automated extraction results")
    print(f"   ({len(auto_by_doi)} with DOI for flexible matching)")
    return auto, auto_by_doi


def extract_id(paper_name):
    """Extract study ID from paper filename."""
    base = paper_name.replace('.pdf', '')
    match = re.search(r'^([A-Za-z]+).*?(\d{4})', base)
    return f"{match.group(1)}{match.group(2)}" if match else base.split()[0]


def fuzzy_match(gold_val, auto_val, param_name=None):
    """Check if two values match (exact, substring, or numeric)."""
    if gold_val is None or auto_val is None:
        return False
    
    g, a = str(gold_val).lower().strip(), str(auto_val).lower().strip()
    
    # Exact match
    if g == a:
        return True
    
    # Check parameter-specific synonyms first
    if param_name and values_are_synonyms(param_name, gold_val, auto_val):
        return True
    
    # Normalize text: remove underscores, extra spaces, punctuation
    g_norm = re.sub(r'[_\s]+', ' ', g).strip()
    a_norm = re.sub(r'[_\s]+', ' ', a).strip()
    
    # Match after normalization (handles "visuomotor_rotation" vs "visuomotor rotation")
    if g_norm == a_norm:
        return True
    
    # Substring match (check both normalized and original)
    if g in a or a in g or g_norm in a_norm or a_norm in g_norm:
        return True
    
    # For compound values, check if key terms match
    # e.g., "aim_report" should match "reported aiming direction"
    g_words = set(re.findall(r'\w+', g_norm))
    a_words = set(re.findall(r'\w+', a_norm))
    
    # If gold has multiple words and most are in auto, consider it a match
    if len(g_words) >= 2 and len(g_words & a_words) >= len(g_words) * 0.6:
        return True
    
    # Numeric match with tolerance (handles "45" vs "45.0")
    try:
        g_num = float(re.search(r'[-+]?\d*\.?\d+', g).group())
        a_num = float(re.search(r'[-+]?\d*\.?\d+', a).group())
        return abs(g_num - a_num) / max(abs(g_num), 0.001) < 0.01  # 1% tolerance
    except:
        pass
    
    return False


def compare_study(gold_params, auto_params):
    """Compare one study."""
    metadata = {'study_id', 'title', 'authors', 'year', 'notes', 'doi_or_url', 'lab', 'dataset_link'}
    all_params = set(gold_params.keys()) | set(auto_params.keys())
    params = [p for p in all_params if p not in metadata]
    
    tp, fp, fn, vm = [], [], [], []
    
    for param in params:
        gold_val = gold_params.get(param)
        auto_val = auto_params.get(param)
        
        # Skip if gold is null/empty (not annotated) or if it's 'lab' (per user request)
        if param == 'lab':
            continue
        if not gold_val or gold_val.lower() in ['null', 'none', '', 'n/a', '?']:
            continue
        
        if auto_val is None or auto_val == '':
            fn.append(param)  # False Negative: should have extracted
        elif fuzzy_match(gold_val, auto_val, param):  # Pass param_name for synonym checking
            tp.append(param)  # True Positive: correct match
        else:
            vm.append(param)  # Value Mismatch: extracted but wrong
    
    # Check for False Positives (extracted but not in gold)
    for param in auto_params:
        if param not in metadata and param not in gold_params and param != 'lab':
            fp.append(param)
    
    return {'tp': tp, 'fp': fp, 'fn': fn, 'vm': vm}


def calculate_metrics(all_results):
    """Calculate overall precision, recall, F1."""
    total_tp = sum(len(r['tp']) for r in all_results.values())
    total_fp = sum(len(r['fp']) for r in all_results.values())
    total_fn = sum(len(r['fn']) for r in all_results.values())
    total_vm = sum(len(r['vm']) for r in all_results.values())
    
    precision = total_tp / (total_tp + total_fp + total_vm) if (total_tp + total_fp + total_vm) > 0 else 0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'tp': total_tp,
        'fp': total_fp,
        'fn': total_fn,
        'vm': total_vm
    }


def calculate_per_parameter_metrics(all_results, gold_data):
    """Calculate metrics per parameter."""
    param_stats = defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0, 'vm': 0, 'total_gold': 0})
    
    for study_id, result in all_results.items():
        for param in result['tp']:
            param_stats[param]['tp'] += 1
        for param in result['fp']:
            param_stats[param]['fp'] += 1
        for param in result['fn']:
            param_stats[param]['fn'] += 1
        for param in result['vm']:
            param_stats[param]['vm'] += 1
    
    # Count total gold annotations per parameter
    metadata = {'study_id', 'title', 'authors', 'year', 'notes', 'doi_or_url', 'lab', 'dataset_link'}
    for gold_params in gold_data.values():
        for param, val in gold_params.items():
            if param in metadata or param == 'lab':
                continue
            if val and val.lower() not in ['null', 'none', '', 'n/a', '?']:
                param_stats[param]['total_gold'] += 1
    
    # Calculate metrics
    param_metrics = {}
    for param, stats in param_stats.items():
        tp, fp, fn, vm = stats['tp'], stats['fp'], stats['fn'], stats['vm']
        total_gold = stats['total_gold']
        
        precision = tp / (tp + fp + vm) if (tp + fp + vm) > 0 else 0
        recall = tp / total_gold if total_gold > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        param_metrics[param] = {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'tp': tp,
            'fp': fp,
            'fn': fn,
            'vm': vm,
            'total_gold': total_gold
        }
    
    return param_metrics


def print_report(overall, per_param):
    """Print formatted validation report."""
    print("\n" + "="*80)
    print("📊 VALIDATION REPORT")
    print("="*80)
    
    print(f"\n🎯 Overall Metrics:")
    print(f"   Precision: {overall['precision']:.3f}")
    print(f"   Recall:    {overall['recall']:.3f}")
    print(f"   F1 Score:  {overall['f1']:.3f}")
    print(f"\n   True Positives:  {overall['tp']}")
    print(f"   False Positives: {overall['fp']}")
    print(f"   False Negatives: {overall['fn']}")
    print(f"   Value Mismatches: {overall['vm']}")
    
    print(f"\n📋 Per-Parameter Performance (Top 10 by F1):")
    sorted_params = sorted(per_param.items(), key=lambda x: x[1]['f1'], reverse=True)
    print(f"{'Parameter':<30} {'F1':>6} {'Prec':>6} {'Rec':>6} {'TP':>4} {'FP':>4} {'FN':>4} {'VM':>4}")
    print("-"*80)
    for param, metrics in sorted_params[:10]:
        print(f"{param:<30} {metrics['f1']:>6.3f} {metrics['precision']:>6.3f} {metrics['recall']:>6.3f} "
              f"{metrics['tp']:>4} {metrics['fp']:>4} {metrics['fn']:>4} {metrics['vm']:>4}")
    
    print(f"\n⚠️ Bottom 10 Parameters (need improvement):")
    print(f"{'Parameter':<30} {'F1':>6} {'Prec':>6} {'Rec':>6} {'TP':>4} {'FP':>4} {'FN':>4} {'VM':>4}")
    print("-"*80)
    for param, metrics in sorted_params[-10:]:
        print(f"{param:<30} {metrics['f1']:>6.3f} {metrics['precision']:>6.3f} {metrics['recall']:>6.3f} "
              f"{metrics['tp']:>4} {metrics['fp']:>4} {metrics['fn']:>4} {metrics['vm']:>4}")


def match_studies(gold_data, auto_data, auto_by_doi):
    """Match gold standard entries to automated results.
    
    Returns dict mapping gold_study_id -> (auto_study_id, auto_params)
    """
    matches = {}
    
    print(f"\n🔗 Matching gold standard to automated results...")
    
    for gold_id, gold_params in gold_data.items():
        # Strategy 1: Try DOI matching (most reliable)
        gold_doi = gold_params.get('doi_or_url', '')
        if gold_doi:
            clean_doi = gold_doi.replace('https://', '').replace('http://', '')
            clean_doi = clean_doi.replace('dx.doi.org/', '').replace('doi.org/', '')
            clean_doi = clean_doi.replace('DOI ', '').strip()
            
            if clean_doi in auto_by_doi:
                auto_id, auto_params = auto_by_doi[clean_doi]
                matches[gold_id] = (auto_id, auto_params)
                print(f"   ✅ {gold_id} → {auto_id} (via DOI: {clean_doi[:30]}...)")
                continue
        
        # Strategy 2: Try fuzzy study_id matching
        # Extract author/year from gold_id
        match = re.search(r'^([A-Za-z]+)(\d{4})', gold_id)
        if match:
            author, year = match.groups()
            
            # Look for matching auto_id with same author+year
            for auto_id, auto_params in auto_data.items():
                if author.lower() in auto_id.lower() and year in auto_id:
                    matches[gold_id] = (auto_id, auto_params)
                    print(f"   ✅ {gold_id} → {auto_id} (via author+year)")
                    break
    
    unmatched = set(gold_data.keys()) - set(matches.keys())
    if unmatched:
        print(f"\n   ⚠️  Unmatched gold standard entries: {unmatched}")
    
    return matches


def main():
    """Main validation workflow."""
    import argparse
    parser = argparse.ArgumentParser(description='Validate extraction against public Google Sheet')
    parser.add_argument('--spreadsheet-id', required=True, help='Google Sheets ID')
    parser.add_argument('--gid', default='486594143', help='Sheet GID (default: 486594143)')
    parser.add_argument('--results', required=True, help='Path to batch_processing_results.json')
    args = parser.parse_args()
    
    # Load data
    gold_data = load_gold_standard_csv(args.spreadsheet_id, args.gid)
    if not gold_data:
        print("❌ Failed to load gold standard")
        return 1
    
    auto_data, auto_by_doi = load_automated_results(args.results)
    if not auto_data:
        print("❌ Failed to load automated results")
        return 1
    
    # Match studies
    matches = match_studies(gold_data, auto_data, auto_by_doi)
    
    if not matches:
        print("\n❌ No matching studies found between gold standard and automated results")
        return 1
    
    # Compare
    print(f"\n🔍 Comparing {len(matches)} matched studies...")
    all_results = {}
    
    for gold_id, (auto_id, auto_params) in matches.items():
        all_results[gold_id] = compare_study(gold_data[gold_id], auto_params)
    
    # Calculate metrics
    overall = calculate_metrics(all_results)
    per_param = calculate_per_parameter_metrics(all_results, gold_data)
    
    # Print report
    print_report(overall, per_param)
    
    print("\n✅ Validation complete!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
