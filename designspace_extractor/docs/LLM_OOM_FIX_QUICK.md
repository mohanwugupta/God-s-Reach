# LLM OOM Fix - Quick Reference

## Problem
Multiple workers → Multiple vLLM instances → GPU OOM → Extraction fails

## Solution
Singleton pattern → One vLLM instance → Shared across workers → No OOM

## What Changed

### ✅ Created `llm/singleton.py`
```python
from llm.singleton import get_shared_llm_provider

# All workers call this - only first one loads model
llm = get_shared_llm_provider(model_path, tensor_parallel_size=4)
```

### ✅ Modified `llm/providers.py`
```python
def create_provider(provider, model, **kwargs):
    if provider == 'qwen72b':
        return get_shared_llm_provider(model, ...)  # Singleton!
    # ... other providers normal
```

### ✅ Reduced GPU Memory
```python
gpu_memory_utilization=0.75  # Was 0.9, now 0.75
```

## Test It

```bash
# On cluster
sbatch slurm/batch_extract.sh

# Look for these in logs:
# Worker 1: "🔄 Initializing shared LLM provider (singleton)..."
# Worker 2-4: "✓ Using shared qwen72b provider (singleton)"
```

## Expected Results

| Metric | Before | After |
|--------|--------|-------|
| Model loads | 4 attempts (all fail) | 1 success |
| GPU memory | OOM error | ~60 GB total |
| Init time | 240s (failed) | 60s (success) |
| Extractions | 0 | All workers succeed |

## If Still Failing

1. **Check logs**: `grep "shared qwen72b" slurm-*.out`
2. **Check GPU memory**: `nvidia-smi` before job
3. **Reduce further**: Change `0.75` → `0.65` in `providers.py:285`
4. **Test single worker**: `--num-workers 1` first

## Revert If Needed

Comment out singleton in `llm/providers.py`:
```python
# if provider.lower() == 'qwen72b':
#     from .singleton import get_shared_llm_provider
#     return get_shared_llm_provider(...)
```

---

**TL;DR**: Singleton prevents 4 workers from loading 4 models. Now: 1 model, shared by all. No more OOM! 🎉
