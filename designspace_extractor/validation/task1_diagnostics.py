#!/usr/bin/env python3
"""
Task 1 Diagnostics Tool
Analyzes false negatives where Task 1 (LLM finding missed library parameters) failed to recover
parameters that regex extraction missed but are in the gold standard.
"""

import json
import csv
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple


class Task1Diagnostics:
    """Diagnostic tool for analyzing Task 1 performance."""
    
    def __init__(self, batch_results_path: str, gold_standard_path: str):
        """
        Initialize diagnostics tool.
        
        Args:
            batch_results_path: Path to batch_processing_results.json
            gold_standard_path: Path to gold_standard.csv
        """
        self.batch_results_path = Path(batch_results_path)
        self.gold_standard_path = Path(gold_standard_path)
        
        self.batch_results = None
        self.gold_standard = None
        
    def load_data(self):
        """Load batch results and gold standard."""
        print("📥 Loading data...")
        
        # Load batch results
        with open(self.batch_results_path, 'r', encoding='utf-8') as f:
            self.batch_results = json.load(f)
        print(f"   ✅ Loaded {len(self.batch_results)} batch results")
        
        # Load gold standard
        self.gold_standard = {}
        with open(self.gold_standard_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                study_id = row.get('study_id')
                if study_id:
                    self.gold_standard[study_id] = {k: v.strip() if v else None for k, v in row.items()}
        
        print(f"   ✅ Loaded {len(self.gold_standard)} gold standard entries")
    
    def extract_paper_experiments(self) -> Dict[str, List[Dict]]:
        """
        Extract experiments from batch results, organized by paper.
        
        Returns:
            Dict mapping paper_name -> list of experiments
        """
        paper_experiments = defaultdict(list)
        
        for result in self.batch_results:
            if not result.get('success'):
                continue
            
            paper_name = result.get('paper_name', 'unknown')
            extraction = result.get('extraction_result', {})
            
            # Handle both single and multi-experiment formats
            experiments = extraction.get('experiments', [extraction])
            
            for exp in experiments:
                paper_experiments[paper_name].append(exp)
        
        return paper_experiments
    
    def identify_extraction_sources(self, experiment: Dict) -> Tuple[Set[str], Set[str], Set[str]]:
        """
        Identify which parameters came from regex vs Task 1 vs Task 2.
        
        Args:
            experiment: Single experiment dict with parameters
            
        Returns:
            (regex_params, task1_params, task2_params) - sets of parameter names
        """
        regex_params = set()
        task1_params = set()
        task2_params = set()
        
        parameters = experiment.get('parameters', {})
        
        for param_name, param_data in parameters.items():
            if not isinstance(param_data, dict):
                continue
            
            source_type = param_data.get('source_type', '')
            method = param_data.get('method', '')
            
            # Categorize based on source/method
            if 'regex' in source_type.lower() or 'library' in source_type.lower():
                regex_params.add(param_name)
            elif 'task1' in source_type.lower() or 'missed' in method.lower():
                task1_params.add(param_name)
            elif 'task2' in source_type.lower() or 'discovery' in method.lower():
                task2_params.add(param_name)
            else:
                # Default: assume regex if no clear LLM marker
                regex_params.add(param_name)
        
        return regex_params, task1_params, task2_params
    
    def match_experiment_to_gold(self, experiment: Dict, paper_name: str) -> str:
        """
        Match an experiment to gold standard entry.
        
        Args:
            experiment: Experiment dict
            paper_name: Paper filename
            
        Returns:
            study_id if matched, None otherwise
        """
        # Extract base paper name (remove .pdf extension)
        base_name = paper_name.replace('.pdf', '').replace('.PDF', '')
        
        # Try to match by paper name pattern
        for study_id, gold_entry in self.gold_standard.items():
            # Extract author/year from study_id (e.g., "Butcher2018EXP1")
            import re
            match = re.match(r'^([A-Za-z]+)(\d{4})', study_id)
            if match:
                author, year = match.groups()
                # Check if paper name contains author and year
                if author.lower() in base_name.lower() and year in base_name:
                    return study_id
        
        return None
    
    def analyze_false_negatives(self) -> Dict:
        """
        Analyze false negatives: parameters in gold standard but not extracted.
        Focus on Task 1 failures (regex missed but Task 1 also didn't find).
        
        Returns:
            Analysis dict with detailed statistics
        """
        print("\n🔍 Analyzing False Negatives...")
        
        paper_experiments = self.extract_paper_experiments()
        
        total_fn = 0
        regex_misses = 0
        task1_failures = 0
        task1_successes = 0
        
        # Track which parameters Task 1 struggles with
        task1_failure_by_param = defaultdict(int)
        task1_success_by_param = defaultdict(int)
        
        # Track which papers have most Task 1 failures
        task1_failure_by_paper = defaultdict(int)
        
        # Detailed failure cases
        failure_cases = []
        
        for paper_name, experiments in paper_experiments.items():
            for exp_idx, exp in enumerate(experiments):
                # Try to match to gold standard
                study_id = self.match_experiment_to_gold(exp, paper_name)
                if not study_id:
                    continue
                
                gold_entry = self.gold_standard.get(study_id)
                if not gold_entry:
                    continue
                
                # Get extraction sources
                regex_params, task1_params, task2_params = self.identify_extraction_sources(exp)
                extracted_params = regex_params | task1_params | task2_params
                
                # Find parameters in gold standard
                gold_params = set()
                for key, value in gold_entry.items():
                    # Skip metadata fields
                    if key in {'study_id', 'title', 'authors', 'year', 'doi_or_url', 'lab', 'dataset_link', 'notes'}:
                        continue
                    if value and value.strip():
                        gold_params.add(key)
                
                # Identify false negatives (in gold but not extracted)
                false_negatives = gold_params - extracted_params
                total_fn += len(false_negatives)
                
                # For each false negative, check if regex missed it
                for fn_param in false_negatives:
                    if fn_param not in regex_params:
                        regex_misses += 1
                        
                        # This is a Task 1 failure: regex missed AND Task 1 didn't recover
                        if fn_param not in task1_params:
                            task1_failures += 1
                            task1_failure_by_param[fn_param] += 1
                            task1_failure_by_paper[paper_name] += 1
                            
                            failure_cases.append({
                                'paper_name': paper_name,
                                'study_id': study_id,
                                'parameter': fn_param,
                                'gold_value': gold_entry.get(fn_param),
                                'in_regex': fn_param in regex_params,
                                'in_task1': fn_param in task1_params,
                                'in_task2': fn_param in task2_params
                            })
                        else:
                            # Task 1 successfully recovered it!
                            task1_successes += 1
                            task1_success_by_param[fn_param] += 1
        
        # Sort parameters by failure frequency
        top_failure_params = sorted(task1_failure_by_param.items(), key=lambda x: x[1], reverse=True)
        top_success_params = sorted(task1_success_by_param.items(), key=lambda x: x[1], reverse=True)
        top_failure_papers = sorted(task1_failure_by_paper.items(), key=lambda x: x[1], reverse=True)
        
        # Calculate Task 1 recovery rate
        task1_recovery_rate = task1_successes / regex_misses if regex_misses > 0 else 0
        
        analysis = {
            'total_false_negatives': total_fn,
            'regex_misses': regex_misses,
            'task1_failures': task1_failures,
            'task1_successes': task1_successes,
            'task1_recovery_rate': task1_recovery_rate,
            'top_failure_params': top_failure_params[:20],
            'top_success_params': top_success_params[:20],
            'top_failure_papers': top_failure_papers[:10],
            'failure_cases': failure_cases
        }
        
        return analysis
    
    def generate_report(self, analysis: Dict) -> str:
        """
        Generate comprehensive diagnostic report.
        
        Args:
            analysis: Analysis dict from analyze_false_negatives()
            
        Returns:
            Formatted report string
        """
        report = f"""
{'='*80}
TASK 1 DIAGNOSTIC REPORT
Analyzing LLM Performance in Recovering Missed Library Parameters
{'='*80}

OVERALL STATISTICS
------------------
Total False Negatives: {analysis['total_false_negatives']}
  ├─ Regex Misses: {analysis['regex_misses']} (parameters that regex extraction missed)
  ├─ Task 1 Failures: {analysis['task1_failures']} (regex missed AND Task 1 didn't recover)
  └─ Task 1 Successes: {analysis['task1_successes']} (regex missed BUT Task 1 recovered)

Task 1 Recovery Rate: {analysis['task1_recovery_rate']:.1%}
  → {analysis['task1_successes']}/{analysis['regex_misses']} regex misses were recovered by Task 1

PARAMETERS WITH MOST TASK 1 FAILURES
-------------------------------------
These parameters are in gold standard but Task 1 consistently fails to find them:
"""
        
        for param, count in analysis['top_failure_params']:
            report += f"  {param:30s} : {count:3d} failures\n"
        
        report += f"""
PARAMETERS WITH MOST TASK 1 SUCCESSES
--------------------------------------
These parameters Task 1 successfully recovers when regex misses:
"""
        
        for param, count in analysis['top_success_params']:
            report += f"  {param:30s} : {count:3d} successes\n"
        
        report += f"""
PAPERS WITH MOST TASK 1 FAILURES
---------------------------------
These papers have the most Task 1 failures:
"""
        
        for paper, count in analysis['top_failure_papers']:
            report += f"  {paper:50s} : {count:3d} failures\n"
        
        report += f"""
SAMPLE FAILURE CASES (first 20)
--------------------------------
"""
        
        for case in analysis['failure_cases'][:20]:
            report += f"""
Paper: {case['paper_name']}
Study ID: {case['study_id']}
Parameter: {case['parameter']}
Gold Value: {case['gold_value']}
Sources: Regex={case['in_regex']}, Task1={case['in_task1']}, Task2={case['in_task2']}
"""
        
        report += f"""
{'='*80}
RECOMMENDATIONS
{'='*80}

Based on this analysis:

1. Task 1 Recovery Rate is {analysis['task1_recovery_rate']:.1%}
   → Target: Increase to >50% by relaxing evidence requirements

2. Top Failing Parameters:
"""
        
        for param, count in analysis['top_failure_params'][:5]:
            report += f"   - {param}: {count} failures\n"
        
        report += """
   → These parameters need special attention in Task 1 prompt
   → Consider adding examples of these parameters to the prompt

3. Papers with High Failure Rates:
"""
        
        for paper, count in analysis['top_failure_papers'][:3]:
            report += f"   - {paper}: {count} failures\n"
        
        report += """
   → These papers may have unusual formatting or terminology
   → Consider manual review to understand what Task 1 is missing

{'='*80}
"""
        
        return report
    
    def run(self) -> str:
        """Run full diagnostic analysis and return report."""
        self.load_data()
        analysis = self.analyze_false_negatives()
        report = self.generate_report(analysis)
        return report


def main():
    """Main diagnostic function."""
    import sys
    from pathlib import Path
    
    # Default paths
    project_root = Path(__file__).parent.parent
    batch_results = project_root / 'batch_processing_results.json'
    gold_standard = project_root / 'validation' / 'gold_standard.csv'
    
    # Check if files exist
    if not batch_results.exists():
        print(f"❌ Batch results not found: {batch_results}")
        print("   Run batch processing first to generate results.")
        return
    
    if not gold_standard.exists():
        print(f"❌ Gold standard not found: {gold_standard}")
        return
    
    # Run diagnostics
    diagnostics = Task1Diagnostics(
        batch_results_path=str(batch_results),
        gold_standard_path=str(gold_standard)
    )
    
    report = diagnostics.run()
    
    # Print report
    print(report)
    
    # Save report
    report_file = project_root / 'TASK1_DIAGNOSTIC_REPORT.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n💾 Report saved to: {report_file}")


if __name__ == '__main__':
    main()
