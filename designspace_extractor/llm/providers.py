"""
LLM provider initialization and configuration.

Supports Claude, OpenAI, Qwen (transformers), and local models via vLLM.
"""
import logging
import os
from typing import Optional, Any, Type
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Import JSON parsing utilities
from .json_parser import extract_json_from_text, parse_llm_json_response

try:
    import outlines
    from outlines import generate
    OUTLINES_AVAILABLE = True
    logger.info("✓ Outlines library available for structured generation")
except ImportError:
    OUTLINES_AVAILABLE = False
    logger.warning("Outlines not available. Structured generation will be disabled.")
    
try:
    from pydantic import BaseModel
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    logger.warning("Pydantic not available. Type validation will be limited.")


class LLMProvider:
    """Base class for LLM providers."""
    
    def __init__(self, provider_name: str, model_name: str):
        self.provider_name = provider_name
        self.model_name = model_name
        self.client = None
    
    def initialize(self) -> bool:
        """Initialize the provider. Returns True if successful."""
        raise NotImplementedError


class ClaudeProvider(LLMProvider):
    """Claude (Anthropic) provider."""
    
    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022", api_key: Optional[str] = None):
        super().__init__("claude", model_name)
        self.api_key = api_key
    
    def initialize(self) -> bool:
        try:
            import anthropic
            import os
            
            api_key = self.api_key or os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                logger.error("ANTHROPIC_API_KEY not set")
                return False
            
            self.client = anthropic.Anthropic(api_key=api_key)
            logger.info(f"Claude provider initialized: {self.model_name}")
            return True
            
        except ImportError:
            logger.error("anthropic package not installed. Run: pip install anthropic")
            return False
    
    def generate(self, prompt: str, max_tokens: int = 4096, temperature: float = 0.0) -> Optional[str]:
        """Generate completion from Claude."""
        if not self.client:
            logger.error("Provider not initialized")
            return None
        
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return None


class OpenAIProvider(LLMProvider):
    """OpenAI provider."""
    
    def __init__(self, model_name: str = "gpt-4o", api_key: Optional[str] = None):
        super().__init__("openai", model_name)
        self.api_key = api_key
    
    def initialize(self) -> bool:
        try:
            import openai
            import os
            
            api_key = self.api_key or os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.error("OPENAI_API_KEY not set")
                return False
            
            self.client = openai.OpenAI(api_key=api_key)
            logger.info(f"OpenAI provider initialized: {self.model_name}")
            return True
            
        except ImportError:
            logger.error("openai package not installed. Run: pip install openai")
            return False
    
    def generate(self, prompt: str, max_tokens: int = 4096, temperature: float = 0.0) -> Optional[str]:
        """Generate completion from OpenAI."""
        if not self.client:
            logger.error("Provider not initialized")
            return None
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None


class QwenProvider(LLMProvider):
    """Qwen provider using transformers."""
    
    def __init__(self, model_name: str = None, device: str = "auto"):
        # Use environment variable or provided path, fallback to HF ID only if needed
        if model_name:
            resolved_model = model_name
        else:
            resolved_model = os.getenv('QWEN_MODEL_PATH', "Qwen/Qwen2.5-32B-Instruct")
        
        super().__init__("qwen", resolved_model)
        self.device = device
        self.tokenizer = None
        self.model = None
    
    def initialize(self) -> bool:
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            logger.info(f"Loading Qwen model from: {self.model_name}")
            
            # Force offline mode to prevent downloads
            os.environ['HF_HUB_OFFLINE'] = '1'
            
            # Check if path exists
            if not os.path.exists(self.model_name):
                logger.error(f"Model path does not exist: {self.model_name}")
                logger.error("Make sure the model is downloaded to the cache or local directory")
                return False
            
            # Verify required files exist
            required_files = ['config.json', 'tokenizer.json', 'tokenizer_config.json']
            missing_files = [f for f in required_files if not os.path.exists(os.path.join(self.model_name, f))]
            if missing_files:
                logger.error(f"Model incomplete, missing: {missing_files}")
                logger.error(f"Check model directory: {self.model_name}")
                return False
            
            logger.info("✓ Model files verified, loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                local_files_only=True,
                trust_remote_code=True
            )
            
            logger.info("✓ Loading model...")
            # Use appropriate dtype and device_map
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto",  # Distribute across available GPUs
                local_files_only=True,
                trust_remote_code=True
            )
            
            logger.info(f"✓ Qwen model loaded successfully from {self.model_name}")
            return True
            
        except ImportError:
            logger.error("transformers package not installed. Run: pip install transformers torch")
            return False
        except Exception as e:
            logger.error(f"Failed to load Qwen model: {e}")
            logger.error("Make sure:")
            logger.error("1. Model is downloaded to the correct path")
            logger.error("2. HF_HOME is set to the cache directory")
            logger.error("3. All required model files are present")
            return False
    
    def generate(self, prompt: str, max_tokens: int = 4096, temperature: float = 0.0) -> Optional[str]:
        """Generate completion from Qwen."""
        if not self.model or not self.tokenizer:
            logger.error("Provider not initialized")
            return None
        
        try:
            messages = [{"role": "user", "content": prompt}]
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
            
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature if temperature > 0 else 0.7,  # transformers needs temp > 0
                do_sample=temperature > 0
            )
            
            response = self.tokenizer.decode(outputs[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
            return response
            
        except Exception as e:
            logger.error(f"Qwen generation error: {e}")
            return None


class Qwen72BProvider(LLMProvider):
    """Qwen2.5-72B-Instruct provider using vLLM with Outlines for structured generation (local only)."""
    
    def __init__(self, model_name: str = None, tensor_parallel_size: int = 4):
        # Use environment variable or provided path
        if model_name:
            resolved_model = model_name
        else:
            # Default path follows same pattern as Qwen3-32B
            base_path = os.getenv('QWEN_MODEL_PATH', '/scratch/gpfs/JORDANAT/mg9965/models/Qwen--Qwen3-32B')
            resolved_model = base_path.replace('Qwen--Qwen3-32B', 'Qwen--Qwen2.5-72B-Instruct')
            # Check if custom env var is set
            resolved_model = os.getenv('QWEN72B_MODEL_PATH', resolved_model)
        
        super().__init__("qwen72b", resolved_model)
        self.tensor_parallel_size = tensor_parallel_size
        self.llm = None  # vLLM LLM instance
        self.outlines_available = False
    
    def initialize(self) -> bool:
        try:
            from vllm import LLM
            
            logger.info(f"Loading Qwen2.5-72B-Instruct model from: {self.model_name} with TP={self.tensor_parallel_size}")
            
            # Force offline mode to prevent downloads
            os.environ['HF_HUB_OFFLINE'] = '1'
            
            # Check if path exists
            if not os.path.exists(self.model_name):
                logger.error(f"Model path does not exist: {self.model_name}")
                logger.error("Make sure the model is downloaded to the cache or local directory")
                return False
            
            # Verify required files exist
            required_files = ['config.json', 'tokenizer.json', 'tokenizer_config.json']
            missing_files = [f for f in required_files if not os.path.exists(os.path.join(self.model_name, f))]
            if missing_files:
                logger.error(f"Model incomplete, missing: {missing_files}")
                logger.error(f"Check model directory: {self.model_name}")
                return False
            
            logger.info("✓ Model files verified, loading Qwen2.5-72B with vLLM...")
            # Use vLLM with tensor parallelism
            self.llm = LLM(
                model=self.model_name,
                tensor_parallel_size=self.tensor_parallel_size,  # Enable TP=4
                dtype="auto",
                trust_remote_code=True,
                max_model_len=32768,  # Adjust based on your needs
                gpu_memory_utilization=0.9,  # Use 90% of GPU memory
                enforce_eager=False,  # Use CUDA graphs for better performance
            )
            
            logger.info(f"✓ Qwen2.5-72B-Instruct model loaded successfully from {self.model_name}")
            
            # Wrap the vLLM model for Outlines (offline mode)
            if OUTLINES_AVAILABLE:
                try:
                    self.llm = outlines.from_vllm_offline(self.llm)
                    self.outlines_available = True
                    logger.info("✓ vLLM model wrapped for Outlines structured generation (offline)")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to wrap vLLM model for Outlines: {e}")
                    self.outlines_available = False
            else:
                logger.info("Outlines not available, using regular generation")
            
            return True
            
        except ImportError:
            logger.error("vllm package not installed. Run: pip install vllm")
            return False
        except Exception as e:
            logger.error(f"Failed to load Qwen2.5-72B model: {e}")
            logger.error("Make sure:")
            logger.error("1. Model is downloaded to the correct path")
            logger.error("2. HF_HOME is set to the cache directory")
            logger.error("3. All required model files are present")
            logger.error("4. Sufficient GPU memory available (requires 4 GPUs)")
            return False
    
    def generate(self, prompt: str, max_tokens: int = 4096, temperature: float = 0.0, 
                 schema: Optional[dict] = None, output_type: Optional[Type[BaseModel]] = None,
                 task_type: Optional[str] = None) -> Optional[str]:
        """
        Generate completion from Qwen2.5-72B using vLLM. 
        
        Args:
            prompt: The input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0 for greedy)
            schema: Optional JSON schema (legacy, prefer output_type)
            output_type: Optional Pydantic model for structured generation (PREFERRED)
            task_type: Optional task identifier for logging/debugging
            
        Returns:
            Generated text (JSON string if structured generation used) or None
        """
        if not self.llm:
            logger.error("Provider not initialized")
            return None
        
        try:
            import json
            
            # CRITICAL FIX: Check if Outlines wrapper is actually working
            # If we have a wrapped model, it won't have .generate() method
            is_wrapped = self.outlines_available and hasattr(self.llm, '__wrapped__')
            
            # Apply Qwen chat template to prompt for all strategies
            formatted_prompt = f"""<|im_start|>system
You are a helpful assistant that outputs only valid JSON as requested.<|im_end|>
<|im_start|>user
{prompt}<|im_end|>
<|im_start|>assistant
"""
            
            # STRATEGY 1: Use Pydantic output_type if provided (STRONGEST - PREFERRED)
            if output_type and self.outlines_available and PYDANTIC_AVAILABLE:
                logger.info(f"Attempting Outlines Pydantic generation for {task_type}")
                try:
                    # Use Outlines with Pydantic model
                    generator = generate.json(self.llm, output_type)
                    response = generator(formatted_prompt)
                    
                    # Convert Pydantic model to JSON string
                    if isinstance(response, BaseModel):
                        result = response.model_dump_json(indent=2)
                        logger.info(f"✓ Outlines Pydantic generation successful for {task_type}")
                        return result
                    elif isinstance(response, dict):
                        result = json.dumps(response, indent=2)
                        logger.info(f"✓ Outlines dict generation successful for {task_type}")
                        return result
                    elif isinstance(response, str):
                        # Already a JSON string
                        logger.info(f"✓ Outlines string generation successful for {task_type}")
                        return response
                    else:
                        logger.warning(f"Unexpected response type from Outlines: {type(response)}, value: {response}")
                        # Fall through to regular generation
                        
                except Exception as e:
                    logger.error(f"Outlines Pydantic generation failed: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # Fall through to next strategy
            
            # STRATEGY 2: Use JSON schema if provided (legacy support)
            elif schema and self.outlines_available:
                logger.info(f"Attempting Outlines schema generation for {task_type}")
                try:
                    generator = generate.json(self.llm, schema)
                    response = generator(formatted_prompt)
                    
                    # Convert response to JSON string
                    if isinstance(response, dict):
                        result = json.dumps(response, indent=2)
                        logger.info(f"✓ Outlines schema generation successful for {task_type}")
                        return result
                    elif isinstance(response, str):
                        logger.info(f"✓ Outlines schema string generation successful for {task_type}")
                        return response
                    else:
                        result = str(response)
                        logger.info(f"✓ Outlines generation successful for {task_type}")
                        return result
                        
                except Exception as e:
                    logger.error(f"Outlines schema generation failed: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # Fall through to regular generation
            
            # STRATEGY 3: Regular vLLM generation (fallback)
            logger.info(f"Using regular vLLM generation for {task_type}")
            
            # Check if we need to unwrap the model
            vllm_model = self.llm
            if is_wrapped and hasattr(self.llm, 'model'):
                vllm_model = self.llm.model
                logger.debug("Using unwrapped vLLM model for regular generation")
            
            from vllm import SamplingParams
            
            # CRITICAL: Apply Qwen chat template to prompt
            # Qwen expects messages in chat format, not raw text
            formatted_prompt = f"""<|im_start|>system
You are a helpful assistant that outputs only valid JSON as requested.<|im_end|>
<|im_start|>user
{prompt}<|im_end|>
<|im_start|>assistant
"""
            
            # Set up sampling parameters
            sampling_params = SamplingParams(
                temperature=temperature if temperature > 0 else 0.0,
                max_tokens=max_tokens,
                top_p=0.95,
                top_k=50,
                repetition_penalty=1.1,
                stop=["</s>", "<|endoftext|>", "<|im_end|>"]  # Qwen-specific stop tokens
            )
            
            outputs = vllm_model.generate([formatted_prompt], sampling_params)
            
            if not outputs or len(outputs) == 0:
                logger.error("No output generated from vLLM")
                return None
            
            raw_response = outputs[0].outputs[0].text.strip()
            
            # Log raw response for debugging (truncated)
            logger.info(f"Raw vLLM response (task: {task_type}): {raw_response[:200]}...")
            
            # ROBUST PARSING: Extract JSON from response even if it has extra text
            if schema or output_type:
                # This should be JSON - try to extract it
                parsed_json, error = extract_json_from_text(raw_response)
                
                if parsed_json:
                    cleaned_response = json.dumps(parsed_json, indent=2)
                    logger.info(f"✓ Extracted valid JSON from vLLM response for {task_type}")
                    return cleaned_response
                else:
                    logger.error(f"Failed to extract JSON from vLLM response for {task_type}: {error}")
                    logger.error(f"Raw response: {raw_response[:500]}...")
                    # Return None instead of raw response to signal failure
                    return None
            
            # Not expecting JSON - return as is
            return raw_response
            
        except Exception as e:
            logger.error(f"Qwen2.5-72B generation error (task: {task_type}): {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None


class DeepSeekProvider(LLMProvider):
    """DeepSeek-V2.5 provider using vLLM with tensor parallelism (local only)."""
    
    def __init__(self, model_name: str = None, tensor_parallel_size: int = 4):
        # Use environment variable or provided path
        if model_name:
            resolved_model = model_name
        else:
            # Default path follows same pattern as Qwen
            base_path = os.getenv('QWEN_MODEL_PATH', '/scratch/gpfs/JORDANAT/mg9965/models/Qwen--Qwen3-32B')
            resolved_model = base_path.replace('Qwen--Qwen3-32B', 'deepseek-ai--DeepSeek-V2.5')
            # Check if custom env var is set
            resolved_model = os.getenv('DEEPSEEK_MODEL_PATH', resolved_model)
        
        super().__init__("deepseek", resolved_model)
        self.tensor_parallel_size = tensor_parallel_size
        self.llm = None  # vLLM LLM instance
    
    def initialize(self) -> bool:
        try:
            from vllm import LLM
            
            logger.info(f"Loading DeepSeek-V2.5 model from: {self.model_name} with TP={self.tensor_parallel_size}")
            
            # Force offline mode to prevent downloads
            os.environ['HF_HUB_OFFLINE'] = '1'
            
            # Check if path exists
            if not os.path.exists(self.model_name):
                logger.error(f"Model path does not exist: {self.model_name}")
                logger.error("Make sure the model is downloaded to the cache or local directory")
                return False
            
            # Verify required files exist
            required_files = ['config.json', 'tokenizer.json', 'tokenizer_config.json']
            missing_files = [f for f in required_files if not os.path.exists(os.path.join(self.model_name, f))]
            if missing_files:
                logger.error(f"Model incomplete, missing: {missing_files}")
                logger.error(f"Check model directory: {self.model_name}")
                return False
            
            logger.info("✓ Model files verified, loading DeepSeek-V2.5 with vLLM...")
            # Use vLLM with tensor parallelism
            self.llm = LLM(
                model=self.model_name,
                tensor_parallel_size=self.tensor_parallel_size,  # Enable TP=4
                dtype="auto",
                trust_remote_code=True,
                max_model_len=4096,  # Adjust based on needs
                gpu_memory_utilization=0.9,  # Optimize GPU usage
            )
            
            logger.info(f"✓ DeepSeek-V2.5 model loaded successfully from {self.model_name} with TP={self.tensor_parallel_size}")
            return True
            
        except ImportError:
            logger.error("vllm package not installed. Run: pip install vllm")
            return False
        except Exception as e:
            logger.error(f"Failed to load DeepSeek-V2.5 model: {e}")
            logger.error("Make sure:")
            logger.error("1. Model is downloaded to the correct path")
            logger.error("2. HF_HOME is set to the cache directory")
            logger.error("3. All required model files are present")
            logger.error("4. Sufficient GPU memory available (requires 4 GPUs for TP=4)")
            return False
    
    def generate(self, prompt: str, max_tokens: int = 4096, temperature: float = 0.0) -> Optional[str]:
        """Generate completion from DeepSeek-V2.5 using vLLM."""
        if not self.llm:
            logger.error("Provider not initialized")
            return None
        
        try:
            from vllm import SamplingParams
            
            # Set up sampling parameters
            sampling_params = SamplingParams(
                temperature=temperature if temperature > 0 else 0.0,
                max_tokens=max_tokens,
                stop=None,  # Add stop tokens if needed
            )
            
            # Generate response
            outputs = self.llm.generate([prompt], sampling_params)
            response = outputs[0].outputs[0].text
            
            return response
            
        except Exception as e:
            logger.error(f"DeepSeek-V2.5 generation error: {e}")
            return None


class LocalProvider(LLMProvider):
    """Local model provider using vLLM."""
    
    def __init__(self, model_name: str, vllm_url: str = "http://localhost:8000/v1"):
        super().__init__("local", model_name)
        self.vllm_url = vllm_url
    
    def initialize(self) -> bool:
        try:
            import openai
            
            # vLLM provides OpenAI-compatible API
            self.client = openai.OpenAI(
                base_url=self.vllm_url,
                api_key="dummy"  # vLLM doesn't require a real key
            )
            
            logger.info(f"Local provider initialized: {self.model_name} at {self.vllm_url}")
            return True
            
        except ImportError:
            logger.error("openai package not installed. Run: pip install openai")
            return False
    
    def generate(self, prompt: str, max_tokens: int = 4096, temperature: float = 0.0) -> Optional[str]:
        """Generate completion from local vLLM server."""
        if not self.client:
            logger.error("Provider not initialized")
            return None
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Local vLLM error: {e}")
            return None


def create_provider(provider: str, model: Optional[str] = None, **kwargs) -> Optional[LLMProvider]:
    """
    Factory function to create LLM providers.
    
    Args:
        provider: Provider name (claude, openai, qwen, qwen72b, deepseek, local)
        model: Model name (optional, uses defaults)
        **kwargs: Additional provider-specific arguments
        
    Returns:
        Initialized LLMProvider or None
    """
    providers = {
        'claude': ClaudeProvider,
        'openai': OpenAIProvider,
        'qwen': QwenProvider,
        'qwen72b': Qwen72BProvider,
        'deepseek': DeepSeekProvider,
        'local': LocalProvider
    }
    
    provider_class = providers.get(provider.lower())
    if not provider_class:
        logger.error(f"Unknown provider: {provider}")
        return None
    
    # Create provider instance
    if model:
        provider_instance = provider_class(model_name=model, **kwargs)
    else:
        provider_instance = provider_class(**kwargs)
    
    # Initialize
    if not provider_instance.initialize():
        logger.error(f"Failed to initialize {provider} provider")
        return None
    
    return provider_instance
