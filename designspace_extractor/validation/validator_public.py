#!/usr/bin/env python3
"""Validation Engine - Compare automated extraction to gold standard from public Google Sheet."""
import json
import sys
import re
import csv
from pathlib import Path
from collections import defaultdict
import urllib.request

# Set UTF-8 encoding for Windows terminal
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass


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
        'arm': ['reaching', 'horizontal reaching movements', 'upper limb', 'hand', 'wrist', 'reaching arm'],
        'leg': ['lower limb', 'foot', 'ankle', 'lower extremity'],
        'finger': ['digits', 'hand'],
    },
    'environment': {
        'tablet': ['tablet/mouse', 'touchscreen', 'digitizer'],
        'virtual': ['vr', '2d display', 'computer screen', 'monitor', 'display'],
        'vr': ['virtual reality', 'virtual environment', 'immersive', 'head-mounted display'],
        'robotic manipulandum': ['robot', 'robotic device', 'manipulandum', 'haptic device'],
        'kinarm': ['bkin', 'kinarm robot', 'robotic manipulandum'],
    },
    'population_type': {
        'healthy_adult': ['young adults', 'undergraduate', 'adults', 'healthy young adults', 'neurotypical', 'healthy', 'control'],
        'older_adult': ['elderly', 'seniors', 'aged', 'older adults', 'older'],
        'cerebellar_patient': ['cerebellar', 'ataxia', 'sca', 'spinocerebellar ataxia'],
        'stroke_patient': ['stroke', 'hemiparetic', 'post-stroke'],
    },
    'perturbation_class': {
        'visuomotor_rotation': ['visuomotor rotation', 'visual rotation', 'cursor rotation', 'vmr', 'visuomotor', 'rotation'],
        'force_field': ['curl field', 'velocity-dependent force field', 'dynamic perturbation', 'force'],
        'gain_change': ['gain', 'visuomotor gain', 'cursor gain'],
    },
    'feedback_type': {
        'endpoint_only': ['endpoint-only', 'endpoint feedback', 'endpoint', 'terminal feedback', 'terminal', 'end-point', 'end point'],
        'error_clamped': ['clamped', 'error clamp', 'clamped feedback', 'clamp', 'task-irrelevant feedback', 'error-clamped'],
        'continuous': ['concurrent', 'online feedback', 'continuous feedback', 'online', 'continous'],
        'delayed': ['delayed feedback', 'delay'],
        'cursor': ['cursor feedback', 'cursor visible'],
        'no_cursor': ['no cursor', 'without cursor', 'cursor hidden'],
    },
    'perturbation_schedule': {
        'abrupt': ['abruptly', 'sudden', 'suddenly', 'single-step', 'immediate', 'immediately', 'step'],
        'gradual': ['gradually', 'incremental', 'incrementally', 'ramp', 'ramped', 'slowly', 'progressive'],
        'random': ['stochastic', 'variable', 'randomized'],
    },
    'instruction_awareness': {
        'aim_report': ['aim reports', 'aim reporting', 'verbal report', 'verbal reports', 'reported angle', 'reported aiming', 'reported aiming direction', 'report aiming direction', 'aiming report'],
        'strategy_report': ['strategy reports', 'strategy reporting', 'reported strategy'],
        'instructed': ['informed', 'told', 'aware', 'explicit instruction', 'explicit group'],
        'uninstructed': ['naïve', 'unaware', 'no instruction', 'implicit learning', 'implicit group', 'none'],
        'none': ['no awareness', 'not measured', 'no report'],
    },
    'mechanism_focus': {
        'mixed': ['explicit and implicit', 'both explicit and implicit', 'implicit and explicit', 'combined'],
        'implicit': ['implicit only', 'purely implicit', 'exclusively implicit', 'implicit adaptation', 'implicit learning'],
        'explicit': ['explicit only', 'purely explicit', 'exclusively explicit', 'explicit strategy', 'explicit learning'],
    },
    'coordinate_frame': {
        'horizontal': ['horiztonal', 'cartesian', 'cartesian coordinates'],
        'polar': ['angular', 'radial'],
    },
    'target_hit_criteria': {
        'shooting': ['ballistic', 'through target', 'shoot through'],
        'stop_at_target': ['stop', 'controlled stop', 'reach to target'],
        'predetermined': ['pre-programmed', 'fixed trajectory'],
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


def load_gold_standard_csv(spreadsheet_id=None, gid='0', local_file=None):
    """
    Load gold standard from Google Sheet CSV or local file.
    
    Args:
        spreadsheet_id: Google Sheets ID (for online mode)
        gid: Sheet GID (for online mode)
        local_file: Path to local CSV file (for offline mode)
    
    Returns:
        Dictionary of gold standard entries keyed by study_id
    """
    gold = {}
    
    # Try local file first (offline mode)
    if local_file:
        print(f"📥 Loading gold standard from local file...")
        print(f"   Path: {local_file}")
        
        try:
            with open(local_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # Clean up the row
                    entry = {k: v.strip() if v else None for k, v in row.items()}
                    
                    study_id = entry.get('study_id')
                    if study_id:
                        gold[study_id] = entry
            
            print(f"✅ Loaded {len(gold)} gold standard entries from local file")
            return gold
            
        except FileNotFoundError:
            print(f"❌ ERROR: Local file not found: {local_file}")
            print(f"   Download gold standard with:")
            print(f"   python validation/download_gold_standard.py")
            return {}
        except Exception as e:
            print(f"❌ ERROR loading local file: {e}")
            return {}
    
    # Fall back to online mode (Google Sheets)
    if spreadsheet_id:
        csv_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
        
        print(f"📥 Fetching gold standard from Google Sheets...")
        print(f"   URL: {csv_url}")
        
        try:
            with urllib.request.urlopen(csv_url) as response:
                content = response.read().decode('utf-8')
            
            lines = content.splitlines()
            reader = csv.DictReader(lines)
            
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
            print(f"\n💡 TIP: For offline use, download gold standard first:")
            print(f"   python validation/download_gold_standard.py --spreadsheet-id {spreadsheet_id} --gid {gid}")
            return {}
    
    print("❌ ERROR: Must provide either --local-file or --spreadsheet-id")
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
    """
    Enhanced fuzzy matching with multiple strategies.
    
    Args:
        gold_val: Gold standard value
        auto_val: Automated extraction value
        param_name: Parameter name for context-specific matching
    
    Returns:
        Boolean indicating if values match
    """
    if gold_val is None or auto_val is None:
        return False
    
    g, a = str(gold_val).lower().strip(), str(auto_val).lower().strip()
    
    # 1. Exact match
    if g == a:
        return True
    
    # 2. Check parameter-specific synonyms first
    if param_name and values_are_synonyms(param_name, gold_val, auto_val):
        return True
    
    # 3. Normalize text: remove underscores, extra spaces, punctuation
    g_norm = re.sub(r'[_\s]+', ' ', g).strip()
    a_norm = re.sub(r'[_\s]+', ' ', a).strip()
    
    # Remove common punctuation that doesn't affect meaning
    for char in ['-', '_', '/', '°', '(', ')', '[', ']']:
        g_norm = g_norm.replace(char, ' ')
        a_norm = a_norm.replace(char, ' ')
    g_norm = re.sub(r'\s+', ' ', g_norm).strip()
    a_norm = re.sub(r'\s+', ' ', a_norm).strip()
    
    # Match after normalization
    if g_norm == a_norm:
        return True
    
    # 4. Substring match (check both normalized and original)
    if g in a or a in g or g_norm in a_norm or a_norm in g_norm:
        return True
    
    # 5. Typo tolerance: check for common typos
    typo_pairs = [
        ('horizontal', 'horiztonal'),
        ('continuous', 'continous'),
        ('endpoint', 'end-point'),
        ('endpoint', 'end point'),
    ]
    for correct, typo in typo_pairs:
        if (correct in g_norm and typo in a_norm) or (typo in g_norm and correct in a_norm):
            return True
    
    # 6. Word-based matching for compound values
    # e.g., "aim_report" should match "reported aiming direction"
    g_words = set(re.findall(r'\w+', g_norm))
    a_words = set(re.findall(r'\w+', a_norm))
    
    # Remove common stop words that don't affect meaning
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
    g_words = g_words - stop_words
    a_words = a_words - stop_words
    
    # If gold has multiple words and most are in auto, consider it a match
    if len(g_words) >= 2:
        overlap = len(g_words & a_words)
        # Match if at least 60% of meaningful words overlap
        if overlap >= len(g_words) * 0.6:
            return True
    
    # 7. Handle multi-value fields (comma-separated)
    if ',' in g or ',' in a:
        g_values = {v.strip() for v in g.split(',')}
        a_values = {v.strip() for v in a.split(',')}
        
        # Check if there's significant overlap in the value sets
        overlap = len(g_values & a_values)
        if overlap > 0 and overlap >= min(len(g_values), len(a_values)) * 0.5:
            return True
    
    # 8. Numeric match with tolerance (handles "45" vs "45.0", "30°" vs "30")
    try:
        # Extract all numbers from both strings
        g_nums = re.findall(r'[-+]?\d*\.?\d+', g)
        a_nums = re.findall(r'[-+]?\d*\.?\d+', a)
        
        if g_nums and a_nums:
            # For single numbers, check if they're close
            if len(g_nums) == 1 and len(a_nums) == 1:
                g_num = float(g_nums[0])
                a_num = float(a_nums[0])
                # 5% tolerance for numeric values
                if abs(g_num - a_num) / max(abs(g_num), 0.001) < 0.05:
                    return True
            # For multiple numbers, check if primary number matches
            elif g_nums[0] == a_nums[0]:
                return True
    except:
        pass
    
    # 9. Abbreviation matching
    abbreviations = {
        'ccw': 'counterclockwise',
        'cw': 'clockwise',
        'deg': 'degrees',
        's': 'seconds',
        'ms': 'milliseconds',
        'vmr': 'visuomotor rotation',
    }
    for abbr, full in abbreviations.items():
        if (abbr in g_words and full in a_norm) or (abbr in a_words and full in g_norm):
            return True
    
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
    parser = argparse.ArgumentParser(description='Validate extraction against gold standard')
    parser.add_argument('--spreadsheet-id', help='Google Sheets ID (for online mode)')
    parser.add_argument('--gid', default='486594143', help='Sheet GID (default: 486594143)')
    parser.add_argument('--local-file', help='Path to local gold standard CSV (for offline mode)')
    parser.add_argument('--results', required=True, help='Path to batch_processing_results.json')
    args = parser.parse_args()
    
    # Validate arguments
    if not args.local_file and not args.spreadsheet_id:
        print("❌ ERROR: Must provide either --local-file or --spreadsheet-id")
        print("\nUsage:")
        print("  Online:  python validator_public.py --spreadsheet-id ID --results results.json")
        print("  Offline: python validator_public.py --local-file gold_standard.csv --results results.json")
        return 1
    
    # Load data
    gold_data = load_gold_standard_csv(
        spreadsheet_id=args.spreadsheet_id,
        gid=args.gid,
        local_file=args.local_file
    )
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
