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
cd /scratch/gpfs/JORDANAT/mg9965/God-s-Reach/

# Load required modules
module load anaconda3/2025.6
module load cuda/12.1  # Adjust CUDA version as needed

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
export QWEN_MODEL_PATH=/scratch/gpfs/JORDANAT/mg9965/models/Qwen2.5-72B-Instruct

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
if [ -d "papers" ]; then
    echo "✅ Papers directory found"
    echo "   Number of PDFs: $(find papers -name '*.pdf' | wc -l)"
else
    echo "❌ ERROR: Papers directory not found at $(pwd)/papers"
    exit 1
fi

echo ""
echo "🔍 Running batch extraction..."
echo ""

# Run batch extraction
cd designspace_extractor

python run_batch_extraction.py \
    --papers ../papers \
    --output batch_processing_results.json \
    --workers 8

EXTRACT_EXIT_CODE=$?

if [ $EXTRACT_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ Batch extraction completed successfully"
    echo ""
    
    # Check if results file was created
    if [ -f "batch_processing_results.json" ]; then
        echo "📊 Results saved to: batch_processing_results.json"
        
        # Count successful extractions
        SUCCESS_COUNT=$(python -c "import json; data=json.load(open('batch_processing_results.json')); print(sum(1 for r in data if r['success']))")
        TOTAL_COUNT=$(python -c "import json; data=json.load(open('batch_processing_results.json')); print(len(data))")
        
        echo "   Successful: $SUCCESS_COUNT / $TOTAL_COUNT papers"
        echo ""
        
        # Run validation against gold standard (offline mode)
        if [ -f "validation/validator_public.py" ]; then
            echo "🔍 Running validation against gold standard..."
            
            # Check if local gold standard exists
            if [ -f "validation/gold_standard.csv" ]; then
                echo "   Using local gold standard: validation/gold_standard.csv"
                python validation/validator_public.py \
                    --local-file validation/gold_standard.csv \
                    --results 'batch_processing_results.json' \
                    > validation_report.txt 2>&1
            else
                echo "⚠️  Local gold standard not found at validation/gold_standard.csv"
                echo "   Skipping validation"
                echo ""
                echo "💡 To enable validation on cluster:"
                echo "   1. On login node (with internet): python designspace_extractor/validation/download_gold_standard.py"
                echo "   2. This will create validation/gold_standard.csv"
                echo "   3. Re-run this job"
            fi
            
            if [ -f "validation_report.txt" ]; then
                echo "✅ Validation completed"
                echo "   Report saved to: validation_report.txt"
                
                # Extract F1 score from report
                F1_SCORE=$(grep "F1 Score:" validation_report.txt | awk '{print $3}')
                if [ ! -z "$F1_SCORE" ]; then
                    echo "   Overall F1 Score: $F1_SCORE"
                fi
            fi
        fi
        
    else
        echo "⚠️  WARNING: Results file not created"
    fi
else
    echo ""
    echo "❌ Batch extraction failed with exit code: $EXTRACT_EXIT_CODE"
    echo "   Check logs for details"
    exit $EXTRACT_EXIT_CODE
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
