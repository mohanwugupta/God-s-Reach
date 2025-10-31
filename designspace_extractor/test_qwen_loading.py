#!/usr/bin/env python
"""
Quick diagnostic to test Qwen model loading.
Run this BEFORE full extraction to identify loading issues.
"""
import os
import sys
import logging
import signal
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Custom timeout exception."""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeouts."""
    raise TimeoutError("Operation timed out")


def test_qwen_loading():
    """Test Qwen model loading step by step."""
    
    model_path = os.getenv('QWEN_MODEL_PATH', '/scratch/gpfs/JORDANAT/mg9965/models/Qwen--Qwen3-32B')
    
    logger.info("=" * 60)
    logger.info("QWEN MODEL LOADING DIAGNOSTIC")
    logger.info("=" * 60)
    
    # Step 1: Check files
    logger.info(f"\n1. Checking model path: {model_path}")
    if not os.path.exists(model_path):
        logger.error(f"❌ Model path does not exist!")
        logger.error(f"   Set QWEN_MODEL_PATH environment variable")
        return False
    logger.info(f"✓ Path exists")
    
    files = os.listdir(model_path)
    logger.info(f"✓ Found {len(files)} files")
    
    required = ['config.json', 'tokenizer.json', 'tokenizer_config.json']
    for req in required:
        if req in files:
            logger.info(f"  ✓ {req}")
        else:
            logger.warning(f"  ⚠ {req} missing")
    
    # Check for model weights
    model_files = [f for f in files if 'model' in f.lower() and ('.safetensors' in f or '.bin' in f)]
    logger.info(f"  Found {len(model_files)} model weight files")
    
    # Step 2: CUDA check
    logger.info("\n2. Checking CUDA...")
    try:
        import torch
    except ImportError:
        logger.error("❌ PyTorch not installed!")
        return False
    
    if not torch.cuda.is_available():
        logger.error("❌ CUDA not available!")
        logger.error("   Check CUDA drivers and PyTorch installation")
        return False
    
    logger.info(f"✓ CUDA available")
    logger.info(f"  Device: {torch.cuda.get_device_name(0)}")
    logger.info(f"  Total Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    
    free_mem, total_mem = torch.cuda.mem_get_info(0)
    logger.info(f"  Free Memory: {free_mem / 1e9:.1f} GB")
    logger.info(f"  Used Memory: {(total_mem - free_mem) / 1e9:.1f} GB")
    
    if free_mem / 1e9 < 60:
        logger.warning(f"⚠ Only {free_mem / 1e9:.1f} GB free (need ~64GB for Qwen3-32B)")
        logger.warning("  Consider freeing GPU memory or using a smaller model")
    
    # Step 3: Try vLLM first (recommended)
    logger.info("\n3. Testing vLLM availability...")
    try:
        from vllm import LLM
        logger.info("✓ vLLM installed")
        logger.info("  Attempting vLLM initialization (timeout: 5 minutes)...")
        
        # Set timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(300)  # 5 minute timeout
        
        try:
            llm = LLM(
                model=model_path,
                tensor_parallel_size=1,
                gpu_memory_utilization=0.9,
                trust_remote_code=True,
                enforce_eager=True,
            )
            signal.alarm(0)  # Cancel timeout
            logger.info("✓✓✓ vLLM loaded successfully!")
            logger.info("    Your setup is working correctly!")
            del llm
            torch.cuda.empty_cache()
            return True
            
        except TimeoutError as e:
            signal.alarm(0)
            logger.error(f"❌ vLLM loading timed out after 5 minutes")
            logger.error("   This indicates a problem with:")
            logger.error("   - Model files (may be corrupted)")
            logger.error("   - CUDA drivers (incompatibility)")
            logger.error("   - GPU memory (fragmentation)")
            return False
        except Exception as e:
            signal.alarm(0)
            logger.error(f"❌ vLLM failed: {e}")
            logger.info("   Will try transformers instead...")
            
    except ImportError:
        logger.info("  vLLM not installed")
        logger.info("  Install with: pip install vllm")
        logger.info("  Will try transformers instead...")
    
    # Step 4: Try transformers
    logger.info("\n4. Testing transformers...")
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        
        logger.info("  Step 4a: Loading tokenizer (timeout: 2 minutes)...")
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(120)  # 2 minute timeout
        
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=True,
                local_files_only=True
            )
            signal.alarm(0)
            logger.info("  ✓ Tokenizer loaded")
        except TimeoutError:
            signal.alarm(0)
            logger.error("  ❌ Tokenizer loading timed out")
            logger.error("     This suggests network issues or corrupted files")
            return False
        except Exception as e:
            signal.alarm(0)
            logger.error(f"  ❌ Tokenizer loading failed: {e}")
            return False
        
        logger.info("  Step 4b: Loading model (timeout: 10 minutes)...")
        logger.info("             This is the most common place for hangs...")
        logger.info("             Watch GPU memory with: nvidia-smi")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(600)  # 10 minute timeout
        
        try:
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.bfloat16,
                device_map="cuda:0",
                trust_remote_code=True,
                attn_implementation="eager",
                max_memory={0: "72GiB"},
                low_cpu_mem_usage=True,
                local_files_only=True,
            )
            signal.alarm(0)  # Cancel timeout
            logger.info("  ✓✓✓ Model loaded successfully!")
            logger.info(f"      Device: {next(model.parameters()).device}")
            logger.info("      Your setup is working correctly!")
            
            # Test a quick inference
            logger.info("\n5. Testing quick inference...")
            try:
                inputs = tokenizer("Hello, how are you?", return_tensors="pt").to("cuda:0")
                outputs = model.generate(**inputs, max_new_tokens=10)
                response = tokenizer.decode(outputs[0], skip_special_tokens=True)
                logger.info(f"  ✓ Inference works! Response: {response[:50]}...")
                logger.info("\n🎉 ALL TESTS PASSED! Your model is ready to use.")
            except Exception as e:
                logger.warning(f"  ⚠ Inference test failed: {e}")
                logger.info("     Model loaded but inference has issues")
            
            del model
            torch.cuda.empty_cache()
            return True
            
        except TimeoutError:
            signal.alarm(0)
            logger.error("  ❌❌❌ Model loading TIMED OUT after 10 minutes!")
            logger.error("\n  DIAGNOSIS:")
            logger.error("  This is the hanging issue you're experiencing.")
            logger.error("\n  Possible causes:")
            logger.error("  1. CUDA driver incompatibility with PyTorch")
            logger.error("     Fix: Update CUDA drivers or use compatible PyTorch")
            logger.error("  2. GPU memory fragmentation")
            logger.error("     Fix: Restart GPU, clear all CUDA processes")
            logger.error("  3. Corrupted model files")
            logger.error("     Fix: Re-download model from HuggingFace")
            logger.error("  4. device_map='cuda:0' forcing issue")
            logger.error("     Fix: Try device_map='auto' instead")
            logger.error("\n  Recommended actions:")
            logger.error("  - Check: nvidia-smi (is GPU stuck?)")
            logger.error("  - Try: pkill -9 python (kill stuck processes)")
            logger.error("  - Try: sudo nvidia-smi --gpu-reset (reset GPU)")
            logger.error("  - Try: Re-download model files")
            return False
            
        except torch.cuda.OutOfMemoryError as e:
            signal.alarm(0)
            logger.error(f"  ❌ GPU Out of Memory: {e}")
            logger.error("     Free up GPU memory or use a smaller model")
            return False
        except Exception as e:
            signal.alarm(0)
            logger.error(f"  ❌ Model loading failed: {e}")
            logger.exception("     Full traceback:")
            return False
            
    except ImportError as e:
        logger.error(f"❌ Transformers not installed: {e}")
        logger.error("   Install with: pip install transformers torch")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        logger.exception("Full traceback:")
        return False


def main():
    """Main entry point."""
    logger.info("Starting Qwen model diagnostic...")
    logger.info("This will help identify why model loading hangs.\n")
    
    try:
        success = test_qwen_loading()
        
        if success:
            logger.info("\n" + "=" * 60)
            logger.info("✅ DIAGNOSTIC COMPLETE - ALL TESTS PASSED")
            logger.info("=" * 60)
            logger.info("Your model is ready for extraction!")
            sys.exit(0)
        else:
            logger.error("\n" + "=" * 60)
            logger.error("❌ DIAGNOSTIC COMPLETE - ISSUES FOUND")
            logger.error("=" * 60)
            logger.error("Fix the issues above before running extraction.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("\n⚠ Diagnostic interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ Diagnostic crashed: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()
