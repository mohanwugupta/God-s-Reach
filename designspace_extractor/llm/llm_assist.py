"""
LLM-assisted parameter extraction with three-stage policy.

Stage 1: Deterministic extraction (rules/regex/AST) - handled by extractors
Stage 2: LLM verify/fallback - low-confidence or missing critical fields
Stage 3: LLM discovery - propose new parameters, never overwrite

Implements evidence-based inference with full provenance tracking.

This module orchestrates the three-stage extraction policy using modular components:
- providers: LLM provider initialization (Claude, OpenAI, Qwen, local vLLM)
- inference: Stage 2 verification and fallback inference
- discovery: Stage 3 parameter discovery
- prompt_builder: Prompt construction from templates
- response_parser: LLM response parsing and validation
- base: Shared dataclasses (ParameterProposal, LLMInferenceResult)
"""
import os
import logging
from typing import Dict, Any, Optional, List, Literal

from .base import ParameterProposal, LLMInferenceResult
from .providers import create_provider, LLMProvider
from .inference import VerificationEngine
from .discovery import DiscoveryEngine

logger = logging.getLogger(__name__)


class LLMAssistant:
    """
    LLM-assisted extraction orchestrator with three-stage policy.
    
    Coordinates verification and discovery engines using modular components.
    """
    
    def __init__(self, provider_name: str = 'claude', model: str = None, 
                 temperature: float = 0.0,
                 mode: Literal['verify', 'fallback', 'discover'] = 'verify'):
        """
        Initialize LLM assistant.
        
        Args:
            provider_name: LLM provider (claude, openai, qwen, local)
            model: Model name (default: from env or provider default)
            temperature: Sampling temperature (default: 0.0 per policy)
            mode: Extraction mode (verify=check all, fallback=only low-confidence, discover=propose new)
        """
        self.provider_name = provider_name
        self.model_name = model
        self.temperature = temperature
        self.mode = mode
        self.enabled = os.getenv('LLM_ENABLE', 'false').lower() == 'true'
        self.budget_usd = float(os.getenv('LLM_BUDGET_USD', '10.0'))
        self.current_spend = 0.0
        
        # Confidence thresholds per policy
        self.verify_threshold = float(os.getenv('LLM_VERIFY_THRESHOLD', '0.3'))
        self.accept_threshold = float(os.getenv('LLM_ACCEPT_THRESHOLD', '0.7'))
        
        # Critical parameters that always get LLM verification if missing/low-confidence
        self.critical_params = set([
            'sample_size_n', 'perturbation_class', 'perturbation_magnitude',
            'rotation_magnitude_deg', 'adaptation_trials', 'baseline_trials',
            'effector', 'environment', 'feedback_type'
        ])
        
        # Initialize LLM provider and engines
        self.llm_provider: Optional[LLMProvider] = None
        self.verification_engine: Optional[VerificationEngine] = None
        self.discovery_engine: Optional[DiscoveryEngine] = None
        
        if not self.enabled:
            logger.info("LLM assistance is disabled (set LLM_ENABLE=true to enable)")
            return
        
        # Create and initialize provider
        try:
            self.llm_provider = create_provider(
                provider=provider_name,
                model=model
            )
            
            if not self.llm_provider:
                logger.error("Failed to create LLM provider")
                self.enabled = False
                return
            
            # Initialize engines
            self.verification_engine = VerificationEngine(
                provider=self.llm_provider,
                confidence_threshold=self.accept_threshold,
                require_evidence=True,
                min_evidence_length=20
            )
            
            self.discovery_engine = DiscoveryEngine(
                provider=self.llm_provider,
                min_evidence_length=20,
                max_proposals=10
            )
            
            logger.info(f"LLM assistant initialized: {provider_name}/{self.llm_provider.model_name} in {mode} mode")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM assistant: {e}")
            self.enabled = False
    
    def should_verify(self, extracted_params: Dict[str, Any], 
                     missing_params: List[str]) -> bool:
        """
        Gate function to determine if LLM verification should run (Stage 2 gate).
        
        Args:
            extracted_params: Parameters extracted by deterministic methods
            missing_params: List of missing parameter names
            
        Returns:
            True if LLM should be used for verification/fallback
        """
        if not self.enabled or not self.verification_engine:
            return False
        
        if self.mode == 'discover':
            return False  # Discovery mode doesn't use verification
        
        # Delegate to verification engine's gate
        total_expected = len(extracted_params) + len(missing_params)
        return self.verification_engine.should_verify(
            extracted_params=extracted_params,
            num_missing=len(missing_params),
            total_expected=total_expected
        )
    
    def verify_and_infer(self, extracted_params: Dict[str, Any],
                        missing_params: List[str], context: str,
                        study_type: str, num_experiments: int) -> Dict[str, LLMInferenceResult]:
        """
        Stage 2: Verify extracted parameters and infer missing ones.
        
        Args:
            extracted_params: Deterministically extracted parameters
            missing_params: List of missing parameter names
            context: Paper content
            study_type: Type of study (between/within/mixed)
            num_experiments: Number of experiments
            
        Returns:
            Dict mapping parameter names to LLMInferenceResult
        """
        if not self.enabled or not self.verification_engine:
            logger.warning("LLM verification not available")
            return {}
        
        return self.verification_engine.verify_and_fallback(
            extracted_params=extracted_params,
            missing_params=missing_params,
            context=context,
            study_type=study_type,
            num_experiments=num_experiments
        )
    
    def discover_new_parameters(self, context: str, study_type: str,
                               num_experiments: int,
                               already_extracted: Optional[Dict[str, Any]] = None) -> List[ParameterProposal]:
        """
        Stage 3: Discover new parameters from paper content.
        
        Args:
            context: Paper content
            study_type: Type of study
            num_experiments: Number of experiments
            already_extracted: Parameters already extracted (to avoid duplicates)
            
        Returns:
            List of ParameterProposal objects
        """
        if not self.enabled or not self.discovery_engine:
            logger.warning("LLM discovery not available")
            return []
        
        return self.discovery_engine.discover_parameters(
            context=context,
            study_type=study_type,
            num_experiments=num_experiments,
            already_extracted=already_extracted
        )
    
    def export_proposals_csv(self, proposals: List[ParameterProposal], output_path: str) -> None:
        """Export discovery proposals to CSV for review."""
        if not self.discovery_engine:
            logger.error("Discovery engine not initialized")
            return
        
        self.discovery_engine.export_proposals_csv(proposals, output_path)
    
    def export_proposals_json(self, proposals: List[ParameterProposal], 
                             output_path: str, include_metadata: bool = True) -> None:
        """Export discovery proposals to JSON format."""
        if not self.discovery_engine:
            logger.error("Discovery engine not initialized")
            return
        
        self.discovery_engine.export_proposals_json(proposals, output_path, include_metadata)
    
    def filter_by_prevalence(self, proposals: List[ParameterProposal],
                            min_prevalence: str = 'medium') -> List[ParameterProposal]:
        """Filter proposals by minimum prevalence level."""
        if not self.discovery_engine:
            return proposals
        
        return self.discovery_engine.filter_proposals_by_prevalence(proposals, min_prevalence)
    
    def filter_by_importance(self, proposals: List[ParameterProposal],
                            min_importance: str = 'medium') -> List[ParameterProposal]:
        """Filter proposals by minimum importance level."""
        if not self.discovery_engine:
            return proposals
        
        return self.discovery_engine.filter_proposals_by_importance(proposals, min_importance)


# Export key classes for backward compatibility
__all__ = ['LLMAssistant', 'ParameterProposal', 'LLMInferenceResult']
