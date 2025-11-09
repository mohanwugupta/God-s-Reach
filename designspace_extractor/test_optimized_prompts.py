"""
Quick test to validate optimized prompts.

Tests:
1. Verify prompts are more concise
2. Discovery prompt includes both missed params and new params
3. Response parser handles new format
"""
import json
from pathlib import Path
from llm.prompt_builder import PromptBuilder
from llm.response_parser import ResponseParser
from llm.base import ParameterProposal


def test_verify_batch_prompt_conciseness():
    """Verify batch prompt is more concise than before."""
    builder = PromptBuilder()
    
    prompt = builder.build_batch_verification_prompt(
        extracted_params={'sample_size_n': 20},
        context='Study with 20 participants using 30° rotation',
        study_type='visuomotor_rotation',
        num_experiments=1
    )
    
    # Check it's reasonably sized (not bloated)
    assert len(prompt) < 1500, f"Prompt too long: {len(prompt)} chars"
    
    # Check key instructions present
    assert 'Quick verification' in prompt or 'TASK' in prompt
    assert 'verified' in prompt  # New format
    
    print(f"✓ Batch verification prompt: {len(prompt)} chars (concise)")


def test_verify_single_prompt_conciseness():
    """Verify single param prompt is concise."""
    builder = PromptBuilder()
    
    prompt = builder.build_single_parameter_prompt(
        parameter_name='target_distance_cm',
        context='Targets at 10 cm distance',
        description='Distance to target in cm'
    )
    
    # Should be very short for single param
    assert len(prompt) < 800, f"Single param prompt too long: {len(prompt)} chars"
    assert 'Quick verification' in prompt or 'TASK' in prompt
    
    print(f"✓ Single param prompt: {len(prompt)} chars (concise)")


def test_discovery_prompt_includes_both_tasks():
    """Discovery prompt should ask for both missed library params and new params."""
    builder = PromptBuilder()
    
    prompt = builder.build_discovery_prompt(
        context='Study used 30° rotation with 20 participants',
        study_type='visuomotor_rotation',
        num_experiments=1,
        already_extracted={'sample_size_n': 20}
    )
    
    # Check it asks for both tasks
    assert 'TASK 1' in prompt or 'missed' in prompt.lower()
    assert 'TASK 2' in prompt or 'new' in prompt.lower()
    assert 'missed_from_library' in prompt
    assert 'new_parameters' in prompt
    
    print(f"✓ Discovery prompt includes both tasks: {len(prompt)} chars")


def test_response_parser_handles_new_discovery_format():
    """Response parser should handle new two-part discovery format."""
    parser = ResponseParser()
    
    # New format response
    response = json.dumps({
        "missed_from_library": [
            {
                "parameter_name": "rotation_magnitude_deg",
                "value": 30,
                "confidence": 0.95,
                "evidence": "visuomotor rotation of 30 degrees was applied to cursor feedback",
                "evidence_location": "Methods, page 3"
            }
        ],
        "new_parameters": [
            {
                "parameter_name": "break_duration_min",
                "description": "Rest break duration between blocks",
                "category": "trials",
                "evidence": "participants took 5-minute rest breaks between experimental blocks",
                "evidence_location": "Procedures, page 4",
                "example_values": ["5"],
                "units": "min",
                "prevalence": "medium",
                "importance": "low",
                "mapping_suggestion": "new",
                "hed_hint": None
            }
        ]
    })
    
    proposals = parser.parse_discovery_response(response, min_evidence_length=20)
    
    # Should have 2 proposals
    assert len(proposals) == 2, f"Expected 2 proposals, got {len(proposals)}"
    
    # Missed library param should come first (EXTRACTION category)
    assert proposals[0].category == 'EXTRACTION', "Missed param should be first"
    assert proposals[0].parameter_name == 'rotation_magnitude_deg'
    assert proposals[0].importance == 'high', "Missed params are high importance"
    
    # New param should be second
    assert proposals[1].category == 'trials'
    assert proposals[1].parameter_name == 'break_duration_min'
    
    print(f"✓ Parser handles new format: {len(proposals)} proposals")
    print(f"  - Missed: {proposals[0].parameter_name}")
    print(f"  - New: {proposals[1].parameter_name}")


def test_response_parser_handles_legacy_format():
    """Response parser should still handle legacy array format."""
    parser = ResponseParser()
    
    # Legacy format (plain array)
    response = json.dumps([
        {
            "parameter_name": "cursor_size_cm",
            "description": "Size of cursor in cm",
            "category": "feedback",
            "evidence": "cursor diameter was 0.5 cm on the screen display",
            "evidence_location": "Equipment, page 2",
            "example_values": ["0.5"],
            "units": "cm",
            "prevalence": "medium",
            "importance": "low",
            "mapping_suggestion": "new",
            "hed_hint": None
        }
    ])
    
    proposals = parser.parse_discovery_response(response, min_evidence_length=20)
    
    assert len(proposals) == 1
    assert proposals[0].parameter_name == 'cursor_size_cm'
    
    print(f"✓ Parser handles legacy format: {len(proposals)} proposals")


def test_prompts_emphasize_speed():
    """Prompts should emphasize quick responses without excessive thinking."""
    builder = PromptBuilder()
    
    # Batch verification
    batch_prompt = builder.build_batch_verification_prompt(
        extracted_params={'sample_size_n': 20},
        context='20 participants',
        study_type='test',
        num_experiments=1
    )
    
    # Check for speed emphasis
    speed_indicators = [
        'quick', 'Quick', 'no thinking', 'concise', 'CONCISE',
        'Only provide reasoning if', 'NO reasoning', 'JSON only'
    ]
    
    found = [ind for ind in speed_indicators if ind in batch_prompt]
    assert len(found) > 0, f"Batch prompt should emphasize speed. Found: {found}"
    
    # Single verification
    single_prompt = builder.build_single_parameter_prompt(
        parameter_name='test_param',
        context='test context'
    )
    
    found = [ind for ind in speed_indicators if ind in single_prompt]
    assert len(found) > 0, f"Single prompt should emphasize speed. Found: {found}"
    
    print(f"✓ Prompts emphasize quick responses")


if __name__ == '__main__':
    print("Testing optimized prompts...\n")
    
    test_verify_batch_prompt_conciseness()
    test_verify_single_prompt_conciseness()
    test_discovery_prompt_includes_both_tasks()
    test_response_parser_handles_new_discovery_format()
    test_response_parser_handles_legacy_format()
    test_prompts_emphasize_speed()
    
    print("\n✅ All optimization tests passed!")
