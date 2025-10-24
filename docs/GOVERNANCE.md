# GOVERNANCE.md

## Purpose
Define a lightweight, multi-lab process for evolving the Design-Space Extractor’s schema, code, and standards mappings while preserving stability and backward compatibility.

## Roles
- **Steering Group (SG):** ≥2 PIs or senior leads from distinct labs; approves breaking changes.
- **Maintainers:** Core engineers maintaining main branch, CI, and releases.
- **Contributors:** Anyone submitting issues/PRs, including RAs and external labs.
- **Reviewers:** Domain experts who review schema and mapping proposals.

## Decision Principles
1. **User impact first:** Prefer changes that reduce RA time, increase accuracy, or improve interoperability.
2. **Stability over novelty:** Breaking changes require migration scripts and deprecation windows.
3. **Open standards:** Prefer HED/BIDS/Psych-DS alignment; map to Cognitive Atlas tasks & contrasts when reasonable.
4. **Evidence-driven:** Use benchmark results (recall/precision/F1) and gold-standard outcomes to justify changes.

## Change Types
- **Patch (x.y.z → x.y.(z+1))**: Bug fixes, doc-only updates, non-breaking code changes.
- **Minor (x.y.z → x.(y+1).0)**: Backward-compatible schema extensions (new optional fields, enum additions).
- **Major ((x).y.z → (x+1).0.0)**: Breaking schema changes, renamed/removed columns, altered semantics.

## Proposal Workflow
1. **Open an Issue** (template: `Schema/Extractor/Standards/Infra`) with:
   - Problem statement & motivation
   - Affected modules/fields
   - Examples (≥3 papers/repos)
   - Migration plan (if any)
   - Validation plan (benchmarks to run)
2. **Discussion Window**: 7–14 days; SG invites domain reviewers.
3. **Decision & Labeling**:
   - `accepted` / `rejected` / `needs-revision`
   - Version bump class (patch/minor/major)
4. **Implementation** (PR):
   - Code + tests + docs + migration scripts
   - Update `benchmark_results.csv` and CI thresholds
5. **Release**:
   - Tag and changelog
   - Announce on project channels; deprecations flagged for 2 releases before removal.

## Deprecation Policy
- Mark fields as `deprecated: true` in schema with rationale.
- Provide migration script (`migrations/<from>_to_<to>.py`) and mapping.
- Maintain deprecated fields for at least **two minor releases** before removal.

## Conflict of Interest
- SG members abstain from votes where they are primary proponents.
- Require one SG member from an unaffiliated lab to approve major changes.

## Voting
- **Minor/Patch:** Maintainer approval + one reviewer.
- **Major:** 2/3 SG approval + 1 maintainer + 1 external reviewer.

## Meetings
- Monthly 30-min sync for roadmap and open proposals.
- Ad hoc meetings for urgent reproducibility/security issues.

## Artifacts
- `docs/decisions/`: one-paragraph rationale for accepted major proposals.
- `validation/benchmark_results.csv`: updated after each release.
