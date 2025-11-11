#!/usr/bin/env python3
"""
Pre-cache tiktoken encodings and sentence-transformers models for offline use.

Run this script on a machine with internet access to download and cache
required models, then transfer the cache directory to the cluster.

Usage:
    python cache_tiktoken.py
    
This will download:
- tiktoken encodings to ~/.tiktoken_cache/
- sentence-transformers models to ~/.cache/huggingface/
"""
import os
import sys
from pathlib import Path

def cache_tiktoken_encoding():
    """Download and cache tiktoken encoding."""
    try:
        import tiktoken
    except ImportError:
        print("WARNING: tiktoken not installed. Install with: pip install tiktoken")
        return False
    
    # Set cache directory
    cache_dir = Path.home() / ".tiktoken_cache"
    cache_dir.mkdir(exist_ok=True)
    
    # Set environment variable for tiktoken
    os.environ['TIKTOKEN_CACHE_DIR'] = str(cache_dir)
    
    print(f"📦 Caching tiktoken encodings to: {cache_dir}")
    
    # Download encodings
    encodings = ['cl100k_base', 'p50k_base', 'r50k_base']
    
    for enc_name in encodings:
        try:
            print(f"  Downloading {enc_name}...", end=" ")
            enc = tiktoken.get_encoding(enc_name)
            print("✓")
        except Exception as e:
            print(f"✗ ({e})")
    
    print(f"✅ Tiktoken encodings cached successfully!")
    return True


def cache_sentence_transformers():
    """Download and cache sentence-transformers model."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("WARNING: sentence-transformers not installed. Install with: pip install sentence-transformers")
        return False
    
    # Set cache directory (HuggingFace standard location)
    cache_dir = Path.home() / ".cache" / "huggingface"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Set environment variables for HuggingFace
    os.environ['HF_HOME'] = str(cache_dir)
    os.environ['TRANSFORMERS_CACHE'] = str(cache_dir / "transformers")
    
    print(f"\n📦 Caching sentence-transformers models to: {cache_dir}")
    
    # Download the specific model used in RAG pipeline
    model_name = 'sentence-transformers/all-MiniLM-L6-v2'
    
    try:
        print(f"  Downloading {model_name}...")
        print(f"  (This may take a few minutes - model is ~90MB)")
        model = SentenceTransformer(model_name)
        
        # Test encoding
        test_embedding = model.encode(["test sentence"])
        print(f"  ✓ Model loaded successfully (embedding dim: {test_embedding.shape[1]})")
        
        print(f"✅ Sentence-transformers model cached successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Failed to cache model: {e}")
        return False


def print_transfer_instructions():
    """Print instructions for transferring cache to cluster."""
    tiktoken_cache = Path.home() / ".tiktoken_cache"
    hf_cache = Path.home() / ".cache" / "huggingface"
    
    print(f"\n" + "="*70)
    print("📋 TRANSFER INSTRUCTIONS FOR CLUSTER")
    print("="*70)
    
    print(f"\n1️⃣  Transfer tiktoken cache:")
    print(f"   scp -r {tiktoken_cache} cluster:/home/username/.tiktoken_cache")
    
    print(f"\n2️⃣  Transfer HuggingFace cache:")
    print(f"   scp -r {hf_cache} cluster:/home/username/.cache/huggingface")
    
    print(f"\n3️⃣  Add to SLURM script:")
    print(f"   export TIKTOKEN_CACHE_DIR=$HOME/.tiktoken_cache")
    print(f"   export HF_HOME=$HOME/.cache/huggingface")
    print(f"   export TRANSFORMERS_CACHE=$HOME/.cache/huggingface/transformers")
    print(f"   export HF_HUB_OFFLINE=1  # Force offline mode")
    print(f"   export TRANSFORMERS_OFFLINE=1")
    
    print(f"\n4️⃣  Verify on cluster:")
    print(f"   ls -lh $HOME/.tiktoken_cache/")
    print(f"   ls -lh $HOME/.cache/huggingface/hub/")
    
    print(f"\n" + "="*70)
    print("✅ All caches ready for offline use!")
    print("="*70 + "\n")


if __name__ == "__main__":
    print("🚀 Pre-caching models for offline cluster use...\n")
    
    tiktoken_ok = cache_tiktoken_encoding()
    st_ok = cache_sentence_transformers()
    
    if tiktoken_ok or st_ok:
        print_transfer_instructions()
    else:
        print("\n❌ No caches were created. Install required packages:")
        print("   pip install tiktoken sentence-transformers")
        sys.exit(1)
