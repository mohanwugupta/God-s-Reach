# LLM Module Quick Reference

## Module Structure

```
llm/
├── __init__.py              # Package exports
├── base.py                  # Dataclasses (55 lines)
├── providers.py             # LLM provider implementations (255 lines)
├── prompt_builder.py        # Prompt loading + building (175 lines) ← CONSOLIDATED
├── response_parser.py       # Response parsing (175 lines)
├── inference.py             # Stage 2 verification engine (180 lines)
├── discovery.py             # Stage 3 discovery engine (195 lines)
├── llm_assist.py            # Main orchestrator (220 lines) ← SIMPLIFIED!
└── prompts/                 # Prompt templates directory
    ├── verify_batch.txt     # Multi-parameter verification
    ├── verify_single.txt    # Single parameter inference
    ├── discovery.txt        # New parameter discovery
    └── README.md            # Template documentation
```

## Quick Import Guide

### Standard Usage
```python
from llm import LLMAssistant, ParameterProposal, LLMInferenceResult

# Initialize
assistant = LLMAssistant(provider_name='claude', mode='verify')

# Use...
results = assistant.verify_and_infer(...)
proposals = assistant.discover_new_parameters(...)
```

### Advanced Usage (Direct Module Access)
```python
from llm.providers import create_provider
from llm.inference import VerificationEngine
from llm.discovery import DiscoveryEngine

# Create custom setup
provider = create_provider('qwen', model='Qwen/Qwen2.5-32B-Instruct')
verification = VerificationEngine(provider, confidence_threshold=0.8)
```

## Common Tasks

### Add a New LLM Provider
**File**: `llm/providers.py`

```python
class MyProvider(LLMProvider):
    def __init__(self, model_name: str = "default-model"):
        super().__init__("myprovider", model_name)
    
    def initialize(self) -> bool:
        # Setup code
        return True
    
    def generate(self, prompt: str, max_tokens: int, temperature: float) -> Optional[str]:
        # Call API
        return response_text

# Add to factory
providers = {
    'claude': ClaudeProvider,
    'openai': OpenAIProvider,
    'qwen': QwenProvider,
    'local': LocalProvider,
    'myprovider': MyProvider,  # ← Add here
}
```

### Add a New Prompt Template
**Location**: `llm/prompts/my_new_prompt.txt`

```
You are helping extract parameters from a research paper.

Context: ${context}
Parameter: ${parameter_name}

Please respond with JSON:
{
  "value": "...",
  "confidence": 0.0-1.0,
  "evidence": "direct quote"
}
```

**Use in code**:
```python
from llm.prompt_builder import PromptBuilder

builder = PromptBuilder()
prompt = builder.loader.format_prompt(
    'my_new_prompt',
    context="Paper text...",
    parameter_name="sample_size_n"
)
```

Or use PromptLoader directly for more control:
```python
from llm.prompt_builder import PromptLoader

loader = PromptLoader()
prompt = loader.format_prompt(
    'my_new_prompt',
    context="Paper text...",
    parameter_name="sample_size_n"
)
```

### Modify Verification Logic
**File**: `llm/inference.py`

Edit the `VerificationEngine` class:
- `should_verify()` - Change gate criteria
- `verify_batch()` - Modify batch processing
- `infer_single()` - Adjust single parameter logic

### Modify Discovery Logic
**File**: `llm/discovery.py`

Edit the `DiscoveryEngine` class:
- `discover_parameters()` - Change discovery prompt/logic
- `export_proposals_json()` - Modify JSON output format
- `filter_proposals_*()` - Add new filtering methods

### Parse Different Response Formats
**File**: `llm/response_parser.py`

Add a new method to `ResponseParser`:
```python
def parse_my_format(self, response: str) -> MyDataType:
    # Custom parsing logic
    return parsed_result
```

## Testing

### Unit Test a Module
```python
# Test providers
from llm.providers import create_provider

provider = create_provider('claude')
assert provider is not None
assert provider.provider_name == 'claude'
```

### Integration Test
```python
# Test full workflow
from llm import LLMAssistant

os.environ['LLM_ENABLE'] = 'false'  # Disable for testing
assistant = LLMAssistant(provider_name='claude')

results = assistant.verify_and_infer(
    extracted_params={},
    missing_params=['sample_size_n'],
    context="test",
    study_type="between",
    num_experiments=1
)

assert isinstance(results, dict)
```

## Troubleshooting

### Import Errors
**Problem**: `ModuleNotFoundError: No module named 'llm'`

**Solution**: Ensure you're in the right directory:
```bash
cd designspace_extractor/
python your_script.py
```

### Provider Initialization Fails
**Problem**: `Failed to create LLM provider`

**Solutions**:
1. Check API keys: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`
2. Verify model paths for local providers
3. Install required packages:
   - Claude: `pip install anthropic`
   - OpenAI: `pip install openai`
   - Qwen: `pip install transformers torch`
   - Local: `pip install vllm`

### Prompt Template Not Found
**Problem**: `Prompt template not found: verify_batch`

**Solution**: Check that `llm/prompts/verify_batch.txt` exists.

### Evidence Validation Fails
**Problem**: Parameters skipped with "Insufficient evidence"

**Solutions**:
1. Check `min_evidence_length` setting (default: 20 chars)
2. Adjust in VerificationEngine or DiscoveryEngine:
   ```python
   engine = VerificationEngine(
       provider=provider,
       min_evidence_length=10  # Lower threshold
   )
   ```

## Configuration

### Environment Variables
```bash
# Enable/disable LLM
export LLM_ENABLE=true

# Budget control
export LLM_BUDGET_USD=50.0

# Confidence thresholds
export LLM_VERIFY_THRESHOLD=0.3   # When to verify
export LLM_ACCEPT_THRESHOLD=0.7   # When to auto-accept

# Model selection
export LLM_MODEL=claude-3-5-sonnet-20241022
export QWEN_MODEL_PATH=./models/Qwen--Qwen3-32B
export LOCAL_MODEL_PATH=./models/llama-3-8b-instruct

# API keys
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
```

### Mode Selection
- `verify`: Verify all extracted parameters (Stage 2 only)
- `fallback`: Only verify missing/low-confidence params
- `discover`: Discover new parameters (Stage 3 only)

## Performance Tips

### Batch Processing
Use batch methods for efficiency:
```python
# Good - batch verification
results = engine.verify_batch(extracted_params, context, ...)

# Avoid - individual calls in loop
for param in params:
    result = engine.infer_single(param, context, ...)  # Slower
```

### Context Truncation
Large contexts are auto-truncated:
- Verification: 5000 chars
- Discovery: 8000 chars

Override in PromptBuilder if needed.

### Local Models for Discovery
Use smaller local models for discovery (7-13B):
```python
assistant = LLMAssistant(
    provider_name='local',
    model='meta-llama/Llama-3-8B-Instruct',
    mode='discover'
)
```

Use larger models for verification (32B+):
```python
assistant = LLMAssistant(
    provider_name='qwen',
    model='Qwen/Qwen2.5-32B-Instruct',
    mode='verify'
)
```

## Migration from Old Code

### Before Refactoring
```python
from llm.llm_assist import LLMAssistant

assistant = LLMAssistant(provider='claude')
results = assistant.infer_parameters_batch(
    parameter_names=['sample_size_n'],
    context=text,
    extracted_params={}
)
```

### After Refactoring (Same!)
```python
from llm import LLMAssistant

assistant = LLMAssistant(provider_name='claude')  # Note: provider_name
results = assistant.verify_and_infer(  # More descriptive name
    extracted_params={},
    missing_params=['sample_size_n'],
    context=text,
    study_type='between',
    num_experiments=1
)
```

## Key Differences

| Old | New | Notes |
|-----|-----|-------|
| `provider` | `provider_name` | Clearer parameter name |
| `infer_parameters_batch()` | `verify_and_infer()` | More descriptive |
| CSV export only | CSV + JSON export | JSON export added |
| Inline prompts | `llm/prompts/*.txt` | Externalized |
| 1164-line monolith | 7 modular files | Better organization |

## Support

For issues or questions:
1. Check test files: `test_refactored_llm.py`, `test_comprehensive_refactoring.py`
2. Review documentation: `docs/LLM_THREE_STAGE_IMPLEMENTATION.md`
3. See refactoring summary: `docs/LLM_REFACTORING_SUMMARY.md`
