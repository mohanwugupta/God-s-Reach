# 📘 Product Requirements Document
**Project:** Automated Design-Space Parameter Extractor  
**Phase:** 1 – Motor Adaptation Experiments  
**Owner:** Mohan Gupta / Princeton Lab  
**Version:** v1.3 (Incorporates Review Recommendations)  
**Date:** 2025-10-20  

---

## 1️⃣ Purpose

This document specifies a **Python command-line tool** for automated extraction, mapping, validation, and storage of experimental design parameters across motor adaptation studies. It transforms heterogeneous experimental scripts and papers into structured, standards-compliant metadata that can be searched, validated, and visualized.

Version **1.3** integrates the review’s recommendations: conflict resolution policy, temporal/context representation, expanded schema (equipment, reward, noise), rigorous validation (including longitudinal tests), reproducibility (Docker & pinning), provenance auditing, Cognitive Atlas contrasts, and formal governance & LLM policies.

---

## 2️⃣ Objectives

| Objective | Success Metric |
|---|---|
| Automate metadata capture | ≥ 80% of parameters correctly extracted across 200 repos |
| Quantitative validation | ≥ 0.85 overall F1; per-parameter targets in §7 |
| Schema scalability | Schema supports ≥ 95% of variation within motor adaptation |
| Community adoption & governance | ≥ 3 partner labs; active governance (see §11) |
| Standards alignment | 100% HED/BIDS & Psych-DS; Cognitive Atlas **tasks & contrasts** mapped |
| Reproducibility & provenance | Dockerized & pinned; full provenance trail captured |

---

## 3️⃣ Architecture Overview

```
user input (repo or pdf)
      ↓
 file discovery
      ↓
 extractor (code/logs/pdf)
      ↓
 conflict resolution + confidence scoring
      ↓
 mapping + normalization (HED-aware)
      ↓
 validation (quantitative + schema compliance + longitudinal checks)
      ↓
 structured database (SQLite) + provenance tables
      ↓
 Google Sheet (entry_status=needs_review) & export bridges (Psych-DS, MetaLab)
```

---

## 4️⃣ Core Modules & Responsibilities

| Module | Description | Key Files |
|---|---|---|
| **CLI Interface** | Unified entry-point for all users | `cli.py`, `__main__.py` |
| **Extractors** | Parse code/logs/configs/PDFs; populate schema | `extractors/code_data.py`, `extractors/pdfs.py` |
| **MATLAB/JS Bridges** | MATLAB Engine (or Octave fallback) and Babel parser for JS | `extractors/matlab_bridge.py`, `extractors/js_babel.py` |
| **Conflict Resolution** | Reconcile parameter conflicts; log discrepancies | `utils/conflict_resolution.py` |
| **Mapping Layer** | Aliases → canonical schema; unit normalization | `mapping/schema_map.yaml`, `mapping/synonyms.yaml` |
| **Schema Migrations** | Track and migrate schema versions | `migrations/` |
| **Validation Suite** | Recall/precision/F1; cross-lab/adversarial/longitudinal tests | `validation/` |
| **Structured DB Layer** | SQLite (Experiments→Sessions→Blocks→Trials) + provenance | `database/models.py`, `database/schema.sql` |
| **HED Layer** | Tag generation & validation (MotorAdaptation library) | `hed/` |
| **Standards Bridges** | Psych-DS, Cognitive Atlas (tasks **and** contrasts), MetaLab/PsychMADS exporters | `standards/` |
| **Sheets Integration** | Sync DB → Sheets for collaborative review | `utils/sheets_api.py` |
| **LLM Assist (optional)** | Controlled, logged inference for implicit parameters | `llm/llm_assist.py`, `docs/llm_policy.md` |

---

## 5️⃣ Repo Skeleton

```
designspace_extractor/
│
├── cli.py
├── __main__.py
│
├── extractors/
│   ├── code_data.py
│   ├── pdfs.py
│   ├── matlab_bridge.py
│   ├── js_babel.py
│   ├── kinarm_plugin.py
│   └── __init__.py
│
├── utils/
│   ├── conflict_resolution.py
│   ├── sheets_api.py
│   ├── io_helpers.py
│   └── __init__.py
│
├── mapping/
│   ├── schema_map.yaml
│   ├── synonyms.yaml
│   ├── patterns.yaml
│   ├── migrations/
│   └── __init__.py
│
├── database/
│   ├── models.py
│   ├── schema.sql
│   └── __init__.py
│
├── hed/
│   ├── hed_map.yaml
│   ├── generate_tags.py
│   ├── validate_tags.py
│   ├── MotorAdaptation_HED_library.json
│   └── __init__.py
│
├── standards/
│   ├── psychds_export.py
│   ├── cognitive_atlas_map.yaml
│   ├── metalab_export.py
│   └── psychmads_export.py
│
├── validation/
│   ├── tests/
│   ├── gold_standard_protocol.md
│   ├── benchmark_results.csv
│   ├── adversarial_fixtures/
│   └── longitudinal_fixtures/
│
├── llm/
│   ├── llm_assist.py
│   └── prompts/
│
├── out/
│   ├── staging_adaptation.csv
│   ├── hed_events.tsv
│   └── logs/
│
├── Dockerfile
├── requirements.lock
├── README.md
└── GOVERNANCE.md
```

---

## 6️⃣ Functional Enhancements

### 6.1 Conflict Resolution Policy
- Precedence: **trial logs > config > code > paper**.
- Conflicts set `conflict_flag=true`; all sources listed in `provenance_sources` with file paths + content hashes.
- Policies editable in `conflict_resolution.yaml`; exposed in review UI.

### 6.2 Schema Improvements
- **Temporal schedule:** `schedule_structure` JSON epochs/blocks (onset, duration, parameter values & transitions).
- **Context transitions:** Instruction and feedback changes with onset trial indices & durations.
- **Critical metadata:** `sample_size_n`, demographics (`age_mean`, `age_sd`, `handedness_criteria`), `equipment` (see 6.3), `counterbalancing_scheme`, `trial_exclusion_criteria`, `preprocessing_pipeline`, structured `outcome_measures` `{type, timing, aggregation}`.
- **Error models/noise:** `cursor_noise_sd_mm`, `motor_noise_model` (optional).
- **Reward:** `reward_type` (points/money/none), `reward_schedule`.
- **Familiarization & breaks:** `familiarization_trials`, `block_breaks` (timing/criteria).
- **Versioning:** `schema_version`, `created_at`, `updated_at` in DB and exports.

### 6.3 Equipment Specification Schema
```yaml
equipment:
  manipulandum_type: [kinarm_exoskeleton, vbot_planar, phantom_haptic, touchscreen, vr_controller, other]
  workspace_dimensions_cm: {width: float, height: float}
  mass_inertia_compensation: [yes, no, unknown]
  position_sensor_resolution_mm: float
  sampling_rate_hz: float
```

### 6.4 Extraction Improvements
- **MATLAB Parsing:** MATLAB Engine API where available; **Octave fallback** (headless); regex only as last resort.
- **JavaScript Parsing:** `@babel/parser` for modern syntax.
- **KinArm:** Optional plugin (XML/HDF5 readers).
- **PDF:** GROBID first; **VLM fallback** (GPT‑4V or equivalent) under LLM policy.
- **Performance:** Multiprocessing for AST; **async I/O** for HDF5/MAT/JSON.

### 6.5 Structured Data Model (SQLite + Provenance)
- Tables: `Experiments`, `Sessions`, `Blocks`, `Trials`, `Provenance`, `ManualOverrides`.
- `Provenance` records repo URL, commit hash, extractor version, LLM model/version/temp, prompts, timestamps.
- Google Sheet is a synchronized *view* for review; SQLite is source of truth.

### 6.6 Validation & Benchmarking
- **Gold Standard:** 20 repos; 3 expert raters; κ>0.8; **decision tree** for implicit parameters in `gold_standard_protocol.md`.
- **Metrics:** Recall, precision, F1 **per parameter**; adversarial & cross-lab suites; **longitudinal consistency test** after migrations.
- **CI gates:** F1 non‑regression; longitudinal diffs within tolerance.

### 6.7 Reproducibility & Budgeting
- **Docker** + **requirements.lock**; CI runs in container.
- **Caching & Parallelism:** Hash-based cache; worker pools with progress.
- **LLM Cost Controls:** Budget cap via env vars; dry‑run; `temperature=0`; usage & prompts logged.

### 6.8 Standards Integration
- **HED/BIDS:** MotorAdaptation library; events.tsv + JSON sidecar.
- **Cognitive Atlas:** Map **task** and **contrast** IDs.
- **Psych-DS:** Auto-generate `dataset_description.json` (authors, license, funding) for FAIR sharing.
- **MetaLab/PsychMADS:** Exporters for meta-analytic pipelines.

---

## 7️⃣ Validation Metrics (Per-Parameter Targets)

| Parameter | Recall | Precision | F1 | Notes |
|---|---:|---:|---:|---|
| rotation_magnitude | 0.95 | 0.90 | 0.92 | Explicit in configs/logs |
| feedback_delay | 0.85 | 0.80 | 0.82 | Often implicit |
| perturbation_schedule | 0.90 | 0.88 | 0.89 | From epoch structure |
| instruction_awareness | 0.78 | 0.80 | 0.79 | With decision tree |
| context_cues | 0.85 | 0.85 | 0.85 | Events + sidecars |
| demographics/sample_size | 0.95 | 0.95 | 0.95 | Usually explicit |
| equipment_spec | 0.90 | 0.92 | 0.91 | Plugin-based |
| reward_structure | 0.85 | 0.90 | 0.87 | Methods/logs |
| noise_model | 0.70 | 0.85 | 0.77 | Optional; rarer |

**Overall F1 goal:** ≥ 0.85; CI enforces non‑regression.

---

## 8️⃣ Roadmap & Gates

| Phase | Duration | Deliverables |
|---|---|---|
| **Phase 0 – Governance & Gold Standard** | 2–4 wks | `GOVERNANCE.md`, `docs/llm_policy.md`, recruit raters, annotate 20 repos, compute κ |
| **Phase 1A – MVP (Python/JSON + SQLite)** | 4 wks | Hybrid extraction, DB + provenance, Psych‑DS export |
| **Phase 1B – Conflict + Temporal Schema** | 4 wks | Merge policies, `schedule_structure`, review UI |
| **Phase 2 – Full Validation Suite** | 6 wks | MATLAB bridge, benchmarks, adversarial/cross‑lab/longitudinal tests, CI gates |
| **Phase 3 – Multi‑Lab Beta & Exporters** | 4+ wks | MetaLab/PsychMADS exporters, CogAtlas contrasts, plugin API |

**Go/No‑Go Gates:** After Phase 0: κ ≥ 0.75; After 1A: overall F1 ≥ 0.70; After 2: cross‑lab F1 drop ≤ 0.15 vs. in‑lab.

---

## 9️⃣ Non‑Functional Requirements

| Attribute | Requirement |
|---|---|
| Install | Docker or `pip install -r requirements.lock` |
| Runtime | ≤ 5 min per large repo (95th percentile) |
| Multi‑User | Concurrent RA usage; optimistic locking on DB sync |
| Privacy | Metadata‑only; no PII; optional DOI redaction prior to public export |
| Interoperability | HED/BIDS/Psych‑DS; Cognitive Atlas tasks & contrasts |
| Reliability | CI enforces F1 and longitudinal stability gates |
| Cost Control | LLM budget caps & full usage logs |

---

## 🔟 Future Extensions

- **Parameter Explorer Dashboard** (Plotly/Streamlit) for heatmaps, co‑occurrence networks, timeline of design‑space coverage.
- **Preregistration template generator** from schema fields.
- **Automated Methods section generator** (reverse mapping from schema row).
- **Teaching module** for reproducible neuroscience.

---

## 1️⃣1️⃣ Governance & Policies

- **GOVERNANCE.md:** Multi‑lab schema process: issue → review → approval by ≥2 lab PIs; deprecations flagged for 2 releases; semantic versioning for breaking changes.
- **LLM Policy (`docs/llm_policy.md`):** Use only when code‑based confidence < 0.3; exclude primary outcomes; `temperature=0`; log model/version/prompt; human review required; budget caps via env vars; never run on unpublished private data without owner consent.
- **Provenance Auditing:** `Provenance` table captures repo URL, commit hash, extractor version, LLM settings, prompts, timestamps, manual overrides; included in Psych‑DS export for FAIR compliance.

---

## ✅ Summary

v1.3 operationalizes the review’s recommendations with concrete modules, metrics, policies, and gates. It establishes a robust, community‑ready infrastructure for mapping the motor adaptation design space and sets the stage for Phase‑2 expansion to motor sequence learning.

