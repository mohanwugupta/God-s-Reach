-- Migration: Add proposed_parameters and llm_inference_provenance tables
-- Version: 1.5 (LLM Three-Stage Policy Support)
-- Date: 2025-11-06
-- Description: Support for LLM discovery (Stage 3) and inference provenance (Stage 2)

-- ============================================================================
-- Proposed Parameters Table (Stage 3 discovery output)
-- ============================================================================
CREATE TABLE IF NOT EXISTS proposed_parameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parameter_name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN (
        'demographics', 'task_design', 'perturbation', 'feedback',
        'equipment', 'outcome', 'trials', 'context'
    )),
    evidence TEXT NOT NULL,  -- Verbatim quote
    evidence_location TEXT,  -- Page/section/line
    example_values TEXT,  -- JSON array of examples
    units TEXT,
    prevalence TEXT CHECK(prevalence IN ('low', 'medium', 'high')),
    importance TEXT CHECK(importance IN ('low', 'medium', 'high')),
    mapping_suggestion TEXT,  -- Closest existing parameter or "new"
    hed_hint TEXT,  -- HED tag suggestion
    confidence REAL CHECK(confidence BETWEEN 0 AND 1),
    
    -- Governance fields
    proposed_date TEXT NOT NULL,
    proposed_by TEXT DEFAULT 'llm_discovery',
    source_paper_id TEXT,  -- Paper that triggered discovery
    promoted BOOLEAN DEFAULT 0,
    promoted_date TEXT,
    reviewer_1 TEXT,
    reviewer_2 TEXT,
    review_notes TEXT,
    
    FOREIGN KEY (source_paper_id) REFERENCES experiments(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_proposed_parameters_name ON proposed_parameters(parameter_name);
CREATE INDEX IF NOT EXISTS idx_proposed_parameters_promoted ON proposed_parameters(promoted);
CREATE INDEX IF NOT EXISTS idx_proposed_parameters_importance ON proposed_parameters(importance, prevalence);
CREATE INDEX IF NOT EXISTS idx_proposed_parameters_source ON proposed_parameters(source_paper_id);

-- ============================================================================
-- LLM Inference Provenance Table (Stage 2 verify/fallback output)
-- ============================================================================
CREATE TABLE IF NOT EXISTS llm_inference_provenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT NOT NULL,
    parameter_name TEXT NOT NULL,
    inferred_value TEXT NOT NULL,
    confidence REAL CHECK(confidence BETWEEN 0 AND 1),
    evidence TEXT NOT NULL,  -- Verbatim quote
    evidence_location TEXT,  -- Page/section/line
    reasoning TEXT,
    llm_provider TEXT,
    llm_model TEXT,
    inference_mode TEXT CHECK(inference_mode IN ('verify', 'fallback')) DEFAULT 'fallback',
    inference_date TEXT NOT NULL,
    abstained BOOLEAN DEFAULT 0,
    
    -- Review fields
    requires_review BOOLEAN DEFAULT 1,
    reviewed BOOLEAN DEFAULT 0,
    reviewer TEXT,
    review_date TEXT,
    review_decision TEXT CHECK(review_decision IN ('accept', 'reject', 'modify', NULL)),
    review_notes TEXT,
    
    FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_llm_provenance_experiment ON llm_inference_provenance(experiment_id);
CREATE INDEX IF NOT EXISTS idx_llm_provenance_parameter ON llm_inference_provenance(parameter_name);
CREATE INDEX IF NOT EXISTS idx_llm_provenance_review ON llm_inference_provenance(requires_review, reviewed);
CREATE INDEX IF NOT EXISTS idx_llm_provenance_mode ON llm_inference_provenance(inference_mode);

-- ============================================================================
-- Views for LLM Governance
-- ============================================================================

-- Proposed parameters needing review
CREATE VIEW IF NOT EXISTS v_proposed_parameters_review AS
SELECT 
    id,
    parameter_name,
    description,
    category,
    evidence,
    importance,
    prevalence,
    confidence,
    source_paper_id,
    proposed_date,
    reviewer_1,
    reviewer_2
FROM proposed_parameters
WHERE promoted = 0
ORDER BY 
    CASE importance WHEN 'high' THEN 3 WHEN 'medium' THEN 2 ELSE 1 END DESC,
    CASE prevalence WHEN 'high' THEN 3 WHEN 'medium' THEN 2 ELSE 1 END DESC,
    proposed_date DESC;

-- LLM inferences needing review
CREATE VIEW IF NOT EXISTS v_llm_inferences_review AS
SELECT 
    l.id,
    l.experiment_id,
    l.parameter_name,
    l.inferred_value,
    l.confidence,
    l.evidence,
    l.inference_mode,
    l.inference_date,
    e.paper_id,
    e.lab_name
FROM llm_inference_provenance l
JOIN experiments e ON l.experiment_id = e.id
WHERE l.requires_review = 1 AND l.reviewed = 0
ORDER BY 
    CASE WHEN l.confidence < 0.5 THEN 1 ELSE 0 END DESC,  -- Low confidence first
    l.inference_date DESC;

-- Aggregated proposal statistics
CREATE VIEW IF NOT EXISTS v_proposal_statistics AS
SELECT 
    parameter_name,
    COUNT(*) as proposal_count,
    GROUP_CONCAT(DISTINCT source_paper_id) as source_papers,
    MAX(importance) as max_importance,
    MAX(prevalence) as max_prevalence,
    AVG(confidence) as avg_confidence,
    MAX(promoted) as is_promoted
FROM proposed_parameters
GROUP BY parameter_name
HAVING proposal_count >= 2  -- Only show parameters proposed by multiple papers
ORDER BY proposal_count DESC, max_importance DESC;
