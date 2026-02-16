#!/usr/bin/env python3
"""
Analyze gold standard entries for consistency and provide recommendations
for human raters to improve alignment with automated extraction.
"""
import json
import urllib.request
import csv
import sys
from collections import defaultdict
from typing import Dict, List, Set, Tuple

# Set UTF-8 encoding for Windows terminal
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Synonym mapping from validator
VALUE_SYNONYMS = {
    'feedback_type': {
        'endpoint_only': ['endpoint', 'end-point', 'terminal', 'end point'],
        'continuous': ['continous', 'continuous view', 'online'],
        'error_clamped': ['clamped', 'clamp', 'error clamp'],
        'delayed': ['delayed feedback'],
        'cursor': ['cursor feedback'],
    },
    'instruction_awareness': {
        'aim_report': ['aim report', 'aiming report', 'strategy report', 'verbal report'],
        'none': ['no instruction', 'uninstructed'],
    },
    'perturbation_schedule': {
        'abrupt': ['sudden', 'immediate', 'step'],
        'gradual': ['progressive', 'incremental', 'ramped'],
        'random': ['stochastic', 'variable'],
    },
}

def normalize_value(value: str, parameter: str = None) -> str:
    """Normalize a value for comparison."""
    if not value or value in ['?', 'null', 'none', '', 'N/A']:
        return None
    
    val = value.strip().lower()
    
    # Check synonyms if parameter is specified
    if parameter and parameter in VALUE_SYNONYMS:
        for canonical, synonyms in VALUE_SYNONYMS[parameter].items():
            if val in [s.lower() for s in synonyms]:
                return canonical
            if val == canonical.lower():
                return canonical
    
    return val

def load_gold_standard() -> List[Dict]:
    """Load gold standard from Google Sheets."""
    spreadsheet_id = "1nc34GT31emdpVJw7Vq-1cRI7_TtJ8Tdj"
    gid = "486594143"
    csv_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
    
    with urllib.request.urlopen(csv_url) as response:
        content = response.read().decode('utf-8')
    
    lines = content.splitlines()
    reader = csv.DictReader(lines)
    entries = []
    for row in reader:
        entry = {k: v.strip() if v else None for k, v in row.items()}
        if entry.get('study_id'):  # Only include rows with study_id
            entries.append(entry)
    
    return entries

def load_automated_results() -> Dict:
    """Load automated extraction results."""
    with open('batch_processing_results.json', 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Build a lookup by paper_name and study_id
    lookup = {}
    for r in results:
        if r['success']:
            exp = r['extraction_result']
            study_id = exp.get('study_id', '')
            paper_name = r.get('paper_name', '')
            
            # Add by study_id
            if study_id:
                lookup[study_id] = exp
            
            # Also try to extract author+year from paper_name
            # e.g., "Taylor2014_JNeuro_Endpoint.pdf" -> "Taylor2014"
            if paper_name:
                # Remove .pdf
                base_name = paper_name.replace('.pdf', '')
                # Store with various keys
                lookup[base_name] = exp
                # Try to extract author+year pattern
                import re
                match = re.match(r'^([A-Za-z]+)(\d{4})', base_name)
                if match:
                    author_year = f"{match.group(1)}{match.group(2)}"
                    lookup[author_year] = exp
    
    return lookup

def analyze_value_mismatches(gold_entries: List[Dict], auto_results: Dict) -> Dict:
    """
    Analyze value mismatches and identify patterns in gold standard entries.
    Returns dict with mismatch analysis and recommendations.
    """
    analysis = {
        'parameter_mismatches': defaultdict(list),
        'terminology_issues': defaultdict(set),
        'format_inconsistencies': defaultdict(list),
        'missing_in_auto': defaultdict(int),
        'missing_in_gold': defaultdict(int),
    }
    
    metadata_fields = {'study_id', 'title', 'authors', 'year', 'doi_or_url', 'lab', 'dataset_link', 'notes'}
    
    for gold_entry in gold_entries:
        study_id = gold_entry['study_id']
        
        # Try to find matching automated result
        # Extract author and year from study_id (e.g., "Butcher2018EXP1" -> "Butcher" "2018")
        import re
        match = re.match(r'^([A-Za-z]+)(\d{4})', study_id)
        if not match:
            continue
        
        gold_author = match.group(1).lower()
        gold_year = match.group(2)
        
        # Try exact match first, then partial matches
        auto_exp = None
        
        # Look for keys containing both author and year
        for key, exp in auto_results.items():
            key_lower = key.lower()
            # Check if both author and year are in the key
            if gold_author in key_lower and gold_year in key_lower:
                auto_exp = exp
                print(f"   Matched {study_id} -> {key}")
                break
        
        if not auto_exp:
            print(f"   ⚠️  No match for {study_id}")
            continue
        
        # Extract automated parameters
        auto_params = {}
        for name, data in auto_exp.get('parameters', {}).items():
            value = data.get('value') if isinstance(data, dict) else data
            auto_params[name] = value
        
        # Compare each parameter
        for param_name, gold_value in gold_entry.items():
            if param_name in metadata_fields:
                continue
            
            # Skip empty/unknown gold values
            if not gold_value or gold_value.lower() in ['?', 'null', 'none', '', 'n/a']:
                continue
            
            auto_value = auto_params.get(param_name)
            
            if auto_value is None or auto_value == '':
                analysis['missing_in_auto'][param_name] += 1
                continue
            
            # Normalize both values
            norm_gold = normalize_value(gold_value, param_name)
            norm_auto = normalize_value(str(auto_value), param_name)
            
            if norm_gold != norm_auto:
                analysis['parameter_mismatches'][param_name].append({
                    'study_id': study_id,
                    'gold': gold_value,
                    'auto': str(auto_value),
                    'norm_gold': norm_gold,
                    'norm_auto': norm_auto,
                })
                
                # Track terminology differences
                if norm_gold and norm_auto:
                    analysis['terminology_issues'][param_name].add((gold_value, str(auto_value)))
    
    return analysis

def print_recommendations(analysis: Dict):
    """Print recommendations for human raters based on analysis."""
    print("\n" + "="*80)
    print("GOLD STANDARD CONSISTENCY ANALYSIS & RATER RECOMMENDATIONS")
    print("="*80)
    
    print("\n📊 OVERVIEW:")
    print(f"   Parameters with mismatches: {len(analysis['parameter_mismatches'])}")
    print(f"   Total mismatch instances: {sum(len(v) for v in analysis['parameter_mismatches'].values())}")
    
    # Analyze each parameter
    for param_name in sorted(analysis['parameter_mismatches'].keys()):
        mismatches = analysis['parameter_mismatches'][param_name]
        if not mismatches:
            continue
        
        print("\n" + "-"*80)
        print(f"📌 PARAMETER: {param_name}")
        print(f"   Mismatch count: {len(mismatches)}")
        
        # Show unique gold/auto value pairs
        value_pairs = defaultdict(list)
        for m in mismatches:
            key = (m['gold'], m['auto'])
            value_pairs[key].append(m['study_id'])
        
        print("\n   Value Comparisons:")
        for (gold_val, auto_val), study_ids in sorted(value_pairs.items(), key=lambda x: len(x[1]), reverse=True):
            count = len(study_ids)
            examples = ', '.join(study_ids[:3])
            if count > 3:
                examples += f" (+{count-3} more)"
            print(f"      Gold: '{gold_val}' vs Auto: '{auto_val}' [{examples}]")
        
        # Provide recommendations
        print("\n   💡 RECOMMENDATIONS FOR HUMAN RATERS:")
        
        if param_name == 'perturbation_schedule':
            print("      • Use ONLY: 'abrupt', 'gradual', 'random', 'gradual_abrupt'")
            print("      • 'abrupt' = sudden onset (step function)")
            print("      • 'gradual' = progressive increase/decrease (ramp)")
            print("      • 'gradual_abrupt' = combination (some gradual, some abrupt)")
            print("      • Avoid: 'consistensy of X in a row' - this is consistency, not schedule")
        
        elif param_name == 'feedback_type':
            print("      • Use ONLY: 'endpoint_only', 'continuous', 'error_clamped', 'delayed', 'cursor', 'no_cursor'")
            print("      • Separate multiple types with commas: 'endpoint_only, continuous'")
            print("      • 'endpoint_only' or 'endpoint' (not 'end-point' or 'terminal')")
            print("      • 'continuous' (not 'continous' - fix typo)")
            print("      • 'error_clamped' or 'clamped' (both acceptable)")
        
        elif param_name == 'instruction_awareness':
            print("      • Use ONLY: 'aim_report', 'strategy_report', 'none'")
            print("      • 'aim_report' = participants report aiming direction")
            print("      • 'strategy_report' = participants report strategy used")
            print("      • 'none' = no explicit measurement of awareness")
        
        elif param_name == 'mechanism_focus':
            print("      • Use ONLY: 'explicit', 'implicit', 'mixed'")
            print("      • 'explicit' = study focuses on conscious strategies")
            print("      • 'implicit' = study focuses on automatic learning")
            print("      • 'mixed' = study examines both explicit and implicit")
        
        elif param_name == 'primary_outcomes':
            print("      • Be specific about the KEY finding(s)")
            print("      • Focus on adaptation-related outcomes (not demographics)")
            print("      • Example formats:")
            print("        - 'Implicit adaptation reduced in cerebellar patients'")
            print("        - 'Direction information required for implicit learning'")
            print("        - 'Aftereffects present only with cursor feedback'")
        
        elif param_name == 'feedback_delay':
            print("      • Use format: NUMBER + UNIT (e.g., '1.5s', '500ms', '2s')")
            print("      • Use 's' for seconds, 'ms' for milliseconds")
            print("      • Use '0s' for immediate feedback (not just '0')")
            print("      • For multiple delays, separate with commas: '0s, 2s'")
        
        elif param_name == 'perturbation_magnitude':
            print("      • Include UNIT with number: '45°', '30°' (not just '45')")
            print("      • For multiple values, use commas: '45°, 90°'")
            print("      • For ranges, use 'to': '0° to 45°'")
            print("      • Include direction if relevant: '45° CCW', '30° CW'")
        
        elif param_name == 'target_hit_criteria':
            print("      • Use ONLY: 'shooting', 'stop_at_target', 'predetermined', 'via_point'")
            print("      • 'shooting' = ballistic reach through target")
            print("      • 'stop_at_target' = controlled stop at target")
            print("      • 'predetermined' = pre-programmed trajectory")
        
        elif param_name == 'cue_modalities':
            print("      • Use ONLY: 'visual', 'auditory', 'spatial', 'text', 'color'")
            print("      • Capitalize first letter: 'Visual', 'Text', 'Spatial'")
            print("      • For multiple, separate with commas: 'Visual, Auditory'")
        
        else:
            # Generic recommendation
            print(f"      • Check for typos and spelling consistency")
            print(f"      • Use consistent terminology across studies")
            print(f"      • Refer to automated extraction for suggested values")
    
    # Show parameters frequently missing in auto
    print("\n" + "="*80)
    print("📋 PARAMETERS FREQUENTLY MISSING IN AUTOMATED EXTRACTION:")
    print("   (These may need better extraction patterns)")
    missing_sorted = sorted(analysis['missing_in_auto'].items(), key=lambda x: x[1], reverse=True)
    for param, count in missing_sorted[:10]:
        print(f"      {param}: {count} instances")
    
    print("\n" + "="*80)
    print("✅ GENERAL RECOMMENDATIONS FOR ALL RATERS:")
    print("="*80)
    print("""
   1. CONSISTENCY IS KEY:
      • Use the same terminology across all studies
      • Refer to previous entries for similar parameters
      • When in doubt, check what the automated extraction suggests
   
   2. USE CONTROLLED VOCABULARIES:
      • Each parameter has a limited set of valid values
      • See parameter-specific recommendations above
      • Avoid free-form text unless necessary (e.g., notes field)
   
   3. FORMAT STANDARDS:
      • Numbers with units: '45°', '1.5s', '500ms'
      • Multiple values: separated by commas
      • Ranges: use 'to' (e.g., '0° to 45°')
      • Boolean-like: use 'yes'/'no' or presence/absence
   
   4. HANDLING UNCERTAINTY:
      • Use '?' for unknown values (don't leave blank)
      • Add clarification in 'notes' field if needed
      • Don't guess - mark as unknown if not clearly stated in paper
   
   5. MULTI-EXPERIMENT STUDIES:
      • Create separate rows for each experiment
      • Use consistent study_id format: AuthorYearEXP1, AuthorYearEXP2, etc.
      • Include experiment number in title if needed
   
   6. QUALITY CHECKS:
      • Review your entries against automated extraction
      • Check for typos (especially common: 'continous' → 'continuous')
      • Ensure units are included with numeric values
      • Verify controlled vocabulary terms match exactly
""")

def main():
    print("Loading gold standard...")
    gold_entries = load_gold_standard()
    print(f"✅ Loaded {len(gold_entries)} gold standard entries with study_id")
    
    print("\nLoading automated extraction results...")
    auto_results = load_automated_results()
    print(f"✅ Loaded {len(auto_results)} automated results")
    print(f"\nSample automated result keys: {list(auto_results.keys())[:10]}")
    print(f"Sample gold standard study_ids: {[e['study_id'] for e in gold_entries[:10]]}")
    
    print("\nAnalyzing mismatches...")
    analysis = analyze_value_mismatches(gold_entries, auto_results)
    
    print_recommendations(analysis)

if __name__ == '__main__':
    main()
