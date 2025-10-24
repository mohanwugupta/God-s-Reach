#!/usr/bin/env python3#!/usr/bin/env python3#!/usr/bin/env python3#!/usr/bin/env python3"""

"""Validation Engine - Compare automated extraction to gold standard."""

# -*- coding: utf-8 -*-

import json

import sys"""# -*- coding: utf-8 -*-

import re

from pathlib import PathValidation Engine - Compare Automated Extraction to Gold Standard

from collections import defaultdict

""""""# -*- coding: utf-8 -*-Validation module for checking extracted parameters.

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.sheets_api import GoogleSheetsAPI



import jsonValidation Engine - Compare Automated Extraction to Gold Standard

class ValidationEngine:

    """Validates automated extraction against gold standard."""import sys

    

    def __init__(self):import ioLoads gold standard from Google Sheets and validates automated extraction results.""""""

        self.sheets_api = GoogleSheetsAPI()

        self.gold_standard = {}from pathlib import Path

        self.automated_results = {}

        from typing import Dict, List, Any"""

    def load_gold_standard(self, worksheet_name='Sheet1'):

        """Load gold standard from Google Sheets."""from collections import defaultdict

        print(f"Loading gold standard from: {worksheet_name}")

        rows = self.sheets_api.get_all_rows(worksheet_name)import reValidation Enginefrom typing import Dict, Any, List

        

        if not rows:

            print("No data found")

            return {}# Set UTF-8 encodingimport json

        

        headers = rows[0]sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

        gold = {}

        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')import sysCompares automated extraction results against gold standard annotations in Google Sheets.import logging

        for row_idx, row in enumerate(rows[1:], 2):

            if not row:

                continue

            # Add parent directory to pathimport io

            entry = {}

            for col_idx, header in enumerate(headers):sys.path.insert(0, str(Path(__file__).parent.parent))

                if col_idx < len(row):

                    val = row[col_idx].strip() if row[col_idx] else Nonefrom pathlib import PathCalculates precision, recall, F1 scores and identifies discrepancies for pattern improvement.

                    entry[header] = val if val != '' else None

            from utils.sheets_api import GoogleSheetsAPI

            study_id = entry.get('study_id')

            if study_id:from typing import Dict, List, Any, Tuple, Optional

                gold[study_id] = {'row': row_idx, 'params': entry}

        

        print(f"Loaded {len(gold)} gold standard entries")

        self.gold_standard = goldclass ValidationEngine:from collections import defaultdict"""logger = logging.getLogger(__name__)

        return gold

        """Validates automated extraction against gold standard annotations."""

    def load_automated_results(self, results_file):

        """Load automated extraction results."""    import re

        print(f"Loading automated results from: {results_file}")

            def __init__(self, sheets_api: GoogleSheetsAPI = None):

        with open(results_file, 'r', encoding='utf-8') as f:

            results = json.load(f)        self.sheets_api = sheets_api or GoogleSheetsAPI()

        

        auto = {}        self.gold_standard = {}

        for result in results:

            if not result['success']:        self.automated_results = {}# Set UTF-8 encoding

                continue

                    

            paper = result['paper_name']

            extraction = result['extraction_result']    def load_gold_standard(self, worksheet_name: str = 'Sheet1'):sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')import json

            experiments = extraction.get('experiments', [extraction])

                    """Load gold standard from Google Sheets."""

            for exp_idx, exp in enumerate(experiments, 1):

                base_id = self._extract_base_id(paper)        print(f"Loading gold standard from: {worksheet_name}")sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

                study_id = f"{base_id}_EXP{exp_idx}" if len(experiments) > 1 else base_id

                        

                params = {}

                for name, data in exp.get('parameters', {}).items():        rows = self.sheets_api.get_all_rows(worksheet_name)import sysclass ExperimentValidator:

                    if isinstance(data, dict):

                        params[name] = data.get('value')        if not rows:

                    else:

                        params[name] = data            print("❌ No data found")# Add parent directory to path

                

                auto[study_id] = {'paper': paper, 'params': params}            return {}

        

        print(f"Loaded {len(auto)} automated results")        sys.path.insert(0, str(Path(__file__).parent.parent))import io    """Validates extracted experiment parameters."""

        self.automated_results = auto

        return auto        headers = rows[0]

    

    def _extract_base_id(self, paper_name):        gold_standard = {}

        """Extract study ID from paper filename."""

        base = paper_name.replace('.pdf', '')        

        match = re.search(r'^([A-Za-z]+).*?(\d{4})', base)

        if match:        for row_idx, row in enumerate(rows[1:], 2):from utils.sheets_api import GoogleSheetsAPIfrom pathlib import Path    

            return f"{match.group(1)}{match.group(2)}"

        return base.split()[0] if base else base            if not row:

    

    def compare_parameters(self, study_id):                continue

        """Compare one study."""

        gold = self.gold_standard.get(study_id)                

        auto = self.automated_results.get(study_id)

                    entry = {}from typing import Dict, List, Any, Tuple, Optional    def __init__(self, db):

        if not gold or not auto:

            return {'error': 'missing'}            for col_idx, header in enumerate(headers):

        

        gold_params = gold['params']                if col_idx < len(row):class ValidationEngine:

        auto_params = auto['params']

                            value = row[col_idx].strip() if row[col_idx] else None

        metadata_cols = {'study_id', 'title', 'authors', 'year', 'notes', 'doi_or_url'}

        all_params = set(gold_params.keys()) | set(auto_params.keys())                    entry[header] = value if value != '' else None    """Validates automated extraction against gold standard annotations."""from collections import defaultdict        """

        param_names = [p for p in all_params if p not in metadata_cols]

                    

        result = {'study_id': study_id, 'tp': [], 'fp': [], 'fn': [], 'vm': []}

                    study_id = entry.get('study_id')    

        for param in param_names:

            g_val = gold_params.get(param)            if not study_id:

            a_val = auto_params.get(param)

                            continue    def __init__(self, sheets_api: GoogleSheetsAPI = None):from datetime import datetime        Initialize validator.

            has_g = g_val is not None and g_val != ''

            has_a = a_val is not None and a_val != ''                

            

            if has_g and has_a:            gold_standard[study_id] = {        """

                if self._match(g_val, a_val):

                    result['tp'].append({'param': param, 'value': g_val})                'row': row_idx,

                else:

                    result['vm'].append({'param': param, 'gold': g_val, 'auto': a_val})                'params': entry        Initialize validation engine.import argparse        

            elif has_g:

                result['fn'].append({'param': param, 'gold': g_val})            }

            elif has_a:

                result['fp'].append({'param': param, 'auto': a_val})                

        

        return result        print(f"✅ Loaded {len(gold_standard)} entries")

    

    def _match(self, gold_val, auto_val):        self.gold_standard = gold_standard        Args:        Args:

        """Check if values match."""

        g = str(gold_val).strip().lower()        return gold_standard

        a = str(auto_val).strip().lower()

                        sheets_api: Google Sheets API instance (optional, will create if not provided)

        if g == a or g in a or a in g:

            return True    def load_automated_results(self, results_file: Path):

        

        try:        """Load automated extraction results."""        """# Set UTF-8 encoding            db: Database instance

            g_nums = re.findall(r'[-+]?\d*\.?\d+', g)

            a_nums = re.findall(r'[-+]?\d*\.?\d+', a)        print(f"Loading automated results from: {results_file}")

            if g_nums and a_nums:

                return abs(float(g_nums[0]) - float(a_nums[0])) < 0.01                self.sheets_api = sheets_api or GoogleSheetsAPI()

        except:

            pass        with open(results_file, 'r', encoding='utf-8') as f:

        

        return False            results = json.load(f)        self.gold_standard = {}sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')        """

    

    def calculate_metrics(self, comp):        

        """Calculate metrics."""

        tp = len(comp['tp'])        automated = {}        self.automated_results = {}

        fp = len(comp['fp'])

        fn = len(comp['fn'])        for result in results:

        vm = len(comp['vm'])

                    if not result['success']:        self.discrepancies = []sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')        self.db = db

        p = tp / (tp + fp + vm) if (tp + fp + vm) > 0 else 0

        r = tp / (tp + fn + vm) if (tp + fn + vm) > 0 else 0                continue

        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0

                                

        return {'precision': p, 'recall': r, 'f1': f1, 'tp': tp, 'fp': fp, 'fn': fn, 'vm': vm}

                paper_name = result['paper_name']

    def validate_all(self):

        """Validate all studies."""            extraction = result['extraction_result']    def load_gold_standard(self, worksheet_name: str = 'Sheet1') -> Dict[str, Any]:    

        print("\n" + "=" * 80)

        print("VALIDATION REPORT")            experiments = extraction.get('experiments', [extraction])

        print("=" * 80)

                            """

        comparisons = []

        per_param = defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0, 'vm': 0})            for exp_idx, exp in enumerate(experiments, 1):

        

        for study_id in self.gold_standard.keys():                base_id = self._extract_base_id(paper_name)        Load gold standard annotations from Google Sheets.# Add parent directory to path    def validate_experiment(self, exp_id: str) -> Dict[str, Any]:

            comp = self.compare_parameters(study_id)

            if 'error' in comp:                study_id = f"{base_id}_EXP{exp_idx}" if len(experiments) > 1 else base_id

                continue

                                    

            comp['metrics'] = self.calculate_metrics(comp)

            comparisons.append(comp)                params = {}

            

            for item in comp['tp']:                for param_name, param_data in exp.get('parameters', {}).items():        Your sheet format:sys.path.insert(0, str(Path(__file__).parent.parent))        """

                per_param[item['param']]['tp'] += 1

            for item in comp['fp']:                    if isinstance(param_data, dict):

                per_param[item['param']]['fp'] += 1

            for item in comp['fn']:                        params[param_name] = param_data.get('value')        study_id | title | authors | year | doi_or_url | ... parameter columns ...

                per_param[item['param']]['fn'] += 1

            for item in comp['vm']:                    else:

                per_param[item['param']]['vm'] += 1

                                params[param_name] = param_data                Validate a single experiment.

        total_tp = sum(c['metrics']['tp'] for c in comparisons)

        total_fp = sum(c['metrics']['fp'] for c in comparisons)                

        total_fn = sum(c['metrics']['fn'] for c in comparisons)

        total_vm = sum(c['metrics']['vm'] for c in comparisons)                automated[study_id] = {        Args:

        

        overall_p = total_tp / (total_tp + total_fp + total_vm) if (total_tp + total_fp + total_vm) > 0 else 0                    'paper': paper_name,

        overall_r = total_tp / (total_tp + total_fn + total_vm) if (total_tp + total_fn + total_vm) > 0 else 0

        overall_f1 = 2 * overall_p * overall_r / (overall_p + overall_r) if (overall_p + overall_r) > 0 else 0                    'params': params            worksheet_name: Name of worksheet containing gold standardfrom utils.sheets_api import GoogleSheetsAPI        

        

        param_metrics = {}                }

        for name, counts in per_param.items():

            tp = counts['tp']                    

            fp = counts['fp']

            fn = counts['fn']        print(f"✅ Loaded {len(automated)} results")

            vm = counts['vm']

                    self.automated_results = automated        Returns:        Args:

            p = tp / (tp + fp + vm) if (tp + fp + vm) > 0 else 0

            r = tp / (tp + fn + vm) if (tp + fn + vm) > 0 else 0        return automated

            f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0

                            Dictionary mapping study_id to ground truth parameters

            param_metrics[name] = {'precision': p, 'recall': r, 'f1': f1, 'tp': tp, 'fp': fp, 'fn': fn, 'vm': vm}

            def _extract_base_id(self, paper_name: str) -> str:

        report = {

            'overall': {'precision': overall_p, 'recall': overall_r, 'f1': overall_f1,        """Extract base ID from paper filename."""        """            exp_id: Experiment ID to validate

                       'tp': total_tp, 'fp': total_fp, 'fn': total_fn, 'vm': total_vm},

            'per_parameter': param_metrics,        base = paper_name.replace('.pdf', '')

            'per_study': comparisons,

            'total_studies': len(comparisons)        match = re.search(r'^([A-Za-z]+).*?(\d{4})', base)        print(f"Loading gold standard from Google Sheets: {worksheet_name}")

        }

                if match:

        self._print_report(report)

        return report            return f"{match.group(1)}{match.group(2)}"        class DiscrepancyType:            

    

    def _print_report(self, report):        return base.split()[0] if base else base

        """Print report."""

        ov = report['overall']            # Get all rows from sheet

        

        print(f"\nOVERALL PERFORMANCE")    def compare_parameters(self, study_id: str) -> Dict[str, Any]:

        print(f"  Studies: {report['total_studies']}")

        print(f"  Precision: {ov['precision']:.3f}")        """Compare automated vs gold for one study."""        rows = self.sheets_api.get_all_rows(worksheet_name)    """Types of discrepancies between automated and gold standard."""        Returns:

        print(f"  Recall: {ov['recall']:.3f}")

        print(f"  F1: {ov['f1']:.3f}")        gold = self.gold_standard.get(study_id)

        print(f"  TP: {ov['tp']}, FP: {ov['fp']}, FN: {ov['fn']}, VM: {ov['vm']}")

                auto = self.automated_results.get(study_id)        

        sorted_params = sorted(report['per_parameter'].items(), key=lambda x: x[1]['f1'], reverse=True)

                

        print(f"\nTOP 10 PARAMETERS")

        for idx, (param, m) in enumerate(sorted_params[:10], 1):        if not gold:        if not rows:    FALSE_POSITIVE = "false_positive"  # Extracted but wrong            Dictionary with validation results

            print(f"  {idx:2}. {param:30} F1: {m['f1']:.3f}")

                    return {'error': 'no_gold'}

        print(f"\nBOTTOM 10 PARAMETERS")

        for idx, (param, m) in enumerate(sorted_params[-10:], 1):        if not auto:            print("❌ No data found in gold standard sheet")

            print(f"  {idx:2}. {param:30} F1: {m['f1']:.3f} (FN:{m['fn']} FP:{m['fp']} VM:{m['vm']})")

                    return {'error': 'no_auto'}

        print("\n" + "=" * 80)

                        return {}    FALSE_NEGATIVE = "false_negative"  # Missing/not extracted        """

    def suggest_improvements(self, report):

        """Generate suggestions."""        gold_params = gold['params']

        suggestions = []

                auto_params = auto['params']        

        for param, metrics in report['per_parameter'].items():

            if metrics['f1'] < 0.8:        

                sugg = {'parameter': param, 'f1': metrics['f1'], 'issues': [], 'recs': []}

                        # Exclude metadata columns        # First row is headers    VALUE_MISMATCH = "value_mismatch"  # Extracted but wrong value        logger.info(f"Validating experiment: {exp_id}")

                if metrics['fn'] > 0:

                    sugg['issues'].append(f"Missing {metrics['fn']} values")        metadata_cols = {'study_id', 'title', 'authors', 'year', 'notes', 'row_number', 'doi_or_url'}

                    sugg['recs'].append("Add extraction patterns")

                        all_params = set(gold_params.keys()) | set(auto_params.keys())        headers = rows[0]

                if metrics['vm'] > 0:

                    sugg['issues'].append(f"{metrics['vm']} mismatches")        param_names = [p for p in all_params if p not in metadata_cols]

                    sugg['recs'].append("Check synonyms")

                                    CONFIDENCE_ISSUE = "confidence_issue"  # Correct but low confidence        

                if metrics['fp'] > 0:

                    sugg['issues'].append(f"{metrics['fp']} false positives")        result = {

                    sugg['recs'].append("Tighten patterns")

                            'study_id': study_id,        # Parse each row into gold standard entry

                suggestions.append(sugg)

                    'tp': [],

        return sorted(suggestions, key=lambda x: x['f1'])

            'fp': [],        gold_standard = {}        session = self.db.get_session()



def main():            'fn': [],

    import argparse

                'vm': []        for row_idx, row in enumerate(rows[1:], 2):  # Skip header, start at row 2

    parser = argparse.ArgumentParser()

    parser.add_argument('--results', default='./batch_processing_results.json')        }

    parser.add_argument('--worksheet', default='Sheet1')

    parser.add_argument('--output')                    if not row or len(row) == 0:        try:

    parser.add_argument('--suggest', action='store_true')

    args = parser.parse_args()        for param in param_names:

    

    v = ValidationEngine()            gold_val = gold_params.get(param)                continue

    v.load_gold_standard(args.worksheet)

                auto_val = auto_params.get(param)

    results_file = Path(args.results)

    if not results_file.exists():                        class ValidationMetrics:            from database.models import Experiment

        print(f"Results not found: {results_file}")

        return 1            has_gold = gold_val is not None and gold_val != ''

    

    v.load_automated_results(results_file)            has_auto = auto_val is not None and auto_val != ''            # Create dict from headers and values

    report = v.validate_all()

                

    if args.suggest:

        print("\n" + "=" * 80)            if has_gold and has_auto:            entry = {}    """Container for validation metrics."""            

        print("IMPROVEMENT SUGGESTIONS")

        print("=" * 80)                if self._values_match(gold_val, auto_val):

        

        suggestions = v.suggest_improvements(report)                    result['tp'].append({'param': param, 'value': gold_val})            for col_idx, header in enumerate(headers):

        for idx, s in enumerate(suggestions[:15], 1):

            print(f"\n{idx}. {s['parameter']} (F1: {s['f1']:.3f})")                else:

            print(f"   Issues: {', '.join(s['issues'])}")

            print(f"   → {', '.join(s['recs'])}")                    result['vm'].append({'param': param, 'gold': gold_val, 'auto': auto_val})                if col_idx < len(row):                exp = session.query(Experiment).filter_by(id=exp_id).first()

    

    if args.output:            elif has_gold and not has_auto:

        with open(args.output, 'w', encoding='utf-8') as f:

            json.dump(report, f, indent=2)                result['fn'].append({'param': param, 'gold': gold_val})                    value = row[col_idx].strip() if row[col_idx] else None

        print(f"\nReport saved: {args.output}")

                elif not has_gold and has_auto:

    return 0

                result['fp'].append({'param': param, 'auto': auto_val})                    # Convert empty strings to None    def __init__(self, parameter_name: str):            if not exp:



if __name__ == '__main__':        

    sys.exit(main())

        return result                    if value == '':

    

    def _values_match(self, gold_value: Any, auto_value: Any) -> bool:                        value = None        self.parameter_name = parameter_name                return {

        """Fuzzy value matching."""

        gold_str = str(gold_value).strip().lower()                    entry[header] = value

        auto_str = str(auto_value).strip().lower()

                            self.true_positives = 0  # Correctly extracted                    'valid': False,

        if gold_str == auto_str:

            return True            # Get study_id (first column)

        

        # Try numeric comparison            study_id = entry.get('study_id')        self.false_positives = 0  # Extracted but wrong                    'errors': [f"Experiment not found: {exp_id}"],

        try:

            gold_nums = re.findall(r'[-+]?\d*\.?\d+', gold_str)            if not study_id:

            auto_nums = re.findall(r'[-+]?\d*\.?\d+', auto_str)

                            print(f"⚠️  Row {row_idx} missing study_id, skipping")        self.false_negatives = 0  # Should exist but not extracted                    'warnings': []

            if gold_nums and auto_nums:

                gold_num = float(gold_nums[0])                continue

                auto_num = float(auto_nums[0])

                if abs(gold_num - auto_num) / max(abs(gold_num), 1e-10) < 0.01:                    self.value_matches = 0  # Extracted with exactly correct value                }

                    return True

        except (ValueError, TypeError):            # Store all parameters for this study

            pass

                    gold_standard[study_id] = {        self.value_mismatches = 0  # Extracted but value is wrong            

        # Substring matching

        if gold_str in auto_str or auto_str in gold_str:                'row_number': row_idx,

            return True

                        'parameters': entry,                    errors = []

        return False

                    'paper_info': {

    def calculate_metrics(self, comparison: Dict[str, Any]) -> Dict[str, float]:

        """Calculate precision, recall, F1."""                    'title': entry.get('title'),        self.discrepancies = []  # List of specific discrepancies            warnings = []

        tp = len(comparison['tp'])

        fp = len(comparison['fp'])                    'authors': entry.get('authors'),

        fn = len(comparison['fn'])

        vm = len(comparison['vm'])                    'year': entry.get('year'),                

        

        precision = tp / (tp + fp + vm) if (tp + fp + vm) > 0 else 0                    'doi_or_url': entry.get('doi_or_url')

        recall = tp / (tp + fn + vm) if (tp + fn + vm) > 0 else 0

        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0                }    @property            # Check required fields

        

        return {            }

            'precision': precision,

            'recall': recall,            def precision(self) -> float:            if not exp.name:

            'f1': f1,

            'tp': tp,        print(f"✅ Loaded {len(gold_standard)} gold standard entries")

            'fp': fp,

            'fn': fn,        self.gold_standard = gold_standard        """Precision = TP / (TP + FP)"""                errors.append("Missing experiment name")

            'vm': vm

        }        return gold_standard

    

    def validate_all(self) -> Dict[str, Any]:            denominator = self.true_positives + self.false_positives            

        """Validate all studies."""

        print("\n" + "=" * 80)    def load_automated_results(self, results_file: Path) -> Dict[str, Any]:

        print("VALIDATION REPORT")

        print("=" * 80)        """        return self.true_positives / denominator if denominator > 0 else 0.0            if not exp.study_type:

        

        all_comparisons = []        Load automated extraction results.

        per_param_metrics = defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0, 'vm': 0})

                                    warnings.append("Study type not specified")

        for study_id in self.gold_standard.keys():

            comp = self.compare_parameters(study_id)        Args:

            if 'error' in comp:

                continue            results_file: Path to batch_processing_results.json    @property            

                

            metrics = self.calculate_metrics(comp)            

            comp['metrics'] = metrics

            all_comparisons.append(comp)        Returns:    def recall(self) -> float:            # Check for conflicts

            

            # Aggregate per-parameter            Dictionary mapping study_id to automated extraction

            for item in comp['tp']:

                per_param_metrics[item['param']]['tp'] += 1        """        """Recall = TP / (TP + FN)"""            if exp.conflict_flag:

            for item in comp['fp']:

                per_param_metrics[item['param']]['fp'] += 1        print(f"Loading automated results from: {results_file}")

            for item in comp['fn']:

                per_param_metrics[item['param']]['fn'] += 1                denominator = self.true_positives + self.false_negatives                warnings.append("Experiment has unresolved conflicts")

            for item in comp['vm']:

                per_param_metrics[item['param']]['vm'] += 1        with open(results_file, 'r', encoding='utf-8') as f:

        

        # Overall metrics            results = json.load(f)        return self.true_positives / denominator if denominator > 0 else 0.0            

        total_tp = sum(c['metrics']['tp'] for c in all_comparisons)

        total_fp = sum(c['metrics']['fp'] for c in all_comparisons)        

        total_fn = sum(c['metrics']['fn'] for c in all_comparisons)

        total_vm = sum(c['metrics']['vm'] for c in all_comparisons)        # Index by study_id (need to match to gold standard)                # TODO: Add more validation rules

        

        overall_precision = total_tp / (total_tp + total_fp + total_vm) if (total_tp + total_fp + total_vm) > 0 else 0        automated = {}

        overall_recall = total_tp / (total_tp + total_fn + total_vm) if (total_tp + total_fn + total_vm) > 0 else 0

        overall_f1 = 2 * (overall_precision * overall_recall) / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0        for result in results:    @property            # - Check value ranges

        

        # Per-parameter metrics            if not result['success']:

        param_metrics = {}

        for param_name, counts in per_param_metrics.items():                continue    def f1_score(self) -> float:            # - Check consistency across hierarchy

            tp = counts['tp']

            fp = counts['fp']            

            fn = counts['fn']

            vm = counts['vm']            paper_name = result['paper_name']        """F1 = 2 * (Precision * Recall) / (Precision + Recall)"""            # - Check for implausible values

            

            precision = tp / (tp + fp + vm) if (tp + fp + vm) > 0 else 0            extraction = result['extraction_result']

            recall = tp / (tp + fn + vm) if (tp + fn + vm) > 0 else 0

            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0                    p_plus_r = self.precision + self.recall            

            

            param_metrics[param_name] = {            # Handle multi-experiment papers

                'precision': precision,

                'recall': recall,            experiments = extraction.get('experiments', [extraction])        return 2 * (self.precision * self.recall) / p_plus_r if p_plus_r > 0 else 0.0            return {

                'f1': f1,

                'tp': tp,            for exp_idx, exp in enumerate(experiments, 1):

                'fp': fp,

                'fn': fn,                # Generate study_id to match gold standard format                    'valid': len(errors) == 0,

                'vm': vm

            }                # Example: "Taylor2014_JNeuro" for single exp

        

        report = {                #          "Butcher2018_EXP1" for multi-exp    @property                'errors': errors,

            'overall': {

                'precision': overall_precision,                

                'recall': overall_recall,

                'f1': overall_f1,                base_id = self._extract_base_id(paper_name)    def value_accuracy(self) -> float:                'warnings': warnings,

                'tp': total_tp,

                'fp': total_fp,                if len(experiments) > 1:

                'fn': total_fn,

                'vm': total_vm                    study_id = f"{base_id}_EXP{exp_idx}"        """Accuracy of extracted values when parameter is found."""                'experiment_id': exp_id

            },

            'per_parameter': param_metrics,                else:

            'per_study': all_comparisons,

            'total_studies': len(all_comparisons)                    study_id = base_id        total = self.value_matches + self.value_mismatches            }

        }

                        

        self._print_report(report)

        return report                # Extract parameters from automated result        return self.value_matches / total if total > 0 else 0.0            

    

    def _print_report(self, report: Dict[str, Any]):                params = exp.get('parameters', {})

        """Print formatted report."""

        overall = report['overall']                automated_params = {}            except Exception as e:

        

        print(f"\n📊 OVERALL PERFORMANCE")                for param_name, param_data in params.items():

        print(f"   Studies: {report['total_studies']}")

        print(f"   Precision: {overall['precision']:.3f}")                    if isinstance(param_data, dict):    def to_dict(self) -> Dict[str, Any]:            logger.error(f"Validation failed: {e}")

        print(f"   Recall: {overall['recall']:.3f}")

        print(f"   F1: {overall['f1']:.3f}")                        automated_params[param_name] = {

        print(f"\n   TP: {overall['tp']}, FP: {overall['fp']}, FN: {overall['fn']}, VM: {overall['vm']}")

                                    'value': param_data.get('value'),        return {            return {

        # Top parameters

        sorted_params = sorted(report['per_parameter'].items(), key=lambda x: x[1]['f1'], reverse=True)                            'confidence': param_data.get('confidence', 0),

        

        print(f"\n🏆 TOP 10 PARAMETERS")                            'method': param_data.get('method'),            'parameter': self.parameter_name,                'valid': False,

        for idx, (param, m) in enumerate(sorted_params[:10], 1):

            print(f"   {idx:2}. {param:30} F1: {m['f1']:.3f}")                            'section': param_data.get('section')

        

        print(f"\n⚠️  BOTTOM 10 PARAMETERS")                        }            'true_positives': self.true_positives,                'errors': [str(e)],

        for idx, (param, m) in enumerate(sorted_params[-10:], 1):

            print(f"   {idx:2}. {param:30} F1: {m['f1']:.3f} (FN: {m['fn']}, FP: {m['fp']}, VM: {m['vm']})")                    else:

        

        print("\n" + "=" * 80)                        automated_params[param_name] = {            'false_positives': self.false_positives,                'warnings': []

    

    def suggest_improvements(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:                            'value': param_data,

        """Generate improvement suggestions."""

        suggestions = []                            'confidence': 1.0,            'false_negatives': self.false_negatives,            }

        

        for param_name, metrics in report['per_parameter'].items():                            'method': 'unknown',

            if metrics['f1'] < 0.8:

                sugg = {                            'section': 'unknown'            'value_matches': self.value_matches,        finally:

                    'parameter': param_name,

                    'f1': metrics['f1'],                        }

                    'issues': [],

                    'recommendations': []                            'value_mismatches': self.value_mismatches,            session.close()

                }

                                automated[study_id] = {

                if metrics['fn'] > 0:

                    sugg['issues'].append(f"Missing {metrics['fn']} values")                    'paper_name': paper_name,            'precision': self.precision,    

                    sugg['recommendations'].append("Add more extraction patterns")

                                    'experiment_number': exp_idx if len(experiments) > 1 else None,

                if metrics['vm'] > 0:

                    sugg['issues'].append(f"{metrics['vm']} value mismatches")                    'parameters': automated_params,            'recall': self.recall,    def validate_all(self) -> Dict[str, Dict[str, Any]]:

                    sugg['recommendations'].append("Review synonym mappings")

                                    'metadata': exp.get('metadata', {})

                if metrics['fp'] > 0:

                    sugg['issues'].append(f"{metrics['fp']} false positives")                }            'f1_score': self.f1_score,        """

                    sugg['recommendations'].append("Tighten pattern matching")

                        

                suggestions.append(sugg)

                print(f"✅ Loaded {len(automated)} automated extraction results")            'value_accuracy': self.value_accuracy,        Validate all experiments in database.

        suggestions.sort(key=lambda x: x['f1'])

        return suggestions        self.automated_results = automated



        return automated            'discrepancy_count': len(self.discrepancies)        

def main():

    """Main validation workflow."""    

    import argparse

        def _extract_base_id(self, paper_name: str) -> str:        }        Returns:

    parser = argparse.ArgumentParser(description='Validate automated extraction')

    parser.add_argument('--results', default='./batch_processing_results.json')        """Extract base ID from paper filename to match gold standard study_id."""

    parser.add_argument('--worksheet', default='Sheet1')

    parser.add_argument('--output', help='Save report to JSON')        # Remove .pdf extension            Dictionary mapping experiment IDs to validation results

    parser.add_argument('--suggest', action='store_true', help='Generate suggestions')

            base = paper_name.replace('.pdf', '')

    args = parser.parse_args()

                    """

    validator = ValidationEngine()

    validator.load_gold_standard(args.worksheet)        # Try to extract First Author + Year

    

    results_file = Path(args.results)        # Examples:class GoldStandardLoader:        session = self.db.get_session()

    if not results_file.exists():

        print(f"❌ Results file not found: {results_file}")        #   "Bond and Taylor - 2017 - Title.pdf" -> "Bond2017"

        return 1

            #   "Taylor, Krakauer & Ivry - 2014.pdf" -> "Taylor2014"    """Loads gold standard annotations from Google Sheets."""        try:

    validator.load_automated_results(results_file)

    report = validator.validate_all()        

    

    if args.suggest:        match = re.search(r'^([A-Za-z]+).*?(\d{4})', base)                from database.models import Experiment

        print("\n" + "=" * 80)

        print("IMPROVEMENT SUGGESTIONS")        if match:

        print("=" * 80)

                    author = match.group(1)    def __init__(self, sheets_api: GoogleSheetsAPI):            

        suggestions = validator.suggest_improvements(report)

        for idx, sugg in enumerate(suggestions[:15], 1):            year = match.group(2)

            print(f"\n{idx}. {sugg['parameter']} (F1: {sugg['f1']:.3f})")

            print(f"   Issues: {', '.join(sugg['issues'])}")            return f"{author}{year}"        self.sheets_api = sheets_api            experiments = session.query(Experiment).all()

            print(f"   → {', '.join(sugg['recommendations'])}")

            

    if args.output:

        with open(args.output, 'w', encoding='utf-8') as f:        # Fallback: use first word                results = {}

            json.dump(report, f, indent=2)

        print(f"\n💾 Report saved: {args.output}")        return base.split()[0] if base else base

    

    return 0        def load_annotations(self, sheet_name: str = "Gold_Standard_Annotations") -> Dict[str, Dict]:            



    def compare_parameters(self, study_id: str) -> Dict[str, Any]:

if __name__ == '__main__':

    sys.exit(main())        """        """            for exp in experiments:


        Compare automated extraction to gold standard for a single study.

                Load gold standard annotations from Google Sheets.                results[exp.id] = self.validate_experiment(exp.id)

        Args:

            study_id: Study identifier                    

            

        Returns:        Returns:            return results

            Dictionary with comparison results and discrepancies

        """            Dictionary mapping (paper_name, exp_num, param_name) to ground truth data            

        gold = self.gold_standard.get(study_id)

        auto = self.automated_results.get(study_id)        """        finally:

        

        if not gold:        print(f"\n📥 Loading gold standard from sheet: {sheet_name}")            session.close()

            return {'error': 'no_gold_standard', 'study_id': study_id}

                

        if not auto:        # Load the sheet

            return {'error': 'no_automated_result', 'study_id': study_id}        rows = self.sheets_api.read_sheet(sheet_name)

                

        gold_params = gold['parameters']        if not rows or len(rows) < 2:

        auto_params = auto['parameters']            print("❌ No data in gold standard sheet")

                    return {}

        # Get all parameter names from both        

        all_param_names = set(gold_params.keys()) | set(auto_params.keys())        headers = rows[0]

                data_rows = rows[1:]

        # Exclude metadata columns (not parameters)        

        metadata_cols = {'study_id', 'title', 'authors', 'year', 'notes', 'row_number'}        # Create column index map

        param_names = [p for p in all_param_names if p not in metadata_cols]        col_map = {header.strip().lower(): idx for idx, header in enumerate(headers)}

                

        comparison = {        # Parse rows into structured format

            'study_id': study_id,        annotations = {}

            'true_positives': [],        for row in data_rows:

            'false_positives': [],            if not row or len(row) == 0:

            'false_negatives': [],                continue

            'value_mismatches': [],            

            'correct_count': 0,            # Extract fields

            'total_gold_params': 0,            paper_name = row[col_map['paper_name']].strip() if 'paper_name' in col_map and len(row) > col_map['paper_name'] else ''

            'total_auto_params': 0            exp_num_str = row[col_map['experiment_number']].strip() if 'experiment_number' in col_map and len(row) > col_map['experiment_number'] else ''

        }            param_name = row[col_map['parameter_name']].strip() if 'parameter_name' in col_map and len(row) > col_map['parameter_name'] else ''

                    ground_truth = row[col_map['ground_truth_value']].strip() if 'ground_truth_value' in col_map and len(row) > col_map['ground_truth_value'] else ''

        for param_name in param_names:            

            gold_value = gold_params.get(param_name)            if not paper_name or not param_name:

            auto_data = auto_params.get(param_name, {})                continue

            auto_value = auto_data.get('value') if isinstance(auto_data, dict) else auto_data            

                        # Parse experiment number

            # Count gold standard parameters (excluding None/empty)            exp_num = int(exp_num_str) if exp_num_str and exp_num_str.isdigit() else None

            if gold_value is not None and gold_value != '':            

                comparison['total_gold_params'] += 1            # Create key

                        key = (paper_name, exp_num, param_name)

            # Count automated parameters            

            if auto_value is not None and auto_value != '':            # Parse ground truth value

                comparison['total_auto_params'] += 1            value_type = row[col_map['value_type']].strip() if 'value_type' in col_map and len(row) > col_map['value_type'] else 'text'

                        

            # Compare values            if value_type == 'numeric':

            if gold_value is None or gold_value == '':                try:

                # Parameter not in gold standard                    ground_truth_value = float(ground_truth)

                if auto_value is not None and auto_value != '':                except ValueError:

                    # False positive: extracted but not in gold standard                    ground_truth_value = ground_truth

                    comparison['false_positives'].append({            elif value_type == 'boolean':

                        'parameter': param_name,                ground_truth_value = ground_truth.lower() in ('true', 'yes', '1', 'y')

                        'automated_value': auto_value,            elif value_type == 'null':

                        'confidence': auto_data.get('confidence', 0) if isinstance(auto_data, dict) else 1.0,                ground_truth_value = None

                        'section': auto_data.get('section', 'unknown') if isinstance(auto_data, dict) else 'unknown'            else:

                    })                ground_truth_value = ground_truth

            else:            

                # Parameter in gold standard            # Store annotation

                if auto_value is None or auto_value == '':            annotations[key] = {

                    # False negative: missed in extraction                'value': ground_truth_value,

                    comparison['false_negatives'].append({                'confidence': row[col_map['confidence']].strip() if 'confidence' in col_map and len(row) > col_map['confidence'] else 'unknown',

                        'parameter': param_name,                'evidence_section': row[col_map['evidence_section']].strip() if 'evidence_section' in col_map and len(row) > col_map['evidence_section'] else '',

                        'gold_standard_value': gold_value                'evidence_quote': row[col_map['evidence_quote']].strip() if 'evidence_quote' in col_map and len(row) > col_map['evidence_quote'] else '',

                    })                'evidence_page': row[col_map['evidence_page']].strip() if 'evidence_page' in col_map and len(row) > col_map['evidence_page'] else '',

                else:                'annotator': row[col_map['annotator']].strip() if 'annotator' in col_map and len(row) > col_map['annotator'] else '',

                    # Both have values - check if they match                'notes': row[col_map['notes']].strip() if 'notes' in col_map and len(row) > col_map['notes'] else '',

                    if self._values_match(gold_value, auto_value):                'review_status': row[col_map['review_status']].strip() if 'review_status' in col_map and len(row) > col_map['review_status'] else 'draft'

                        # True positive: correctly extracted            }

                        comparison['true_positives'].append({        

                            'parameter': param_name,        print(f"✅ Loaded {len(annotations)} gold standard annotations")

                            'value': gold_value,        

                            'confidence': auto_data.get('confidence', 0) if isinstance(auto_data, dict) else 1.0        # Group by paper

                        })        papers = set(key[0] for key in annotations.keys())

                        comparison['correct_count'] += 1        print(f"   Papers annotated: {len(papers)}")

                    else:        

                        # Value mismatch: extracted but wrong value        # Count by review status

                        comparison['value_mismatches'].append({        status_counts = defaultdict(int)

                            'parameter': param_name,        for ann in annotations.values():

                            'gold_standard_value': gold_value,            status_counts[ann['review_status']] += 1

                            'automated_value': auto_value,        

                            'confidence': auto_data.get('confidence', 0) if isinstance(auto_data, dict) else 1.0,        print(f"   Review status: {dict(status_counts)}")

                            'section': auto_data.get('section', 'unknown') if isinstance(auto_data, dict) else 'unknown'        

                        })        return annotations

            

        return comparison    def load_missing_parameters(self, sheet_name: str = "Missing_Parameters") -> Dict[Tuple[str, Optional[int]], List[str]]:

            """

    def _values_match(self, gold_value: Any, auto_value: Any) -> bool:        Load parameters confirmed as missing from papers.

        """        

        Check if two values match (with fuzzy matching for numbers and strings).        Returns:

                    Dictionary mapping (paper_name, exp_num) to list of missing parameter names

        Args:        """

            gold_value: Gold standard value        print(f"\n📥 Loading missing parameters from sheet: {sheet_name}")

            auto_value: Automated extraction value        

                    try:

        Returns:            rows = self.sheets_api.read_sheet(sheet_name)

            True if values match        except Exception as e:

        """            print(f"⚠️  Could not load {sheet_name}: {e}")

        # Convert to strings for comparison            return {}

        gold_str = str(gold_value).strip().lower()        

        auto_str = str(auto_value).strip().lower()        if not rows or len(rows) < 2:

                    print("   No missing parameters documented")

        # Exact match            return {}

        if gold_str == auto_str:        

            return True        headers = rows[0]

                data_rows = rows[1:]

        # Try numeric comparison        

        try:        col_map = {header.strip().lower(): idx for idx, header in enumerate(headers)}

            # Extract numbers from strings (e.g., "45°" -> 45, "45 CCW" -> 45)        

            gold_nums = re.findall(r'[-+]?\d*\.?\d+', gold_str)        missing = defaultdict(list)

            auto_nums = re.findall(r'[-+]?\d*\.?\d+', auto_str)        for row in data_rows:

                        if not row or len(row) == 0:

            if gold_nums and auto_nums:                continue

                gold_num = float(gold_nums[0])            

                auto_num = float(auto_nums[0])            paper_name = row[col_map['paper_name']].strip() if 'paper_name' in col_map and len(row) > col_map['paper_name'] else ''

                # Allow 1% tolerance for floating point            exp_num_str = row[col_map['experiment_number']].strip() if 'experiment_number' in col_map and len(row) > col_map['experiment_number'] else ''

                if abs(gold_num - auto_num) / max(abs(gold_num), 1e-10) < 0.01:            param_name = row[col_map['parameter_name']].strip() if 'parameter_name' in col_map and len(row) > col_map['parameter_name'] else ''

                    return True            confirmed = row[col_map.get('confirmed_missing', 999)].strip().lower() if 'confirmed_missing' in col_map and len(row) > col_map.get('confirmed_missing', 999) else ''

        except (ValueError, TypeError):            

            pass            if not paper_name or not param_name:

                        continue

        # Fuzzy string matching (contains)            

        if gold_str in auto_str or auto_str in gold_str:            # Only include if confirmed

            return True            if confirmed not in ('true', 'yes', '1', '✓', 'checked'):

                        continue

        # Common equivalences            

        equivalences = [            exp_num = int(exp_num_str) if exp_num_str and exp_num_str.isdigit() else None

            ('visuomotor_rotation', 'visual'),            key = (paper_name, exp_num)

            ('visuomotor rotation', 'visual'),            

            ('endpoint_only', 'endpoint'),            missing[key].append(param_name)

            ('healthy_adult', 'young adults'),        

            ('healthy_adult', 'healthy adults'),        print(f"✅ Loaded {sum(len(v) for v in missing.values())} confirmed missing parameters")

            ('tablet/mouse', 'tablet'),        

            ('tablet/mouse', 'virtual'),        return missing

        ]

        

        for eq1, eq2 in equivalences:class ValidationEngine:

            if (gold_str == eq1 and auto_str == eq2) or (gold_str == eq2 and auto_str == eq1):    """Compares automated extraction to gold standard."""

                return True    

            def __init__(self, gold_standard: Dict, missing_params: Dict = None):

        return False        self.gold_standard = gold_standard

            self.missing_params = missing_params or {}

    def calculate_metrics(self, comparison: Dict[str, Any]) -> Dict[str, float]:        self.metrics_by_parameter = {}

        """    

        Calculate precision, recall, and F1 score.    def compare_value(self, automated_value: Any, ground_truth_value: Any, tolerance: float = 0.01) -> bool:

                """

        Args:        Compare automated value to ground truth with appropriate tolerance.

            comparison: Comparison results from compare_parameters        

                    Args:

        Returns:            automated_value: Value from automated extraction

            Dictionary with precision, recall, F1            ground_truth_value: Ground truth value

        """            tolerance: Numeric tolerance for float comparison

        tp = len(comparison['true_positives'])        """

        fp = len(comparison['false_positives'])        # Handle None/null

        fn = len(comparison['false_negatives'])        if ground_truth_value is None:

        vm = len(comparison['value_mismatches'])            return automated_value is None or automated_value == ''

                

        # Precision: TP / (TP + FP + VM)        # Handle numeric comparison

        precision = tp / (tp + fp + vm) if (tp + fp + vm) > 0 else 0        if isinstance(ground_truth_value, (int, float)):

                    try:

        # Recall: TP / (TP + FN + VM)                auto_num = float(automated_value)

        recall = tp / (tp + fn + vm) if (tp + fn + vm) > 0 else 0                return abs(auto_num - ground_truth_value) <= tolerance

                    except (ValueError, TypeError):

        # F1: Harmonic mean of precision and recall                return False

        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0        

                # Handle boolean

        # Accuracy: TP / (TP + FP + FN + VM)        if isinstance(ground_truth_value, bool):

        accuracy = tp / (tp + fp + fn + vm) if (tp + fp + fn + vm) > 0 else 0            auto_bool = str(automated_value).lower() in ('true', 'yes', '1', 'y')

                    return auto_bool == ground_truth_value

        return {        

            'precision': precision,        # Handle text (case-insensitive, strip whitespace)

            'recall': recall,        return str(automated_value).strip().lower() == str(ground_truth_value).strip().lower()

            'f1': f1,    

            'accuracy': accuracy,    def validate_experiment(self, paper_name: str, exp_number: Optional[int], 

            'true_positives': tp,                          automated_params: Dict[str, Any]) -> Dict[str, ValidationMetrics]:

            'false_positives': fp,        """

            'false_negatives': fn,        Validate automated extraction for one experiment against gold standard.

            'value_mismatches': vm        

        }        Args:

                paper_name: Name of the paper

    def validate_all(self) -> Dict[str, Any]:            exp_number: Experiment number or None

        """            automated_params: Parameters extracted by automated system

        Validate all studies in gold standard.            

                Returns:

        Returns:            Dictionary of ValidationMetrics by parameter name

            Comprehensive validation report        """

        """        metrics_map = {}

        print("\n" + "=" * 80)        

        print("VALIDATION REPORT: Automated Extraction vs Gold Standard")        # Get gold standard for this experiment

        print("=" * 80)        gold_for_exp = {k[2]: v for k, v in self.gold_standard.items() 

                               if k[0] == paper_name and k[1] == exp_number}

        all_comparisons = []        

        per_parameter_metrics = defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0, 'vm': 0})        # Get confirmed missing parameters

                missing_key = (paper_name, exp_number)

        # Compare each study        confirmed_missing = set(self.missing_params.get(missing_key, []))

        for study_id in self.gold_standard.keys():        

            comparison = self.compare_parameters(study_id)        # All possible parameters (union of gold standard and automated)

                    all_params = set(gold_for_exp.keys()) | set(automated_params.keys())

            if 'error' in comparison:        

                print(f"  ⚠️  {study_id}: {comparison['error']}")        for param_name in all_params:

                continue            if param_name not in metrics_map:

                            metrics_map[param_name] = ValidationMetrics(param_name)

            metrics = self.calculate_metrics(comparison)            

            comparison['metrics'] = metrics            metrics = metrics_map[param_name]

            all_comparisons.append(comparison)            

                        in_gold = param_name in gold_for_exp

            # Aggregate per-parameter metrics            in_automated = param_name in automated_params

            for tp in comparison['true_positives']:            is_confirmed_missing = param_name in confirmed_missing

                per_parameter_metrics[tp['parameter']]['tp'] += 1            

                        # Case 1: In gold standard and in automated extraction

            for fp in comparison['false_positives']:            if in_gold and in_automated:

                per_parameter_metrics[fp['parameter']]['fp'] += 1                gold_value = gold_for_exp[param_name]['value']

                            auto_data = automated_params[param_name]

            for fn in comparison['false_negatives']:                auto_value = auto_data.get('value') if isinstance(auto_data, dict) else auto_data

                per_parameter_metrics[fn['parameter']]['fn'] += 1                auto_confidence = auto_data.get('confidence', 0) if isinstance(auto_data, dict) else 1.0

                            

            for vm in comparison['value_mismatches']:                values_match = self.compare_value(auto_value, gold_value)

                per_parameter_metrics[vm['parameter']]['vm'] += 1                

                        if values_match:

        # Calculate overall metrics                    metrics.true_positives += 1

        total_tp = sum(c['metrics']['true_positives'] for c in all_comparisons)                    metrics.value_matches += 1

        total_fp = sum(c['metrics']['false_positives'] for c in all_comparisons)                else:

        total_fn = sum(c['metrics']['false_negatives'] for c in all_comparisons)                    metrics.true_positives += 1  # Found the parameter

        total_vm = sum(c['metrics']['value_mismatches'] for c in all_comparisons)                    metrics.value_mismatches += 1

                            

        overall_precision = total_tp / (total_tp + total_fp + total_vm) if (total_tp + total_fp + total_vm) > 0 else 0                    # Record discrepancy

        overall_recall = total_tp / (total_tp + total_fn + total_vm) if (total_tp + total_fn + total_vm) > 0 else 0                    metrics.discrepancies.append({

        overall_f1 = 2 * (overall_precision * overall_recall) / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0                        'type': DiscrepancyType.VALUE_MISMATCH,

        overall_accuracy = total_tp / (total_tp + total_fp + total_fn + total_vm) if (total_tp + total_fp + total_fn + total_vm) > 0 else 0                        'paper': paper_name,

                                'experiment': exp_number,

        # Calculate per-parameter metrics                        'parameter': param_name,

        param_metrics = {}                        'automated_value': auto_value,

        for param_name, counts in per_parameter_metrics.items():                        'ground_truth_value': gold_value,

            tp = counts['tp']                        'automated_confidence': auto_confidence,

            fp = counts['fp']                        'gold_confidence': gold_for_exp[param_name]['confidence'],

            fn = counts['fn']                        'evidence': gold_for_exp[param_name]['evidence_quote']

            vm = counts['vm']                    })

                        

            precision = tp / (tp + fp + vm) if (tp + fp + vm) > 0 else 0            # Case 2: In gold standard but NOT in automated (False Negative)

            recall = tp / (tp + fn + vm) if (tp + fn + vm) > 0 else 0            elif in_gold and not in_automated and not is_confirmed_missing:

            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0                metrics.false_negatives += 1

                            

            param_metrics[param_name] = {                metrics.discrepancies.append({

                'precision': precision,                    'type': DiscrepancyType.FALSE_NEGATIVE,

                'recall': recall,                    'paper': paper_name,

                'f1': f1,                    'experiment': exp_number,

                'true_positives': tp,                    'parameter': param_name,

                'false_positives': fp,                    'ground_truth_value': gold_for_exp[param_name]['value'],

                'false_negatives': fn,                    'gold_confidence': gold_for_exp[param_name]['confidence'],

                'value_mismatches': vm,                    'evidence': gold_for_exp[param_name]['evidence_quote'],

                'total': tp + fp + fn + vm                    'evidence_section': gold_for_exp[param_name]['evidence_section']

            }                })

                    

        report = {            # Case 3: In automated but NOT in gold standard (False Positive)

            'overall_metrics': {            elif not in_gold and in_automated and not is_confirmed_missing:

                'precision': overall_precision,                metrics.false_positives += 1

                'recall': overall_recall,                

                'f1': overall_f1,                auto_data = automated_params[param_name]

                'accuracy': overall_accuracy,                auto_value = auto_data.get('value') if isinstance(auto_data, dict) else auto_data

                'true_positives': total_tp,                

                'false_positives': total_fp,                metrics.discrepancies.append({

                'false_negatives': total_fn,                    'type': DiscrepancyType.FALSE_POSITIVE,

                'value_mismatches': total_vm                    'paper': paper_name,

            },                    'experiment': exp_number,

            'per_parameter_metrics': param_metrics,                    'parameter': param_name,

            'per_study_comparisons': all_comparisons,                    'automated_value': auto_value,

            'total_studies': len(all_comparisons)                    'reason': 'Parameter extracted but not in gold standard (may be incorrect extraction or missing annotation)'

        }                })

                    

        self._print_validation_report(report)            # Case 4: Confirmed missing - automated correctly did not extract

                    # (True Negative - not counted in metrics)

        return report        

            return metrics_map

    def _print_validation_report(self, report: Dict[str, Any]):    

        """Print formatted validation report."""    def aggregate_metrics(self, all_metrics: List[Dict[str, ValidationMetrics]]) -> Dict[str, ValidationMetrics]:

                """Aggregate metrics across all experiments."""

        overall = report['overall_metrics']        aggregated = {}

                

        print(f"\n📊 OVERALL PERFORMANCE")        for exp_metrics in all_metrics:

        print(f"   Studies Validated: {report['total_studies']}")            for param_name, metrics in exp_metrics.items():

        print(f"   Precision: {overall['precision']:.3f}")                if param_name not in aggregated:

        print(f"   Recall: {overall['recall']:.3f}")                    aggregated[param_name] = ValidationMetrics(param_name)

        print(f"   F1 Score: {overall['f1']:.3f}")                

        print(f"   Accuracy: {overall['accuracy']:.3f}")                agg = aggregated[param_name]

        print(f"\n   True Positives: {overall['true_positives']}")                agg.true_positives += metrics.true_positives

        print(f"   False Positives: {overall['false_positives']}")                agg.false_positives += metrics.false_positives

        print(f"   False Negatives: {overall['false_negatives']}")                agg.false_negatives += metrics.false_negatives

        print(f"   Value Mismatches: {overall['value_mismatches']}")                agg.value_matches += metrics.value_matches

                        agg.value_mismatches += metrics.value_mismatches

        # Top performing parameters                agg.discrepancies.extend(metrics.discrepancies)

        param_metrics = report['per_parameter_metrics']        

        sorted_params = sorted(param_metrics.items(), key=lambda x: x[1]['f1'], reverse=True)        return aggregated

        

        print(f"\n🏆 TOP 10 PARAMETERS (by F1)")

        for idx, (param_name, metrics) in enumerate(sorted_params[:10], 1):def load_automated_results(results_file: Path) -> List[Dict]:

            print(f"   {idx:2}. {param_name:30} F1: {metrics['f1']:.3f} (P: {metrics['precision']:.3f}, R: {metrics['recall']:.3f})")    """Load automated extraction results."""

            with open(results_file, 'r', encoding='utf-8') as f:

        # Worst performing parameters        return json.load(f)

        print(f"\n⚠️  BOTTOM 10 PARAMETERS (need improvement)")

        for idx, (param_name, metrics) in enumerate(sorted_params[-10:], 1):

            print(f"   {idx:2}. {param_name:30} F1: {metrics['f1']:.3f} (FP: {metrics['false_positives']}, FN: {metrics['false_negatives']}, VM: {metrics['value_mismatches']})")def print_validation_report(metrics: Dict[str, ValidationMetrics], detailed: bool = False):

            """Print formatted validation report."""

        print("\n" + "=" * 80)    

        print("\n" + "=" * 80)

    def suggest_improvements(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:    print("VALIDATION REPORT: Automated vs Gold Standard")

        """    print("=" * 80)

        Analyze discrepancies and suggest pattern improvements.    

            # Overall statistics

        Args:    total_tp = sum(m.true_positives for m in metrics.values())

            report: Validation report from validate_all()    total_fp = sum(m.false_positives for m in metrics.values())

                total_fn = sum(m.false_negatives for m in metrics.values())

        Returns:    

            List of improvement suggestions    overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0

        """    overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0

        suggestions = []    overall_f1 = 2 * (overall_precision * overall_recall) / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0

            

        param_metrics = report['per_parameter_metrics']    print(f"\n📊 OVERALL METRICS")

        comparisons = report['per_study_comparisons']    print(f"   Precision: {overall_precision:.3f}")

            print(f"   Recall:    {overall_recall:.3f}")

        for param_name, metrics in param_metrics.items():    print(f"   F1 Score:  {overall_f1:.3f}")

            if metrics['f1'] < 0.8:  # Parameters below 80% F1 need improvement    print(f"\n   True Positives:  {total_tp}")

                suggestion = {    print(f"   False Positives: {total_fp}")

                    'parameter': param_name,    print(f"   False Negatives: {total_fn}")

                    'current_f1': metrics['f1'],    

                    'precision': metrics['precision'],    # Per-parameter metrics

                    'recall': metrics['recall'],    print(f"\n📋 PER-PARAMETER METRICS (sorted by F1 score)")

                    'issues': [],    print(f"   {'Parameter':<35} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Val Acc':>10}")

                    'recommendations': []    print(f"   {'-'*35} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")

                }    

                    sorted_metrics = sorted(metrics.values(), key=lambda m: m.f1_score, reverse=True)

                # Analyze false negatives (missed extractions)    

                if metrics['false_negatives'] > 0:    for m in sorted_metrics:

                    # Collect examples        print(f"   {m.parameter_name:<35} {m.precision:>10.3f} {m.recall:>10.3f} {m.f1_score:>10.3f} {m.value_accuracy:>10.3f}")

                    fn_examples = []    

                    for comp in comparisons:    # Parameters with issues

                        for fn in comp['false_negatives']:    print(f"\n⚠️  PARAMETERS NEEDING ATTENTION")

                            if fn['parameter'] == param_name:    

                                fn_examples.append(fn['gold_standard_value'])    low_recall = [m for m in sorted_metrics if m.recall < 0.7 and m.false_negatives > 0]

                        if low_recall:

                    suggestion['issues'].append(f"Missing {metrics['false_negatives']} values")        print(f"\n   Low Recall (missing parameters):")

                    suggestion['recommendations'].append(f"Add patterns for: {', '.join(map(str, fn_examples[:3]))}")        for m in low_recall[:10]:

                            print(f"      {m.parameter_name:<35} Recall: {m.recall:.3f}, FN: {m.false_negatives}")

                # Analyze value mismatches (wrong values)    

                if metrics['value_mismatches'] > 0:    low_precision = [m for m in sorted_metrics if m.precision < 0.7 and m.false_positives > 0]

                    vm_examples = []    if low_precision:

                    for comp in comparisons:        print(f"\n   Low Precision (incorrect extractions):")

                        for vm in comp['value_mismatches']:        for m in low_precision[:10]:

                            if vm['parameter'] == param_name:            print(f"      {m.parameter_name:<35} Precision: {m.precision:.3f}, FP: {m.false_positives}")

                                vm_examples.append({    

                                    'expected': vm['gold_standard_value'],    low_value_acc = [m for m in sorted_metrics if m.value_accuracy < 0.7 and m.value_mismatches > 0]

                                    'got': vm['automated_value']    if low_value_acc:

                                })        print(f"\n   Low Value Accuracy (wrong values):")

                            for m in low_value_acc[:10]:

                    suggestion['issues'].append(f"{metrics['value_mismatches']} value mismatches")            print(f"      {m.parameter_name:<35} Accuracy: {m.value_accuracy:.3f}, Mismatches: {m.value_mismatches}")

                    suggestion['recommendations'].append(f"Review pattern matching for: {vm_examples[0] if vm_examples else 'N/A'}")    

                    # Detailed discrepancy report

                # Analyze false positives (extra extractions)    if detailed:

                if metrics['false_positives'] > 0:        print(f"\n🔍 DETAILED DISCREPANCY REPORT")

                    suggestion['issues'].append(f"{metrics['false_positives']} false positives")        

                    suggestion['recommendations'].append("Tighten pattern matching or add exclusion rules")        for param_name, metric in sorted(metrics.items()):

                            if len(metric.discrepancies) > 0:

                suggestions.append(suggestion)                print(f"\n   Parameter: {param_name} ({len(metric.discrepancies)} discrepancies)")

                        

        # Sort by F1 (worst first)                for disc in metric.discrepancies[:5]:  # Show first 5

        suggestions.sort(key=lambda x: x['current_f1'])                    print(f"      Type: {disc['type']}")

                            print(f"      Paper: {disc['paper']}, Exp: {disc.get('experiment', 'N/A')}")

        return suggestions                    

                    if disc['type'] == DiscrepancyType.VALUE_MISMATCH:

                        print(f"      Automated: {disc['automated_value']}")

def main():                        print(f"      Gold:      {disc['ground_truth_value']}")

    """Main validation workflow."""                        print(f"      Evidence:  \"{disc['evidence'][:80]}...\"")

    import argparse                    elif disc['type'] == DiscrepancyType.FALSE_NEGATIVE:

                            print(f"      Missing value: {disc['ground_truth_value']}")

    parser = argparse.ArgumentParser(description='Validate automated extraction against gold standard')                        print(f"      Section: {disc.get('evidence_section', 'unknown')}")

    parser.add_argument('--results', type=str, default='./batch_processing_results.json',                        print(f"      Evidence: \"{disc['evidence'][:80]}...\"")

                       help='Path to automated extraction results')                    elif disc['type'] == DiscrepancyType.FALSE_POSITIVE:

    parser.add_argument('--worksheet', type=str, default='Sheet1',                        print(f"      Extracted: {disc['automated_value']}")

                       help='Google Sheets worksheet name containing gold standard')                        print(f"      Reason: {disc.get('reason', 'Unknown')}")

    parser.add_argument('--output', type=str,                    

                       help='Save validation report to JSON file')                    print()

    parser.add_argument('--suggest', action='store_true',

                       help='Generate pattern improvement suggestions')

    def main():

    args = parser.parse_args()    parser = argparse.ArgumentParser(description='Validate automated extraction against gold standard')

        parser.add_argument('--results', type=str, default='./batch_processing_results.json',

    # Initialize validation engine                       help='Path to automated extraction results')

    validator = ValidationEngine()    parser.add_argument('--gold-sheet', type=str, default='Gold_Standard_Annotations',

                           help='Name of gold standard sheet')

    # Load gold standard from Google Sheets    parser.add_argument('--missing-sheet', type=str, default='Missing_Parameters',

    validator.load_gold_standard(args.worksheet)                       help='Name of missing parameters sheet')

        parser.add_argument('--detailed', action='store_true',

    # Load automated results                       help='Show detailed discrepancy report')

    results_file = Path(args.results)    parser.add_argument('--output', type=str,

    if not results_file.exists():                       help='Save validation report to JSON file')

        print(f"❌ Results file not found: {results_file}")    

        return 1    args = parser.parse_args()

        

    validator.load_automated_results(results_file)    # Load automated results

        results_file = Path(args.results)

    # Validate    if not results_file.exists():

    report = validator.validate_all()        print(f"❌ Results file not found: {results_file}")

            return 1

    # Generate improvement suggestions    

    if args.suggest:    print(f"Loading automated results from: {results_file}")

        print("\n" + "=" * 80)    automated_results = load_automated_results(results_file)

        print("PATTERN IMPROVEMENT SUGGESTIONS")    

        print("=" * 80)    # Load gold standard from Google Sheets

            sheets_api = GoogleSheetsAPI()

        suggestions = validator.suggest_improvements(report)    gold_loader = GoldStandardLoader(sheets_api)

            

        for idx, sugg in enumerate(suggestions[:15], 1):    gold_standard = gold_loader.load_annotations(args.gold_sheet)

            print(f"\n{idx}. {sugg['parameter']}")    missing_params = gold_loader.load_missing_parameters(args.missing_sheet)

            print(f"   Current F1: {sugg['current_f1']:.3f} (P: {sugg['precision']:.3f}, R: {sugg['recall']:.3f})")    

            print(f"   Issues:")    if not gold_standard:

            for issue in sugg['issues']:        print("❌ No gold standard data loaded. Please annotate papers first.")

                print(f"     - {issue}")        return 1

            print(f"   Recommendations:")    

            for rec in sugg['recommendations']:    # Run validation

                print(f"     → {rec}")    print("\n🔬 Running validation...")

        validator = ValidationEngine(gold_standard, missing_params)

    # Save report    

    if args.output:    all_exp_metrics = []

        with open(args.output, 'w', encoding='utf-8') as f:    

            json.dump(report, f, indent=2)    for result in automated_results:

        print(f"\n💾 Validation report saved to: {args.output}")        if not result['success']:

                continue

    return 0        

        paper_name = result['paper_name']

        extraction = result['extraction_result']

if __name__ == '__main__':        experiments = extraction.get('experiments', [extraction])

    sys.exit(main())        

        for exp_idx, exp in enumerate(experiments, 1):
            exp_num = exp_idx if len(experiments) > 1 else None
            params = exp.get('parameters', {})
            
            exp_metrics = validator.validate_experiment(paper_name, exp_num, params)
            all_exp_metrics.append(exp_metrics)
    
    # Aggregate metrics
    aggregated_metrics = validator.aggregate_metrics(all_exp_metrics)
    
    # Print report
    print_validation_report(aggregated_metrics, args.detailed)
    
    # Save output
    if args.output:
        output_data = {
            'validation_date': datetime.now().isoformat(),
            'automated_results_file': str(results_file),
            'gold_standard_sheet': args.gold_sheet,
            'metrics_by_parameter': {name: m.to_dict() for name, m in aggregated_metrics.items()},
            'discrepancies': {
                name: m.discrepancies for name, m in aggregated_metrics.items() if m.discrepancies
            }
        }
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n💾 Validation report saved to: {args.output}")
    
    print("\n" + "=" * 80)
    print("Validation complete!")
    print("=" * 80 + "\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
