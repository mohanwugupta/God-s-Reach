#!/usr/bin/env python3
"""
Pre-cache tiktoken encodings for offline use.

Run this script on a machine with internet access to download and cache
the tiktoken encoding file, then transfer the cache directory to the cluster.

Usage:
    python cache_tiktoken.py
    
This will download cl100k_base.tiktoken to ~/.tiktoken_cache/
"""
import os
import sys
from pathlib import Path

def cache_tiktoken_encoding():
    """Download and cache tiktoken encoding."""
    try:
        import tiktoken
    except ImportError:
        print("ERROR: tiktoken not installed. Install with: pip install tiktoken")
        sys.exit(1)
    
    # Set cache directory
    cache_dir = Path.home() / ".tiktoken_cache"
    cache_dir.mkdir(exist_ok=True)
    
    # Set environment variable for tiktoken
    os.environ['TIKTOKEN_CACHE_DIR'] = str(cache_dir)
    
    print(f"Caching tiktoken encodings to: {cache_dir}")
    
    # Download encodings
    encodings = ['cl100k_base', 'p50k_base', 'r50k_base']
    
    for enc_name in encodings:
        try:
            print(f"  Downloading {enc_name}...", end=" ")
            enc = tiktoken.get_encoding(enc_name)
            print("✓")
        except Exception as e:
            print(f"✗ ({e})")
    
    print(f"\n✅ Encodings cached successfully!")
    print(f"\nTo use on cluster, set environment variable:")
    print(f"  export TIKTOKEN_CACHE_DIR={cache_dir}")
    print(f"\nOr copy cache directory to cluster:")
    print(f"  scp -r {cache_dir} cluster:/path/to/.tiktoken_cache")


if __name__ == "__main__":
    cache_tiktoken_encoding()
