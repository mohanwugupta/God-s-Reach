# Task 1 & Task 2 Discovery Implementation

## Overview

The discovery functionality has been split into two separate tasks as requested:

### **Task 1: Find Missed Library Parameters**
- **Purpose**: Find parameters from the current library that regex extraction missed
- **Integration**: Automatically runs during LLM verification (part of batch job)
- **Prompt**: `llm/prompts/task1_missed_params.txt`
- **When it runs**: Automatically when you submit a batch extraction job with LLM enabled

### **Task 2: Discover New Parameters**
- **Purpose**: Identify entirely NEW parameters not in the current library
- **Integration**: Separate CLI command for manual discovery jobs
- **Prompt**: `llm/prompts/task2_new_params.txt`
- **When it runs**: Manually via `designspace-extractor discover` command

---

## Task 1: Missed Library Parameters

### Integration Point
Task 1 is **integrated into the verification workflow**, running automatically when LLM assistance is enabled.

**Workflow**:
1. User submits batch extraction job
2. Regex extracts parameters
3. LLM verification runs:
   - Verifies regex-extracted parameters
   - **Task 1: Finds missed library parameters**
   - Fallback inference for remaining missing parameters

### Files Modified
- `llm/prompts/task1_missed_params.txt` - Task 1 prompt template
- `llm/prompt_builder.py` - Added `build_missed_params_prompt()` method
- `llm/inference.py` - Added `find_missed_library_params()` method
- `llm/inference.py` - Updated `verify_and_fallback()` to include Task 1
- `llm/response_parser.py` - Added `parse_task1_response()` method
- `llm/llm_assist.py` - Updated `verify_and_infer()` to pass schema
- `extractors/pdfs.py` - Updated to pass `self.schema_map` to LLM

### Task 1 Output
Parameters found by Task 1 are automatically added to extraction results with:
- `method`: `'llm_missed_params'`
- `source_type`: `'llm_task1'`
- Full evidence and confidence scores

### Example Task 1 Output
```json
{
  "missed_parameters": [
    {
      "parameter_name": "target_size_cm",
      "value": 1.5,
      "confidence": 0.95,
      "evidence": "circular targets (1.5 cm diameter)",
      "evidence_location": "Methods, Apparatus section"
    }
  ]
}
```

---

## Task 2: Discover New Parameters

### Separate CLI Command
Task 2 runs as a **separate discovery job** via new CLI command:

```bash
designspace-extractor discover paper.pdf -o proposals.csv
```

### Full Command Options
```bash
designspace-extractor discover PDF_PATH [OPTIONS]

Options:
  -o, --output PATH              Output file for proposals (CSV or JSON)
  --format [csv|json]            Output format (default: csv)
  --llm-provider [claude|openai|qwen]  LLM provider (default: claude)
  --min-prevalence [low|medium|high]   Filter by minimum prevalence
  --min-importance [low|medium|high]   Filter by minimum importance
  --help                         Show this message and exit
```

### Files Modified
- `llm/prompts/task2_new_params.txt` - Task 2 prompt template
- `llm/prompt_builder.py` - Added `build_new_params_prompt()` method
- `llm/discovery.py` - Updated `discover_parameters()` to use Task 2
- `llm/response_parser.py` - Added `parse_task2_response()` method
- `llm/llm_assist.py` - Updated `discover_new_parameters()` signature
- `cli.py` - Added `discover` command

### Task 2 Workflow
1. User runs: `designspace-extractor discover paper.pdf -o proposals.csv`
2. System extracts PDF text and detects sections
3. Extracts current parameters via regex (for context)
4. Calls LLM with Task 2 prompt
5. LLM analyzes paper and proposes NEW parameters
6. Results filtered by prevalence/importance (optional)
7. Exports to CSV or JSON for review

### Task 2 Output Format

**CSV Format** (default):
```csv
parameter_name,description,category,evidence,evidence_location,example_values,units,prevalence,importance,mapping_suggestion,hed_hint,confidence,review_status
inter_trial_interval_sec,"Time delay between consecutive trials",trials,"A 2-second inter-trial interval separated each reaching movement","Methods, page 4","['2.0', '1.5', '3.0']",sec,high,medium,new,Duration/Inter-trial-interval,0.75,pending
```

**JSON Format**:
```json
{
  "metadata": {
    "total_proposals": 5,
    "generated_at": "2025-11-08T...",
    "pdf_source": "paper.pdf"
  },
  "proposals": [
    {
      "parameter_name": "inter_trial_interval_sec",
      "description": "Time delay between consecutive trials in seconds",
      "category": "trials",
      "evidence": "A 2-second inter-trial interval separated each reaching movement",
      "evidence_location": "Methods, Procedures section, page 4",
      "example_values": ["2.0", "1.5", "3.0"],
      "units": "sec",
      "prevalence": "high",
      "importance": "medium",
      "mapping_suggestion": "new",
      "hed_hint": "Duration/Inter-trial-interval",
      "confidence": 0.75,
      "review_status": "pending"
    }
  ]
}
```

---

## Usage Examples

### Task 1 (Automatic - Part of Batch Extraction)

```bash
# Run batch extraction with LLM enabled
python batch_process_papers.py --llm-mode verify

# Task 1 runs automatically during verification
# Output shows in logs:
# ✅ Task 1 found 3 missed parameters:
#    - target_size_cm = 1.5
#    - feedback_delay_ms = 50
#    - cursor_size_mm = 3
```

### Task 2 (Manual Discovery Job)

```bash
# Basic discovery - outputs to proposals_paper.csv
designspace-extractor discover paper.pdf

# Custom output file
designspace-extractor discover paper.pdf -o my_proposals.csv

# JSON format with filters
designspace-extractor discover paper.pdf -o proposals.json \
  --format json \
  --min-prevalence medium \
  --min-importance medium

# Use different LLM provider
designspace-extractor discover paper.pdf -o proposals.csv --llm-provider openai
```

### Example Task 2 Output (Terminal)

```
🔍 Task 2: Discovering new parameters from Taylor2012.pdf

📄 Extracting text from PDF...
   Context prepared: 45,231 characters
📊 Extracting current parameters via regex...
   Found 23 parameters via regex
🤖 Running Task 2 discovery with claude...

✅ Discovered 7 new parameter proposals

📋 Preview of top proposals:

1. inter_trial_interval_sec
   Description: Time delay between consecutive trials in seconds
   Evidence: "A 2-second inter-trial interval separated each reaching movement..."
   Prevalence: high, Importance: medium

2. screen_refresh_rate_hz
   Description: Visual display refresh rate in Hertz
   Evidence: "Stimuli were presented on a 144 Hz LCD monitor..."
   Prevalence: medium, Importance: low

   ... and 5 more proposals

💾 Proposals saved to: proposals_Taylor2012.csv
   Review the proposals and add valuable ones to your schema_map.yaml
```

---

## Review & Integration Workflow

### After Running Task 2

1. **Review the output file** (CSV/JSON)
   - Check evidence quality
   - Assess prevalence and importance ratings
   - Validate example values

2. **Select valuable parameters**
   - High prevalence + high importance = definitely add
   - Medium/medium = consider based on research goals
   - Low/low = probably skip

3. **Add to schema_map.yaml**
   ```yaml
   trials:
     inter_trial_interval_sec:
       type: float
       description: "Time delay between consecutive trials in seconds"
       units: "sec"
       validation:
         range: [0.5, 10.0]
   ```

4. **Update patterns.yaml** (if regex patterns needed)
   ```yaml
   inter_trial_interval:
     - 'inter-trial interval of (\d+\.?\d*)\s*(?:s|sec|seconds?)'
     - '(\d+\.?\d*)\s*(?:s|sec|seconds?) between trials'
   ```

5. **Re-run extraction** to test the new parameter

---

## Technical Details

### Task 1 Implementation

**VerificationEngine.find_missed_library_params()**:
```python
def find_missed_library_params(self, current_schema, already_extracted, context):
    # Build Task 1 prompt with schema and already-extracted params
    prompt = self.prompt_builder.build_missed_params_prompt(...)
    
    # Call LLM
    response = self.provider.generate(prompt, max_tokens=1536, temperature=0.0)
    
    # Parse response
    results = self.response_parser.parse_task1_response(...)
    
    return results  # Dict[param_name -> LLMInferenceResult]
```

**Integrated into verify_and_fallback()**:
```python
def verify_and_fallback(self, ...):
    all_results = {}
    
    # Step 1: Verify extracted parameters
    verified = self.verify_batch(...)
    all_results.update(verified)
    
    # Step 2: Task 1 - Find missed library parameters
    if current_schema:
        missed_params = self.find_missed_library_params(...)
        all_results.update(missed_params)
    
    # Step 3: Fallback inference for remaining missing
    for param in remaining_missing:
        result = self.infer_single(...)
        all_results.update(result)
    
    return all_results
```

### Task 2 Implementation

**CLI Command Handler**:
```python
@cli.command('discover')
def discover(ctx, pdf_path, output, ...):
    # 1. Extract PDF text
    text_data = pdf_extractor.extract_text(pdf_path)
    
    # 2. Prepare context
    sections = pdf_extractor.detect_sections(full_text)
    context = prepare_context(sections)
    
    # 3. Extract current parameters (for "already extracted")
    all_parameters = extract_current_params(sections)
    
    # 4. Run Task 2 discovery
    proposals = llm_assistant.discover_new_parameters(
        context=context,
        current_schema=pdf_extractor.schema_map,
        already_extracted=all_parameters
    )
    
    # 5. Filter and export
    proposals = apply_filters(proposals, min_prevalence, min_importance)
    export_proposals(proposals, output, format)
```

---

## Key Differences

| Aspect | Task 1 | Task 2 |
|--------|--------|--------|
| **Purpose** | Find missed library params | Discover new params |
| **When** | Automatic (during verification) | Manual (separate command) |
| **Integration** | Part of batch job | Standalone CLI command |
| **Input** | Current schema + extracted params | Current schema + extracted params |
| **Output** | LLMInferenceResult (added to extraction) | ParameterProposal (CSV/JSON file) |
| **Prompt** | task1_missed_params.txt | task2_new_params.txt |
| **Review** | Auto-accepted if confidence high | Manual review required |
| **Use Case** | Improve extraction completeness | Expand library coverage |

---

## Configuration

### Enable LLM for Task 1 (Automatic)
```bash
# In .env file
LLM_ENABLE=true
LLM_PROVIDER=claude  # or openai, qwen
LLM_MODE=verify      # Task 1 runs in verify mode

# Run batch job
python batch_process_papers.py --llm-mode verify
```

### Run Task 2 (Manual Discovery)
```bash
# No special .env needed - LLM is always used for discovery
# Just set API keys
ANTHROPIC_API_KEY=your_key

# Run discovery
designspace-extractor discover paper.pdf -o proposals.csv
```

---

## Testing

### Test Task 1
```bash
# Run extraction on a PDF with LLM enabled
python -c "
from extractors.pdfs import PDFExtractor
from pathlib import Path

extractor = PDFExtractor(use_llm=True, llm_mode='verify')
result = extractor.extract_from_file(Path('papers/test.pdf'))

# Check for Task 1 results
task1_params = {k: v for k, v in result['parameters'].items() 
                if v.get('method') == 'llm_missed_params'}
print(f'Task 1 found {len(task1_params)} missed parameters')
"
```

### Test Task 2
```bash
# Test discovery command
designspace-extractor discover papers/test.pdf -o test_proposals.csv

# Check output
cat test_proposals.csv
```

---

## Benefits

### Task 1 Benefits
✅ **Automatic**: Runs without user intervention  
✅ **Immediate value**: Parameters added to extraction results  
✅ **No extra work**: Integrated into existing workflow  
✅ **Catches regex gaps**: Finds what pattern matching missed  

### Task 2 Benefits
✅ **Library expansion**: Systematically grows your parameter coverage  
✅ **Manual control**: User reviews before adding to schema  
✅ **Research insights**: Reveals what researchers are measuring  
✅ **Quality filter**: Prevalence/importance filtering  

---

## Next Steps

1. **Test Task 1** by running batch extraction with LLM enabled
2. **Test Task 2** by running discovery on a representative paper
3. **Review proposals** and add valuable parameters to schema_map.yaml
4. **Update patterns.yaml** with regex patterns for new parameters
5. **Re-run extraction** to validate new parameters are captured

## Questions?

- Task 1 not finding parameters? Check that `current_schema` is being passed
- Task 2 output empty? Paper may already be well-covered by current library
- Want to adjust filters? Use `--min-prevalence` and `--min-importance` flags
- Need different output format? Use `--format json` instead of default CSV
