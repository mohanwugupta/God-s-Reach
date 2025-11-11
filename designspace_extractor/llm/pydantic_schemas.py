"""
Pydantic models for Outlines structured generation.
These models provide stronger type enforcement than JSON schemas.
Compatible with Outlines v0.1.2+
"""

from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


# ==================== VERIFICATION MODELS ====================

class VerificationResult(BaseModel):
    """Single parameter verification result."""
    verified: bool = Field(..., description="Whether the parameter value is verified as correct")
    value: Optional[Union[str, int, float, bool, List[Any]]] = Field(None, description="The verified value (if applicable)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    evidence: str = Field(..., description="Direct quote from the paper supporting this verification")
    reasoning: str = Field("", description="Explanation of the verification decision")
    abstained: bool = Field(False, description="Whether the verifier chose to abstain from making a decision")
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0 and 1")
        return v


class VerificationBatchResponse(BaseModel):
    """Response for batch verification of multiple parameters."""
    parameters: dict[str, VerificationResult] = Field(..., description="Dictionary mapping parameter names to verification results")
    
    class Config:
        # Allow extra fields for flexibility
        extra = "allow"


class VerificationSingleResponse(BaseModel):
    """Response for single parameter verification."""
    verified: bool = Field(..., description="Whether the parameter value is verified as correct")
    value: Optional[Union[str, int, float, bool, List[Any]]] = Field(None, description="The verified value (if applicable)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    evidence: str = Field(..., description="Direct quote from the paper supporting this verification")
    reasoning: str = Field("", description="Explanation of the verification decision")
    abstained: bool = Field(False, description="Whether the verifier chose to abstain from making a decision")
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0 and 1")
        return v


# ==================== PARAMETER EXTRACTION MODELS ====================

class MissedParameter(BaseModel):
    """A parameter that was missed by the extractor but found in the paper."""
    parameter_name: str = Field(..., description="Name of the missed parameter from the schema")
    value: Union[str, int, float, bool, List[Any]] = Field(..., description="The value found in the paper")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in this extraction (0-1)")
    evidence: str = Field(..., description="Direct quote from the paper containing this parameter")
    evidence_location: str = Field(..., description="Section where evidence was found (e.g., Methods, Results)")
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0 and 1")
        return v


class MissedParametersResponse(BaseModel):
    """Response for task 1: finding missed parameters from the schema."""
    missed_parameters: List[MissedParameter] = Field(default_factory=list, description="List of parameters from the schema that were missed by the extractor")


class NewParameter(BaseModel):
    """A novel parameter discovered that's not in the current schema."""
    parameter_name: str = Field(..., description="Descriptive name for the new parameter")
    description: str = Field(..., description="Clear description of what this parameter measures/represents")
    category: str = Field(..., description="Category this parameter belongs to (e.g., demographics, task_design, stimuli)")
    evidence: str = Field(..., description="Direct quote from the paper describing this parameter")
    evidence_location: str = Field(..., description="Section where evidence was found")
    example_values: List[str] = Field(default_factory=list, description="Example values from the paper")
    units: Optional[str] = Field(None, description="Units of measurement if applicable")
    prevalence: Optional[str] = Field(None, description="How common this parameter might be across studies (low/medium/high)")
    importance: Optional[str] = Field(None, description="Importance for replication (low/medium/high)")
    mapping_suggestion: Optional[str] = Field(None, description="Suggestion for which existing schema section this should map to")
    hed_hint: Optional[str] = Field(None, description="HED (Hierarchical Event Descriptor) tag suggestion if applicable")


class NewParametersResponse(BaseModel):
    """Response for task 2: discovering new parameters not in the schema."""
    new_parameters: List[NewParameter] = Field(default_factory=list, description="List of novel parameters discovered in the paper")


# ==================== HELPER FUNCTIONS ====================

def get_pydantic_model(task_type: str) -> type[BaseModel]:
    """
    Get the appropriate Pydantic model for a given task type.
    
    Args:
        task_type: One of 'missed_params', 'new_params', 'verify_single', 'verify_batch'
        
    Returns:
        Pydantic model class
        
    Raises:
        ValueError: If task_type is not recognized
    """
    models = {
        'missed_params': MissedParametersResponse,
        'new_params': NewParametersResponse,
        'verify_single': VerificationSingleResponse,
        'verify_batch': VerificationBatchResponse,
    }
    
    if task_type not in models:
        raise ValueError(f"Unknown task type: {task_type}. Must be one of {list(models.keys())}")
    
    return models[task_type]


def validate_and_parse(response_text: str, task_type: str) -> Union[BaseModel, dict]:
    """
    Validate and parse LLM response using the appropriate Pydantic model.
    
    Args:
        response_text: Raw JSON string from LLM
        task_type: Type of task (determines which model to use)
        
    Returns:
        Parsed Pydantic model instance or dict
        
    Raises:
        ValueError: If validation fails
    """
    import json
    
    model_class = get_pydantic_model(task_type)
    
    # Parse JSON
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    
    # Validate with Pydantic
    try:
        return model_class(**data)
    except Exception as e:
        raise ValueError(f"Pydantic validation failed: {e}")
