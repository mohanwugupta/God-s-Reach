-- Design-Space Parameter Extractor Database Schema
-- Version: 1.4 (Added Multi-Experiment Support)
-- Date: 2025-10-23

-- ============================================================================
-- Experiments Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,  -- e.g., EXP001
    name TEXT NOT NULL,
    description TEXT,
    
    -- Multi-experiment support
    parent_experiment_id TEXT,  -- NULL for standalone/parent, references parent for child experiments
    experiment_number INTEGER,  -- Sequential number within paper (1, 2, 3...), NULL for standalone
    paper_id TEXT,  -- Shared ID for all experiments from same paper/source
    is_multi_experiment BOOLEAN DEFAULT 0,  -- TRUE if this is a parent of multiple experiments
    
    -- Study metadata
    study_type TEXT,  -- e.g., "visuomotor_rotation", "force_field"
    publication_doi TEXT,
    lab_name TEXT,
    principal_investigator TEXT,
    
    -- Sample information
    sample_size_n INTEGER,
    age_mean REAL,
    age_sd REAL,
    handedness_criteria TEXT,  -- e.g., "right-handed", "Edinburgh >50"
    
    -- Equipment specification
    equipment_manipulandum_type TEXT,  -- kinarm_exoskeleton, vbot_planar, etc.
    equipment_workspace_width_cm REAL,
    equipment_workspace_height_cm REAL,
    equipment_mass_inertia_compensation TEXT,  -- yes, no, unknown
    equipment_position_sensor_resolution_mm REAL,
    equipment_sampling_rate_hz REAL,
    
    -- Experimental design
    counterbalancing_scheme TEXT,
    trial_exclusion_criteria TEXT,
    preprocessing_pipeline TEXT,
    
    -- Temporal schedule (JSON)
    schedule_structure TEXT,  -- JSON: epochs/blocks with onset, duration, parameter transitions
    
    -- Outcome measures (JSON)
    outcome_measures TEXT,  -- JSON: [{type, timing, aggregation}]
    
    -- Raw extracted parameters (JSON)
    extracted_params TEXT,  -- JSON: raw extraction results from PDFs/code
    
    -- Flags and status
    conflict_flag BOOLEAN DEFAULT 0,
    entry_status TEXT DEFAULT 'needs_review',  -- needs_review, validated, published
    
    -- Provenance
    provenance_sources TEXT,  -- JSON: [{source_type, file_path, content_hash}]
    extractor_version TEXT,
    
    -- Schema versioning
    schema_version TEXT DEFAULT '1.4',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    FOREIGN KEY (parent_experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
);

-- ============================================================================
-- Sessions Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,  -- e.g., EXP001_S01
    experiment_id TEXT NOT NULL,
    session_number INTEGER NOT NULL,
    
    -- Session details
    session_type TEXT,  -- baseline, adaptation, retention, etc.
    session_date DATE,
    duration_minutes REAL,
    
    -- Context information
    instruction_text TEXT,
    instruction_awareness TEXT,  -- explicit, implicit, unknown
    context_cues TEXT,  -- JSON: visual, auditory, proprioceptive cues
    
    -- Familiarization and breaks
    familiarization_trials INTEGER,
    block_breaks TEXT,  -- JSON: [{after_block, duration_minutes, criteria}]
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
);

-- ============================================================================
-- Blocks Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS blocks (
    id TEXT PRIMARY KEY,  -- e.g., EXP001_S01_B01
    session_id TEXT NOT NULL,
    block_number INTEGER NOT NULL,
    
    -- Block characteristics
    block_type TEXT,  -- baseline, adaptation, washout, etc.
    num_trials INTEGER,
    
    -- Perturbation parameters
    rotation_magnitude_deg REAL,
    rotation_direction TEXT,  -- CW, CCW
    force_field_strength REAL,
    force_field_type TEXT,  -- curl, divergent, etc.
    
    -- Feedback parameters
    feedback_type TEXT,  -- visual, haptic, auditory, none
    feedback_delay_ms REAL,
    cursor_visible BOOLEAN,
    cursor_noise_sd_mm REAL,
    
    -- Timing
    trial_duration_ms REAL,
    inter_trial_interval_ms REAL,
    
    -- Reward structure
    reward_type TEXT,  -- points, money, none
    reward_schedule TEXT,  -- continuous, intermittent, etc.
    
    -- Motor noise model (optional)
    motor_noise_model TEXT,  -- JSON: model parameters
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- ============================================================================
-- Trials Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS trials (
    id TEXT PRIMARY KEY,  -- e.g., EXP001_S01_B01_T001
    block_id TEXT NOT NULL,
    trial_number INTEGER NOT NULL,
    
    -- Trial-level parameters (override block defaults if needed)
    rotation_magnitude_deg REAL,
    feedback_delay_ms REAL,
    cursor_visible BOOLEAN,
    reward_given BOOLEAN,
    
    -- Trial timing
    trial_onset_time_ms REAL,
    trial_duration_ms REAL,
    
    -- Trial outcome (if available from logs)
    endpoint_error_mm REAL,
    movement_time_ms REAL,
    peak_velocity_mm_s REAL,
    reaction_time_ms REAL,
    trial_excluded BOOLEAN DEFAULT 0,
    exclusion_reason TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (block_id) REFERENCES blocks(id) ON DELETE CASCADE
);

-- ============================================================================
-- Provenance Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS provenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT NOT NULL,
    
    -- Source information
    repo_url TEXT,
    repo_commit_hash TEXT,
    file_path TEXT,
    file_content_hash TEXT,
    source_type TEXT,  -- code, config, log, pdf, manual
    
    -- Extraction metadata
    extractor_version TEXT,
    extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- LLM usage (if applicable)
    llm_provider TEXT,  -- claude, openai, qwen, none
    llm_model TEXT,
    llm_temperature REAL,
    llm_prompt TEXT,
    llm_response TEXT,
    llm_cost_usd REAL,
    
    -- Conflict information
    conflict_detected BOOLEAN DEFAULT 0,
    conflict_resolution_policy TEXT,
    alternative_values TEXT,  -- JSON: alternative parameter values from other sources
    
    FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
);

-- ============================================================================
-- Manual Overrides Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS manual_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT NOT NULL,
    parameter_name TEXT NOT NULL,
    
    -- Override details
    original_value TEXT,
    override_value TEXT,
    override_reason TEXT,
    override_by TEXT,  -- username or RA identifier
    override_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Approval tracking
    approved_by TEXT,
    approval_timestamp TIMESTAMP,
    
    FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(entry_status);
CREATE INDEX IF NOT EXISTS idx_experiments_lab ON experiments(lab_name);
CREATE INDEX IF NOT EXISTS idx_experiments_parent ON experiments(parent_experiment_id);
CREATE INDEX IF NOT EXISTS idx_experiments_paper ON experiments(paper_id);
CREATE INDEX IF NOT EXISTS idx_sessions_experiment ON sessions(experiment_id);
CREATE INDEX IF NOT EXISTS idx_blocks_session ON blocks(session_id);
CREATE INDEX IF NOT EXISTS idx_trials_block ON trials(block_id);
CREATE INDEX IF NOT EXISTS idx_provenance_experiment ON provenance(experiment_id);
CREATE INDEX IF NOT EXISTS idx_provenance_source_type ON provenance(source_type);
CREATE INDEX IF NOT EXISTS idx_manual_overrides_experiment ON manual_overrides(experiment_id);

-- ============================================================================
-- Views for Common Queries
-- ============================================================================

-- Full experiment view with all hierarchy
CREATE VIEW IF NOT EXISTS v_experiment_full AS
SELECT 
    e.id as experiment_id,
    e.name,
    e.study_type,
    e.parent_experiment_id,
    e.experiment_number,
    e.paper_id,
    e.is_multi_experiment,
    e.sample_size_n,
    e.equipment_manipulandum_type,
    e.conflict_flag,
    e.entry_status,
    s.id as session_id,
    s.session_number,
    b.id as block_id,
    b.block_number,
    b.rotation_magnitude_deg,
    b.feedback_delay_ms,
    t.id as trial_id,
    t.trial_number
FROM experiments e
LEFT JOIN sessions s ON e.id = s.experiment_id
LEFT JOIN blocks b ON s.id = b.session_id
LEFT JOIN trials t ON b.id = t.block_id;

-- Experiments needing review
CREATE VIEW IF NOT EXISTS v_experiments_needs_review AS
SELECT 
    id,
    name,
    study_type,
    lab_name,
    parent_experiment_id,
    experiment_number,
    paper_id,
    conflict_flag,
    created_at,
    updated_at
FROM experiments
WHERE entry_status = 'needs_review'
ORDER BY created_at DESC;

-- Multi-experiment groups view
CREATE VIEW IF NOT EXISTS v_multi_experiment_groups AS
SELECT 
    paper_id,
    COUNT(*) as num_experiments,
    GROUP_CONCAT(id) as experiment_ids,
    MIN(created_at) as first_created,
    MAX(updated_at) as last_updated
FROM experiments
WHERE paper_id IS NOT NULL
GROUP BY paper_id;

-- Parent-child experiment relationships
CREATE VIEW IF NOT EXISTS v_experiment_hierarchy AS
SELECT 
    parent.id as parent_id,
    parent.name as parent_name,
    parent.paper_id,
    child.id as child_id,
    child.name as child_name,
    child.experiment_number,
    child.entry_status
FROM experiments parent
LEFT JOIN experiments child ON parent.id = child.parent_experiment_id
WHERE parent.is_multi_experiment = 1
ORDER BY parent.id, child.experiment_number;
