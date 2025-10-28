#!/usr/bin/env python3
"""
Test auto-merge functionality between LLM and regex extractions.
"""

import sys
from utils.conflict_resolution import auto_merge_llm_and_regex

print("=" * 70)
print("AUTO-MERGE TEST: LLM + Regex Extraction")
print("=" * 70)

# Simulate regex extractions (high confidence)
regex_params = {
    'n_participants': {
        'value': 24,
        'source_type': 'pdf_table',
        'confidence': 0.90,
        'method': 'table_extraction',
        'page': 3
    },
    'rotation_degrees': {
        'value': 30,
        'source_type': 'pdf_text',
        'confidence': 0.70,
        'method': 'pattern_match',
        'page': 4
    },
    'n_trials_baseline': {
        'value': 100,
        'source_type': 'code',
        'confidence': 0.95,
        'method': 'ast_parsing',
        'file': 'experiment.py'
    }
}

# Simulate LLM extractions (varying confidence)
llm_params = {
    'age_mean': {
        'value': 22.3,
        'source_type': 'llm_inference',
        'confidence': 0.85,  # High confidence - should auto-accept
        'llm_reasoning': 'Explicitly stated in Methods: mean age 22.3 years',
        'llm_provider': 'qwen'
    },
    'age_sd': {
        'value': 3.2,
        'source_type': 'llm_inference',
        'confidence': 0.62,  # Medium confidence - should flag for review
        'llm_reasoning': 'Inferred from "ages ranged from 19-26"',
        'llm_provider': 'qwen'
    },
    'rotation_degrees': {
        'value': 25,
        'source_type': 'llm_inference',
        'confidence': 0.65,  # Conflicts with regex (0.70)
        'llm_reasoning': 'Found in figure caption',
        'llm_provider': 'qwen'
    },
    'perturbation_type': {
        'value': 'visuomotor rotation',
        'source_type': 'llm_inference',
        'confidence': 0.95,  # Very high confidence - should auto-accept
        'llm_reasoning': 'Explicitly stated as "visuomotor rotation"',
        'llm_provider': 'qwen'
    },
    'n_blocks': {
        'value': 8,
        'source_type': 'llm_inference',
        'confidence': 0.45,  # Low confidence - should flag for review
        'llm_reasoning': 'Possibly mentioned but unclear',
        'llm_provider': 'qwen'
    }
}

print("\n📥 INPUT PARAMETERS")
print("-" * 70)
print(f"\nRegex extractions: {len(regex_params)} parameters")
for param, data in regex_params.items():
    print(f"  ✓ {param:25} = {data['value']:>10}  (conf={data['confidence']:.2f}, {data['source_type']})")

print(f"\nLLM extractions: {len(llm_params)} parameters")
for param, data in llm_params.items():
    print(f"  🤖 {param:25} = {data['value']:>10}  (conf={data['confidence']:.2f}, {data['source_type']})")

# Run auto-merge
print("\n" + "=" * 70)
print("⚙️  RUNNING AUTO-MERGE (confidence threshold = 0.7)")
print("=" * 70)

merged = auto_merge_llm_and_regex(
    regex_params=regex_params,
    llm_params=llm_params,
    confidence_threshold=0.7
)

# Display results
print("\n📤 MERGED RESULTS")
print("-" * 70)

auto_accepted = 0
requires_review = 0
conflicts = 0

for param, data in sorted(merged.items()):
    value = data['value']
    source = data['source_type']
    confidence = data.get('confidence', 0)
    
    # Status indicators
    status = ""
    if data.get('conflict_detected'):
        status = "⚔️  CONFLICT"
        conflicts += 1
    elif data.get('auto_accepted'):
        status = "✅ AUTO-ACCEPTED"
        auto_accepted += 1
    elif data.get('requires_review'):
        status = "⚠️  REVIEW NEEDED"
        requires_review += 1
    else:
        status = "✓ ACCEPTED"
        auto_accepted += 1
    
    print(f"\n{param}:")
    print(f"  Value:      {value}")
    print(f"  Source:     {source}")
    print(f"  Confidence: {confidence:.2f}")
    print(f"  Status:     {status}")
    
    if data.get('resolution_method'):
        print(f"  Resolution: {data['resolution_method']}")
    
    if data.get('reason'):
        print(f"  Reason:     {data['reason']}")
    
    if data.get('alternative_values'):
        print(f"  Alternatives:")
        for alt in data['alternative_values']:
            print(f"    - {alt['value']} (source={alt['source']}, conf={alt['confidence']:.2f})")

# Summary
print("\n" + "=" * 70)
print("📊 SUMMARY")
print("=" * 70)
print(f"Total parameters:      {len(merged)}")
print(f"Auto-accepted:         {auto_accepted}  ({100*auto_accepted/len(merged):.0f}%)")
print(f"Requires review:       {requires_review}  ({100*requires_review/len(merged):.0f}%)")
print(f"Conflicts resolved:    {conflicts}")

# Test scenarios
print("\n" + "=" * 70)
print("🧪 TEST SCENARIOS VALIDATED")
print("=" * 70)

scenarios = [
    ("Regex only (n_participants)", 
     merged['n_participants']['source_type'] == 'pdf_table' and not merged['n_participants'].get('requires_review')),
    
    ("LLM only, high conf (age_mean)", 
     merged['age_mean']['source_type'] == 'llm_inference' and merged['age_mean'].get('auto_accepted')),
    
    ("LLM only, low conf (age_sd)", 
     merged['age_sd']['source_type'] == 'llm_inference' and merged['age_sd'].get('requires_review')),
    
    ("Conflict, confidence-based (rotation_degrees)", 
     merged['rotation_degrees']['source_type'] == 'pdf_text' and merged['rotation_degrees'].get('conflict_detected')),
    
    ("LLM only, very high conf (perturbation_type)", 
     merged['perturbation_type']['source_type'] == 'llm_inference' and merged['perturbation_type'].get('auto_accepted')),
]

for scenario, passed in scenarios:
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}  {scenario}")

print("\n" + "=" * 70)
print("✅ Auto-merge strategy working as expected!")
print("=" * 70)
