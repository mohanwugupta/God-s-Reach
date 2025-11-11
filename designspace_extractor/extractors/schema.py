"""
Pydantic schemas for structured parameter extraction.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any


class ExtractedParams(BaseModel):
    """Structured schema for extracted experimental parameters."""
    sample_size: Optional[int] = Field(None, description="Total participants (N).")
    rotation_magnitude_deg: Optional[float] = Field(None, description="Rotation magnitude in degrees.")
    adaptation_trials: Optional[int] = Field(None, description="Number of adaptation trials.")
    num_blocks: Optional[int] = Field(None, description="Number of experimental blocks.")
    age_mean_years: Optional[float] = Field(None, description="Mean age in years.")
    manipulandum_type: Optional[str] = Field(None, description="Type of manipulandum used.")
    perturbation_type: Optional[str] = Field(None, description="Type of perturbation (visuomotor, force field, etc.).")
    feedback_type: Optional[str] = Field(None, description="Type of feedback provided.")
    handedness_criteria: Optional[str] = Field(None, description="Handedness inclusion criteria.")
    num_trials: Optional[int] = Field(None, description="Total number of trials.")
    baseline_trials: Optional[int] = Field(None, description="Number of baseline trials.")
    training_trials: Optional[int] = Field(None, description="Number of training trials.")
    movement_time_ms: Optional[float] = Field(None, description="Movement time in milliseconds.")
    feedback_delay_ms: Optional[float] = Field(None, description="Feedback delay in milliseconds.")
    trial_duration_ms: Optional[float] = Field(None, description="Trial duration in milliseconds.")
    age_range: Optional[str] = Field(None, description="Age range of participants.")
    gender_composition: Optional[str] = Field(None, description="Gender composition (e.g., '10F/10M').")


class Evidence(BaseModel):
    """Evidence for a parameter extraction."""
    page: int
    quote: str
    box: Optional[List[float]] = None  # [x0, y0, x1, y1]
    method: str  # "regex", "rag_llm", "ocr+regex", "camelot"


class ParameterWithEvidence(BaseModel):
    """Parameter with value, confidence, and evidence."""
    value: Any
    confidence: float
    evidence: List[Evidence]


# JSON schema for LLM structured outputs
PARAM_SCHEMA = ExtractedParams.model_json_schema()
