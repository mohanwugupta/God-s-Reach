# Using Alternative LLM Models

This guide explains how to use Qwen2.5-72B-Instruct and DeepSeek-V2.5 models for parameter extraction.

## Available Models

1. **Qwen3-32B** (Default)
   - Parameters: 32B
   - GPUs required: 2x A100 (80GB each)
   - Provider: `qwen`

2. **Qwen2.5-72B-Instruct** (New)
   - Parameters: 72B
   - GPUs required: 4x A100 (80GB each)
   - Provider: `qwen72b`

3. **DeepSeek-V2.5** (New)
   - Parameters: 236B
   - GPUs required: 8x A100 (80GB each)
   - Provider: `deepseek`

## Model Paths

Models should be stored locally following this pattern:
```
/scratch/gpfs/JORDANAT/mg9965/models/
├── Qwen--Qwen3-32B/                    # Default Qwen model
├── Qwen--Qwen2.5-72B-Instruct/         # 72B model
└── deepseek-ai--DeepSeek-V2.5/         # DeepSeek model
```

## Using Qwen2.5-72B-Instruct

### Via SLURM Script
```bash
sbatch slurm/run_batch_qwen72b.sh
```

### Manual Configuration
```bash
export LLM_PROVIDER=qwen72b
export QWEN72B_MODEL_PATH=/scratch/gpfs/JORDANAT/mg9965/models/Qwen--Qwen2.5-72B-Instruct
export CUDA_VISIBLE_DEVICES=0,1,2,3

python run_batch_extraction.py --papers ../papers --output results_qwen72b.json
```

## Using DeepSeek-V2.5

### Via SLURM Script
```bash
sbatch slurm/run_batch_deepseek.sh
```

### Manual Configuration
```bash
export LLM_PROVIDER=deepseek
export DEEPSEEK_MODEL_PATH=/scratch/gpfs/JORDANAT/mg9965/models/deepseek-ai--DeepSeek-V2.5
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7

python run_batch_extraction.py --papers ../papers --output results_deepseek.json
```

## Downloading Models

To download models to your local cache (run on login node with internet access):

### Qwen2.5-72B-Instruct
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import os

os.environ['HF_HOME'] = '/scratch/gpfs/JORDANAT/mg9965/models'

model_name = "Qwen/Qwen2.5-72B-Instruct"
save_path = "/scratch/gpfs/JORDANAT/mg9965/models/Qwen--Qwen2.5-72B-Instruct"

# Download tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
tokenizer.save_pretrained(save_path)

# Download model
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="cpu",  # Don't load to GPU during download
    trust_remote_code=True
)
model.save_pretrained(save_path)
```

### DeepSeek-V2.5
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import os

os.environ['HF_HOME'] = '/scratch/gpfs/JORDANAT/mg9965/models'

model_name = "deepseek-ai/DeepSeek-V2.5"
save_path = "/scratch/gpfs/JORDANAT/mg9965/models/deepseek-ai--DeepSeek-V2.5"

# Download tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
tokenizer.save_pretrained(save_path)

# Download model
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="cpu",  # Don't load to GPU during download
    trust_remote_code=True
)
model.save_pretrained(save_path)
```

## GPU Memory Requirements

| Model | Parameters | Min GPUs | VRAM per GPU | Total VRAM |
|-------|-----------|----------|--------------|------------|
| Qwen3-32B | 32B | 2 | 40GB | 80GB |
| Qwen2.5-72B | 72B | 4 | 35GB | 140GB |
| DeepSeek-V2.5 | 236B | 8 | 40GB | 320GB |

## Performance Expectations

- **Qwen3-32B**: Fast inference, good for most tasks
- **Qwen2.5-72B**: Better reasoning, more accurate parameter extraction
- **DeepSeek-V2.5**: Best performance, highest accuracy, but slowest

## Troubleshooting

### Model Not Found
```
⚠️  WARNING: Model not found at: /path/to/model
```
Solution: Verify the model path exists and contains required files (config.json, tokenizer.json, etc.)

### Out of Memory
```
RuntimeError: CUDA out of memory
```
Solution: Ensure you have requested enough GPUs in your SLURM script. Check GPU allocation with `nvidia-smi`.

### Offline Mode Errors
```
OSError: You are trying to access a gated repo...
```
Solution: Models must be pre-downloaded. Run download script on login node with internet access.

## Provider Selection in Code

You can also select providers programmatically:

```python
from llm.llm_assist import LLMAssistant

# Use Qwen2.5-72B
assistant = LLMAssistant(provider_name='qwen72b', mode='verify')

# Use DeepSeek-V2.5
assistant = LLMAssistant(provider_name='deepseek', mode='verify')

# Use default Qwen3-32B
assistant = LLMAssistant(provider_name='qwen', mode='verify')
```

## Comparison Results

After running all three models, compare results:

```bash
# Run all models
sbatch slurm/run_batch_extraction.sh      # Qwen3-32B
sbatch slurm/run_batch_qwen72b.sh         # Qwen2.5-72B
sbatch slurm/run_batch_deepseek.sh        # DeepSeek-V2.5

# Compare F1 scores
grep "F1 Score:" validation_report.txt
grep "F1 Score:" validation_report_qwen72b.txt
grep "F1 Score:" validation_report_deepseek.txt
```
