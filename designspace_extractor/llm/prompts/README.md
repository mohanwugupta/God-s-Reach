# LLM Prompt Templates

This directory contains externalized prompt templates for LLM-assisted parameter extraction.

## Templates

### verify_batch.txt
**Purpose:** Batch verification of multiple parameters (Stage 2)  
**Variables:**
- `parameter_list` - Newline-separated list of parameters to verify
- `context` - Full context text (paper/methods/code)
- `extracted_params_section` - Already extracted parameters for reference
- `evidence_requirement` - "REQUIRED" or "strongly recommended"

**Usage:**
```python
prompt = prompt_loader.format_prompt(
    'verify_batch',
    parameter_list="\n".join(f"  - {p}" for p in params),
    context=paper_text,
    extracted_params_section=existing_params_text,
    evidence_requirement="REQUIRED"
)
```

### verify_single.txt
**Purpose:** Single parameter inference (Stage 2 fallback)  
**Variables:**
- `parameter_name` - Name of parameter to infer
- `context` - Context text
- `extracted_params_section` - Already extracted parameters

**Usage:**
```python
prompt = prompt_loader.format_prompt(
    'verify_single',
    parameter_name='sample_size_n',
    context=methods_text,
    extracted_params_section=params_text
)
```

### discovery.txt
**Purpose:** Discover new parameters not in schema (Stage 3)  
**Variables:**
- `current_schema` - Comma-separated list of existing parameters
- `paper_text` - Full paper text or Methods section

**Usage:**
```python
prompt = prompt_loader.format_prompt(
    'discovery',
    current_schema=', '.join(sorted(schema_params)),
    paper_text=full_text
)
```

## Prompt Engineering Guidelines

1. **Evidence Requirements:** Always demand verbatim quotes (20+ chars minimum)
2. **Abstention:** Allow LLM to explicitly decline with `abstained: true`
3. **Structured Output:** Enforce strict JSON schema for parsing
4. **Location Tracking:** Require page/section/line references
5. **Confidence Calibration:** Set thresholds for auto-accept vs. manual review

## Versioning

When modifying prompts:
1. Test on validation set before deploying
2. Document changes in git commit message
3. Track performance metrics (precision/recall/abstention rate)
4. A/B test major changes

## Variable Substitution

Uses Python's `string.Template`:
- Variables: `${variable_name}` or `$variable_name`
- Escaping: `$$` for literal `$`
- Safe substitution: Missing variables left as placeholders

## Fallback

If prompt template loading fails, code falls back to inline prompts for backward compatibility.
