#!/bin/bash
#SBATCH --job-name=design-space-extract-noLLM
#SBATCH --nodes=1
#SBATCH --ntasks=1            # Single task (not MPI)
#SBATCH --cpus-per-task=8     # 8 CPUs for parallel PDF processing
#SBATCH --mem=32G             # Less memory without LLM
#SBATCH --mail-type=end
#SBATCH --mail-user=your-email@domain.edu
#SBATCH --time=1:00:00        # Faster without LLM
#SBATCH --output=logs/batch_extraction_noLLM_%j.out
#SBATCH --error=logs/batch_extraction_noLLM_%j.err

# Design Space Extractor: Batch PDF Extraction (Regex Only, No LLM)
# Faster extraction using only regex patterns

echo "🚀 Starting Design Space Batch Extraction (No LLM)"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURMD_NODENAME"
echo "Time: $(date)"

# Change to project directory (adjust path as needed)
cd /scratch/gpfs/JORDANAT/mg9965/God-s-Reach/designspace_extractor

# Load required modules
module load anaconda3/2024.2

# Activate Python environment
if command -v conda &> /dev/null; then
    eval "$(conda shell.bash hook)"
    conda activate godsreach
elif [ -f ~/.conda/envs/godsreach/bin/activate ]; then
    source ~/.conda/envs/godsreach/bin/activate
else
    source activate godsreach
fi

# CPU & Threading Configuration (use all 8 allocated CPUs)
export OMP_NUM_THREADS=8
export TOKENIZERS_PARALLELISM=true

# Disable LLM
export LLM_ENABLE=false

# Create output directories
mkdir -p logs
mkdir -p out/logs

echo ""
echo "📂 Environment:"
echo "  Working directory: $(pwd)"
echo "  Python: $(python --version)"
echo "  PDFs to process: $(find ../papers -name '*.pdf' 2>/dev/null | wc -l)"
echo ""

# Run batch extraction
python run_batch_extraction.py \
    --papers ../papers \
    --output batch_processing_results.json \
    --workers 8

EXTRACT_EXIT_CODE=$?

if [ $EXTRACT_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ Extraction completed"
    
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
            echo "   Run on login node: python designspace_extractor/validation/download_gold_standard.py"
        fi
    fi
else
    echo "❌ Extraction failed with exit code: $EXTRACT_EXIT_CODE"
    exit $EXTRACT_EXIT_CODE
fi

echo ""
echo "✅ Job completed at $(date)"
