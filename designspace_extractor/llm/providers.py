"""
LLM provider initialization and configuration.

Supports Claude, OpenAI, Qwen (transformers), and local models via vLLM.
"""
import logging
import os
from typing import Optional, Any

logger = logging.getLogger(__name__)


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
        provider: Provider name (claude, openai, qwen, local)
        model: Model name (optional, uses defaults)
        **kwargs: Additional provider-specific arguments
        
    Returns:
        Initialized LLMProvider or None
    """
    providers = {
        'claude': ClaudeProvider,
        'openai': OpenAIProvider,
        'qwen': QwenProvider,
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
