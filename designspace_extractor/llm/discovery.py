"""
Stage 3 LLM Discovery - Discover new parameters from papers.

Identifies unreported parameters and generates proposals for review.
"""
import logging
import csv
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base import ParameterProposal
from .providers import LLMProvider
from .prompt_builder import PromptBuilder
from .response_parser import ResponseParser

logger = logging.getLogger(__name__)


class DiscoveryEngine:
    """
    Stage 3 discovery engine.
    
    Discovers new design space parameters not covered by current schema.
    """
    
    def __init__(self, provider: LLMProvider,
                 min_evidence_length: int = 20,
                 max_proposals: int = 10):
        """
        Initialize discovery engine.
        
        Args:
            provider: Initialized LLM provider
            min_evidence_length: Minimum character length for evidence
            max_proposals: Maximum number of proposals to return
        """
        self.provider = provider
        self.min_evidence_length = min_evidence_length
        self.max_proposals = max_proposals
        
        self.prompt_builder = PromptBuilder()
        self.response_parser = ResponseParser()
    
    def discover_parameters(self, context: str, current_schema: Dict[str, Any],
                           already_extracted: Optional[Dict[str, Any]] = None) -> List[ParameterProposal]:
        """
        Task 2: Discover entirely NEW parameters not in the current library.
        
        Args:
            context: Paper content
            current_schema: Current parameter library/schema
            already_extracted: Parameters already extracted (to avoid duplicates)
            
        Returns:
            List of ParameterProposal objects sorted by importance/prevalence
        """
        # Build Task 2 discovery prompt
        prompt = self.prompt_builder.build_new_params_prompt(
            current_schema=current_schema,
            already_extracted=already_extracted,
            context=context
        )
        
        logger.info(f"Running Task 2: Discovering new parameters with {self.provider.provider_name}")
        
        # Generate response
        response = self.provider.generate(
            prompt=prompt,
            max_tokens=2048,
            temperature=0.2  # Slightly higher for creativity
        )
        
        if not response:
            logger.error("No response from LLM for Task 2")
            return []
        
        # Parse Task 2 proposals
        proposals = self.response_parser.parse_task2_response(
            response=response,
            min_evidence_length=self.min_evidence_length
        )
        
        # Limit to max_proposals
        if len(proposals) > self.max_proposals:
            logger.info(f"Limiting from {len(proposals)} to {self.max_proposals} proposals")
            proposals = proposals[:self.max_proposals]
        
        logger.info(f"Task 2 discovered {len(proposals)} new parameter proposals")
        return proposals
    
    def export_proposals_csv(self, proposals: List[ParameterProposal], 
                            output_path: str) -> None:
        """
        Export proposals to CSV for review.
        
        Args:
            proposals: List of proposals
            output_path: Output CSV file path
        """
        if not proposals:
            logger.warning("No proposals to export")
            return
        
        # Convert to dicts
        proposal_dicts = [p.to_dict() for p in proposals]
        
        # Write CSV
        fieldnames = [
            'parameter_name', 'description', 'category', 'evidence',
            'evidence_location', 'example_values', 'units', 'prevalence',
            'importance', 'mapping_suggestion', 'hed_hint', 'confidence',
            'review_status'
        ]
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(proposal_dicts)
        
        logger.info(f"Exported {len(proposals)} proposals to {output_path}")
    
    def export_proposals_json(self, proposals: List[ParameterProposal],
                             output_path: str, include_metadata: bool = True) -> None:
        """
        Export proposals to JSON format.
        
        Args:
            proposals: List of proposals
            output_path: Output JSON file path
            include_metadata: Whether to include metadata wrapper
        """
        if not proposals:
            logger.warning("No proposals to export")
            return
        
        # Convert to dicts
        proposal_dicts = [p.to_dict() for p in proposals]
        
        # Build output structure
        if include_metadata:
            output = {
                'metadata': {
                    'total_proposals': len(proposals),
                    'provider': self.provider.provider_name,
                    'model': self.provider.model_name,
                    'min_evidence_length': self.min_evidence_length
                },
                'proposals': proposal_dicts
            }
        else:
            output = proposal_dicts
        
        # Write JSON
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(proposals)} proposals to {output_path}")
    
    def filter_proposals_by_prevalence(self, proposals: List[ParameterProposal],
                                      min_prevalence: str = 'medium') -> List[ParameterProposal]:
        """
        Filter proposals by minimum prevalence level.
        
        Args:
            proposals: List of proposals
            min_prevalence: Minimum prevalence ('low', 'medium', 'high')
            
        Returns:
            Filtered list
        """
        prevalence_order = {'low': 1, 'medium': 2, 'high': 3}
        threshold = prevalence_order.get(min_prevalence, 1)
        
        filtered = [
            p for p in proposals
            if prevalence_order.get(p.prevalence, 0) >= threshold
        ]
        
        logger.info(f"Filtered {len(proposals)} proposals to {len(filtered)} "
                   f"with prevalence >= {min_prevalence}")
        
        return filtered
    
    def filter_proposals_by_importance(self, proposals: List[ParameterProposal],
                                      min_importance: str = 'medium') -> List[ParameterProposal]:
        """
        Filter proposals by minimum importance level.
        
        Args:
            proposals: List of proposals
            min_importance: Minimum importance ('low', 'medium', 'high')
            
        Returns:
            Filtered list
        """
        importance_order = {'low': 1, 'medium': 2, 'high': 3}
        threshold = importance_order.get(min_importance, 1)
        
        filtered = [
            p for p in proposals
            if importance_order.get(p.importance, 0) >= threshold
        ]
        
        logger.info(f"Filtered {len(proposals)} proposals to {len(filtered)} "
                   f"with importance >= {min_importance}")
        
        return filtered
