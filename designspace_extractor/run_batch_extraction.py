#!/usr/bin/env python3
"""
Simple Batch Processing Script for Multi-Experiment Paper Extraction
No emojis - Windows compatible
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from extractors.pdfs import PDFExtractor


def process_single_paper(extractor, pdf_path):
    """Process a single PDF paper with multi-experiment detection."""
    paper_name = os.path.basename(pdf_path)
    print(f"\nProcessing: {paper_name}")
    
    try:
        # Extract with multi-experiment detection
        result = extractor.extract_from_file(pdf_path, detect_multi_experiment=True)
        
        # Determine if multi-experiment
        experiments = result.get('experiments', [result])
        num_experiments = len(experiments)
        is_multi = num_experiments > 1
        
        # Count parameters per experiment
        param_counts = []
        all_params = set()
        for exp in experiments:
            params = exp.get('parameters', {})
            param_counts.append(len(params))
            all_params.update(params.keys())
        
        print(f"  SUCCESS: {num_experiments} experiment(s)")
        print(f"  Parameters: {param_counts}")
        print(f"  Unique params: {len(all_params)}")
        
        return {
            'paper_name': paper_name,
            'success': True,
            'is_multi_experiment': is_multi,
            'num_experiments': num_experiments,
            'param_counts': param_counts,
            'unique_params': len(all_params),
            'all_params': sorted(list(all_params)),
            'extraction_result': result
        }
        
    except Exception as e:
        print(f"  FAILED: {str(e)}")
        return {
            'paper_name': paper_name,
            'success': False,
            'error': str(e)
        }


def generate_summary_report(results):
    """Generate comprehensive summary report from batch results."""
    
    total_papers = len(results)
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    multi_exp_papers = [r for r in successful if r['is_multi_experiment']]
    single_exp_papers = [r for r in successful if not r['is_multi_experiment']]
    
    # Statistics
    total_experiments = sum(r['num_experiments'] for r in successful)
    avg_params_per_exp = sum(sum(r['param_counts']) for r in successful) / total_experiments if total_experiments > 0 else 0
    
    # Parameter frequency analysis
    param_frequency = defaultdict(int)
    for result in successful:
        for param in result['all_params']:
            param_frequency[param] += 1
    
    # Sort parameters by frequency
    sorted_params = sorted(param_frequency.items(), key=lambda x: x[1], reverse=True)
    
    # Experiments per paper distribution
    exp_distribution = defaultdict(int)
    for result in multi_exp_papers:
        exp_distribution[result['num_experiments']] += 1
    
    # Generate report
    report = f"""
{'='*80}
BATCH PROCESSING SUMMARY REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*80}

PROCESSING OVERVIEW
-------------------
Total Papers Processed: {total_papers}
Successful: {len(successful)} ({len(successful)/total_papers*100:.1f}%)
Failed: {len(failed)} ({len(failed)/total_papers*100:.1f}%)

MULTI-EXPERIMENT DETECTION
--------------------------"""
    
    # Defensive checks for division by zero
    if len(successful) > 0:
        multi_pct = len(multi_exp_papers)/len(successful)*100
        single_pct = len(single_exp_papers)/len(successful)*100
        report += f"""
Multi-Experiment Papers: {len(multi_exp_papers)} ({multi_pct:.1f}% of successful)
Single-Experiment Papers: {len(single_exp_papers)} ({single_pct:.1f}% of successful)"""
    else:
        report += f"""
Multi-Experiment Papers: {len(multi_exp_papers)} (N/A - no successful extractions)
Single-Experiment Papers: {len(single_exp_papers)} (N/A - no successful extractions)"""
    
    report += f"""
Total Experiments Detected: {total_experiments}

Experiments per Paper Distribution:
"""
    
    for num_exp in sorted(exp_distribution.keys()):
        count = exp_distribution[num_exp]
        report += f"  {num_exp} experiments: {count} papers\n"
    
    report += f"""
PARAMETER EXTRACTION STATISTICS
-------------------------------"""
    
    if len(successful) > 0:
        report += f"""
Average Parameters per Experiment: {avg_params_per_exp:.1f}
Total Unique Parameters Found: {len(param_frequency)}

Top 20 Most Common Parameters:
"""
        for param, count in sorted_params[:20]:
            percentage = count / len(successful) * 100
            report += f"  {param:30s} : {count:3d} papers ({percentage:5.1f}%)\n"
    else:
        report += f"""
Average Parameters per Experiment: N/A (no successful extractions)
Total Unique Parameters Found: 0

No parameters extracted - all papers failed.
"""
    
    if multi_exp_papers:
        report += f"""
MULTI-EXPERIMENT PAPERS DETAIL
------------------------------
"""
        for result in multi_exp_papers:
            report += f"\n[MULTI] {result['paper_name']}\n"
            report += f"   Experiments: {result['num_experiments']}\n"
            report += f"   Parameters per experiment: {result['param_counts']}\n"
            report += f"   Total unique parameters: {result['unique_params']}\n"
    
    if failed:
        report += f"""
FAILED EXTRACTIONS
------------------
"""
        for result in failed:
            report += f"  [FAIL] {result['paper_name']}: {result.get('error', 'Unknown error')}\n"
    
    report += f"""
{'='*80}
END OF REPORT
{'='*80}
"""
    
    return report


def main():
    """Main batch processing function."""
    print("="*80)
    print("BATCH PROCESSING: Multi-Experiment Paper Extraction")
    print("="*80)
    
    # Setup paths
    project_root = Path(__file__).parent
    papers_folder = project_root.parent / 'papers'  # papers is at workspace root
    
    if not papers_folder.exists():
        print(f"ERROR: Papers folder not found: {papers_folder}")
        return
    
    # Find all PDF files
    pdf_files = sorted(list(papers_folder.glob('*.pdf')))
    print(f"\nFound {len(pdf_files)} PDF files in {papers_folder}")
    
    if not pdf_files:
        print("ERROR: No PDF files found!")
        return
    
    # Initialize extractor
    print("\nInitializing PDF extractor...")
    
    # Check if LLM is enabled via environment
    use_llm = os.getenv('LLM_ENABLE', 'false').lower() in ('true', '1', 'yes')
    llm_provider = os.getenv('LLM_PROVIDER', 'qwen')
    llm_mode = os.getenv('LLM_MODE', 'verify')  # 'verify' or 'fallback'
    
    if use_llm:
        print(f"   LLM assistance: ENABLED (provider: {llm_provider}, mode: {llm_mode})")
    else:
        print("   LLM assistance: DISABLED")
    
    extractor = PDFExtractor(use_llm=use_llm, llm_provider=llm_provider, llm_mode=llm_mode)
    
    if extractor.llm_assistant:
        print(f"   LLM assistant initialized: {extractor.llm_assistant.enabled}")
    else:
        print("   LLM assistant: None")
    
    # Process all papers
    print("\n" + "="*80)
    print("PROCESSING PAPERS")
    print("="*80)
    
    results = []
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}]", end=" ")
        result = process_single_paper(extractor, pdf_path)
        results.append(result)
    
    # Generate summary report
    print("\n" + "="*80)
    print("GENERATING SUMMARY REPORT")
    print("="*80)
    
    summary_report = generate_summary_report(results)
    print(summary_report)
    
    # Save results to JSON
    output_file = project_root / 'batch_processing_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nDetailed results saved to: {output_file}")
    
    # Save summary report to text file
    report_file = project_root / 'BATCH_PROCESSING_REPORT.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(summary_report)
    print(f"Summary report saved to: {report_file}")
    
    print("\nBatch processing complete!")


if __name__ == '__main__':
    main()
