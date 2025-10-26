# SLURM Job Scripts for Design Space Extraction

This directory contains SLURM job submission scripts for running batch extraction on computing clusters.

## 📋 Available Scripts

### 1. `run_batch_extraction.sh` (With LLM)
**Use when:** You want LLM-assisted extraction for ambiguous parameters

**Requirements:**
- 2 GPUs (for Qwen2.5-72B-Instruct)
- 64GB RAM
- ~4 hours for ~20 papers

**Features:**
- Regex extraction + LLM inference for ambiguous cases
- Automatic validation against gold standard
- LLM usage logging

### 2. `run_batch_extraction_noLLM.sh` (Regex Only)
**Use when:** Quick extraction without LLM, or for testing

**Requirements:**
- No GPU needed
- 32GB RAM
- ~1 hour for ~20 papers

**Features:**
- Fast regex-based extraction only
- Automatic validation
- Lower resource usage

## 🚀 Quick Start

### First Time Setup

1. **Clone repository on cluster:**
   ```bash
   cd /scratch/gpfs/JORDANAT/mg9965/
   git clone git@github.com:mohanwugupta/God-s-Reach.git
   cd God-s-Reach
   ```

2. **Create conda environment:**
   ```bash
   module load anaconda3/2024.2
   conda create -n godsreach python=3.11
   conda activate godsreach
   pip install -r designspace_extractor/requirements.txt
   ```

3. **Install additional packages for LLM (optional):**
   ```bash
   # For fast LLM inference (recommended)
   pip install vllm
   
   # OR for fallback transformers
   pip install transformers torch accelerate
   ```

4. **Download Qwen model (for LLM version):**
   ```bash
   # Create models directory
   mkdir -p models
   cd models
   
   # Download from HuggingFace (on login node with internet)
   huggingface-cli download Qwen/Qwen2.5-72B-Instruct --local-dir Qwen2.5-72B-Instruct
   ```

5. **Upload PDF papers:**
   ```bash
   # Copy your papers to the papers/ directory
   scp *.pdf username@cluster:/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/papers/
   ```

### Edit Configuration

Before submitting, edit the SLURM script to match your cluster setup:

1. **Update paths:**
   - Change `/scratch/gpfs/JORDANAT/mg9965/` to your actual scratch directory
   - Update email address in `#SBATCH --mail-user`

2. **Adjust resources:**
   - Modify `--time` based on number of papers
   - Adjust `--mem` and `--cpus-per-task` as needed

3. **Check module names:**
   - Verify `module load anaconda3/2024.2` matches your cluster
   - Adjust `module load cuda/12.1` to your CUDA version

### Submit Job

```bash
# For LLM-assisted extraction
sbatch slurm/run_batch_extraction.sh

# For regex-only extraction
sbatch slurm/run_batch_extraction_noLLM.sh
```

### Monitor Job

```bash
# Check job status
squeue -u $USER

# View output in real-time
tail -f logs/batch_extraction_*.out

# Check for errors
tail -f logs/batch_extraction_*.err
```

### Cancel Job

```bash
# Cancel by job ID
scancel <job_id>

# Cancel all your jobs
scancel -u $USER
```

## 📊 Output Files

After job completes, you'll find:

- `designspace_extractor/batch_processing_results.json` - Extracted parameters
- `designspace_extractor/validation_report.txt` - Validation metrics (F1, precision, recall)
- `logs/batch_extraction_*.out` - Standard output
- `logs/batch_extraction_*.err` - Error messages
- `designspace_extractor/out/logs/llm_usage.log` - LLM inference log (if LLM enabled)

## 🔧 Troubleshooting

### Job fails immediately
- Check paths in script match your directory structure
- Verify conda environment exists: `conda env list`
- Check if papers directory exists and contains PDFs

### Out of memory
- Reduce `--workers` in the script (default: 8)
- Increase `#SBATCH --mem`
- For LLM version, try quantization (see LLM_SETUP_GUIDE.md)

### GPU not available
- Check GPU availability: `sinfo -o "%20N %10c %10m %25f %10G"`
- Reduce GPU request: `#SBATCH --gres=gpu:1`
- Use `run_batch_extraction_noLLM.sh` instead

### Model not found (LLM version)
- Verify model path: `ls /path/to/models/Qwen2.5-72B-Instruct`
- Check `QWEN_MODEL_PATH` in script
- Ensure model was downloaded on login node

### Validation fails
- Check internet connectivity on compute node (may need to run validation on login node)
- Verify gold standard spreadsheet ID in script

## 📈 Expected Performance

### Without LLM (Regex Only)
- **Speed:** ~2-3 minutes per paper
- **Accuracy:** F1 ≈ 0.22 (baseline)
- **Resource:** 1 CPU, 2-4GB RAM per paper

### With LLM (Qwen2.5-72B)
- **Speed:** ~5-10 minutes per paper
- **Accuracy:** F1 ≈ 0.30-0.40 (estimated with LLM assistance)
- **Resource:** 2 GPUs, 140GB VRAM total

## 🔄 Pull Latest Changes

To update the code on the cluster:

```bash
cd /scratch/gpfs/JORDANAT/mg9965/God-s-Reach
git pull origin main
```

## 📚 Additional Documentation

- `../docs/LLM_SETUP_GUIDE.md` - Detailed LLM configuration
- `../docs/FUZZY_MATCHING_AND_LLM_SUMMARY.md` - Technical details
- `../docs/GOLD_STANDARD_ENTRY_GUIDELINES.md` - Gold standard format
- `../designspace_extractor/README.md` - Package documentation

## 💡 Tips

1. **Start with noLLM version** to test pipeline before using expensive GPU time
2. **Use array jobs** for very large batches (contact cluster admin for help)
3. **Run validation locally first** to ensure gold standard access works
4. **Check logs directory** before submitting to avoid overwriting outputs
5. **Request more time than needed** - jobs terminated early waste resources

## 🆘 Getting Help

If you encounter issues:

1. Check the error log: `logs/batch_extraction_*.err`
2. Verify Python packages: `pip list | grep -E '(pymupdf|pdfplumber|pandas)'`
3. Test manually on login node first
4. Consult cluster documentation for SLURM settings
5. Contact cluster support for resource/module issues
