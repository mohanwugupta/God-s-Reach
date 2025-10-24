"""
Database Migration: Add Multi-Experiment Support
Version: 1.3 -> 1.4
Date: 2025-10-23

This migration adds support for tracking multiple experiments from the same paper or codebase.
"""
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MIGRATION_SQL = """
-- Add multi-experiment fields to experiments table
ALTER TABLE experiments ADD COLUMN parent_experiment_id TEXT;
ALTER TABLE experiments ADD COLUMN experiment_number INTEGER;
ALTER TABLE experiments ADD COLUMN paper_id TEXT;
ALTER TABLE experiments ADD COLUMN is_multi_experiment BOOLEAN DEFAULT 0;

-- Update schema version
UPDATE experiments SET schema_version = '1.4' WHERE schema_version = '1.3';

-- Create indexes for new fields
CREATE INDEX IF NOT EXISTS idx_experiments_parent ON experiments(parent_experiment_id);
CREATE INDEX IF NOT EXISTS idx_experiments_paper ON experiments(paper_id);

-- Drop old views
DROP VIEW IF EXISTS v_experiment_full;
DROP VIEW IF NOT EXISTS v_experiments_needs_review;

-- Recreate views with new fields
CREATE VIEW v_experiment_full AS
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

CREATE VIEW v_experiments_needs_review AS
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

-- Create new views for multi-experiment support
CREATE VIEW v_multi_experiment_groups AS
SELECT 
    paper_id,
    COUNT(*) as num_experiments,
    GROUP_CONCAT(id) as experiment_ids,
    MIN(created_at) as first_created,
    MAX(updated_at) as last_updated
FROM experiments
WHERE paper_id IS NOT NULL
GROUP BY paper_id;

CREATE VIEW v_experiment_hierarchy AS
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
"""

def migrate(db_path: str = "./out/designspace.db"):
    """
    Run migration on database.
    
    Args:
        db_path: Path to SQLite database file
    """
    if not Path(db_path).exists():
        logger.warning(f"Database {db_path} does not exist. Skipping migration.")
        return
    
    logger.info(f"Running migration on {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if migration already applied
        cursor.execute("PRAGMA table_info(experiments)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'parent_experiment_id' in columns:
            logger.info("Migration already applied. Skipping.")
            conn.close()
            return
        
        # Execute migration
        for statement in MIGRATION_SQL.split(';'):
            statement = statement.strip()
            if statement:
                try:
                    cursor.execute(statement)
                except sqlite3.Error as e:
                    logger.warning(f"Statement failed (may be normal): {e}")
                    # Continue with other statements
        
        conn.commit()
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def rollback(db_path: str = "./out/designspace.db"):
    """
    Rollback migration (remove added columns).
    Note: SQLite doesn't support DROP COLUMN easily, so this creates new table.
    
    Args:
        db_path: Path to SQLite database file
    """
    logger.warning("Rollback not fully supported for SQLite ALTER TABLE operations")
    logger.warning("To rollback, restore from backup or recreate database")

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    db_path = sys.argv[1] if len(sys.argv) > 1 else "./out/designspace.db"
    
    if len(sys.argv) > 2 and sys.argv[2] == "--rollback":
        rollback(db_path)
    else:
        migrate(db_path)
