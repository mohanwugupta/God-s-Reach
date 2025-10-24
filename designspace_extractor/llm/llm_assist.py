"""
LLM-assisted parameter extraction.
Implements the LLM policy for controlled, logged, and auditable inference.
"""
import os
import json
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class LLMAssistant:
    """LLM-assisted extraction for implicit or ambiguous parameters."""
    
    def __init__(self, provider: str = 'claude', model: str = None, temperature: float = 0.0):
        """
        Initialize LLM assistant.
        
        Args:
            provider: LLM provider (claude, openai, qwen)
            model: Model name (default: from env or provider default)
            temperature: Sampling temperature (default: 0.0 per policy)
        """
        self.provider = provider
        self.temperature = temperature
        self.enabled = os.getenv('LLM_ENABLE', 'false').lower() == 'true'
        self.budget_usd = float(os.getenv('LLM_BUDGET_USD', '10.0'))
        self.current_spend = 0.0
        
        if not self.enabled:
            logger.info("LLM assistance is disabled")
            return
        
        # Initialize provider-specific client
        if provider == 'claude':
            self.model = model or os.getenv('LLM_MODEL', 'claude-3-sonnet-20240229')
            self._init_claude()
        elif provider == 'openai':
            self.model = model or os.getenv('LLM_MODEL', 'gpt-4-turbo-preview')
            self._init_openai()
        elif provider == 'qwen':
            self.model = model or os.getenv('QWEN_MODEL_PATH', './models/qwen2.5')
            self._init_qwen()
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    
    def _init_claude(self):
        """Initialize Claude (Anthropic) client."""
        try:
            import anthropic
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set in environment")
            self.client = anthropic.Anthropic(api_key=api_key)
            logger.info(f"Initialized Claude client with model {self.model}")
        except ImportError:
            logger.error("anthropic package not installed. Install with: pip install anthropic")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize Claude: {e}")
            self.enabled = False
    
    def _init_openai(self):
        """Initialize OpenAI client."""
        try:
            import openai
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set in environment")
            self.client = openai.OpenAI(api_key=api_key)
            logger.info(f"Initialized OpenAI client with model {self.model}")
        except ImportError:
            logger.error("openai package not installed. Install with: pip install openai")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            self.enabled = False
    
    def _init_qwen(self):
        """Initialize Qwen (local model)."""
        logger.info(f"Qwen initialization not yet implemented. Model path: {self.model}")
        self.enabled = False
    
    def infer_parameter(self, parameter_name: str, context: str, 
                       extracted_params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Use LLM to infer a parameter value from context.
        
        Args:
            parameter_name: Name of parameter to infer
            context: Context text (code snippet, methods section, etc.)
            extracted_params: Already extracted parameters for context
            
        Returns:
            Dictionary with inferred value and metadata, or None
        """
        if not self.enabled:
            logger.debug("LLM inference requested but LLM is disabled")
            return None
        
        # Check budget
        if self.current_spend >= self.budget_usd:
            logger.warning(f"LLM budget exhausted ({self.current_spend:.2f} / {self.budget_usd:.2f} USD)")
            return None
        
        # Build prompt
        prompt = self._build_prompt(parameter_name, context, extracted_params)
        
        # Call LLM
        try:
            response, cost = self._call_llm(prompt)
            self.current_spend += cost
            
            # Parse response
            result = self._parse_response(response, parameter_name)
            
            # Log usage (per LLM policy)
            self._log_usage(parameter_name, prompt, response, cost)
            
            return result
            
        except Exception as e:
            logger.error(f"LLM inference failed for {parameter_name}: {e}")
            return None
    
    def _build_prompt(self, parameter_name: str, context: str, 
                     extracted_params: Dict[str, Any] = None) -> str:
        """Build prompt for LLM inference."""
        prompt = f"""You are assisting in extracting experimental parameters from motor adaptation studies.

Parameter to infer: {parameter_name}

Context:
{context}

"""
        if extracted_params:
            prompt += f"\nAlready extracted parameters:\n"
            for param, value in extracted_params.items():
                prompt += f"  - {param}: {value}\n"
        
        prompt += f"""
Please analyze the context and infer the value of '{parameter_name}'.

Respond ONLY with a JSON object in this exact format:
{{
  "value": <inferred value>,
  "confidence": <confidence score 0-1>,
  "reasoning": "<brief explanation>"
}}

If you cannot infer the parameter with reasonable confidence, respond with:
{{"value": null, "confidence": 0.0, "reasoning": "Insufficient information"}}
"""
        return prompt
    
    def _call_llm(self, prompt: str) -> tuple[str, float]:
        """
        Call the LLM and return response and cost.
        
        Returns:
            Tuple of (response_text, cost_in_usd)
        """
        if self.provider == 'claude':
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text
            
            # Estimate cost (approximate)
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = (input_tokens * 0.000003) + (output_tokens * 0.000015)  # Rough estimate
            
            return text, cost
            
        elif self.provider == 'openai':
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=1024
            )
            text = response.choices[0].message.content
            
            # Estimate cost
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = (input_tokens * 0.00001) + (output_tokens * 0.00003)  # GPT-4 pricing
            
            return text, cost
        
        else:
            raise NotImplementedError(f"LLM provider {self.provider} not implemented")
    
    def _parse_response(self, response: str, parameter_name: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response into structured format."""
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                logger.error("No JSON found in LLM response")
                return None
            
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            
            if data.get('value') is None:
                return None
            
            return {
                'value': data['value'],
                'confidence': data.get('confidence', 0.5),
                'source_type': 'llm_inference',
                'method': 'llm_inference',
                'llm_provider': self.provider,
                'llm_model': self.model,
                'llm_reasoning': data.get('reasoning', ''),
                'requires_review': True  # Always flag LLM-inferred values
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return None
    
    def _log_usage(self, parameter_name: str, prompt: str, response: str, cost: float):
        """Log LLM usage for audit trail."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'parameter': parameter_name,
            'provider': self.provider,
            'model': self.model,
            'temperature': self.temperature,
            'prompt_length': len(prompt),
            'response_length': len(response),
            'cost_usd': cost,
            'cumulative_spend': self.current_spend
        }
        
        # Log to file
        log_file = './out/logs/llm_usage.log'
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        logger.info(f"LLM usage logged: {parameter_name}, cost=${cost:.4f}")
    
    def discover_new_parameters(self, paper_text: str, current_schema: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze paper text to discover parameters not in current schema.
        
        Args:
            paper_text: Full text of the paper or Methods section
            current_schema: List of parameter names currently in schema
            
        Returns:
            List of suggested new parameters with metadata
        """
        if not self.enabled:
            logger.warning("LLM is not enabled. Cannot discover new parameters.")
            return []
        
        prompt = f"""You are analyzing a motor adaptation research paper to identify experimental parameters that are NOT captured in the current extraction schema.

CURRENT SCHEMA (parameters already extracted):
{', '.join(sorted(current_schema))}

PAPER TEXT TO ANALYZE:
{paper_text[:4000]}  # First 4000 chars

Your task: Identify important experimental parameters mentioned in this paper that are NOT in the current schema.

For each NEW parameter you identify, provide:
1. parameter_name: Short snake_case name (e.g., "target_size_cm")
2. description: What this parameter measures
3. example_values: 2-3 example values from the text
4. importance: "high", "medium", or "low" - how critical is this parameter?
5. prevalence: "common", "occasional", or "rare" - how often is this likely reported?
6. category: One of: demographics, task_design, perturbation, feedback, equipment, outcome
7. evidence: Direct quote from the text showing this parameter

IMPORTANT:
- Only suggest parameters that are SPECIFIC, MEASURABLE values (not concepts)
- Focus on parameters that could be extracted automatically
- Don't suggest parameters similar to ones already in schema
- Prioritize parameters that appear in Methods sections
- Maximum 10 suggestions

Return your response as a JSON array:
[
  {{
    "parameter_name": "target_size_cm",
    "description": "Diameter of the reach target in centimeters",
    "example_values": ["1.0 cm", "1.5 cm", "2.0 cm"],
    "importance": "medium",
    "prevalence": "common",
    "category": "task_design",
    "evidence": "Participants reached to circular targets (1.0 cm diameter)"
  }}
]

RESPOND WITH ONLY THE JSON ARRAY, NO OTHER TEXT."""

        try:
            if self.provider == 'claude':
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    temperature=self.temperature,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                content = response.content[0].text
                
            elif self.provider == 'openai':
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{
                        "role": "system",
                        "content": "You are an expert at analyzing motor adaptation research papers."
                    }, {
                        "role": "user",
                        "content": prompt
                    }],
                    temperature=self.temperature,
                    max_tokens=2000
                )
                content = response.choices[0].message.content
            
            # Parse JSON response
            # Remove markdown code blocks if present
            content = content.strip()
            if content.startswith('```'):
                content = '\n'.join(content.split('\n')[1:-1])
            
            suggestions = json.loads(content)
            
            # Log usage
            self._log_usage('discover_parameters', len(paper_text), len(content), 
                          metadata={'num_suggestions': len(suggestions)})
            
            logger.info(f"Discovered {len(suggestions)} new parameter suggestions")
            return suggestions
            
        except Exception as e:
            logger.error(f"Error discovering parameters: {e}")
            return []


# Convenience function
def infer_with_llm(parameter_name: str, context: str, provider: str = 'claude') -> Optional[Dict[str, Any]]:
    """
    Convenience function for one-off LLM inference.
    
    Args:
        parameter_name: Parameter to infer
        context: Context text
        provider: LLM provider
        
    Returns:
        Inferred parameter data or None
    """
    assistant = LLMAssistant(provider=provider)
    return assistant.infer_parameter(parameter_name, context)
