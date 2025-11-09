#!/bin/bash
#SBATCH --job-name=test_outlines
#SBATCH --output=test_outlines_%j.out
#SBATCH --error=test_outlines_%j.err
#SBATCH --time=00:30:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:2
#SBATCH --mem=64G

# Outlines Integration Test SLURM Script
# This script runs the comprehensive test suite on the cluster
#
# Usage:
#   sbatch test_outlines_cluster.slurm
#
# Monitor:
#   tail -f test_outlines_<JOBID>.out

echo "=========================================="
echo "Outlines Integration Test"
echo "=========================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "GPUs: $CUDA_VISIBLE_DEVICES"
echo "Start time: $(date)"
echo "=========================================="
echo ""

# Load required modules (adjust for your cluster)
# module load python/3.9
# module load cuda/11.8

# Set environment variables
export HF_HOME=${HF_HOME:-/scratch/gpfs/$USER/.cache/huggingface}
export QWEN_MODEL_PATH=${QWEN_MODEL_PATH:-/scratch/gpfs/JORDANAT/mg9965/models/Qwen--Qwen2.5-72B-Instruct}
export LLM_ENABLE=true

# Activate virtual environment if needed
# source venv/bin/activate

# Show Python and package versions
echo "Python version:"
python --version
echo ""

echo "Checking Outlines installation:"
python -c "import outlines; print(f'Outlines version: {outlines.__version__ if hasattr(outlines, \"__version__\") else \"unknown\"}')" 2>&1
echo ""

echo "Checking PyTorch and CUDA:"
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}')" 2>&1
echo ""

# Navigate to project directory
cd /scratch/gpfs/JORDANAT/mg9965/God-s-Reach/slurm

echo "Working directory: $(pwd)"
echo ""

# Run the test script
echo "=========================================="
echo "Running Outlines Integration Tests"
echo "=========================================="
python test_outlines_cluster.py

# Capture exit code
EXIT_CODE=$?

echo ""
echo "=========================================="
echo "Test completed with exit code: $EXIT_CODE"
echo "End time: $(date)"
echo "=========================================="

# Exit with test script's exit code
exit $EXIT_CODE
