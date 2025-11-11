"""
Robust JSON parsing utilities for LLM outputs.
Handles common LLM JSON generation issues like extra text, markdown wrappers, etc.
"""

import json
import re
import logging
from typing import Optional, Any, Tuple

logger = logging.getLogger(__name__)


def extract_json_from_text(text: str) -> Tuple[Optional[dict], Optional[str]]:
    """
    Extract JSON from LLM output that may contain extra text.
    Handles two common error patterns:
    1. Extra text before JSON: "Here is the JSON: {...}"
    2. Extra text after JSON: "{...}\\n\\nLet me know if you need anything else."
    
    Args:
        text: Raw LLM output string
        
    Returns:
        Tuple of (parsed_dict, error_message)
        Returns (None, error_msg) if no valid JSON found
    """
    if not text or not text.strip():
        return None, "Empty response"
    
    text = text.strip()
    
    # Strategy 1: Try direct JSON parse first (fastest path)
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        pass  # Continue to extraction strategies
    
    # Strategy 2: Remove markdown code blocks (```json ... ```)
    markdown_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    match = re.search(markdown_pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1)), None
        except json.JSONDecodeError:
            pass
    
    # Strategy 3: Find JSON object by braces (handles extra text before/after)
    # Look for outermost {} or []
    json_patterns = [
        r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\})*)*\}))*\}',  # Nested objects
        r'\[(?:[^\[\]]|(?:\[(?:[^\[\]]|(?:\[[^\[\]]*\])*)*\]))*\]'  # Nested arrays
    ]
    
    for pattern in json_patterns:
        matches = re.finditer(pattern, text, re.DOTALL)
        for match in matches:
            candidate = match.group(0)
            try:
                parsed = json.loads(candidate)
                logger.debug(f"Extracted JSON from position {match.start()}-{match.end()}")
                return parsed, None
            except json.JSONDecodeError:
                continue
    
    # Strategy 4: Try to find JSON after common prefixes
    prefixes = [
        r'(?:here is|here\'s|the|output|result|json|response)[\s:]*',
        r'(?:```json\s*)',
        r'(?:```\s*)',
    ]
    
    for prefix in prefixes:
        pattern = rf'{prefix}(\{{.*?\}})'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1)), None
            except json.JSONDecodeError:
                continue
    
    # Strategy 5: Try to extract just the first complete JSON object/array
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start_idx = text.find(start_char)
        if start_idx == -1:
            continue
        
        # Count braces to find matching closing brace
        depth = 0
        in_string = False
        escape = False
        
        for i, char in enumerate(text[start_idx:], start=start_idx):
            if escape:
                escape = False
                continue
            
            if char == '\\':
                escape = True
                continue
            
            if char == '"' and not escape:
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            if char == start_char:
                depth += 1
            elif char == end_char:
                depth -= 1
                if depth == 0:
                    candidate = text[start_idx:i+1]
                    try:
                        parsed = json.loads(candidate)
                        logger.debug(f"Extracted JSON using brace counting: {start_idx}-{i+1}")
                        return parsed, None
                    except json.JSONDecodeError:
                        break
    
    # All strategies failed
    error_msg = "Could not extract valid JSON from response"
    logger.warning(f"{error_msg}. Response preview: {text[:200]}...")
    return None, error_msg


def parse_llm_json_response(response: str, expected_keys: Optional[list] = None, 
                            task_type: Optional[str] = None) -> Optional[dict]:
    """
    Parse JSON from LLM response with robust error handling.
    
    Args:
        response: Raw LLM response string
        expected_keys: Optional list of keys that must be present in the JSON
        task_type: Optional task type for better error messages
        
    Returns:
        Parsed dictionary or None if parsing failed
    """
    if not response:
        logger.error(f"Empty response for task: {task_type}")
        return None
    
    # Extract JSON from response
    parsed, error = extract_json_from_text(response)
    
    if parsed is None:
        logger.error(f"JSON extraction failed for {task_type}: {error}")
        logger.debug(f"Raw response: {response[:500]}...")
        return None
    
    # Validate expected keys if provided
    if expected_keys:
        missing_keys = [key for key in expected_keys if key not in parsed]
        if missing_keys:
            logger.warning(f"Missing expected keys in {task_type}: {missing_keys}")
            # Don't fail - just warn, as LLM might use different structure
    
    logger.debug(f"Successfully parsed JSON for {task_type}")
    return parsed


def validate_verification_response(data: dict) -> bool:
    """
    Validate that a verification response has required fields.
    
    Args:
        data: Parsed JSON dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['verified', 'evidence', 'abstained']
    
    # For single verification
    if all(field in data for field in required_fields):
        return True
    
    # For batch verification - check if it's a dict of verifications
    if isinstance(data, dict) and len(data) > 0:
        # Check first entry
        first_entry = next(iter(data.values()))
        if isinstance(first_entry, dict):
            return all(field in first_entry for field in required_fields)
    
    return False


def validate_extraction_response(data: dict, task_type: str) -> bool:
    """
    Validate that an extraction response has required fields.
    
    Args:
        data: Parsed JSON dictionary
        task_type: Either 'missed_params' or 'new_params'
        
    Returns:
        True if valid, False otherwise
    """
    if task_type == 'missed_params':
        if 'missed_parameters' not in data:
            return False
        
        # Validate each missed parameter
        for param in data['missed_parameters']:
            required = ['parameter_name', 'value', 'confidence', 'evidence', 'evidence_location']
            if not all(field in param for field in required):
                return False
        
        return True
    
    elif task_type == 'new_params':
        if 'new_parameters' not in data:
            return False
        
        # Validate each new parameter
        for param in data['new_parameters']:
            required = ['parameter_name', 'description', 'category', 'evidence', 'evidence_location']
            if not all(field in param for field in required):
                return False
        
        return True
    
    return False


def clean_json_string(text: str) -> str:
    """
    Clean common JSON formatting issues in LLM outputs.
    
    Args:
        text: Raw JSON string
        
    Returns:
        Cleaned JSON string
    """
    # Remove BOM if present
    text = text.lstrip('\ufeff')
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Remove common prefixes
    prefixes_to_remove = [
        'json\n',
        'JSON\n',
        'Here is the JSON:\n',
        'Here\'s the JSON:\n',
    ]
    
    for prefix in prefixes_to_remove:
        if text.startswith(prefix):
            text = text[len(prefix):].lstrip()
    
    return text
