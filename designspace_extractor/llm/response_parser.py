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
                                   require_evidence: bool, provider: str, model: str,
                                   llm_provider=None) -> Dict[str, LLMInferenceResult]:
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
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}. Attempting auto-fix...")
            
            # Try to auto-fix malformed JSON by asking LLM to correct it
            fixed_response = self._auto_fix_json_response(response, parameter_names, llm_provider)
            if fixed_response:
                try:
                    json_start = fixed_response.find('{')
                    json_end = fixed_response.rfind('}') + 1
                    if json_start != -1 and json_end > 0:
                        data = json.loads(fixed_response[json_start:json_end])
                        logger.info("JSON auto-fix successful")
                    else:
                        logger.error("Auto-fix failed: no valid JSON found")
                        return {}
                except json.JSONDecodeError as e2:
                    logger.error(f"Auto-fix failed: {e2}")
                    return {}
            else:
                logger.error("JSON auto-fix failed: no response from LLM")
                return {}
        
        # Process the parsed JSON data
        try:
            results = {}
            for param_name in parameter_names:
                if param_name not in data:
                    continue
                
                param_data = data[param_name]
                
                # Skip if abstained
                if param_data.get('abstained', False):
                    logger.debug(f"LLM abstained on {param_name}: {param_data.get('reasoning', 'no reason')}")
                    continue
                
                # Get evidence (accept any non-empty evidence if required)
                evidence = param_data.get('evidence', '').strip()
                if require_evidence and not evidence:
                    logger.warning(f"No evidence provided for {param_name}, skipping")
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
            
        except KeyError as e:
            logger.error(f"Missing required field in verification response: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error processing verification response: {e}")
            return {}
    
    def parse_discovery_response(self, response: str, min_evidence_length: int) -> List[ParameterProposal]:
        """
        Parse discovery response handling both missed library params and new proposals.
        
        Args:
            response: Raw LLM response (expects {"missed_from_library": [...], "new_parameters": [...]})
            min_evidence_length: Minimum character length for evidence
            
        Returns:
            List of validated ParameterProposal objects (missed params as high-priority proposals)
        """
        try:
            # Remove markdown code blocks if present
            content = response.strip()
            if content.startswith('```'):
                lines = content.split('\n')
                content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content
                if content.startswith('json'):
                    content = content[4:].strip()
            
            data = json.loads(content)
            
            # Handle legacy format (plain array)
            if isinstance(data, list):
                logger.warning("Legacy discovery format detected - treating as new_parameters only")
                data = {"missed_from_library": [], "new_parameters": data}
            
            if not isinstance(data, dict):
                logger.error("Discovery response must be JSON object or array")
                return []
            
            proposals = []
            
            # PRIORITY 1: Process missed library parameters
            missed = data.get('missed_from_library', [])
            for item in missed:
                evidence = item.get('evidence', '').strip()
                if len(evidence) < min_evidence_length:
                    logger.debug(f"Skipping missed param {item.get('parameter_name')} - insufficient evidence")
                    continue
                
                # Create high-priority proposal (library params are proven valuable)
                proposal = ParameterProposal(
                    parameter_name=item['parameter_name'],
                    description=f"MISSED LIBRARY PARAM - extracted value: {item.get('value')}",
                    category='EXTRACTION',  # Flag for special handling
                    evidence=evidence,
                    evidence_location=item.get('evidence_location', ''),
                    example_values=[str(item.get('value'))],
                    units=None,
                    prevalence='high',  # Library params are important
                    importance='high',
                    mapping_suggestion='existing',
                    hed_hint=None,
                    confidence=item.get('confidence', 0.9)
                )
                proposals.append(proposal)
            
            # PRIORITY 2: Process new parameter proposals
            new_params = data.get('new_parameters', [])
            for item in new_params:
                evidence = item.get('evidence', '').strip()
                if len(evidence) < min_evidence_length:
                    logger.debug(f"Skipping new param {item.get('parameter_name')} - insufficient evidence")
                    continue
                
                # Estimate confidence from prevalence and importance
                prevalence_score = {'low': 0.3, 'medium': 0.6, 'high': 0.9}.get(item.get('prevalence', 'low'), 0.5)
                importance_score = {'low': 0.3, 'medium': 0.6, 'high': 0.9}.get(item.get('importance', 'low'), 0.5)
                confidence = (prevalence_score + importance_score) / 2
                
                proposal = ParameterProposal(
                    parameter_name=item['parameter_name'],
                    description=item['description'],
                    category=item['category'],
                    evidence=evidence,
                    evidence_location=item.get('evidence_location', ''),
                    example_values=item.get('example_values', []),
                    units=item.get('units'),
                    prevalence=item.get('prevalence', 'low'),
                    importance=item.get('importance', 'low'),
                    mapping_suggestion=item.get('mapping_suggestion', 'new'),
                    hed_hint=item.get('hed_hint'),
                    confidence=confidence
                )
                proposals.append(proposal)
            
            logger.info(f"Parsed {len(missed)} missed library params + {len(new_params)} new proposals")
            
            # Sort: missed library params first (category='EXTRACTION'), then by importance/prevalence
            importance_order = {'high': 3, 'medium': 2, 'low': 1}
            proposals.sort(
                key=lambda p: (
                    1 if p.category == 'EXTRACTION' else 0,  # Missed params first
                    importance_order.get(p.importance, 0),
                    importance_order.get(p.prevalence, 0)
                ),
                reverse=True
            )
            
            return proposals
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse discovery response: {e}")
            return []
        except KeyError as e:
            logger.error(f"Missing required field in discovery response: {e}")
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
    
    def parse_task1_response(self, response: str, require_evidence: bool,
                            provider: str, model: str) -> Dict[str, LLMInferenceResult]:
        """
        Parse Task 1 response: Missed library parameters.
        
        Expected format:
        {
          "missed_parameters": [
            {
              "parameter_name": "...",
              "value": ...,
              "confidence": 0.95,
              "evidence": "...",
              "evidence_location": "..."
            }
          ]
        }
        
        Args:
            response: Raw LLM response
            require_evidence: Whether evidence is required
            provider: LLM provider name
            model: LLM model name
            
        Returns:
            Dict mapping parameter names to LLMInferenceResult
        """
        # Track filtering statistics for diagnostics
        filtering_stats = {
            'total_candidates': 0,
            'filtered_no_param_name': 0,
            'filtered_no_value': 0,
            'filtered_insufficient_evidence': 0,
            'filtered_low_confidence': 0,
            'filtered_other_error': 0,
            'accepted': 0
        }
        
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                logger.error("No JSON in Task 1 response")
                return {}
            
            data = json.loads(response[json_start:json_end])
            
            missed_params = data.get('missed_parameters', [])
            if not missed_params:
                logger.info("Task 1: No missed parameters found")
                return {}
            
            filtering_stats['total_candidates'] = len(missed_params)
            
            results = {}
            for item in missed_params:
                # Defensive: ensure item is a dict
                if not isinstance(item, dict):
                    logger.warning(f"Task 1: Skipping non-dict item: {type(item)}")
                    filtering_stats['filtered_other_error'] += 1
                    continue
                
                param_name = item.get('parameter_name')
                if not param_name:
                    filtering_stats['filtered_no_param_name'] += 1
                    logger.debug(f"Task 1: Skipping item without parameter_name")
                    continue
                
                value = item.get('value')
                if value is None:
                    filtering_stats['filtered_no_value'] += 1
                    logger.debug(f"Task 1: Skipping {param_name} - no value provided")
                    continue
                
                # ULTRA-RELAXED EVIDENCE REQUIREMENTS for maximum parameter recovery
                # High confidence (≥0.5): Allow very brief evidence (≥3 chars) - e.g., "30°", "N=24"
                # Lower confidence (<0.5): Still relaxed evidence (≥12 chars) - still liberal
                evidence = item.get('evidence', '').strip()
                confidence = item.get('confidence', 0.5)
                
                if require_evidence:
                    min_evidence_length = 3 if confidence >= 0.5 else 12
                    
                    if len(evidence) < min_evidence_length:
                        filtering_stats['filtered_insufficient_evidence'] += 1
                        logger.debug(
                            f"Task 1: Insufficient evidence for {param_name} "
                            f"(confidence={confidence:.2f}, evidence_len={len(evidence)}, "
                            f"required={min_evidence_length})"
                        )
                        continue
                
                try:
                    results[param_name] = LLMInferenceResult(
                        value=value,
                        confidence=confidence,
                        evidence=evidence,
                        evidence_location=item.get('evidence_location', ''),
                        reasoning=f"Found by Task 1: missed library parameter",
                        source_type='llm_task1',
                        method='llm_missed_params',
                        llm_provider=provider,
                        llm_model=model,
                        requires_review=confidence < self.accept_threshold,
                        abstained=False
                    )
                    filtering_stats['accepted'] += 1
                    
                except Exception as e:
                    filtering_stats['filtered_other_error'] += 1
                    logger.warning(f"Task 1: Failed to create result for {param_name}: {e}")
                    continue
            
            # Log summary statistics
            logger.info(
                f"Task 1 filtering: {filtering_stats['accepted']}/{filtering_stats['total_candidates']} accepted "
                f"(filtered: no_name={filtering_stats['filtered_no_param_name']}, "
                f"no_value={filtering_stats['filtered_no_value']}, "
                f"insufficient_evidence={filtering_stats['filtered_insufficient_evidence']}, "
                f"errors={filtering_stats['filtered_other_error']})"
            )
            
            return results
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Task 1 response: {e}")
            logger.debug(f"Response was: {response[:500]}")
            return {}
        except KeyError as e:
            logger.error(f"Missing required field in Task 1 response: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error parsing Task 1 response: {e}")
            logger.debug(f"Response was: {response[:500] if response else 'None'}")
            return {}
    
    def parse_task2_response(self, response: str, min_evidence_length: int) -> List[ParameterProposal]:
        """
        Parse Task 2 response: Discover new parameters not in library.
        
        Expected format:
        {
          "new_parameters": [
            {
              "parameter_name": "...",
              "description": "...",
              "category": "...",
              "evidence": "...",
              "evidence_location": "...",
              "example_values": [...],
              "units": "...",
              "prevalence": "high|medium|low",
              "importance": "high|medium|low",
              "mapping_suggestion": "new",
              "hed_hint": "..."
            }
          ]
        }
        
        Args:
            response: Raw LLM response
            min_evidence_length: Minimum character length for evidence
            
        Returns:
            List of ParameterProposal objects
        """
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                logger.error("No JSON in Task 2 response")
                return []
            
            data = json.loads(response[json_start:json_end])
            
            new_params = data.get('new_parameters', [])
            if not new_params:
                logger.info("Task 2: No new parameters discovered")
                return []
            
            proposals = []
            for item in new_params:
                param_name = item.get('parameter_name')
                if not param_name:
                    continue
                
                # Validate evidence
                evidence = item.get('evidence', '').strip()
                if len(evidence) < min_evidence_length:
                    logger.debug(f"Task 2: Insufficient evidence for {param_name}, skipping")
                    continue
                
                # Estimate confidence from prevalence and importance
                prevalence = item.get('prevalence', 'low')
                importance = item.get('importance', 'low')
                
                prevalence_score = {'low': 0.3, 'medium': 0.6, 'high': 0.9}.get(prevalence, 0.5)
                importance_score = {'low': 0.3, 'medium': 0.6, 'high': 0.9}.get(importance, 0.5)
                confidence = (prevalence_score + importance_score) / 2
                
                proposal = ParameterProposal(
                    parameter_name=param_name,
                    description=item.get('description', ''),
                    category=item.get('category', 'other'),
                    evidence=evidence,
                    evidence_location=item.get('evidence_location', ''),
                    example_values=item.get('example_values', []),
                    units=item.get('units'),
                    prevalence=prevalence,
                    importance=importance,
                    mapping_suggestion=item.get('mapping_suggestion', 'new'),
                    hed_hint=item.get('hed_hint'),
                    confidence=confidence
                )
                proposals.append(proposal)
            
            # Sort by importance and prevalence
            importance_order = {'high': 3, 'medium': 2, 'low': 1}
            proposals.sort(
                key=lambda p: (
                    importance_order.get(p.importance, 0),
                    importance_order.get(p.prevalence, 0)
                ),
                reverse=True
            )
            
            logger.info(f"Task 2 parsed {len(proposals)} new parameter proposals")
            return proposals
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Task 2 response: {e}")
            logger.debug(f"Response was: {response[:500]}")
            return []
        except KeyError as e:
            logger.error(f"Missing required field in Task 2 response: {e}")
            return []
    
    def _auto_fix_json_response(self, malformed_response: str, parameter_names: List[str], llm_provider) -> Optional[str]:
        """
        Ask the LLM to fix its own malformed JSON response.
        
        Args:
            malformed_response: The original malformed JSON response
            parameter_names: Expected parameter names for context
            llm_provider: LLM provider instance for making fix request
            
        Returns:
            Fixed JSON response or None if fix failed
        """
        if not llm_provider:
            logger.error("No LLM provider available for JSON auto-fix")
            return None
            
        try:
            # Create a simple fix prompt
            fix_prompt = f"""The following JSON response has formatting errors. Please fix it to be valid JSON:

{malformed_response}

Return ONLY the corrected JSON, no explanations or extra text."""

            # Use the provider to fix the JSON
            fixed_response = llm_provider.generate(
                prompt=fix_prompt,
                max_tokens=1024,
                temperature=0.0
            )
            
            if fixed_response:
                logger.info("JSON auto-fix completed")
                return fixed_response.strip()
            else:
                logger.error("No response from LLM for JSON fix")
                return None
            
        except Exception as e:
            logger.error(f"JSON auto-fix failed: {e}")
            return None