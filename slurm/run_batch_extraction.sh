#!/bin/bash
#SBATCH --job-name=design-space-extraction
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8     # For parallel PDF processing
#SBATCH --mem=64G             # Memory for processing multiple PDFs
#SBATCH --gres=gpu:2          # 2 GPUs for Qwen2.5-72B-Instruct
#SBATCH --mail-type=begin
#SBATCH --mail-type=end
#SBATCH --mail-user=your-email@domain.edu
#SBATCH --time=2:00:00        # Adjust based on number of papers
#SBATCH --output=logs/batch_extraction_%j.out
#SBATCH --error=logs/batch_extraction_%j.err

# Design Space Extractor: Batch PDF Extraction with LLM Assistance
# Extracts parameters from motor adaptation papers using regex + Qwen LLM

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
    conda activate godsreach  # Adjust environment name
elif [ -f ~/.conda/envs/godsreach/bin/activate ]; then
    source ~/.conda/envs/godsreach/bin/activate
else
    source activate godsreach
fi

# Set up environment for Qwen model
export HF_HOME=/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/models
export TRANSFORMERS_CACHE=/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/models
export HF_DATASETS_CACHE=/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/models

# LLM Configuration
export LLM_ENABLE=true
export LLM_PROVIDER=qwen
export QWEN_MODEL_PATH=/scratch/gpfs/JORDANAT/mg9965/models/Qwen--Qwen2.5-72B-Instruct

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
