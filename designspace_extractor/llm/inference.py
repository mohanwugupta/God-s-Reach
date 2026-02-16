"""
Stage 2 LLM Verification - Verify and fallback inference.

Handles batch and single-parameter verification with evidence requirements.
"""
import logging
from typing import Dict, Any, List, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .base import LLMInferenceResult
from .providers import LLMProvider
from .prompt_builder import PromptBuilder
from .response_parser import ResponseParser
from .schemas import VERIFICATION_BATCH_SCHEMA, VERIFICATION_SINGLE_SCHEMA, MISSED_PARAMS_SCHEMA
from .pydantic_schemas import (
    VerificationBatchResponse, 
    VerificationSingleResponse, 
    MissedParametersResponse,
    get_pydantic_model
)

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
        self._batch_size = 4  # Default batch size for concurrent requests
    
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
        
        # Generate response with Pydantic model for stronger constraints
        response = self.provider.generate(
            prompt=prompt,
            max_tokens=1024,
            temperature=0.0,
            output_type=VerificationBatchResponse,  # Use Pydantic model (preferred)
            schema=VERIFICATION_BATCH_SCHEMA,  # Fallback to JSON schema
            task_type="verify_batch"
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
            model=self.provider.model_name,
            llm_provider=self.provider
        )
        
        return results
    
    def verify_parameters_batched(self, experiments_params: List[Dict[str, Any]], 
                                 context: str, batch_size: int = None) -> List[Dict[str, Any]]:
        """
        Verify parameters for multiple experiments using batched requests.
        
        Args:
            experiments_params: List of extracted parameters for each experiment
            context: Full paper context
            batch_size: Number of concurrent requests (default: self._batch_size)
            
        Returns:
            List of verification results for each experiment
        """
        batch_size = batch_size or self._batch_size
        logger.info(f"Batching verification for {len(experiments_params)} experiments (batch_size={batch_size})")
        
        # Process experiments in batches to avoid overloading LLM
        results = []
        for i in range(0, len(experiments_params), batch_size):
            batch_experiments = experiments_params[i:i + batch_size]
            
            # Use ThreadPoolExecutor for I/O-bound LLM requests
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures = [
                    executor.submit(self.verify_parameters, exp_params, context, exp_idx + i + 1)
                    for exp_idx, exp_params in enumerate(batch_experiments)
                ]
                
                batch_results = [future.result() for future in futures]
                results.extend(batch_results)
                
            logger.info(f"Completed batch {i//batch_size + 1}/{(len(experiments_params) + batch_size - 1)//batch_size}")
        
        return results
    
    def infer_missing_parameters_batched(self, experiments: List[Dict[str, Any]], 
                                       context: str, batch_size: int = None) -> List[Dict[str, Any]]:
        """
        Batch inference of missing parameters across multiple experiments.
        
        Args:
            experiments: List of experiment data
            context: Full paper context
            batch_size: Concurrent request limit
            
        Returns:
            List of missing parameter results for each experiment
        """
        batch_size = batch_size or self._batch_size
        logger.info(f"Batching missing parameter inference for {len(experiments)} experiments")
        
        results = []
        for i in range(0, len(experiments), batch_size):
            batch_experiments = experiments[i:i + batch_size]
            
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures = [
                    executor.submit(self._infer_missing_for_experiment, exp, context, exp_idx + i + 1)
                    for exp_idx, exp in enumerate(batch_experiments)
                ]
                
                batch_results = [future.result() for future in futures]
                results.extend(batch_results)
        
        return results
    
    def _infer_missing_for_experiment(self, experiment: Dict[str, Any], 
                                    context: str, exp_num: int) -> Dict[str, Any]:
        """
        Helper method to infer missing parameters for a single experiment.
        """
        try:
            # This would call your existing missing parameter inference logic
            # Implementation depends on your current structure
            logger.info(f"Inferring missing parameters for experiment {exp_num}")
            
            # Placeholder - replace with actual missing parameter logic
            missing_params = self.infer_missing_parameters(
                experiment.get('parameters', {}),
                context,
                experiment.get('content', '')
            )
            
            return {
                'experiment_num': exp_num,
                'missing_parameters': missing_params,
                'success': True
            }
        except Exception as e:
            logger.error(f"Failed to infer missing parameters for experiment {exp_num}: {e}")
            return {
                'experiment_num': exp_num,
                'missing_parameters': {},
                'success': False,
                'error': str(e)
            }
    
    def set_batch_size(self, batch_size: int):
        """Set the batch size for concurrent LLM requests."""
        self._batch_size = max(1, min(batch_size, 8))  # Limit to reasonable range
        logger.info(f"LLM batch size set to {self._batch_size}")
    
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
        
        # Generate response with Pydantic model for stronger constraints
        response = self.provider.generate(
            prompt=prompt,
            max_tokens=512,
            temperature=0.0,
            output_type=VerificationSingleResponse,  # Use Pydantic model (preferred)
            schema=VERIFICATION_SINGLE_SCHEMA,  # Fallback to JSON schema
            task_type="verify_single"
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
                           study_type: str, num_experiments: int,
                           current_schema: Optional[Dict[str, Any]] = None) -> Dict[str, LLMInferenceResult]:
        """
        Combined verification and fallback inference with Task 1 integration.
        
        Workflow:
        1. Verify extracted parameters (if any)
        2. Run Task 1: Find missed library parameters
        3. Fallback inference for remaining missing parameters
        
        Args:
            extracted_params: Deterministically extracted parameters
            missing_params: List of missing parameter names
            context: Paper content
            study_type: Type of study
            num_experiments: Number of experiments
            current_schema: Current parameter schema (for Task 1)
            
        Returns:
            Combined dict of verified, Task 1 found, and inferred results
        """
        all_results = {}
        
        # Step 1: Verify extracted parameters
        if extracted_params:
            verified = self.verify_batch(
                extracted_params=extracted_params,
                context=context,
                study_type=study_type,
                num_experiments=num_experiments
            )
            all_results.update(verified)
        
        # Step 2: Task 1 - Find missed library parameters
        if current_schema:
            logger.info("Running Task 1: Finding missed library parameters")
            missed_params = self.find_missed_library_params(
                current_schema=current_schema,
                already_extracted=extracted_params,
                context=context
            )
            if missed_params:
                logger.info(f"Task 1 found {len(missed_params)} missed parameters")
                all_results.update(missed_params)
        
        # Step 3: Fallback inference for remaining missing parameters
        # Filter out parameters found in Task 1
        remaining_missing = [p for p in missing_params if p not in all_results]
        
        if remaining_missing:
            logger.info(f"Attempting fallback inference for {len(remaining_missing)} remaining missing parameters")
            for param_name in remaining_missing:
                result = self.infer_single(
                    parameter_name=param_name,
                    context=context
                )
                if result:
                    all_results[param_name] = result
        
        return all_results
    
    def find_missed_library_params(self, current_schema: Dict[str, Any],
                                   already_extracted: Dict[str, Any],
                                   context: str) -> Dict[str, LLMInferenceResult]:
        """
        Task 1: Find parameters from the library that regex extraction missed.
        
        Args:
            current_schema: Current parameter library/schema
            already_extracted: Parameters already extracted by regex
            context: Paper content
            
        Returns:
            Dict mapping missed parameter names to LLMInferenceResult
        """
        # DIAGNOSTIC: Log context length
        context_length = len(context)
        logger.info(f"Task 1: Context length = {context_length} chars, Already extracted = {len(already_extracted)} params")
        
        if context_length < 3000:
            logger.warning(f"⚠️  Task 1: Context very short ({context_length} chars), may affect results")
        
        # Build Task 1 prompt
        prompt = self.prompt_builder.build_missed_params_prompt(
            current_schema=current_schema,
            already_extracted=already_extracted,
            context=context
        )
        
        logger.info(f"Running Task 1: Finding missed library parameters")
        logger.debug(f"Task 1 prompt length: {len(prompt)} chars")
        
        # Generate response with Pydantic model for stronger constraints
        # INCREASED TEMPERATURE from 0.0 → 0.3 → 0.6 for more liberal parameter discovery
        # Higher temperature allows the LLM to be more creative and find more parameters
        # Task 2 (verification) stays at 0.3 for more conservative validation
        response = self.provider.generate(
            prompt=prompt,
            max_tokens=1536,
            temperature=0.6,  # LIBERAL: encourage finding parameters
            output_type=MissedParametersResponse,  # Use Pydantic model (preferred)
            schema=MISSED_PARAMS_SCHEMA,  # Fallback to JSON schema
            task_type="missed_params"
        )
        
        if not response:
            logger.error("❌ No response from LLM for Task 1")
            return {}
        
        # DIAGNOSTIC: Log raw response
        response_preview = response[:500] if len(response) > 500 else response
        logger.debug(f"Task 1 raw response (first 500 chars): {response_preview}")
        
        # Parse Task 1 response
        results = self.response_parser.parse_task1_response(
            response=response,
            require_evidence=self.require_evidence,
            provider=self.provider.provider_name,
            model=self.provider.model_name
        )
        
        # DIAGNOSTIC: Enhanced logging
        if not results:
            logger.warning(f"⚠️  Task 1 returned 0 parameters (LLM may have returned empty array)")
            logger.debug(f"Full response for debugging: {response[:1000]}")
        else:
            logger.info(f"✅ Task 1 found {len(results)} missed parameters: {list(results.keys())}")
        
        return results
