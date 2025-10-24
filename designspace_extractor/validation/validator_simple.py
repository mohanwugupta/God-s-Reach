#!/usr/bin/env python3
"""Validation Engine - Compare automated extraction to gold standard in Google Sheets."""
import json
import sys
import re
import os
from pathlib import Path
from collections import defaultdict

# Google Sheets API imports
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False


def load_gold_standard(spreadsheet_id, worksheet_name='Sheet1'):
    """Load gold standard from Google Sheets."""
    if not SHEETS_AVAILABLE:
        print("ERROR: Google Sheets libraries not installed")
        return {}
    
    creds_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE', 'credentials.json')
    if not os.path.exists(creds_file):
        print(f"ERROR: Credentials file not found: {creds_file}")
        return {}
    
    credentials = service_account.Credentials.from_service_account_file(
        creds_file, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
    )
    service = build('sheets', 'v4', credentials=credentials)
    
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"{worksheet_name}!A:Z"
    ).execute()
    
    rows = result.get('values', [])
    if not rows:
        return {}
    
    headers = rows[0]
    gold = {}
    
    for row in rows[1:]:
        if not row:
            continue
        entry = {}
        for i, header in enumerate(headers):
            val = row[i].strip() if i < len(row) and row[i] else None
            entry[header] = val if val else None
        
        study_id = entry.get('study_id')
        if study_id:
            gold[study_id] = entry
    
    return gold


def load_automated_results(file_path):
    """Load automated results."""
    with open(file_path, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    auto = {}
    for res in results:
        if not res['success']:
            continue
        
        extraction = res['extraction_result']
        experiments = extraction.get('experiments', [extraction])
        
        for idx, exp in enumerate(experiments, 1):
            base_id = extract_id(res['paper_name'])
            study_id = f"{base_id}_EXP{idx}" if len(experiments) > 1 else base_id
            
            params = {}
            for name, data in exp.get('parameters', {}).items():
                params[name] = data.get('value') if isinstance(data, dict) else data
            
            auto[study_id] = params
    
    return auto


def extract_id(paper_name):
    """Extract study ID from paper filename."""
    base = paper_name.replace('.pdf', '')
    match = re.search(r'^([A-Za-z]+).*?(\d{4})', base)
    return f"{match.group(1)}{match.group(2)}" if match else base.split()[0]


def compare_study(gold_params, auto_params):
    """Compare one study."""
    metadata = {'study_id', 'title', 'authors', 'year', 'notes', 'doi_or_url'}
    all_params = set(gold_params.keys()) | set(auto_params.keys())
    params = [p for p in all_params if p not in metadata]
    
    tp, fp, fn, vm = [], [], [], []
    
    for param in params:
        g = gold_params.get(param)
        a = auto_params.get(param)
        
        has_g = g is not None and str(g).strip() != ''
        has_a = a is not None and str(a).strip() != ''
        
        if has_g and has_a:
            if values_match(g, a):
                tp.append(param)
            else:
                vm.append((param, g, a))
        elif has_g:
            fn.append((param, g))
        elif has_a:
            fp.append((param, a))
    
    return tp, fp, fn, vm


def values_match(g, a):
    """Check if values match."""
    gs = str(g).strip().lower()
    as_str = str(a).strip().lower()
    
    if gs == as_str or gs in as_str or as_str in gs:
        return True
    
    try:
        gn = re.findall(r'[-+]?\d*\.?\d+', gs)
        an = re.findall(r'[-+]?\d*\.?\d+', as_str)
        if gn and an and abs(float(gn[0]) - float(an[0])) < 0.01:
            return True
    except:
        pass
    
    return False


def main():
    """Main validation."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--spreadsheet-id', required=True)
    parser.add_argument('--worksheet', default='Sheet1')
    parser.add_argument('--results', default='./batch_processing_results.json')
    args = parser.parse_args()
    
    print("Loading gold standard...")
    gold = load_gold_standard(args.spreadsheet_id, args.worksheet)
    print(f"Loaded {len(gold)} gold standard entries")
    
    print("\nLoading automated results...")
    auto = load_automated_results(Path(args.results))
    print(f"Loaded {len(auto)} automated results")
    
    print("\n" + "=" * 80)
    print("VALIDATION REPORT")
    print("=" * 80)
    
    all_tp, all_fp, all_fn, all_vm = 0, 0, 0, 0
    param_stats = defaultdict(lambda: [0, 0, 0, 0])  # tp, fp, fn, vm
    
    matched = 0
    for study_id in gold.keys():
        if study_id not in auto:
            continue
        
        matched += 1
        tp, fp, fn, vm = compare_study(gold[study_id], auto[study_id])
        
        all_tp += len(tp)
        all_fp += len(fp)
        all_fn += len(fn)
        all_vm += len(vm)
        
        for p in tp:
            param_stats[p][0] += 1
        for p, _, _ in fp:
            param_stats[p][1] += 1
        for p, _ in fn:
            param_stats[p][2] += 1
        for p, _, _ in vm:
            param_stats[p][3] += 1
    
    precision = all_tp / (all_tp + all_fp + all_vm) if (all_tp + all_fp + all_vm) > 0 else 0
    recall = all_tp / (all_tp + all_fn + all_vm) if (all_tp + all_fn + all_vm) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    print(f"\nOVERALL METRICS ({matched} studies matched)")
    print(f"  Precision: {precision:.3f}")
    print(f"  Recall: {recall:.3f}")
    print(f"  F1 Score: {f1:.3f}")
    print(f"  TP: {all_tp}, FP: {all_fp}, FN: {all_fn}, VM: {all_vm}")
    
    print(f"\nPER-PARAMETER METRICS")
    for param, stats in sorted(param_stats.items(), key=lambda x: -(x[1][0]/(sum(x[1])+1e-10)))[:20]:
        tp, fp, fn, vm = stats
        p = tp / (tp + fp + vm) if (tp + fp + vm) > 0 else 0
        r = tp / (tp + fn + vm) if (tp + fn + vm) > 0 else 0
        f = 2 * p * r / (p + r) if (p + r) > 0 else 0
        print(f"  {param:30} F1:{f:.2f} P:{p:.2f} R:{r:.2f} (TP:{tp} FP:{fp} FN:{fn} VM:{vm})")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
