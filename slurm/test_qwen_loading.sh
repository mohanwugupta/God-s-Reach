#!/bin/bash
#SBATCH --job-name=qwen-diagnostic
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --constraint=gpu80
#SBATCH --mail-type=begin
#SBATCH --mail-type=end
#SBATCH --mail-user=your-email@domain.edu
#SBATCH --time=00:30:00
#SBATCH --output=logs/qwen_diagnostic_%j.out
#SBATCH --error=logs/qwen_diagnostic_%j.err

# Qwen Model Loading Diagnostic
# Tests model loading with timeouts to identify hanging issues
# This should complete in 5-15 minutes (NOT hours!)

echo "🔍 Starting Qwen Model Loading Diagnostic"
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

# Model Configuration
export QWEN_MODEL_PATH=/scratch/gpfs/JORDANAT/mg9965/models/Qwen--Qwen3-32B

# Memory optimization for CUDA
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# Force offline mode (compute nodes typically have no internet)
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# GPU configuration
export CUDA_VISIBLE_DEVICES=0

# Create output directories
mkdir -p logs

echo ""
echo "📂 Environment Setup:"
echo "  Working directory: $(pwd)"
echo "  Python: $(which python)"
echo "  Python version: $(python --version)"
echo "  Model path: $QWEN_MODEL_PATH"
echo ""

# Check if model exists
if [ -d "$QWEN_MODEL_PATH" ]; then
    echo "✅ Model directory found at: $QWEN_MODEL_PATH"
    FILE_COUNT=$(ls -1 "$QWEN_MODEL_PATH" | wc -l)
    echo "   Files in model directory: $FILE_COUNT"
else
    echo "❌ ERROR: Model directory not found"
    echo "   Expected: $QWEN_MODEL_PATH"
    echo "   Please download the model first"
    exit 1
fi

echo ""
echo "🔧 GPU Information:"
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader

echo ""
echo "=================================================================================="
echo "RUNNING DIAGNOSTIC"
echo "=================================================================================="
echo "This will test model loading with automatic timeouts."
echo "Expected completion time: 5-15 minutes"
echo "If it times out, you'll see specific error messages and fixes."
echo ""

# Run diagnostic with time limit
timeout 20m python test_qwen_loading.py

DIAGNOSTIC_EXIT=$?

echo ""
echo "=================================================================================="
echo "DIAGNOSTIC RESULTS"
echo "=================================================================================="

if [ $DIAGNOSTIC_EXIT -eq 0 ]; then
    echo ""
    echo "✅✅✅ SUCCESS - All tests passed!"
    echo ""
    echo "Your Qwen model is working correctly and ready for extraction."
    echo "Next steps:"
    echo "  1. Run full batch extraction: sbatch slurm/run_batch_extraction.sh"
    echo "  2. Or test single paper: python -m designspace_extractor extract --pdf ../papers/test.pdf --llm-enable"
    echo ""
    
elif [ $DIAGNOSTIC_EXIT -eq 124 ]; then
    echo ""
    echo "❌❌❌ TIMEOUT - Diagnostic exceeded 20 minutes"
    echo ""
    echo "This indicates a serious hanging issue."
    echo "The diagnostic script itself has timeouts, so this means:"
    echo "  - The hang occurred before reaching the timeout code"
    echo "  - OR the signal handlers are not working"
    echo ""
    echo "Check the error log for the last message before timeout:"
    echo "  tail -50 logs/qwen_diagnostic_${SLURM_JOB_ID}.err"
    echo ""
    echo "Common causes:"
    echo "  1. Corrupted model files - Re-download the model"
    echo "  2. CUDA driver crash - Contact cluster admin"
    echo "  3. GPU hardware issue - Try different GPU node"
    echo ""
    
elif [ $DIAGNOSTIC_EXIT -eq 1 ]; then
    echo ""
    echo "❌ FAILED - Tests identified issues"
    echo ""
    echo "Check the output above for specific error messages and recommended fixes."
    echo "The diagnostic should have provided actionable recommendations."
    echo ""
    echo "Review full output:"
    echo "  cat logs/qwen_diagnostic_${SLURM_JOB_ID}.out"
    echo "  cat logs/qwen_diagnostic_${SLURM_JOB_ID}.err"
    echo ""
    
else
    echo ""
    echo "⚠️  UNKNOWN EXIT CODE: $DIAGNOSTIC_EXIT"
    echo ""
    echo "Check logs for details:"
    echo "  cat logs/qwen_diagnostic_${SLURM_JOB_ID}.out"
    echo "  cat logs/qwen_diagnostic_${SLURM_JOB_ID}.err"
    echo ""
fi

# GPU status after test
echo ""
echo "🔧 GPU Status After Test:"
nvidia-smi --query-gpu=name,memory.used,memory.free,utilization.gpu --format=csv,noheader

# Check for zombie processes
PYTHON_PROCS=$(pgrep -u $USER python | wc -l)
if [ $PYTHON_PROCS -gt 1 ]; then
    echo ""
    echo "⚠️  Warning: $PYTHON_PROCS Python processes still running"
    echo "   This might indicate hung processes from the test"
    echo "   List: pgrep -u $USER python"
fi

echo ""
echo "✅ Diagnostic job completed at $(date)"
echo "============================================"

# Exit with the same code as the diagnostic
exit $DIAGNOSTIC_EXIT
