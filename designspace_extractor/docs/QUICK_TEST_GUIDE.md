# Quick Testing Guide - JSON Output Strengthening

## 🚀 Quick Start

### Deploy to Cluster
```bash
# From your local machine
rsync -avz designspace_extractor/ della:/scratch/gpfs/JORDANAT/<username>/designspace_extractor/

# SSH to cluster
ssh della

# Navigate to project
cd /scratch/gpfs/JORDANAT/<username>/designspace_extractor
```

### Run Test Batch
```bash
# Submit batch job
sbatch slurm/batch_process.sh

# Monitor job
squeue -u $USER

# Watch logs in real-time
tail -f logs/batch_*.log
```

## 🔍 What to Look For

### Success Indicators ✅

**In logs, look for these patterns**:

```
✓ Outlines Pydantic generation successful for verify_batch
✓ Outlines dict generation successful for missed_params
✓ Extracted valid JSON from vLLM response for new_params
```

**Expected Strategy Distribution**:
- Strategy 1 (Pydantic + Outlines): 70-90% of calls
- Strategy 2 (Schema + Outlines): 5-15% of calls  
- Strategy 3 (Fallback + Parsing): 5-15% of calls

### Error Patterns ❌

**If you see these, investigation needed**:

```
Failed to extract JSON from vLLM response for <task>: Could not extract valid JSON
Pydantic validation failed: <error>
Outlines Pydantic generation failed: <error>
```

## 📊 Quick Analysis Commands

### Count Success Rates
```bash
# Count successful Pydantic generations
grep "Pydantic generation successful" logs/*.log | wc -l

# Count successful JSON extractions
grep "Extracted valid JSON" logs/*.log | wc -l

# Count failures
grep "Failed to extract JSON" logs/*.log | wc -l

# Success rate
grep -E "(Pydantic generation successful|Extracted valid JSON)" logs/*.log | wc -l
grep "generation error" logs/*.log | wc -l
```

### View Error Details
```bash
# See all JSON extraction failures with context
grep -B 2 -A 5 "Failed to extract JSON" logs/*.log

# See which tasks are failing
grep "Failed to extract JSON" logs/*.log | grep -oP 'task: \K\w+'

# See raw responses that failed
grep "Raw vLLM response" logs/*.log | head -20
```

### Check Task Distribution
```bash
# Count by task type
grep "Using Outlines" logs/*.log | grep -oP 'task: \K\w+' | sort | uniq -c

# Example output:
#   150 verify_batch
#   120 missed_params
#    80 new_params
#    50 verify_single
```

## 🐛 Debugging Workflow

### 1. Enable Debug Logging

Edit your SLURM script or config:
```python
# In your main script or config
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 2. Find Problematic Papers

```bash
# Which papers failed?
grep "Failed to extract JSON" logs/*.log | grep -oP 'study_\d+' | sort | uniq
```

### 3. Test Single Paper

```bash
# Test one paper with debug output
python -m designspace_extractor.test_single_paper \
    --study-id study_12345 \
    --provider qwen72b \
    --log-level DEBUG
```

### 4. Examine Raw Output

Look for lines like:
```
DEBUG - Raw vLLM response (task: verify_batch): Here is my verification: {"sample_size_n": ...
```

This shows what the LLM actually returned before parsing.

### 5. Test JSON Parser Locally

Create `test_json_parser.py`:
```python
from llm.json_parser import extract_json_from_text

# Paste problematic response here
raw_response = '''Your LLM response from logs'''

parsed, error = extract_json_from_text(raw_response)

if parsed:
    print("✓ Successfully extracted:", parsed)
else:
    print("✗ Failed:", error)
    print("Response was:", raw_response[:200])
```

Run:
```bash
python test_json_parser.py
```

## 📈 Expected Results

### Baseline (Before Fix)
- JSON parsing errors: ~30-40%
- Common errors: "Expecting property name", "Extra data"
- Failed extractions per batch: 10-15

### Target (After Fix)
- JSON parsing errors: <1%
- Clean Pydantic validation: 70-90%
- Fallback parsing success: 95%+
- Failed extractions per batch: 0-2

## 🔧 Quick Fixes

### If Outlines Not Working

Check installation:
```bash
pip show outlines
# Should show version 0.1.2 or higher

# Reinstall if needed
pip install --upgrade outlines
```

### If Pydantic Errors

Check models are imported:
```python
from llm.pydantic_schemas import (
    VerificationBatchResponse,
    MissedParametersResponse,
    NewParametersResponse
)

# Test model
model = VerificationBatchResponse(parameters={
    "test_param": {
        "verified": True,
        "confidence": 0.9,
        "evidence": "test evidence",
        "abstained": False
    }
})
print(model.model_dump_json())
```

### If Still Getting Extra Text

Check prompts have the new section:
```bash
grep -A 5 "CRITICAL OUTPUT REQUIREMENTS" llm/prompts/*.txt
```

Should show the new instructions in all 4 files.

## ✅ Success Checklist

After running batch, verify:

- [ ] No "Failed to extract JSON" errors (or <1%)
- [ ] Majority using "Pydantic generation successful"
- [ ] Fallback parsing working when needed ("Extracted valid JSON")
- [ ] Task types distributed correctly (verify_batch most common)
- [ ] No Pydantic validation errors
- [ ] Output files contain valid JSON
- [ ] Parameter counts similar to before (not missing data)

## 🚨 Rollback Plan

If implementation causes issues:

```bash
# Revert to previous version
git checkout HEAD~1 llm/

# Or revert specific files
git checkout HEAD~1 llm/providers.py llm/inference.py llm/discovery.py

# Redeploy
rsync -avz designspace_extractor/ cluster:/path/to/project/
```

## 📞 Support

If issues persist:
1. Collect example failures: `grep "Failed" logs/*.log > failures.txt`
2. Collect raw outputs: `grep "Raw vLLM response" logs/*.log > raw_outputs.txt`
3. Check which strategy was attempted
4. Review Pydantic validation errors
5. Document the pattern and create GitHub issue

---

**Remember**: This is a defensive multi-layer approach. If one layer fails, the next should catch it. Look for patterns in which layer is handling which task type.
