# LLM Assistant Three-Stage Policy Implementation

## Overview

Implemented comprehensive improvements to the LLM-assisted parameter extraction system with evidence-based inference, governance gates, and prompt externalization.

## Architecture: Three-Stage Extraction Policy

### Stage 1: Deterministic Extraction (existing)
- **Who:** PDFExtractor, CodeExtractor, HEDExtractor
- **What:** Rules, regex patterns, AST parsing
- **Priority:** configs → code → logs → paper text
- **Output:** Parameters with confidence scores

### Stage 2: LLM Verify/Fallback (enhanced)
- **When:** Low confidence (<0.3) or missing critical parameters
- **Modes:**
  - `verify`: Check ALL extracted parameters
  - `fallback`: Only touch low-confidence or missing critical fields
- **Contract:** Demand verbatim evidence quotes (20+ chars), allow abstention
- **Output:** `LLMInferenceResult` dataclass with full provenance

### Stage 3: LLM Discovery (new)
- **When:** Explicitly enabled with `mode='discover'`
- **Purpose:** Propose NEW parameters not in current schema
- **Governance:** Never overwrites existing extractions
- **Output:** `ParameterProposal` dataclass → human review → schema promotion

## Key Improvements

### 1. Structured Output with Dataclasses

**`ParameterProposal`** (Stage 3 discovery):
```python
@dataclass
class ParameterProposal:
    parameter_name: str
    description: str
    category: str  # demographics/task_design/perturbation/etc.
    evidence: str  # Verbatim quote
    evidence_location: str  # page/section/line
    example_values: List[str]
    units: Optional[str]
    prevalence: str  # low/medium/high
    importance: str  # low/medium/high
    mapping_suggestion: str  # existing param or "new"
    hed_hint: Optional[str]
    confidence: float
```

**`LLMInferenceResult`** (Stage 2 verify):
```python
@dataclass
class LLMInferenceResult:
    value: Any
    confidence: float
    evidence: str  # Verbatim quote
    evidence_location: str
    reasoning: str
    llm_provider: str
    llm_model: str
    requires_review: bool
    abstained: bool
```

### 2. Evidence Requirements

- **Mandatory quotes:** All LLM outputs must include verbatim text excerpts (≥20 chars)
- **Location tracking:** Page/section/line references for reproducibility
- **Abstention enforcement:** LLM can explicitly decline (prevents hallucination)
- **Confidence calibration:** Scores penalize ambiguous language

### 3. Governance Gates

**Discovery (Stage 3):**
- Proposals stored in `proposed_parameters` table
- Requires 2-reviewer approval before schema promotion
- Export to CSV for review: `export_proposals_for_review()`

**Verification (Stage 2):**
- Stores in `llm_inference_provenance` table
- Auto-accept threshold: confidence ≥ 0.7
- Manual review required: confidence < 0.7

### 4. Prompt Externalization

**Before:** Prompts hardcoded in Python f-strings
**After:** Stored in `llm/prompts/` directory:

- `verify_batch.txt` - Multi-parameter verification
- `verify_single.txt` - Single parameter inference
- `discovery.txt` - New parameter discovery

**Benefits:**
- Version control for prompt iterations
- Easier collaboration with domain experts
- A/B testing without code changes
- Separation of concerns (code vs. prompt engineering)

**Usage:**
```python
prompt_loader = PromptLoader()
prompt = prompt_loader.format_prompt(
    'verify_batch',
    parameter_list=params,
    context=text,
    evidence_requirement="REQUIRED"
)
```

### 5. Local LLM Support

**New provider:** `local`
- Uses vLLM/TGI for on-premises deployment
- Optimized for 7-13B instruct models
- Ideal for discovery (cheap, fast)
- Keeps stronger hosted models for verify on critical params

**Example:**
```python
# Cheap local model for discovery
llm_discover = LLMAssistant(provider='local', mode='discover')

# Strong hosted model for verification
llm_verify = LLMAssistant(provider='claude', mode='verify')
```

### 6. Database Schema Extensions

**New tables:**
- `proposed_parameters` - Discovery output with governance fields
- `llm_inference_provenance` - Verification output with evidence

**New views:**
- `v_proposed_parameters_review` - Proposals needing review
- `v_llm_inferences_review` - Inferences needing review
- `v_proposal_statistics` - Aggregated cross-paper proposals

## Usage Examples

### Verify Mode (Stage 2)
```python
from designspace_extractor.llm.llm_assist import LLMAssistant

# Initialize in verify mode (check all extracted params)
llm = LLMAssistant(provider='qwen', mode='verify')

# Check if parameter needs verification
if llm.should_verify('sample_size_n', value=None, confidence=0.2):
    result = llm.infer_parameter(
        parameter_name='sample_size_n',
        context=methods_text,
        extracted_params=existing_params
    )
    
    if result and not result['abstained']:
        print(f"Value: {result['value']}")
        print(f"Evidence: {result['evidence']}")
        print(f"Confidence: {result['confidence']}")
```

### Discovery Mode (Stage 3)
```python
from designspace_extractor.llm.llm_assist import LLMAssistant

# Initialize in discovery mode
llm = LLMAssistant(provider='local', mode='discover')

# Discover new parameters
proposals = llm.discover_new_parameters(
    paper_text=full_text,
    current_schema=['sample_size_n', 'perturbation_class', ...],
    min_evidence_length=20
)

# Export for governance review
llm.export_proposals_for_review(
    proposals,
    output_file='./out/logs/parameter_proposals.csv'
)

# Review workflow:
# 1. Two reviewers check evidence
# 2. Verify measurability and non-redundancy
# 3. Mark 'promoted' column when approved
# 4. Update schema with promoted parameters
```

### Batch Processing with Prioritization
```python
# Stage 1: Deterministic extraction
pdf_extractor = PDFExtractor(llm_mode='disabled')
params = pdf_extractor.extract_from_pdf('paper.pdf')

# Stage 2: LLM fallback for low-confidence
llm = LLMAssistant(provider='qwen', mode='fallback')

low_conf_params = [
    name for name, data in params.items()
    if data['confidence'] < 0.3
]

if low_conf_params:
    llm_results = llm.infer_parameters_batch(
        parameter_names=low_conf_params,
        context=methods_text,
        extracted_params=params,
        require_evidence=True
    )
    
    # Merge LLM results
    for param, result in llm_results.items():
        if not result.abstained:
            params[param] = result.to_dict()
```

## Configuration

### Environment Variables

```bash
# LLM enablement
export LLM_ENABLE=true
export LLM_BUDGET_USD=10.0

# Thresholds
export LLM_VERIFY_THRESHOLD=0.3  # Verify if confidence < 0.3
export LLM_ACCEPT_THRESHOLD=0.7  # Auto-accept if confidence >= 0.7

# Provider selection
export LLM_PROVIDER=qwen  # or claude, openai, local
export QWEN_MODEL_PATH=./models/qwen2.5
export LOCAL_MODEL_PATH=./models/llama-3-8b-instruct
```

### Critical Parameters
Defined in `LLMAssistant.__init__`:
```python
self.critical_params = set([
    'sample_size_n', 'perturbation_class', 'perturbation_magnitude',
    'rotation_magnitude_deg', 'adaptation_trials', 'baseline_trials',
    'effector', 'environment', 'feedback_type'
])
```

## Cost Optimization

1. **Stage 1 first:** Maximize deterministic extraction
2. **Fallback mode:** Only use LLM for low-confidence/missing critical
3. **Local models for discovery:** 7-13B for cheap proposal generation
4. **Hosted models for verification:** Claude/GPT-4 only for critical params
5. **Batch calls:** `infer_parameters_batch()` more efficient than individual calls

## Quality Assurance

### Provenance Tracking
Every LLM output includes:
- Verbatim evidence quote
- Source location (page/section/line)
- LLM provider and model version
- Timestamp and cost
- Confidence score
- Reasoning explanation

### Audit Trail
Logged to `./out/logs/llm_usage.log`:
```json
{
  "timestamp": "2025-11-06T10:30:45",
  "operation": "batch_verify",
  "provider": "qwen",
  "model": "./models/qwen2.5",
  "mode": "verify",
  "cost_usd": 0.0,
  "num_parameters": 15,
  "parameters": ["sample_size_n", "effector", ...]
}
```

Full prompts and responses saved to:
- `./out/logs/llm_response_<timestamp>_<operation>.json`

## Migration Guide

### From Old Code
```python
# OLD: Simple dict output, no evidence
result = llm.infer_parameter('sample_size_n', context)
if result:
    value = result['value']
```

### To New Code
```python
# NEW: Structured output with evidence
result = llm.infer_parameter('sample_size_n', context)
if result and not result.get('abstained'):
    value = result['value']
    evidence = result['evidence']
    confidence = result['confidence']
    
    # Store provenance
    if confidence >= 0.7:
        # Auto-accept
        params['sample_size_n'] = value
    else:
        # Flag for review
        params['sample_size_n'] = {
            'value': value,
            'requires_review': True,
            'llm_evidence': evidence
        }
```

## Testing

```bash
# Test prompt loading
python -c "from designspace_extractor.llm.prompt_loader import PromptLoader; p = PromptLoader(); print(p.format_prompt('verify_single', parameter_name='test', context='context', extracted_params_section=''))"

# Test discovery mode
python -m designspace_extractor.tools.analyze_coverage \
    --input papers/ \
    --discover-new \
    --provider local \
    --output ./out/logs/proposals.csv

# Test verification mode
python -m designspace_extractor.llm.llm_assist \
    --mode verify \
    --provider qwen \
    --test-parameter sample_size_n \
    --test-context "Twenty-four participants..."
```

## Next Steps

1. **Populate `proposed_parameters` table:** Run discovery across corpus
2. **Set up review workflow:** Google Sheets sync or custom UI
3. **Train evaluators:** Establish review guidelines and inter-rater reliability
4. **Monitor performance:** Track acceptance rates, abstention rates, confidence calibration
5. **Iterate prompts:** A/B test prompt variations, measure precision/recall
