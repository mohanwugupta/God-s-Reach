"""
Stage 2 LLM Verification - Verify and fallback inference.

Handles batch and single-parameter verification with evidence requirements.
"""
import logging
from typing import Dict, Any, List, Optional

from .base import LLMInferenceResult
from .providers import LLMProvider
from .prompt_builder import PromptBuilder
from .response_parser import ResponseParser

logger = logging.getLogger(__name__)


class VerificationEngine:
    """
    Stage 2 verification engine.
    
    Verifies deterministically extracted parameters or performs fallback inference.
    """
    
    def __init__(self, provider: LLMProvider, 
                 confidence_threshold: float = 0.7,
                 require_evidence: bool = True,
                 min_evidence_length: int = 20):
        """
        Initialize verification engine.
        
        Args:
            provider: Initialized LLM provider
            confidence_threshold: Threshold for auto-acceptance
            require_evidence: Whether to require evidence quotes
            min_evidence_length: Minimum character length for evidence
        """
        self.provider = provider
        self.confidence_threshold = confidence_threshold
        self.require_evidence = require_evidence
        self.min_evidence_length = min_evidence_length
        
        self.prompt_builder = PromptBuilder()
        self.response_parser = ResponseParser(accept_threshold=confidence_threshold)
    
    def should_verify(self, extracted_params: Dict[str, Any], 
                     num_missing: int, total_expected: int) -> bool:
        """
        Gate function to decide if LLM verification should run.
        
        Args:
            extracted_params: Parameters extracted by deterministic methods
            num_missing: Number of missing critical parameters
            total_expected: Total number of expected parameters
            
        Returns:
            True if LLM should be used for verification/fallback
        """
        # Policy: Use LLM if >30% parameters missing
        if total_expected == 0:
            return False
        
        missing_rate = num_missing / total_expected
        should_run = missing_rate > 0.3
        
        logger.info(f"Verification gate: {num_missing}/{total_expected} missing ({missing_rate:.1%}), "
                   f"should_verify={should_run}")
        
        return should_run
    
    def verify_batch(self, extracted_params: Dict[str, Any], context: str,
                    study_type: str, num_experiments: int) -> Dict[str, LLMInferenceResult]:
        """
        Verify a batch of extracted parameters.
        
        Args:
            extracted_params: Parameters to verify
            context: Paper content
            study_type: Type of study
            num_experiments: Number of experiments
            
        Returns:
            Dict mapping parameter names to LLMInferenceResult
        """
        if not extracted_params:
            logger.warning("No parameters to verify")
            return {}
        
        # Build prompt
        prompt = self.prompt_builder.build_batch_verification_prompt(
            extracted_params=extracted_params,
            context=context,
            study_type=study_type,
            num_experiments=num_experiments
        )
        
        logger.info(f"Verifying {len(extracted_params)} parameters with {self.provider.provider_name}")
        
        # Generate response
        response = self.provider.generate(
            prompt=prompt,
            max_tokens=4096,
            temperature=0.0
        )
        
        if not response:
            logger.error("No response from LLM")
            return {}
        
        # Parse response
        parameter_names = list(extracted_params.keys())
        results = self.response_parser.parse_verification_response(
            response=response,
            parameter_names=parameter_names,
            require_evidence=self.require_evidence,
            provider=self.provider.provider_name,
            model=self.provider.model_name
        )
        
        return results
    
    def infer_single(self, parameter_name: str, context: str,
                    description: str = "") -> Optional[LLMInferenceResult]:
        """
        Infer a single missing parameter.
        
        Args:
            parameter_name: Parameter to infer
            context: Paper content
            description: Parameter description
            
        Returns:
            LLMInferenceResult or None
        """
        # Build prompt
        prompt = self.prompt_builder.build_single_parameter_prompt(
            parameter_name=parameter_name,
            context=context,
            description=description
        )
        
        logger.info(f"Inferring {parameter_name} with {self.provider.provider_name}")
        
        # Generate response
        response = self.provider.generate(
            prompt=prompt,
            max_tokens=2048,
            temperature=0.0
        )
        
        if not response:
            logger.error("No response from LLM")
            return None
        
        # Parse response
        result = self.response_parser.parse_single_parameter_response(
            response=response,
            parameter_name=parameter_name,
            provider=self.provider.provider_name,
            model=self.provider.model_name
        )
        
        return result
    
    def verify_and_fallback(self, extracted_params: Dict[str, Any],
                           missing_params: List[str], context: str,
                           study_type: str, num_experiments: int) -> Dict[str, LLMInferenceResult]:
        """
        Combined verification and fallback inference.
        
        First verifies extracted parameters, then attempts to infer missing ones.
        
        Args:
            extracted_params: Deterministically extracted parameters
            missing_params: List of missing parameter names
            context: Paper content
            study_type: Type of study
            num_experiments: Number of experiments
            
        Returns:
            Combined dict of verified and inferred results
        """
        all_results = {}
        
        # Verify extracted parameters
        if extracted_params:
            verified = self.verify_batch(
                extracted_params=extracted_params,
                context=context,
                study_type=study_type,
                num_experiments=num_experiments
            )
            all_results.update(verified)
        
        # Fallback inference for missing parameters
        if missing_params:
            logger.info(f"Attempting fallback inference for {len(missing_params)} missing parameters")
            for param_name in missing_params:
                result = self.infer_single(
                    parameter_name=param_name,
                    context=context
                )
                if result:
                    all_results[param_name] = result
        
        return all_results
