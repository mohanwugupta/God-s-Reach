#!/bin/bash
# Fix Python 3.10 Environment Setup
# Run this on the cluster to fix missing dependencies and disk quota issues

echo "🔧 Fixing Python 3.10 Environment Setup"
echo "========================================"

# Activate the Python 3.10 environment
conda activate godsreach2

echo ""
echo "1. Installing missing 'accelerate' package..."
pip install accelerate

echo ""
echo "2. Cleaning up home directory caches to free space..."

# Calculate current usage
echo "Current home directory usage:"
du -sh ~/.cache 2>/dev/null || echo "  ~/.cache: Not found or empty"
du -sh ~/.config 2>/dev/null || echo "  ~/.config: Not found or empty"

echo ""
echo "Cleaning old caches..."

# Clean pip cache
if [ -d ~/.cache/pip ]; then
    echo "  Cleaning pip cache..."
    rm -rf ~/.cache/pip/*
fi

# Clean vLLM cache (we'll redirect to scratch)
if [ -d ~/.cache/vllm ]; then
    echo "  Removing vLLM cache (will use scratch instead)..."
    rm -rf ~/.cache/vllm
fi

# Clean config directories that may be large
if [ -d ~/.config/vllm ]; then
    echo "  Removing vLLM config..."
    rm -rf ~/.config/vllm
fi

# Clean huggingface cache if duplicated
if [ -d ~/.cache/huggingface ]; then
    echo "  Cleaning HuggingFace cache (using scratch instead)..."
    rm -rf ~/.cache/huggingface
fi

echo ""
echo "3. Creating vLLM cache directory on scratch..."
mkdir -p /scratch/gpfs/JORDANAT/mg9965/God-s-Reach/models/vllm_cache
echo "  Created: /scratch/gpfs/JORDANAT/mg9965/God-s-Reach/models/vllm_cache"

echo ""
echo "4. Checking disk usage after cleanup..."
echo "Home directory usage:"
du -sh ~/ 2>/dev/null || echo "  Unable to calculate"
echo ""
quota -s 2>/dev/null || echo "  Quota command not available"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Test the diagnostic: sbatch slurm/test_qwen_loading.sh"
echo "  2. Run batch extraction: sbatch slurm/run_batch_extraction.sh"
echo ""
echo "Note: vLLM cache is now redirected to /scratch to avoid home quota issues."
