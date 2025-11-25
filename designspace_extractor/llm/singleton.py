"""
Singleton LLM Manager to prevent OOM from multiple vLLM instances.

Problem: When running parallel PDF extraction, each worker tries to load
the 72B model independently, causing GPU OOM.

Solution: Use a global singleton that ensures only one vLLM instance is
created and shared across all workers.
"""
import logging
import threading
from typing import Optional
from .providers import Qwen72BProvider

logger = logging.getLogger(__name__)


class LLMSingletonManager:
    """
    Thread-safe singleton manager for vLLM instances.
    
    Ensures only one Qwen2.5-72B model is loaded across all parallel workers.
    """
    _instance = None
    _lock = threading.Lock()
    _llm_provider: Optional[Qwen72BProvider] = None
    _initialization_lock = threading.Lock()
    _is_initializing = False
    _initialization_failed = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_provider(self, model_path: str = None, tensor_parallel_size: int = 4) -> Optional[Qwen72BProvider]:
        """
        Get or create the shared LLM provider.
        
        Args:
            model_path: Path to Qwen2.5-72B model
            tensor_parallel_size: Number of GPUs for tensor parallelism
            
        Returns:
            Qwen72BProvider instance or None if initialization failed
        """
        # Quick check without lock
        if self._llm_provider is not None:
            logger.debug("Reusing existing LLM provider (singleton)")
            return self._llm_provider
        
        # If initialization already failed, don't retry
        if self._initialization_failed:
            logger.warning("LLM initialization previously failed, not retrying")
            return None
        
        # Check if another thread is initializing
        with self._initialization_lock:
            # Double-check after acquiring lock
            if self._llm_provider is not None:
                return self._llm_provider
            
            # Check if we're already initializing
            if self._is_initializing:
                logger.info("Another thread is initializing LLM, waiting...")
                # Wait for initialization to complete
                while self._is_initializing:
                    import time
                    time.sleep(0.5)
                
                # Return result (may be None if initialization failed)
                return self._llm_provider
            
            # Mark as initializing
            self._is_initializing = True
            logger.info("🔄 Initializing shared LLM provider (singleton)...")
            
            try:
                # Create provider
                provider = Qwen72BProvider(
                    model_name=model_path,
                    tensor_parallel_size=tensor_parallel_size
                )
                
                # Initialize
                if provider.initialize():
                    self._llm_provider = provider
                    logger.info("✅ Shared LLM provider initialized successfully")
                    return self._llm_provider
                else:
                    logger.error("❌ LLM provider initialization failed")
                    self._initialization_failed = True
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Exception during LLM initialization: {e}")
                self._initialization_failed = True
                return None
                
            finally:
                self._is_initializing = False
    
    def reset(self):
        """
        Reset the singleton (for testing/cleanup).
        
        WARNING: This will NOT unload the vLLM model from GPU memory.
        Only use this for testing or when you're sure no workers are using the model.
        """
        with self._initialization_lock:
            self._llm_provider = None
            self._is_initializing = False
            self._initialization_failed = False
            logger.warning("⚠️ LLM singleton reset (model still in GPU memory)")


# Global singleton instance
_singleton_manager = LLMSingletonManager()


def get_shared_llm_provider(model_path: str = None, tensor_parallel_size: int = 4) -> Optional[Qwen72BProvider]:
    """
    Get the shared LLM provider (singleton).
    
    This is the main entry point for all code that needs the LLM.
    
    Args:
        model_path: Path to Qwen2.5-72B model (only used on first call)
        tensor_parallel_size: Number of GPUs (only used on first call)
        
    Returns:
        Qwen72BProvider instance or None if initialization failed
        
    Example:
        >>> llm = get_shared_llm_provider('/path/to/qwen', tensor_parallel_size=4)
        >>> if llm:
        >>>     result = llm.generate("prompt here")
    """
    return _singleton_manager.get_provider(model_path, tensor_parallel_size)
