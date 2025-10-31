# Local LLM Configuration Guide

## Qwen3-32B Setup for Cluster

This guide explains how to configure and use the local Qwen3-3- **Memory:** ~72GB GPU VRAM for 32B model
- **Recommended:** 1x A100 80GB or 1x H100 80GB GPU model on your cluster for parameter extraction assistance.

## 📁 Model Location

The model should be placed in the following directory structure:

```
God-s-Reach/                    # Your project root
├── designspace_extractor/      # Main package
├── models/                      # Model directory (sibling to project)
│   └── Qwen3-32B/              # Downloaded model files
│       ├── config.json
│       ├── tokenizer.json
│       ├── model-*.safetensors
│       └── ...
└── papers/                      # Papers directory
```

**Expected path:** `../models/Qwen3-32B` (relative to project root)

## 🔧 Installation

### Option 1: vLLM (Recommended - Much Faster)

For GPU clusters with CUDA support:

```bash
# Install vLLM for fast inference
pip install vllm

# Optional: Install with specific CUDA version
pip install vllm --extra-index-url https://download.pytorch.org/whl/cu121
```

**Advantages:**
- 10-20x faster inference than transformers
- Efficient batching and memory management
- Continuous batching for multiple requests

### Option 2: Transformers (Fallback)

If vLLM is not available:

```bash
# Install transformers and torch
pip install transformers torch accelerate
```

**Note:** The system automatically detects which is available and uses vLLM if installed.

## 🚀 Usage

### Environment Variables

Create a `.env` file or set these variables:

```bash
# Enable LLM assistance
export LLM_ENABLE=true

# Set provider to qwen
export LLM_PROVIDER=qwen

# Optional: Override model path (default: ../models/Qwen3-32B)
export QWEN_MODEL_PATH=/path/to/your/model

# Budget (not used for local model, but required by config)
export LLM_BUDGET_USD=0.0
```

### Python Code Example

```python
from llm.llm_assist import LLMAssistant

# Initialize Qwen assistant
llm = LLMAssistant(
    provider='qwen',
    model='../models/Qwen3-32B',  # or custom path
    temperature=0.0  # Deterministic for extraction
)

# Infer a parameter from context
context = """
Participants performed reaching movements in a virtual environment.
A 45° visuomotor rotation was introduced abruptly at trial 100.
Cursor feedback was provided throughout the movement.
"""

result = llm.infer_parameter(
    parameter_name='perturbation_schedule',
    context=context,
    extracted_params={'perturbation_magnitude': '45°'}
)

if result:
    print(f"Value: {result['value']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Reasoning: {result['llm_reasoning']}")
```

### CLI Usage

```bash
# Run extraction with LLM assistance
python -m designspace_extractor extract \
    --pdf path/to/paper.pdf \
    --llm-enable \
    --llm-provider qwen \
    --output results.json
```

## 🎯 When LLM Assistance is Used

The LLM is invoked in these scenarios:

1. **Ambiguous Parameters:** When regex patterns find multiple conflicting values
2. **Missing Critical Parameters:** When important parameters aren't extracted
3. **Validation Failures:** When extracted values fail sanity checks
4. **New Parameter Discovery:** Identifying parameters not in current schema

## 📊 Performance Expectations

### vLLM (Recommended)

- **First inference:** ~2-5 seconds (model loading + generation)
- **Subsequent inferences:** ~0.5-2 seconds
- **Memory:** ~140GB GPU VRAM for 72B model
- **Recommended:** 2x A100 80GB or 2x H100 80GB GPUs

### Transformers

- **First inference:** ~5-10 seconds
- **Subsequent inferences:** ~3-7 seconds
- **Memory:** ~80GB+ (uses CPU offloading if needed)
- **Recommended:** Large system RAM (256GB+) if GPU VRAM limited

## 🔍 LLM Integration Features

### Enhanced Fuzzy Matching

The validator now includes advanced fuzzy matching that handles:

1. **Typo tolerance:** "horiztonal" ↔ "horizontal", "continous" ↔ "continuous"
2. **Abbreviations:** "CCW" ↔ "counterclockwise", "vmr" ↔ "visuomotor rotation"
3. **Multi-value fields:** Handles comma-separated values with partial matching
4. **Numeric tolerance:** 5% tolerance for numeric values (handles "45" vs "45.0" vs "45°")
5. **Word-based matching:** Matches based on meaningful word overlap (60% threshold)
6. **Stop word removal:** Ignores common words like "the", "a", "and"
7. **Expanded synonyms:** Comprehensive synonym dictionary for each parameter

### Synonym Dictionary

Now includes expanded synonyms for:
- `feedback_type`: Added "continous" → "continuous" mapping
- `coordinate_frame`: Added "horiztonal" → "horizontal" mapping
- `environment`: Added "kinarm" synonyms
- `target_hit_criteria`: Added shooting/stopping criteria

## 🔐 Audit Trail

All LLM usage is automatically logged to: `./out/logs/llm_usage.log`

Each log entry includes:
- Timestamp
- Parameter being inferred
- Provider and model
- Prompt and response lengths
- Cost (0.0 for local Qwen)
- Cumulative spend

## 🚨 Important Notes

### GPU Memory Requirements

Qwen3-32B requires significant GPU memory:
- **FP16:** ~72GB VRAM
- **BF16:** ~72GB VRAM
- **INT8:** ~36GB VRAM (with quantization)
- **INT4:** ~18GB VRAM (with quantization)

For clusters with limited GPU memory, consider:

1. **Model Quantization:**
```python
# 4-bit quantization (reduces memory by 75%)
llm = LLM(
    model=model_path,
    quantization="awq",  # or "gptq"
    dtype="half",
    gpu_memory_utilization=0.9,
)
```

2. **Smaller Model:**
Use Qwen2.5-32B-Instruct or Qwen2.5-14B-Instruct instead

### Cluster-Specific Setup

For SLURM clusters:

```bash
#!/bin/bash
#SBATCH --job-name=qwen_extraction
#SBATCH --nodes=1
#SBATCH --gres=gpu:1  # Request 1 GPU
#SBATCH --mem=200G    # System RAM
#SBATCH --time=04:00:00

# Load modules (adjust for your cluster)
module load python/3.11
module load cuda/12.1

# Activate environment
source venv/bin/activate

# Set environment variables
export LLM_ENABLE=true
export LLM_PROVIDER=qwen
export CUDA_VISIBLE_DEVICES=0,1

# Run extraction
python run_batch_extraction.py \
    --papers ../papers \
    --output batch_results.json \
    --llm-enable
```

## 📈 Monitoring

### Check if LLM is working:

```python
from llm.llm_assist import LLMAssistant

llm = LLMAssistant(provider='qwen')
print(f"LLM Enabled: {llm.enabled}")
print(f"Using vLLM: {llm.use_vllm if hasattr(llm, 'use_vllm') else 'N/A'}")
```

### View usage logs:

```bash
# View recent LLM usage
tail -f out/logs/llm_usage.log | python -m json.tool

# Count total inferences
grep -c "timestamp" out/logs/llm_usage.log
```

## 🐛 Troubleshooting

### Model not found
```
Error: Qwen model not found at: ../models/Qwen3-32B
```
**Solution:** Verify model path and download model files to correct location

### Out of memory
```
Error: CUDA out of memory
```
**Solution:** 
- Use quantization (`quantization="awq"`)
- Reduce `gpu_memory_utilization` (try 0.8)
- Use smaller model variant

### vLLM not working
```
Error: Required package not installed: vllm
```
**Solution:** 
- Install vLLM: `pip install vllm`
- Or let it fall back to transformers (slower but works)

## 📚 Additional Resources

- [vLLM Documentation](https://docs.vllm.ai/)
- [Qwen3 Model Card](https://huggingface.co/Qwen/Qwen3-32B)
- [Transformers Documentation](https://huggingface.co/docs/transformers/)

## 🎓 Best Practices

1. **Use vLLM on cluster** - Much faster for batch processing
2. **Set temperature=0.0** - Ensures deterministic extraction
3. **Review LLM outputs** - All LLM-inferred values are flagged for review
4. **Monitor logs** - Check usage patterns and adjust prompts if needed
5. **Start small** - Test on a few papers before batch processing
