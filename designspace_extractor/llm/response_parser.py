"""
Response parsing for LLM outputs.

Handles JSON extraction, cleaning, and validation for both verification and discovery.
"""
import json
import re
import logging
from typing import Dict, Any, List, Optional

from .base import ParameterProposal, LLMInferenceResult

logger = logging.getLogger(__name__)


class ResponseParser:
    """Parse and validate LLM responses."""
    
    def __init__(self, accept_threshold: float = 0.7):
        """
        Initialize parser.
        
        Args:
            accept_threshold: Confidence threshold for auto-acceptance
        """
        self.accept_threshold = accept_threshold
    
    def parse_verification_response(self, response: str, parameter_names: List[str],
                                   require_evidence: bool, provider: str, model: str) -> Dict[str, LLMInferenceResult]:
        """
        Parse batch verification response with evidence validation.
        
        Args:
            response: Raw LLM response
            parameter_names: Expected parameter names
            require_evidence: Whether evidence is required
            provider: LLM provider name
            model: LLM model name
            
        Returns:
            Dict mapping parameter names to LLMInferenceResult objects
        """
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                logger.error("No JSON in LLM response")
                return {}
            
            data = json.loads(response[json_start:json_end])
            
            results = {}
            for param_name in parameter_names:
                if param_name not in data:
                    continue
                
                param_data = data[param_name]
                
                # Skip if abstained
                if param_data.get('abstained', False):
                    logger.debug(f"LLM abstained on {param_name}: {param_data.get('reasoning', 'no reason')}")
                    continue
                
                # Validate evidence if required
                evidence = param_data.get('evidence', '').strip()
                if require_evidence and len(evidence) < 20:
                    logger.warning(f"Insufficient evidence for {param_name} (len={len(evidence)}), skipping")
                    continue
                
                value = param_data.get('value')
                if value is None:
                    continue
                
                confidence = param_data.get('confidence', 0.5)
                
                results[param_name] = LLMInferenceResult(
                    value=value,
                    confidence=confidence,
                    evidence=evidence,
                    evidence_location=param_data.get('evidence_location', ''),
                    reasoning=param_data.get('reasoning', ''),
                    source_type='llm_inference',
                    method='llm_verify',
                    llm_provider=provider,
                    llm_model=model,
                    requires_review=confidence < self.accept_threshold,
                    abstained=False
                )
            
            logger.info(f"Verified {len(results)}/{len(parameter_names)} parameters with evidence")
            return results
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return {}
    
    def parse_discovery_response(self, response: str, min_evidence_length: int) -> List[ParameterProposal]:
        """
        Parse discovery response and validate proposals.
        
        Args:
            response: Raw LLM response
            min_evidence_length: Minimum character length for evidence
            
        Returns:
            List of validated ParameterProposal objects
        """
        try:
            # Remove markdown code blocks if present
            content = response.strip()
            if content.startswith('```'):
                lines = content.split('\n')
                content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content
                if content.startswith('json'):
                    content = content[4:].strip()
            
            proposals_data = json.loads(content)
            
            if not isinstance(proposals_data, list):
                logger.error("Discovery response is not a JSON array")
                return []
            
            proposals = []
            for data in proposals_data:
                # Validate evidence
                evidence = data.get('evidence', '').strip()
                if len(evidence) < min_evidence_length:
                    logger.debug(f"Skipping proposal {data.get('parameter_name')} - insufficient evidence")
                    continue
                
                # Estimate confidence from prevalence and importance
                prevalence_score = {'low': 0.3, 'medium': 0.6, 'high': 0.9}.get(data.get('prevalence', 'low'), 0.5)
                importance_score = {'low': 0.3, 'medium': 0.6, 'high': 0.9}.get(data.get('importance', 'low'), 0.5)
                confidence = (prevalence_score + importance_score) / 2
                
                proposal = ParameterProposal(
                    parameter_name=data['parameter_name'],
                    description=data['description'],
                    category=data['category'],
                    evidence=evidence,
                    evidence_location=data.get('evidence_location', ''),
                    example_values=data.get('example_values', []),
                    units=data.get('units'),
                    prevalence=data.get('prevalence', 'low'),
                    importance=data.get('importance', 'low'),
                    mapping_suggestion=data.get('mapping_suggestion', 'new'),
                    hed_hint=data.get('hed_hint'),
                    confidence=confidence
                )
                proposals.append(proposal)
            
            # Sort by importance then prevalence
            importance_order = {'high': 3, 'medium': 2, 'low': 1}
            proposals.sort(
                key=lambda p: (importance_order.get(p.importance, 0), importance_order.get(p.prevalence, 0)),
                reverse=True
            )
            
            return proposals
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse discovery response: {e}")
            return []
    
    def parse_single_parameter_response(self, response: str, parameter_name: str,
                                       provider: str, model: str) -> Optional[LLMInferenceResult]:
        """
        Parse single parameter inference response.
        
        Args:
            response: Raw LLM response
            parameter_name: Parameter name
            provider: LLM provider
            model: LLM model
            
        Returns:
            LLMInferenceResult or None
        """
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                logger.error("No JSON found in LLM response")
                return None
            
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            
            if data.get('value') is None:
                return None
            
            confidence = data.get('confidence', 0.5)
            return LLMInferenceResult(
                value=data['value'],
                confidence=confidence,
                evidence=data.get('evidence', ''),
                evidence_location=data.get('evidence_location', ''),
                reasoning=data.get('reasoning', ''),
                source_type='llm_inference',
                method='llm_inference',
                llm_provider=provider,
                llm_model=model,
                requires_review=confidence < self.accept_threshold,
                abstained=False
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return None
