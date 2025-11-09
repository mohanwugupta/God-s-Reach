#!/bin/bash
#SBATCH --job-name=extraction-deepseek
#SBATCH --nodes=1
#SBATCH --ntasks=1             # Single task (not MPI)
#SBATCH --cpus-per-task=8      # 8 CPUs for PDF parsing + tokenization parallelism
#SBATCH --mem=512G             # High memory for 236B model
#SBATCH --gres=gpu:8           # Request 8 GPUs for DeepSeek-V2.5 (236B params, needs ~300GB+ VRAM)
#SBATCH --constraint=gpu80
#SBATCH --mail-type=begin
#SBATCH --mail-type=end
#SBATCH --mail-user=your-email@domain.edu
#SBATCH --time=6:00:00         # Longer time for massive model
#SBATCH --output=logs/batch_extraction_deepseek_%j.out
#SBATCH --error=logs/batch_extraction_deepseek_%j.err

# Design Space Extractor: Batch PDF Extraction with DeepSeek-V2.5
# Extracts parameters from motor adaptation papers using regex + DeepSeek-V2.5 LLM (236B params)

echo "🚀 Starting Design Space Batch Extraction (DeepSeek-V2.5)"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURMD_NODENAME"
echo "Time: $(date)"
echo "GPUs: $CUDA_VISIBLE_DEVICES"

# Change to project directory (adjust path as needed)
cd /scratch/gpfs/JORDANAT/mg9965/God-s-Reach/designspace_extractor

# Load required modules
module load anaconda3/2025.6

# Activate Python environment
if command -v conda &> /dev/null; then
    eval "$(conda shell.bash hook)"
    conda activate godsreach2  # Adjust environment name
elif [ -f ~/.conda/envs/godsreach/bin/activate ]; then
    source ~/.conda/envs/godsreach2/bin/activate
else
    source activate godsreach2
fi

# Set up environment for DeepSeek-V2.5 model
export HF_HOME=/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/models
export TRANSFORMERS_CACHE=/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/models
export HF_DATASETS_CACHE=/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/models

# Redirect ALL vLLM and compilation caches to scratch (avoid home directory disk quota)
export VLLM_CACHE_DIR=/scratch/gpfs/JORDANAT/mg9965/vLLM-cache
export VLLM_USAGE_STATS_DIR=/scratch/gpfs/JORDANAT/mg9965/vLLM-cache/usage_stats
export TRITON_CACHE_DIR=/scratch/gpfs/JORDANAT/mg9965/vLLM-cache/triton
export XDG_CACHE_HOME=/scratch/gpfs/JORDANAT/mg9965/vLLM-cache/xdg

# Create cache directories
mkdir -p $VLLM_CACHE_DIR
mkdir -p $VLLM_USAGE_STATS_DIR
mkdir -p $TRITON_CACHE_DIR
mkdir -p $XDG_CACHE_HOME

# CPU & Threading Configuration (use all 8 allocated CPUs)
export OMP_NUM_THREADS=8
export TOKENIZERS_PARALLELISM=true

# PyTorch CUDA Memory Optimization (from PyTorch tuning guide)
# Reduces memory fragmentation which can cause OOM errors
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# NCCL Configuration for 8x A100 on single node
export NCCL_P2P_LEVEL=NVL
export CUDA_DEVICE_MAX_CONNECTIONS=1

# LLM Configuration - USE DEEPSEEK PROVIDER
export LLM_ENABLE=true
export LLM_PROVIDER=deepseek
export LLM_MODE=verify  # 'verify' checks ALL parameters, 'fallback' only low-confidence
export DEEPSEEK_MODEL_PATH=/scratch/gpfs/JORDANAT/mg9965/models/deepseek-ai--DeepSeek-V2.5

# Force offline mode (compute nodes typically have no internet)
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# GPU configuration - all 8 GPUs
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7

# Create output directories
mkdir -p logs
mkdir -p designspace_extractor/out/logs

echo ""
echo "📂 Environment Setup:"
echo "  Working directory: $(pwd)"
echo "  Python: $(which python)"
echo "  Python version: $(python --version)"
echo "  Model path: $DEEPSEEK_MODEL_PATH"
echo "  LLM provider: $LLM_PROVIDER"
echo "  LLM enabled: $LLM_ENABLE"
echo ""

# Check if model exists
if [ -d "$DEEPSEEK_MODEL_PATH" ]; then
    echo "✅ DeepSeek-V2.5 model found at: $DEEPSEEK_MODEL_PATH"
else
    echo "⚠️  WARNING: DeepSeek-V2.5 model not found at: $DEEPSEEK_MODEL_PATH"
    echo "   LLM-assisted extraction will be disabled"
    export LLM_ENABLE=false
fi

# Check if papers directory exists
if [ -d "../papers" ]; then
    PAPER_COUNT=$(ls -1 ../papers/*.pdf 2>/dev/null | wc -l)
    echo "✅ Found $PAPER_COUNT PDF files in papers directory"
else
    echo "❌ ERROR: Papers directory not found"
    echo "   Expected: papers/"
    exit 1
fi

echo ""

echo ""
echo "📊 Running batch extraction with DeepSeek-V2.5..."
echo "   Input: ../papers"
echo "   Output: batch_processing_results_deepseek.json"
echo ""

# Run batch extraction
python run_batch_extraction.py \
    --papers "../papers" \
    --output "batch_processing_results_deepseek.json"

EXTRACT_EXIT=$?

if [ $EXTRACT_EXIT -ne 0 ]; then
    echo "❌ Extraction failed with exit code: $EXTRACT_EXIT"
    exit $EXTRACT_EXIT
fi

echo ""
echo "=================================================================================="
echo "EXTRACTION RESULTS (DeepSeek-V2.5)"
echo "=================================================================================="

# Check results
if [ -f "batch_processing_results_deepseek.json" ]; then
    SUCCESS=$(python -c "import json; d=json.load(open('batch_processing_results_deepseek.json')); print(sum(1 for r in d if r['success']))")
    TOTAL=$(python -c "import json; d=json.load(open('batch_processing_results_deepseek.json')); print(len(d))")
    echo "   Successful: $SUCCESS / $TOTAL papers"
    
    # Run validation (offline mode)
    echo ""
    echo "🔍 Validating against gold standard..."
    
    if [ -f "../validation/gold_standard.csv" ]; then
        echo "   Using local gold standard: ../validation/gold_standard.csv"
        python validation/validator_public.py \
            --local-file ../validation/gold_standard.csv \
            --results 'batch_processing_results_deepseek.json' | tee validation_report_deepseek.txt
    else
        echo "⚠️  Local gold standard not found at: ../validation/gold_standard.csv"
        echo "   Run on login node: python validation/download_gold_standard.py"
    fi
fi

# Check LLM usage if enabled
if [ "$LLM_ENABLE" = "true" ] && [ -f "out/logs/llm_usage.log" ]; then
    echo ""
    echo "🤖 LLM Usage Summary (DeepSeek-V2.5):"
    LLM_CALLS=$(wc -l < out/logs/llm_usage.log)
    echo "   Total LLM inferences: $LLM_CALLS"
    
    if [ $LLM_CALLS -gt 0 ]; then
        echo "   LLM usage log: out/logs/llm_usage.log"
    fi
fi

echo ""
echo "✅ Job completed at $(date)"
echo "============================================"
