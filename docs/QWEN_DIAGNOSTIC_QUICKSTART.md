# Quick Start: Testing Qwen Model on Cluster

## 🎯 Goal
Verify that the Qwen3-32B model loads correctly before running full extraction.

## ⏱️ Time Required
5-15 minutes (NOT hours!)

## 📝 Steps

### 1. Update Paths in Script

Edit `slurm/test_qwen_loading.sh`:

```bash
nano slurm/test_qwen_loading.sh
```

Update these lines to match your setup:
```bash
# Line 23: Your project directory
cd /scratch/gpfs/JORDANAT/mg9965/God-s-Reach/designspace_extractor

# Line 29: Your conda environment name
conda activate godsreach

# Line 38: Your model cache location
export HF_HOME=/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/models

# Line 43: Your model path
export QWEN_MODEL_PATH=/scratch/gpfs/JORDANAT/mg9965/models/Qwen--Qwen3-32B

# Line 13: Your email
#SBATCH --mail-user=your-email@domain.edu
```

### 2. Submit Diagnostic Job

```bash
cd /scratch/gpfs/JORDANAT/mg9965/God-s-Reach

# Submit the job
sbatch slurm/test_qwen_loading.sh
```

You should see:
```
Submitted batch job 12345678
```

### 3. Monitor Progress

```bash
# Watch the output in real-time
tail -f logs/qwen_diagnostic_*.out

# Or check job status
squeue -u $USER
```

### 4. Interpret Results

#### ✅ Success (Exit Code 0)
```
🎉 ALL TESTS PASSED!
Your model is ready for extraction!
```

**Next steps:**
```bash
# Run full extraction
sbatch slurm/run_batch_extraction.sh
```

#### ❌ Failure (Exit Code 1)
```
❌ FAILED - Tests identified issues
Check the output above for specific error messages
```

**Next steps:**
1. Read the error messages in `logs/qwen_diagnostic_*.out`
2. Follow the recommended fixes
3. Re-submit: `sbatch slurm/test_qwen_loading.sh`
4. Repeat until it passes

#### ⏱️ Timeout (Exit Code 124)
```
❌❌❌ TIMEOUT - Diagnostic exceeded 20 minutes
```

**This means:**
- Model loading is hanging
- Check last message in error log
- Likely causes: corrupted files, CUDA driver issue, GPU problem

**Next steps:**
```bash
# Check error log
cat logs/qwen_diagnostic_*.err | tail -50

# Common fixes:
# 1. Re-download model
cd /scratch/gpfs/JORDANAT/mg9965/models
huggingface-cli download Qwen/Qwen3-32B --local-dir Qwen--Qwen3-32B

# 2. Kill stuck processes
pkill -9 python

# 3. Try different GPU node
sbatch --exclude=node-that-failed slurm/test_qwen_loading.sh
```

## 📊 What the Diagnostic Tests

1. **File validation** - Checks model files exist and are complete
2. **CUDA check** - Verifies GPU is available
3. **Memory check** - Ensures enough free GPU memory
4. **vLLM test** - Tries fast vLLM loading (5 min timeout)
5. **Transformers test** - Tries transformers loading (10 min timeout)
6. **Inference test** - Quick generation to verify it works

## 🔍 Detailed Output Example

```
🔍 Starting Qwen Model Loading Diagnostic
Job ID: 12345678
Node: node-gpu-01
Time: Fri Oct 31 10:00:00 EDT 2025
GPUs: 0

📂 Environment Setup:
  Working directory: /scratch/.../designspace_extractor
  Python: /path/to/python
  Python version: Python 3.11.5
  Model path: /path/to/Qwen--Qwen3-32B

✅ Model directory found
   Files in model directory: 47

🔧 GPU Information:
NVIDIA A100-SXM4-80GB, 81920 MiB, 78234 MiB

==================================================
RUNNING DIAGNOSTIC
==================================================

1. Checking model path: /path/to/Qwen--Qwen3-32B
✓ Path exists
✓ Found 47 files
  ✓ config.json
  ✓ tokenizer.json
  ✓ tokenizer_config.json
  Found 39 model weight files

2. Checking CUDA...
✓ CUDA available
  Device: NVIDIA A100-SXM4-80GB
  Total Memory: 80.0 GB
  Free Memory: 76.3 GB

3. Testing vLLM availability...
✓ vLLM installed
  Attempting vLLM initialization (timeout: 5 minutes)...
✓✓✓ vLLM loaded successfully!
    Your setup is working correctly!

5. Testing quick inference...
  ✓ Inference works! Response: Hello, how are you? I'm doing well...

🎉 ALL TESTS PASSED! Your model is ready to use.

==================================================
DIAGNOSTIC RESULTS
==================================================

✅✅✅ SUCCESS - All tests passed!

Your Qwen model is working correctly and ready for extraction.
Next steps:
  1. Run full batch extraction: sbatch slurm/run_batch_extraction.sh
  2. Or test single paper: python -m designspace_extractor extract --pdf ../papers/test.pdf --llm-enable
```

## 🆘 Common Issues

### Issue: "Model directory not found"
```bash
# Download the model
cd /scratch/gpfs/JORDANAT/mg9965/models
huggingface-cli download Qwen/Qwen3-32B --local-dir Qwen--Qwen3-32B
```

### Issue: "CUDA not available"
```bash
# Check CUDA
module load cuda/12.1
nvidia-smi

# Verify PyTorch has CUDA
python -c "import torch; print(torch.cuda.is_available())"
```

### Issue: "Only XX GB free (need ~64GB)"
```bash
# Kill other processes
pkill -9 python

# Or request node with more free memory
sbatch --constraint=gpu80 slurm/test_qwen_loading.sh
```

### Issue: Hangs during "Loading model"
See `docs/QWEN_LOADING_FREEZE_FIX.md` for detailed debugging.

## 📚 Related Documentation

- `docs/QWEN_LOADING_FREEZE_FIX.md` - Detailed debugging guide
- `docs/QWEN3_32B_MIGRATION.md` - Model migration details
- `docs/LLM_SETUP_GUIDE.md` - Complete LLM setup
- `slurm/README.md` - All SLURM scripts

## 💡 Pro Tips

1. **Always run diagnostic first** - Saves time vs debugging during extraction
2. **Check logs directory** - Create `logs/` before submitting
3. **Watch nvidia-smi** - Monitor GPU usage in another session
4. **Use vLLM** - Much faster than transformers (pip install vllm)
5. **Start small** - Test with 1 paper before batch processing

---

**Expected Time:** 5-15 minutes  
**If it takes >20 minutes:** Something is wrong, check logs and see debugging guide
