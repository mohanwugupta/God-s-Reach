#!/bin/bash
#SBATCH --job-name=design-space-extraction
#SBATCH --nodes=1
#SBATCH --ntasks=1             # Single task (not MPI)
#SBATCH --cpus-per-task=8      # 8 CPUs for PDF parsing + tokenization parallelism
#SBATCH --mem=128G             # Memory for processing multiple PDFs
#SBATCH --gres=gpu:2           # Request 2 GPUs to split 72GB model (40GB each + inference headroom)
#SBATCH --constraint=gpu80
#SBATCH --mail-type=begin
#SBATCH --mail-type=end
#SBATCH --mail-user=your-email@domain.edu
#SBATCH --time=1:00:00        # Adjust based on number of papers
#SBATCH --output=logs/batch_extraction_%j.out
#SBATCH --error=logs/batch_extraction_%j.err

# Design Space Extractor: Batch PDF Extraction with LLM Assistance
# Extracts parameters from motor adaptation papers using regex + Qwen3-32B LLM

echo "🚀 Starting Design Space Batch Extraction"
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

# Set up environment for Qwen3-32B model
# CRITICAL: Set offline mode FIRST before any Python imports
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# Point to HuggingFace cache directory
export HF_HOME=/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/models
export TRANSFORMERS_CACHE=/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/models
export HF_DATASETS_CACHE=/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/models

# Redirect ALL vLLM and compilation caches to# R/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/modelsALL vLLM and compilation ca/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/modelsscratch (avoid home directory disk quota)
export # R/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/modelsALL vLLM and compilation ca/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/modelsLLM_CACHE_DIR=/scratch/gpfs/JORDANAT/mg9965/vLLM-c# R/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/modelsALL vLLM and compilation ca/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/modelsLLM
export VLLM_USAGE_STATS_DIR=/scratch/gpfs/JOc# R/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/modelsALL vLLM and compilation ca/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/modelsLLM
mg9965/vLLM-cache/usage_stats
scratch/gpfs/JOc# R/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/modelsALL vLLM and compilation ca/export TRITON_CACHE_DImg9965/God-s-Reach/modelsLLM
R=/scratch/gpfs/JORDANAT/mg9965/scratch/gpfs/JOc# R/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/modelsALL vLLM and compilation ca/vLLM-cache/triton
exDImg9965/God-s-Reach/modelsLLM
Rt XDG_CACHE_HOME=/scratch/gpfs//scratch/gpfs/JOc# R/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/modelsALL vLLM and compilation caJORDANAT/mg9965/vLLMexDImg9965/God-s-Reach/modelsLLM
Rt/xdg

# Create cache directorie/scratch/gpfs/JOc# R/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/modelsALL vLLM and compilation cas
mkdir -p $VLLMvLLMexDImg9965/God-s-Reach/modelsLLM
Rt
mkdir -p $VLLM_USAGE_Sdirectorie/scratch/gpfs/JOc# R/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/modelsALL vLLM and compilation cas
r -p $TRITVLLMvLLMexDImg9965/God-s-Reach/modelsLLM
Rtkdir -p $XDG_CACHE_HOMESdirectorie/scratch/gpfs/JOc# R/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/modelsALL vLLM and compilation cas
r -p $TRITVLLMvLLMexDImg9965/God-s-Reach/modelsLLM
Rtkdir_PARALLELISM=tHOMESdirectorie/scratch/gpfs/JOc# R/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/modelsALL vLLM and compilation cas
r -p $TRITVLLMvLLMexDImg9965/God-s-Reach/modelsLLM
Rtkdirch tuning guitHOMESdirectorie/scratch/gpfs/JOc# R/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/modelsALL vLLM and compilation cas
r -p $TRITVLLMvLLMexDImg9965/God-s-Reach/modelsLLM
Rtkdirchrrors
exguitHOMESdirectorie/scratch/gpfs/JOc# R/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/modelsALL vLLM and compilation cas
r -p $TRITVLLMvLLMexDImg9965/God-s-Reach/modelsLLM
Rtkdirchrrors
guration for 2x A100 on single node
export NCCL_P2P_LEVEL=NVL
export CUDA_DEVICE_MAX_CONNECTIONS=1

# LLM Configuration
export LLM_ENABLE=true
export LLM_PROVIDER=qwen
export LLM_MODE=verify  # 'verify' checks ALL parameters, 'fallback' only low-confidence
export QWEN_MODEL_PATH=/scratch/gpfs/JORDANAT/mg9965/models/Qwen--Qwen3-32B

# Memory optimization for CUDA (reduce fragmentation)
# Note: Already set above, removed duplicate
# export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# Force offline mode (compute nodes typically have no internet)
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# GPU configuration
export CUDA_VISIBLE_DEVICES=0,1

# Create output directories
mkdir -p logs
mkdir -p designspace_extractor/out/logs

echo ""
echo "📂 Environment Setup:"
echo "  Working directory: $(pwd)"
echo "  Python: $(which python)"
echo "  Python version: $(python --version)"
echo "  Model path: $QWEN_MODEL_PATH"
echo "  LLM enabled: $LLM_ENABLE"
echo ""

# Check if model exists
if [ -d "$QWEN_MODEL_PATH" ]; then
    echo "✅ Qwen model found at: $QWEN_MODEL_PATH"
else
    echo "⚠️  WARNING: Qwen model not found at: $QWEN_MODEL_PATH"
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
echo "📊 Running batch extraction..."
echo "   Input: ../papers"
echo "   Output: batch_processing_results.json"
echo ""

# Run batch extraction
python run_batch_extraction.py \
    --papers "../papers" \
    --output "batch_processing_results.json"

EXTRACT_EXIT=$?

if [ $EXTRACT_EXIT -ne 0 ]; then
    echo "❌ Extraction failed with exit code: $EXTRACT_EXIT"
    exit $EXTRACT_EXIT
fi

echo ""
echo "=================================================================================="
echo "EXTRACTION RESULTS"
echo "=================================================================================="

# Check results
if [ -f "batch_processing_results.json" ]; then
    SUCCESS=$(python -c "import json; d=json.load(open('batch_processing_results.json')); print(sum(1 for r in d if r['success']))")
    TOTAL=$(python -c "import json; d=json.load(open('batch_processing_results.json')); print(len(d))")
    echo "   Successful: $SUCCESS / $TOTAL papers"
    
    # Run validation (offline mode)
    echo ""
    echo "🔍 Validating against gold standard..."
    
    if [ -f "../validation/gold_standard.csv" ]; then
        echo "   Using local gold standard: ../validation/gold_standard.csv"
        python validation/validator_public.py \
            --local-file ../validation/gold_standard.csv \
            --results 'batch_processing_results.json' | tee validation_report.txt
    else
        echo "⚠️  Local gold standard not found at: ../validation/gold_standard.csv"
        echo "   Run on login node: python validation/download_gold_standard.py"
    fi
fi

# Check LLM usage if enabled
if [ "$LLM_ENABLE" = "true" ] && [ -f "out/logs/llm_usage.log" ]; then
    echo ""
    echo "🤖 LLM Usage Summary:"
    LLM_CALLS=$(wc -l < out/logs/llm_usage.log)
    echo "   Total LLM inferences: $LLM_CALLS"
    
    if [ $LLM_CALLS -gt 0 ]; then
        echo "   LLM usage log: out/logs/llm_usage.log"
    fi
fi

echo ""
echo "✅ Job completed at $(date)"
echo "============================================"
