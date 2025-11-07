"""
Base classes for LLM-assisted parameter extraction.

Defines structured output types for Stage 2 (verification) and Stage 3 (discovery).
"""
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Literal


@dataclass
class ParameterProposal:
    """Structured proposal for a new parameter from LLM discovery (Stage 3)."""
    parameter_name: str
    description: str
    category: Literal['demographics', 'task_design', 'perturbation', 'feedback', 
                     'equipment', 'outcome', 'trials', 'context']
    evidence: str  # Verbatim quote
    evidence_location: str  # page/line/section
    example_values: List[str]  # Both normalized and raw
    units: Optional[str]
    prevalence: Literal['low', 'medium', 'high']
    importance: Literal['low', 'medium', 'high']
    mapping_suggestion: str  # Closest existing key or "new"
    hed_hint: Optional[str]  # HED tag suggestion if event-like
    confidence: float  # 0-1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)


@dataclass
class LLMInferenceResult:
    """Structured result from LLM inference with full provenance (Stage 2)."""
    value: Any
    confidence: float
    evidence: str  # Verbatim quote supporting the inference
    evidence_location: str  # Page/section/line reference
    reasoning: str  # Brief explanation of inference
    source_type: str = 'llm_inference'
    method: str = 'llm_verify'
    llm_provider: str = ''
    llm_model: str = ''
    requires_review: bool = True
    abstained: bool = False  # True if LLM explicitly abstained
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)
