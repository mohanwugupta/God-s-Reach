#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parameter Coverage Analytics
Analyzes extraction results to identify coverage gaps and suggest improvements.
"""

import json
import sys
import io
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict, Counter
import argparse

# Set UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from llm.llm_assist import LLMAssistant


def load_batch_results(results_file: Path) -> List[Dict]:
    """Load batch processing results."""
    with open(results_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_parameter_coverage(results: List[Dict]) -> Dict[str, Any]:
    """
    Analyze parameter extraction coverage across all papers.
    
    Returns:
        Dictionary with coverage statistics
    """
    # Track which parameters appear in which papers
    parameter_presence = defaultdict(list)
    parameter_values = defaultdict(list)
    total_experiments = 0
    
    for result in results:
        if not result['success']:
            continue
        
        paper_name = result['paper_name']
        extraction = result['extraction_result']
        experiments = extraction.get('experiments', [extraction])
        
        for exp_idx, exp in enumerate(experiments, 1):
            total_experiments += 1
            exp_id = f"{paper_name}_E{exp_idx}" if len(experiments) > 1 else paper_name
            
            params = exp.get('parameters', {})
            for param_name, param_data in params.items():
                if isinstance(param_data, dict):
                    value = param_data.get('value')
                    confidence = param_data.get('confidence', 0)
                else:
                    value = param_data
                    confidence = 1.0
                
                parameter_presence[param_name].append({
                    'experiment': exp_id,
                    'value': value,
                    'confidence': confidence
                })
                parameter_values[param_name].append(value)
    
    # Calculate coverage percentages
    coverage_stats = {}
    for param_name, presences in parameter_presence.items():
        coverage_pct = (len(presences) / total_experiments) * 100
        
        # Get unique values
        unique_values = set(str(v) for v in parameter_values[param_name] if v is not None)
        
        # Average confidence
        confidences = [p['confidence'] for p in presences]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        coverage_stats[param_name] = {
            'count': len(presences),
            'total': total_experiments,
            'coverage_pct': coverage_pct,
            'unique_values': len(unique_values),
            'avg_confidence': avg_confidence,
            'presences': presences
        }
    
    return {
        'total_experiments': total_experiments,
        'total_papers': len([r for r in results if r['success']]),
        'coverage_by_parameter': coverage_stats
    }


def identify_missing_parameters(results: List[Dict], coverage_stats: Dict) -> Dict[str, List[str]]:
    """
    Identify which papers are missing which parameters.
    
    Returns:
        Dictionary mapping parameter names to lists of papers missing that parameter
    """
    missing_by_param = defaultdict(list)
    
    # Get all experiment IDs
    all_experiments = set()
    for result in results:
        if not result['success']:
            continue
        paper_name = result['paper_name']
        extraction = result['extraction_result']
        experiments = extraction.get('experiments', [extraction])
        
        for exp_idx in range(len(experiments)):
            exp_id = f"{paper_name}_E{exp_idx + 1}" if len(experiments) > 1 else paper_name
            all_experiments.add(exp_id)
    
    # For each parameter, find experiments without it
    for param_name, stats in coverage_stats['coverage_by_parameter'].items():
        experiments_with = {p['experiment'] for p in stats['presences']}
        missing = all_experiments - experiments_with
        if missing:
            missing_by_param[param_name] = sorted(missing)
    
    return missing_by_param


def suggest_pattern_improvements(coverage_stats: Dict, threshold: float = 50.0) -> List[Dict[str, Any]]:
    """
    Suggest pattern improvements for low-coverage parameters.
    
    Args:
        coverage_stats: Coverage statistics
        threshold: Coverage percentage threshold for suggestions
        
    Returns:
        List of improvement suggestions
    """
    suggestions = []
    
    for param_name, stats in coverage_stats['coverage_by_parameter'].items():
        if stats['coverage_pct'] < threshold:
            # Categorize by coverage level
            if stats['coverage_pct'] == 0:
                priority = "CRITICAL"
                action = "Add patterns - parameter never extracted"
            elif stats['coverage_pct'] < 25:
                priority = "HIGH"
                action = "Improve patterns - very low coverage"
            elif stats['coverage_pct'] < 50:
                priority = "MEDIUM"
                action = "Review patterns - below target coverage"
            
            suggestions.append({
                'parameter': param_name,
                'coverage_pct': stats['coverage_pct'],
                'count': stats['count'],
                'total': stats['total'],
                'priority': priority,
                'action': action,
                'avg_confidence': stats['avg_confidence']
            })
    
    # Sort by priority and coverage
    priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2}
    suggestions.sort(key=lambda x: (priority_order[x['priority']], x['coverage_pct']))
    
    return suggestions


def print_coverage_report(coverage_stats: Dict, missing_by_param: Dict, suggestions: List[Dict]):
    """Print formatted coverage report."""
    
    print("\n" + "=" * 80)
    print("PARAMETER COVERAGE ANALYSIS REPORT")
    print("=" * 80)
    
    print(f"\n📊 CORPUS STATISTICS")
    print(f"   Total Papers: {coverage_stats['total_papers']}")
    print(f"   Total Experiments: {coverage_stats['total_experiments']}")
    print(f"   Unique Parameters: {len(coverage_stats['coverage_by_parameter'])}")
    
    # Coverage by tier
    coverage_by_param = coverage_stats['coverage_by_parameter']
    excellent = sum(1 for s in coverage_by_param.values() if s['coverage_pct'] >= 80)
    good = sum(1 for s in coverage_by_param.values() if 50 <= s['coverage_pct'] < 80)
    poor = sum(1 for s in coverage_by_param.values() if 25 <= s['coverage_pct'] < 50)
    critical = sum(1 for s in coverage_by_param.values() if s['coverage_pct'] < 25)
    
    print(f"\n📈 COVERAGE TIERS")
    print(f"   ✅ Excellent (≥80%): {excellent} parameters")
    print(f"   👍 Good (50-80%): {good} parameters")
    print(f"   ⚠️  Poor (25-50%): {poor} parameters")
    print(f"   ❌ Critical (<25%): {critical} parameters")
    
    # Top parameters
    print(f"\n🏆 TOP 10 PARAMETERS (by coverage)")
    sorted_params = sorted(coverage_by_param.items(), key=lambda x: x[1]['coverage_pct'], reverse=True)
    for idx, (param_name, stats) in enumerate(sorted_params[:10], 1):
        bar = "█" * int(stats['coverage_pct'] / 5)
        print(f"   {idx:2}. {param_name:30} {stats['coverage_pct']:5.1f}% │{bar}")
    
    # Bottom parameters
    print(f"\n⚠️  BOTTOM 10 PARAMETERS (need improvement)")
    for idx, (param_name, stats) in enumerate(sorted_params[-10:], 1):
        bar = "█" * int(stats['coverage_pct'] / 5)
        missing_count = stats['total'] - stats['count']
        print(f"   {idx:2}. {param_name:30} {stats['coverage_pct']:5.1f}% │{bar} (missing in {missing_count} experiments)")
    
    # Improvement suggestions
    if suggestions:
        print(f"\n💡 IMPROVEMENT SUGGESTIONS ({len(suggestions)} parameters)")
        print(f"   {'Priority':<10} {'Parameter':<30} {'Coverage':<12} {'Action'}")
        print(f"   {'-'*10} {'-'*30} {'-'*12} {'-'*40}")
        for sugg in suggestions[:15]:  # Show top 15
            print(f"   {sugg['priority']:<10} {sugg['parameter']:<30} "
                  f"{sugg['coverage_pct']:5.1f}% ({sugg['count']}/{sugg['total']})  {sugg['action']}")
    
    # Parameter categories
    print(f"\n📂 COVERAGE BY CATEGORY")
    categories = {
        'demographics': ['age_mean', 'age_sd', 'gender_distribution', 'handedness', 'sample_size_n', 'n_total'],
        'metadata': ['doi_or_url', 'authors', 'year', 'lab', 'dataset_link'],
        'task_design': ['effector', 'environment', 'number_of_locations', 'spacing_deg', 'coordinate_frame'],
        'perturbation': ['perturbation_class', 'force_field_type', 'rotation_magnitude_deg', 'rotation_direction'],
        'trials': ['adaptation_trials', 'baseline_trials', 'washout_trials', 'num_trials'],
        'feedback': ['feedback_type', 'cue_modalities', 'instruction_awareness']
    }
    
    for category, params in categories.items():
        present_params = [p for p in params if p in coverage_by_param]
        if present_params:
            avg_coverage = sum(coverage_by_param[p]['coverage_pct'] for p in present_params) / len(present_params)
            print(f"   {category:20} {avg_coverage:5.1f}% (across {len(present_params)} parameters)")


def discover_new_parameters_llm(results: List[Dict], current_schema: List[str], 
                               provider: str = 'claude') -> List[Dict[str, Any]]:
    """
    Use LLM to discover new parameters not in current schema.
    
    Args:
        results: Batch processing results
        current_schema: List of current parameter names
        provider: LLM provider to use
        
    Returns:
        List of suggested new parameters
    """
    print("\n" + "=" * 80)
    print("🤖 LLM-POWERED PARAMETER DISCOVERY")
    print("=" * 80)
    
    assistant = LLMAssistant(provider=provider)
    
    if not assistant.enabled:
        print("\n❌ LLM is not enabled. Set LLM_ENABLE=true and ANTHROPIC_API_KEY in .env")
        return []
    
    print(f"\n   Provider: {provider}")
    print(f"   Model: {assistant.model}")
    print(f"   Current schema: {len(current_schema)} parameters")
    
    # Collect all paper texts (Methods sections preferred)
    all_suggestions = []
    papers_analyzed = 0
    
    for result in results[:5]:  # Analyze first 5 papers to limit cost
        if not result['success']:
            continue
        
        paper_name = result['paper_name']
        extraction = result['extraction_result']
        
        # Get Methods section if available
        text = extraction.get('full_text', '')[:5000]  # First 5000 chars
        
        if len(text) < 500:
            continue
        
        print(f"\n   Analyzing: {paper_name[:60]}...")
        suggestions = assistant.discover_new_parameters(text, current_schema)
        
        if suggestions:
            # Add source paper to each suggestion
            for sugg in suggestions:
                sugg['source_paper'] = paper_name
            all_suggestions.extend(suggestions)
            papers_analyzed += 1
    
    print(f"\n   ✅ Analyzed {papers_analyzed} papers")
    print(f"   💡 Found {len(all_suggestions)} parameter suggestions")
    
    # Aggregate suggestions by parameter name
    aggregated = defaultdict(list)
    for sugg in all_suggestions:
        aggregated[sugg['parameter_name']].append(sugg)
    
    # Create consolidated suggestions
    consolidated = []
    for param_name, suggestions in aggregated.items():
        # Average importance and prevalence
        importances = [s['importance'] for s in suggestions]
        prevalences = [s['prevalence'] for s in suggestions]
        
        consolidated.append({
            'parameter_name': param_name,
            'description': suggestions[0]['description'],
            'category': suggestions[0]['category'],
            'importance': Counter(importances).most_common(1)[0][0],
            'prevalence': Counter(prevalences).most_common(1)[0][0],
            'occurrences': len(suggestions),
            'example_values': suggestions[0]['example_values'],
            'evidence': suggestions[0]['evidence'],
            'source_papers': [s['source_paper'] for s in suggestions]
        })
    
    # Sort by occurrences and importance
    importance_score = {'high': 3, 'medium': 2, 'low': 1}
    consolidated.sort(key=lambda x: (x['occurrences'], importance_score[x['importance']]), reverse=True)
    
    return consolidated


def print_new_parameter_suggestions(suggestions: List[Dict]):
    """Print LLM-discovered parameter suggestions."""
    
    if not suggestions:
        return
    
    print(f"\n📋 NEW PARAMETER RECOMMENDATIONS ({len(suggestions)} unique parameters)")
    print("   " + "=" * 76)
    
    for idx, sugg in enumerate(suggestions, 1):
        print(f"\n   {idx}. {sugg['parameter_name']}")
        print(f"      Description: {sugg['description']}")
        print(f"      Category: {sugg['category']}")
        print(f"      Importance: {sugg['importance']} | Prevalence: {sugg['prevalence']}")
        print(f"      Found in: {sugg['occurrences']} paper(s)")
        print(f"      Examples: {', '.join(str(v) for v in sugg['example_values'][:3])}")
        print(f"      Evidence: \"{sugg['evidence'][:100]}...\"")
    
    print(f"\n💡 SCHEMA EXTENSION RECOMMENDATIONS")
    print(f"   High priority ({sum(1 for s in suggestions if s['importance'] == 'high')} params): "
          f"{', '.join(s['parameter_name'] for s in suggestions if s['importance'] == 'high')[:100]}")
    print(f"   Medium priority ({sum(1 for s in suggestions if s['importance'] == 'medium')} params): "
          f"{', '.join(s['parameter_name'] for s in suggestions if s['importance'] == 'medium')[:100]}")


def main():
    parser = argparse.ArgumentParser(description='Analyze parameter extraction coverage')
    parser.add_argument('--results', type=str, default='./batch_processing_results.json',
                       help='Path to batch processing results file')
    parser.add_argument('--discover-new', action='store_true',
                       help='Use LLM to discover new parameters not in schema')
    parser.add_argument('--llm-provider', type=str, default='claude',
                       choices=['claude', 'openai'],
                       help='LLM provider for parameter discovery')
    parser.add_argument('--threshold', type=float, default=50.0,
                       help='Coverage threshold for improvement suggestions (%)')
    parser.add_argument('--output', type=str,
                       help='Save coverage report to JSON file')
    
    args = parser.parse_args()
    
    # Load results
    results_file = Path(args.results)
    if not results_file.exists():
        print(f"❌ Results file not found: {results_file}")
        return 1
    
    print(f"Loading results from: {results_file}")
    results = load_batch_results(results_file)
    
    # Analyze coverage
    coverage_stats = analyze_parameter_coverage(results)
    missing_by_param = identify_missing_parameters(results, coverage_stats)
    suggestions = suggest_pattern_improvements(coverage_stats, args.threshold)
    
    # Print report
    print_coverage_report(coverage_stats, missing_by_param, suggestions)
    
    # LLM parameter discovery
    new_params = []
    if args.discover_new:
        current_schema = list(coverage_stats['coverage_by_parameter'].keys())
        new_params = discover_new_parameters_llm(results, current_schema, args.llm_provider)
        print_new_parameter_suggestions(new_params)
    
    # Save output
    if args.output:
        output_data = {
            'coverage_statistics': coverage_stats,
            'missing_by_parameter': missing_by_param,
            'improvement_suggestions': suggestions,
            'new_parameter_suggestions': new_params
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        print(f"\n💾 Report saved to: {args.output}")
    
    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80 + "\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
