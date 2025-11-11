# Critical Fixes for JSON Parsing Issues

## 🔴 **Root Cause Analysis**

Based on the error logs, three critical issues were identified:

### **Issue 1: Prompt Echo-Back**
```
Raw response: ---

PARAMETER: "population"
DESCRIPTION: The number of people living in a specific area...
CONTEXT: According to the United Nations...
```

**Problem**: The entire prompt is being echoed back in the response.

**Root Cause**: **Missing chat template formatting** - vLLM was treating input as raw text instead of a chat conversation.

**Fix**: Applied Qwen chat template with system/user/assistant roles:
```python
formatted_prompt = f"""<|im_start|>system
You are a helpful assistant that outputs only valid JSON as requested.<|im_end|>
<|im_start|>user
{prompt}<|im_end|>
<|im_start|>assistant
"""
```

### **Issue 2: Double Braces `{{`**
```
Raw response: {{
  "missed_parameters": []
}}
```

**Problem**: LLM producing `{{` instead of `{`.

**Root Cause**: Model interpreting prompt examples as template placeholders.

**Fix**: Added double-brace cleaning in `json_parser.py`:
```python
# Fix {{ at the very start
text = re.sub(r'^\{\{\s*', '{', text)
# Fix }} at the very end  
text = re.sub(r'\s*\}\}$', '}', text)
```

### **Issue 3: Outlines Not Constraining**
```
}} To ensure the output is as requested, I will provide an example...
```

**Problem**: LLM adding explanatory text after valid JSON despite Outlines.

**Root Cause**: 
1. Outlines may not be properly wrapping the vLLM model
2. Chat template not applied to Outlines prompts
3. Outlines generator might be failing silently

**Fix**: 
- Applied chat template to ALL generation strategies (Outlines + fallback)
- Added better error logging for Outlines failures
- Changed log level from DEBUG to INFO for visibility
- Return `None` instead of malformed response to signal clear failure

---

## ✅ **Fixes Implemented**

### **Fix 1: Chat Template for All Strategies** ✅

**File**: `llm/providers.py` - `Qwen72BProvider.generate()`

**Before**:
```python
response = generator(prompt)  # Raw prompt
```

**After**:
```python
# Apply chat template ONCE at the start
formatted_prompt = f"""<|im_start|>system
You are a helpful assistant that outputs only valid JSON as requested.<|im_end|>
<|im_start|>user
{prompt}<|im_end|>
<|im_start|>assistant
"""

# Use formatted prompt in ALL strategies
response = generator(formatted_prompt)  # Strategy 1 & 2
outputs = vllm_model.generate([formatted_prompt], sampling_params)  # Strategy 3
```

**Impact**: 
- Prevents prompt echo-back
- Establishes clear assistant role for JSON output
- Works with both Outlines and regular vLLM

---

### **Fix 2: Double Brace Cleaning** ✅

**File**: `llm/json_parser.py` - `clean_json_string()`

**Added**:
```python
# Fix double braces that some models produce ({{ -> {)
import re
text = re.sub(r'^\{\{\s*', '{', text)  # Fix {{ at start
text = re.sub(r'\s*\}\}$', '}', text)  # Fix }} at end
```

**Impact**:
- Handles template-style output from model
- Only fixes obvious mistakes (start/end positions)
- Preserves intentional double braces inside JSON strings

---

### **Fix 3: Enhanced Error Logging** ✅

**File**: `llm/providers.py`

**Changes**:
1. Changed `logger.debug()` → `logger.info()` for critical messages
2. Added full traceback logging on Outlines failures
3. Added check for response type from Outlines (dict/str/BaseModel)
4. Return `None` on JSON extraction failure instead of raw text

**Before**:
```python
logger.debug(f"✓ Outlines Pydantic generation successful")
```

**After**:
```python
logger.info(f"✓ Outlines Pydantic generation successful for {task_type}")
logger.error(f"Outlines Pydantic generation failed: {e}")
logger.error(traceback.format_exc())  # Full stack trace
```

**Impact**:
- Immediately see which strategy succeeded/failed
- Detailed error info for debugging Outlines issues
- Task-specific logging helps identify problematic prompts

---

### **Fix 4: Model Unwrapping for Fallback** ✅

**File**: `llm/providers.py`

**Added**:
```python
# Check if we need to unwrap the model
vllm_model = self.llm
if is_wrapped and hasattr(self.llm, 'model'):
    vllm_model = self.llm.model
    logger.debug("Using unwrapped vLLM model for regular generation")
```

**Impact**:
- Handles case where Outlines wrapper exists but isn't used
- Ensures vLLM.generate() works in fallback mode
- Prevents method not found errors

---

### **Fix 5: Clean Failure Signaling** ✅

**File**: `llm/providers.py`

**Before**:
```python
else:
    logger.error(f"Failed to extract JSON...")
    return raw_response  # Return malformed response
```

**After**:
```python
else:
    logger.error(f"Failed to extract JSON...")
    return None  # Signal clear failure
```

**Impact**:
- Calling code can detect failure and handle appropriately
- Prevents malformed JSON from propagating
- Cleaner error handling downstream

---

## 🧪 **Expected Behavior After Fixes**

### **Successful Outlines Generation**:
```
INFO - Attempting Outlines Pydantic generation for missed_params
INFO - ✓ Outlines Pydantic generation successful for missed_params
```

Response will be clean JSON:
```json
{
  "missed_parameters": []
}
```

### **Successful Fallback Generation**:
```
ERROR - Outlines Pydantic generation failed: <error details>
INFO - Using regular vLLM generation for missed_params
INFO - ✓ Extracted valid JSON from vLLM response for missed_params
```

Response will be cleaned JSON (braces fixed, extra text removed).

### **Complete Failure**:
```
ERROR - Outlines Pydantic generation failed: <error>
ERROR - Failed to extract JSON from vLLM response: Could not extract valid JSON
```

Returns `None` - calling code will log "Failed to parse Task 1 response" but won't crash.

---

## 📊 **Testing Checklist**

After deploying fixes, verify:

- [ ] **No more prompt echo-back** - raw response should start with `{` not `---`
- [ ] **No more double braces** - responses should have `{` not `{{`
- [ ] **Less explanatory text** - chat template should enforce JSON-only
- [ ] **Outlines attempts visible** - logs show "Attempting Outlines..."
- [ ] **Clear success/failure** - logs show which strategy worked
- [ ] **Graceful failures** - parsing errors caught, None returned

### **Log Analysis Commands**:

```bash
# Count Outlines successes
grep "Outlines.*generation successful" logs/*.log | wc -l

# Count fallback successes
grep "Extracted valid JSON from vLLM" logs/*.log | wc -l

# Count total failures
grep "Failed to extract JSON" logs/*.log | wc -l

# Check for prompt echo-back (should be ZERO)
grep "Raw response: ---" logs/*.log | wc -l

# Check for double braces (should be much lower)
grep "Raw response: {{" logs/*.log | wc -l
```

---

## 🔄 **What Changed in Workflow**

### **Before**:
1. Build prompt
2. Pass raw prompt to vLLM
3. vLLM treats it as raw text → echoes back
4. JSON parsing fails on echoed prompt
5. Returns malformed response

### **After**:
1. Build prompt
2. **Wrap prompt in chat template** (system/user/assistant)
3. Try Outlines with formatted prompt
4. If Outlines fails, try regular vLLM with formatted prompt
5. Extract JSON with brace cleaning
6. Return clean JSON or None

---

## 🚨 **Potential Issues to Watch**

### **Issue**: Outlines still not working
**Symptom**: All requests use "regular vLLM generation"
**Debug**:
```bash
# Check if Outlines is available
grep "Outlines library available" logs/*.log
# Check if wrapping succeeded
grep "vLLM model wrapped for Outlines" logs/*.log
# Check for wrap failures
grep "Failed to wrap vLLM model" logs/*.log
```

### **Issue**: Chat template breaks Outlines
**Symptom**: "Outlines Pydantic generation failed" on every request
**Debug**: Look at exception in logs, may need to adjust chat template

### **Issue**: Still getting extra text
**Symptom**: Valid JSON followed by "Let me explain..."
**Solution**: Check stop tokens are working:
```python
stop=["</s>", "<|endoftext|>", "<|im_end|>"]
```

---

## 📝 **Files Modified in This Fix**

1. **`llm/providers.py`**
   - Added chat template formatting
   - Enhanced error logging
   - Added model unwrapping
   - Changed return None on failure

2. **`llm/json_parser.py`**
   - Added double-brace cleaning
   - Integrated cleaning into extraction flow

---

## 🎯 **Success Metrics**

| Metric | Before | Target | How to Measure |
|--------|--------|--------|----------------|
| Prompt echo-back | 100% | 0% | `grep "Raw response: ---"` |
| Double braces | 50%+ | <5% | `grep "Raw response: {{"` |
| JSON extraction failures | 30-40% | <5% | `grep "Failed to extract JSON"` |
| Outlines usage | 0% | 70%+ | `grep "Outlines.*successful"` |

---

## 🚀 **Deployment**

```bash
# 1. Sync to cluster
rsync -avz designspace_extractor/ della:/path/to/project/

# 2. Test single paper first
sbatch slurm/test_single.sh

# 3. Check logs immediately
tail -f logs/test_*.log

# 4. Look for these SUCCESS indicators:
# - "Attempting Outlines Pydantic generation"
# - "✓ Outlines Pydantic generation successful"
# - NO "Raw response: ---"
# - NO "Raw response: {{"

# 5. If successful, run full batch
sbatch slurm/batch_process.sh
```

---

**Critical Changes Summary**:
1. ✅ Chat template applied to ALL generation strategies
2. ✅ Double-brace cleaning in JSON parser
3. ✅ Enhanced error logging (DEBUG → INFO)
4. ✅ Model unwrapping for fallback
5. ✅ Return None on failure (not malformed response)

These fixes address the root causes of all three error patterns observed in your logs.
