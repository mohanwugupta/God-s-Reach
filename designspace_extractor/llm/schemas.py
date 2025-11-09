"""
JSON schemas for Outlines structured generation.
These schemas enforce valid JSON output from LLMs for parameter extraction tasks.
"""

# Schema for batch verification (verify_batch.txt)
VERIFICATION_BATCH_SCHEMA = {
    "type": "object",
    "patternProperties": {
        ".*": {  # Any parameter name
            "type": "object",
            "properties": {
                "verified": {"type": "boolean"},
                "value": {},  # Any type (string, number, etc.)
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "evidence": {"type": "string"},
                "reasoning": {"type": "string"},
                "abstained": {"type": "boolean"}
            },
            "required": ["verified", "evidence", "abstained"],
            "additionalProperties": False
        }
    },
    "additionalProperties": True  # Allow any parameter names
}

# Schema for single parameter verification (verify_single.txt)
VERIFICATION_SINGLE_SCHEMA = {
    "type": "object",
    "properties": {
        "verified": {"type": "boolean"},
        "value": {},  # Any type
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "evidence": {"type": "string"},
        "reasoning": {"type": "string"},
        "abstained": {"type": "boolean"}
    },
    "required": ["verified", "evidence", "abstained"],
    "additionalProperties": False
}

# Schema for missed parameters discovery (task1_missed_params.txt)
MISSED_PARAMS_SCHEMA = {
    "type": "object",
    "properties": {
        "missed_parameters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "parameter_name": {"type": "string"},
                    "value": {},  # Any type
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "evidence": {"type": "string"},
                    "evidence_location": {"type": "string"}
                },
                "required": ["parameter_name", "value", "confidence", "evidence", "evidence_location"],
                "additionalProperties": False
            }
        }
    },
    "required": ["missed_parameters"],
    "additionalProperties": False
}

# Schema for new parameters discovery (task2_new_params.txt)
NEW_PARAMS_SCHEMA = {
    "type": "object",
    "properties": {
        "new_parameters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "parameter_name": {"type": "string"},
                    "description": {"type": "string"},
                    "category": {"type": "string"},
                    "evidence": {"type": "string"},
                    "evidence_location": {"type": "string"},
                    "example_values": {"type": "array", "items": {"type": "string"}},
                    "units": {"type": "string"},
                    "prevalence": {"type": "string"},
                    "importance": {"type": "string"},
                    "mapping_suggestion": {"type": "string"},
                    "hed_hint": {"type": "string"}
                },
                "required": ["parameter_name", "description", "category", "evidence", "evidence_location"],
                "additionalProperties": False
            }
        }
    },
    "required": ["new_parameters"],
    "additionalProperties": False
}