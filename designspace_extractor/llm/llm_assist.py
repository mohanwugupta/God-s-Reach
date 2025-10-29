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
        
        # Set context window limits based on provider
        # Claude 3.5 Sonnet: 200K tokens
        # GPT-4 Turbo: 128K tokens  
        # Qwen2.5-72B: 128K tokens
        self.max_context_tokens = {
            'claude': 180000,  # 200K limit, leave buffer for response
            'openai': 120000,  # 128K limit, leave buffer
            'qwen': 120000     # 128K limit, leave buffer
        }
        
        if not self.enabled:
            logger.info("LLM assistance is disabled")
            return
        
        # Initialize provider-specific client
        if provider == 'claude':
            self.model = model or os.getenv('LLM_MODEL', 'claude-3-5-sonnet-20241022')  # Latest with 200K
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
        """Initialize Qwen (local model via vLLM or transformers)."""
        try:
            # Check if vLLM is available for faster inference
            try:
                from vllm import LLM, SamplingParams
                self.use_vllm = True
                logger.info("Using vLLM for Qwen inference (faster)")
            except ImportError:
                from transformers import AutoModelForCausalLM, AutoTokenizer
                import torch
                self.torch = torch  # Store for later use in _call_llm
                self.use_vllm = False
                logger.info("Using transformers for Qwen inference (slower, but works)")
            
            # Resolve model path
            # self.model is set from QWEN_MODEL_PATH environment variable
            import os
            from pathlib import Path
            
            # Use the model path from environment (should be absolute path to model directory)
            model_path = self.model
            
            # Verify model exists
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Qwen model not found at: {model_path}")
            
            logger.info(f"Loading Qwen model from: {model_path}")
            
            if self.use_vllm:
                # Use vLLM for efficient inference
                self.client = LLM(
                    model=model_path,
                    tensor_parallel_size=1,  # Adjust based on available GPUs
                    gpu_memory_utilization=0.9,
                    trust_remote_code=True,
                )
                self.sampling_params = SamplingParams(
                    temperature=self.temperature,
                    max_tokens=2048,
                    top_p=0.95,
                )
                logger.info(f"Initialized vLLM Qwen client: {model_path}")
            else:
                # Use transformers
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_path,
                    trust_remote_code=True
                )
                
                logger.info("Loading model with memory optimization for 40GB GPU")
                # Use int8 dtype with CPU offloading to fit model + activations
                # This avoids bitsandbytes dependency which requires Python.h
                self.client = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    torch_dtype=torch.bfloat16,
                    device_map="auto",  # Auto-distribute across GPUs and CPU
                    trust_remote_code=True,
                    attn_implementation="eager",  # Disable SDPA to avoid sliding window warning
                    max_memory={0: "28GiB", "cpu": "100GiB"},  # Reserve 12GB GPU for activations
                    low_cpu_mem_usage=True,
                    offload_buffers=True  # Offload buffers to CPU when needed
                )
                
                # Fix generation config to avoid warnings
                self.client.generation_config.do_sample = False
                self.client.generation_config.temperature = None
                self.client.generation_config.top_k = None
                self.client.generation_config.top_p = None
                
                # Enable gradient checkpointing to save memory
                if hasattr(self.client, 'gradient_checkpointing_enable'):
                    self.client.gradient_checkpointing_enable()
                
                logger.info(f"Initialized transformers Qwen client: {model_path}")
            
            self.enabled = True
            
        except FileNotFoundError as e:
            logger.error(f"Qwen model not found: {e}")
            logger.error(f"Expected location: ../models/Qwen--Qwen2.5-72B-Instruct")
            self.enabled = False
        except ImportError as e:
            logger.error(f"Required package not installed: {e}")
            logger.error("Install with: pip install vllm transformers torch")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize Qwen: {e}")
            self.enabled = False
    
    def infer_parameters_batch(self, parameter_names: List[str], context: str, 
                              extracted_params: Dict[str, Any] = None) -> Dict[str, Dict[str, Any]]:
        """
        Use LLM to infer multiple parameter values from context in a single query.
        This is more efficient than calling infer_parameter() multiple times.
        
        Args:
            parameter_names: List of parameter names to infer
            context: Context text (code snippet, methods section, etc.)
            extracted_params: Already extracted parameters for context
            
        Returns:
            Dictionary mapping parameter names to their inferred data, or empty dict
        """
        if not self.enabled:
            logger.debug("LLM inference requested but LLM is disabled")
            return {}
        
        # Check budget
        if self.current_spend >= self.budget_usd:
            logger.warning(f"LLM budget exhausted ({self.current_spend:.2f} / {self.budget_usd:.2f} USD)")
            return {}
        
        if not parameter_names:
            return {}
        
        # Build batch prompt
        prompt = self._build_batch_prompt(parameter_names, context, extracted_params)
        
        # Call LLM with increased token limit
        try:
            response, cost = self._call_llm(prompt, max_tokens=4096)
            self.current_spend += cost
            
            # Parse batch response
            results = self._parse_batch_response(response, parameter_names)
            
            # Log usage (per LLM policy)
            self._log_usage('batch_inference', prompt, response, cost, 
                          num_parameters=len(parameter_names),
                          parameters=parameter_names)
            
            return results
            
        except Exception as e:
            logger.error(f"LLM batch inference failed: {e}")
            return {}
    
    def infer_parameter(self, parameter_name: str, context: str, 
                       extracted_params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Use LLM to infer a parameter value from context.
        For efficiency, consider using infer_parameters_batch() for multiple parameters.
        
        Args:
            parameter_name: Name of parameter to infer
            context: Context text (code snippet, methods section, etc.)
            extracted_params: Already extracted parameters for context
            
        Returns:
            Dictionary with inferred value and metadata, or None
        """
        results = self.infer_parameters_batch([parameter_name], context, extracted_params)
        return results.get(parameter_name)
    
    def _build_batch_prompt(self, parameter_names: List[str], context: str, 
                           extracted_params: Dict[str, Any] = None) -> str:
        """Build prompt for batch LLM inference of multiple parameters."""
        # Truncate context to fit within model limits (rough estimate: 4 chars per token)
        max_chars = self.max_context_tokens.get(self.provider, 120000) * 3
        context_excerpt = context[:max_chars]
        
        if len(context) > max_chars:
            logger.info(f"Context truncated from {len(context)} to {max_chars} chars to fit context window")
        
        prompt = f"""You are assisting in extracting experimental parameters from motor adaptation studies.

Parameters to infer (extract ALL that are mentioned):
{chr(10).join(f'  - {name}' for name in parameter_names)}

Context (full paper text or large excerpt):
{context_excerpt}

"""
        if extracted_params:
            prompt += f"\nAlready extracted parameters:\n"
            for param, value in extracted_params.items():
                prompt += f"  - {param}: {value}\n"
        
        prompt += f"""
Please analyze the context and infer the values for as many of the listed parameters as possible.

Respond ONLY with a JSON object in this exact format:
{{
  "parameter_name_1": {{
    "value": <inferred value or null>,
    "confidence": <confidence score 0-1>,
    "reasoning": "<brief explanation>"
  }},
  "parameter_name_2": {{
    "value": <inferred value or null>,
    "confidence": <confidence score 0-1>,
    "reasoning": "<brief explanation>"
  }}
}}

IMPORTANT:
- Include ALL parameters from the list, even if you cannot find them (use null)
- Only provide non-null values if you have reasonable confidence (>0.5)
- Keep reasoning brief (1 sentence max)
- Use exact parameter names as keys
- Search the ENTIRE context provided for each parameter

Example response:
{{
  "n_participants": {{"value": 24, "confidence": 0.95, "reasoning": "Explicitly stated in methods"}},
  "age_mean": {{"value": null, "confidence": 0.0, "reasoning": "Age not mentioned in context"}}
}}
"""
        return prompt
    
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
    
    def _call_llm(self, prompt: str, max_tokens: int = 1024) -> tuple[str, float]:
        """
        Call the LLM and return response and cost.
        
        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens to generate (default 1024, use 4096+ for batch)
        
        Returns:
            Tuple of (response_text, cost_in_usd)
        """
        if self.provider == 'claude':
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
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
                max_tokens=max_tokens
            )
            text = response.choices[0].message.content
            
            # Estimate cost
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = (input_tokens * 0.00001) + (output_tokens * 0.00003)  # GPT-4 pricing
            
            return text, cost
        
        elif self.provider == 'qwen':
            # Local model - no cost
            if self.use_vllm:
                # vLLM inference
                messages = [
                    {"role": "system", "content": "You are a helpful assistant specialized in extracting experimental parameters from scientific papers."},
                    {"role": "user", "content": prompt}
                ]
                
                # Format for Qwen chat template
                formatted_prompt = self._format_qwen_chat(messages)
                
                # Update sampling params with new max_tokens
                from vllm import SamplingParams
                sampling_params = SamplingParams(
                    temperature=self.temperature,
                    max_tokens=max_tokens,
                    top_p=0.95,
                )
                
                outputs = self.client.generate(
                    [formatted_prompt],
                    sampling_params
                )
                text = outputs[0].outputs[0].text
                
            else:
                # Transformers inference
                messages = [
                    {"role": "system", "content": "You are a helpful assistant specialized in extracting experimental parameters from scientific papers."},
                    {"role": "user", "content": prompt}
                ]
                
                text_input = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
                
                model_inputs = self.tokenizer([text_input], return_tensors="pt").to(self.client.device)
                
                # Clear CUDA cache before generation to free memory
                if hasattr(self, 'torch') and self.torch.cuda.is_available():
                    self.torch.cuda.empty_cache()
                
                # Generate with explicit parameters (temperature=0 means greedy decoding)
                generated_ids = self.client.generate(
                    **model_inputs,
                    max_new_tokens=max_tokens,
                    do_sample=False,  # Greedy decoding for temperature=0
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )
                
                generated_ids = [
                    output_ids[len(input_ids):] 
                    for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
                ]
                
                text = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
                
                # Clear cache after generation
                if hasattr(self, 'torch') and self.torch.cuda.is_available():
                    self.torch.cuda.empty_cache()
            
            # Local model has zero cost
            cost = 0.0
            return text, cost
        
        else:
            raise NotImplementedError(f"LLM provider {self.provider} not implemented")
    
    def _format_qwen_chat(self, messages: List[Dict[str, str]]) -> str:
        """Format messages for Qwen chat template (when using vLLM)."""
        # Qwen2.5 chat format
        formatted = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                formatted += f"<|im_start|>system\n{content}<|im_end|>\n"
            elif role == "user":
                formatted += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == "assistant":
                formatted += f"<|im_start|>assistant\n{content}<|im_end|>\n"
        
        # Add assistant prompt for generation
        formatted += "<|im_start|>assistant\n"
        return formatted
    
    def _parse_batch_response(self, response: str, parameter_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """Parse LLM batch response into structured format."""
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                logger.error("No JSON found in LLM batch response")
                return {}
            
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            
            results = {}
            for param_name in parameter_names:
                if param_name in data:
                    param_data = data[param_name]
                    if param_data.get('value') is not None:
                        confidence = param_data.get('confidence', 0.5)
                        results[param_name] = {
                            'value': param_data['value'],
                            'confidence': confidence,
                            'source_type': 'llm_inference',
                            'method': 'llm_batch_inference',
                            'llm_provider': self.provider,
                            'llm_model': self.model,
                            'llm_reasoning': param_data.get('reasoning', ''),
                            'requires_review': confidence < 0.7  # Auto-accept high confidence (≥0.7)
                        }
            
            logger.info(f"Batch extraction: {len(results)}/{len(parameter_names)} parameters inferred")
            return results
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM batch response as JSON: {e}")
            logger.debug(f"Response: {response[:500]}")
            return {}
    
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
            
            confidence = data.get('confidence', 0.5)
            return {
                'value': data['value'],
                'confidence': confidence,
                'source_type': 'llm_inference',
                'method': 'llm_inference',
                'llm_provider': self.provider,
                'llm_model': self.model,
                'llm_reasoning': data.get('reasoning', ''),
                'requires_review': confidence < 0.7  # Auto-accept high confidence (≥0.7)
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return None
    
    def _log_usage(self, parameter_name: str, prompt: str = None, response: str = None, cost: float = 0.0, **kwargs):
        """Log LLM usage for audit trail."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'parameter': parameter_name,
            'provider': self.provider,
            'model': self.model,
            'temperature': self.temperature,
            'cost_usd': cost,
            'cumulative_spend': self.current_spend,
            **kwargs  # Additional metadata
        }
        
        if prompt:
            log_entry['prompt_length'] = len(prompt)
        if response:
            log_entry['response_length'] = len(response)
        
        # Log to file
        log_file = './out/logs/llm_usage.log'
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Save full prompt and response to separate file if available
        if prompt and response:
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            response_file = f'./out/logs/llm_response_{timestamp_str}_{parameter_name}.json'
            os.makedirs(os.path.dirname(response_file), exist_ok=True)
            
            full_entry = {
                'metadata': log_entry,
                'prompt': prompt,
                'response': response
            }
            
            with open(response_file, 'w') as f:
                json.dump(full_entry, f, indent=2)
        
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
        
        # Use full paper text up to context limit (rough estimate: 4 chars per token)
        max_chars = self.max_context_tokens.get(self.provider, 120000) * 3  # Conservative estimate
        paper_excerpt = paper_text[:max_chars]
        
        if len(paper_text) > max_chars:
            logger.info(f"Paper text truncated from {len(paper_text)} to {max_chars} chars to fit context window")
        
        prompt = f"""You are analyzing a motor adaptation research paper to identify experimental parameters that are NOT captured in the current extraction schema.

CURRENT SCHEMA (parameters already extracted):
{', '.join(sorted(current_schema))}

PAPER TEXT TO ANALYZE (full paper or large excerpt):
{paper_excerpt}

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
- Maximum 20 suggestions (prioritize by importance)

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
            response, cost = self._call_llm(prompt, max_tokens=8192)  # Increased for more suggestions
            self.current_spend += cost
            
            # Parse JSON response
            # Remove markdown code blocks if present
            content = response.strip()
            if content.startswith('```'):
                lines = content.split('\n')
                # Remove first and last line (markdown delimiters)
                content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content
                # Also handle ```json prefix
                if content.startswith('json'):
                    content = content[4:].strip()
            
            suggestions = json.loads(content)
            
            # Log usage
            self._log_usage('discover_parameters', prompt=prompt, response=response, cost=cost,
                          metadata={'num_suggestions': len(suggestions), 'paper_chars': len(paper_excerpt)})
            
            logger.info(f"Discovered {len(suggestions)} new parameter suggestions from {len(paper_excerpt)} chars")
            return suggestions
            
        except Exception as e:
            logger.error(f"Error discovering parameters: {e}")
            return []
    
    def export_parameter_recommendations(self, recommendations: List[Dict[str, Any]], 
                                        output_file: str = './out/logs/parameter_recommendations.csv'):
        """
        Export parameter recommendations to CSV for easy review.
        
        Args:
            recommendations: List of parameter suggestions from discover_new_parameters()
            output_file: Path to output CSV file
        """
        if not recommendations:
            logger.warning("No recommendations to export")
            return
        
        import csv
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['parameter_name', 'description', 'example_values', 
                         'importance', 'prevalence', 'category', 'evidence']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for rec in recommendations:
                # Convert example_values list to string
                rec_copy = rec.copy()
                if isinstance(rec_copy.get('example_values'), list):
                    rec_copy['example_values'] = ', '.join(str(v) for v in rec_copy['example_values'])
                writer.writerow(rec_copy)
        
        logger.info(f"Exported {len(recommendations)} recommendations to {output_file}")
        print(f"✅ Parameter recommendations saved to: {output_file}")


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
