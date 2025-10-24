# LLM Policy (docs/llm_policy.md)

## Purpose
Define **safe, reproducible, and cost-controlled** use of Large Language Models (LLMs) for optional, last-resort extraction of **implicit** parameters (e.g., instructions not codified in configs). Primary extraction remains code/logs-first.

## When LLMs Are Allowed
Use LLM assistance **only** when:
1) Code-based extractor confidence for a parameter `< 0.3`, **and**  
2) The parameter is **non-critical** (not a primary outcome or safety-relevant setting), **and**  
3) At least one textual source exists (README, comments, paper methods).

Always mark LLM-derived fields with:
- `extraction_method: llm_assisted`
- `confidence_llm: [0..1]`
- References in `provenance_sources` (files + line spans)

## Models & Deployment Options
### A) Managed (Hosted) APIs
- Use when setup speed is critical and data is public.
- Log: model name, version, temperature, system+user prompts.

### B) Local / Open-Source on Cluster (Recommended for sensitive or high-volume)
- **Serving stacks:** **vLLM** or **Text Generation Inference (TGI)**.
- **Model families:** **Llama 3/3.1**, **Mistral/Mixtral**, **Phi-3/4**, or domain finetunes.
- **Deployment guidance:**
  - Containerize (Docker) with **pinned weights** and **pinned engine version**.
  - Force determinism: `temperature=0`, `top_p=1`.
  - Disable outbound network if required (air-gapped).
  - Access control (VPN, OAuth, node ACLs).
- **Provenance logging (required):**
  - `model_id`, `weights_hash`, `engine_version`, `prompt_template_id`, `sampler_params`.
  - Store prompts/outputs in the **Provenance** table with timestamps.

## Prompting & Output Schema
- Use structured JSON outputs with explicit fields/enums.
- Require **evidence spans** (file + line numbers) where possible.

Example:
```json
{
  "parameter": "instruction_awareness",
  "value": "explicit_error_reduction",
  "evidence": "README.md:L42-L55",
  "confidence_llm": 0.62
}
