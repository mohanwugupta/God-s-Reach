# Quick Reference: Throughput Optimizations

## What Changed

### 🚀 Code Changes
- ✅ **Removed** `torch.cuda.empty_cache()` calls (2 per inference)
- ✅ File: `llm/llm_assist.py`

### 🖥️ SLURM Resource Changes
All scripts updated with:

```bash
#SBATCH --ntasks=1            # Single task
#SBATCH --cpus-per-task=8     # 8 CPUs (was 1)

export OMP_NUM_THREADS=8
export TOKENIZERS_PARALLELISM=true
export NCCL_P2P_LEVEL=NVL
export CUDA_DEVICE_MAX_CONNECTIONS=1
```

---

## Quick Test

```bash
# 1. Test model loading (should be faster)
sbatch slurm/test_qwen_loading.sh

# 2. Check job is using 8 CPUs
squeue -u $USER
# Then on compute node:
htop -u $USER

# 3. Run batch extraction
sbatch slurm/run_batch_extraction.sh
```

---

## Expected Performance

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| PDF Parsing | Single-threaded | 8 threads | 2-3x faster |
| Tokenization | Single-threaded | 8 threads | 2-3x faster |
| LLM Inference | Sync overhead | No sync | 5-10% faster |
| **Total** | ~120s/paper | ~60-90s/paper | **~40-50% faster** |

---

## Monitor Progress

```bash
# Watch job
watch -n 5 'squeue -u $USER'

# Check CPU usage (on compute node)
htop -u $USER

# Check GPU usage
watch nvidia-smi

# Check tokenizer parallelism is working
grep "TOKENIZERS_PARALLELISM" logs/batch_extraction_*.out
```

---

## Rollback (if needed)

```bash
# Edit slurm scripts:
#SBATCH --cpus-per-task=1

# Remove these lines:
# export TOKENIZERS_PARALLELISM=true
# export NCCL_P2P_LEVEL=NVL
# export CUDA_DEVICE_MAX_CONNECTIONS=1
```

---

## Full Documentation

See `docs/THROUGHPUT_OPTIMIZATION.md` for detailed explanation.
