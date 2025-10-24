"""
SQLAlchemy models for the Design-Space Parameter Extractor database.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, 
    ForeignKey, create_engine, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import json

Base = declarative_base()


class Experiment(Base):
    """Experiment-level metadata."""
    __tablename__ = 'experiments'
    
    # Primary key
    id = Column(String, primary_key=True)  # e.g., EXP001
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Multi-experiment support
    parent_experiment_id = Column(String, ForeignKey('experiments.id'))
    experiment_number = Column(Integer)  # 1, 2, 3... within a paper
    paper_id = Column(String)  # Shared ID for experiments from same paper
    is_multi_experiment = Column(Boolean, default=False)
    
    # Study metadata
    study_type = Column(String)  # visuomotor_rotation, force_field, etc.
    publication_doi = Column(String)
    lab_name = Column(String)
    principal_investigator = Column(String)
    
    # Sample information
    sample_size_n = Column(Integer)
    age_mean = Column(Float)
    age_sd = Column(Float)
    handedness_criteria = Column(String)
    
    # Equipment specification
    equipment_manipulandum_type = Column(String)
    equipment_workspace_width_cm = Column(Float)
    equipment_workspace_height_cm = Column(Float)
    equipment_mass_inertia_compensation = Column(String)
    equipment_position_sensor_resolution_mm = Column(Float)
    equipment_sampling_rate_hz = Column(Float)
    
    # Experimental design
    counterbalancing_scheme = Column(String)
    trial_exclusion_criteria = Column(String)
    preprocessing_pipeline = Column(String)
    
    # Temporal schedule (stored as JSON)
    schedule_structure = Column(Text)  # JSON
    
    # Outcome measures (stored as JSON)
    outcome_measures = Column(Text)  # JSON
    
    # Raw extracted parameters (stored as JSON)
    extracted_params = Column(Text)  # JSON - raw extraction results from PDFs/code
    
    # Flags and status
    conflict_flag = Column(Boolean, default=False)
    entry_status = Column(String, default='needs_review')
    
    # Provenance
    provenance_sources = Column(Text)  # JSON
    extractor_version = Column(String)
    
    # Schema versioning
    schema_version = Column(String, default='1.4')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sessions = relationship("Session", back_populates="experiment", cascade="all, delete-orphan")
    provenance_records = relationship("Provenance", back_populates="experiment", cascade="all, delete-orphan")
    manual_overrides = relationship("ManualOverride", back_populates="experiment", cascade="all, delete-orphan")
    
    # Multi-experiment relationships
    parent = relationship("Experiment", remote_side=[id], backref="children")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, parsing JSON fields."""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'parent_experiment_id': self.parent_experiment_id,
            'experiment_number': self.experiment_number,
            'paper_id': self.paper_id,
            'is_multi_experiment': self.is_multi_experiment,
            'study_type': self.study_type,
            'publication_doi': self.publication_doi,
            'lab_name': self.lab_name,
            'principal_investigator': self.principal_investigator,
            'sample_size_n': self.sample_size_n,
            'age_mean': self.age_mean,
            'age_sd': self.age_sd,
            'handedness_criteria': self.handedness_criteria,
            'equipment': {
                'manipulandum_type': self.equipment_manipulandum_type,
                'workspace_width_cm': self.equipment_workspace_width_cm,
                'workspace_height_cm': self.equipment_workspace_height_cm,
                'mass_inertia_compensation': self.equipment_mass_inertia_compensation,
                'position_sensor_resolution_mm': self.equipment_position_sensor_resolution_mm,
                'sampling_rate_hz': self.equipment_sampling_rate_hz,
            },
            'counterbalancing_scheme': self.counterbalancing_scheme,
            'trial_exclusion_criteria': self.trial_exclusion_criteria,
            'preprocessing_pipeline': self.preprocessing_pipeline,
            'conflict_flag': self.conflict_flag,
            'entry_status': self.entry_status,
            'extractor_version': self.extractor_version,
            'schema_version': self.schema_version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        # Parse JSON fields
        if self.schedule_structure:
            try:
                data['schedule_structure'] = json.loads(self.schedule_structure)
            except json.JSONDecodeError:
                data['schedule_structure'] = self.schedule_structure
                
        if self.outcome_measures:
            try:
                data['outcome_measures'] = json.loads(self.outcome_measures)
            except json.JSONDecodeError:
                data['outcome_measures'] = self.outcome_measures
                
        if self.provenance_sources:
            try:
                data['provenance_sources'] = json.loads(self.provenance_sources)
            except json.JSONDecodeError:
                data['provenance_sources'] = self.provenance_sources
        
        if self.extracted_params:
            try:
                data['extracted_params'] = json.loads(self.extracted_params)
            except json.JSONDecodeError:
                data['extracted_params'] = self.extracted_params
        
        return data


class Session(Base):
    """Session-level metadata."""
    __tablename__ = 'sessions'
    
    id = Column(String, primary_key=True)  # e.g., EXP001_S01
    experiment_id = Column(String, ForeignKey('experiments.id'), nullable=False)
    session_number = Column(Integer, nullable=False)
    
    # Session details
    session_type = Column(String)  # baseline, adaptation, retention
    session_date = Column(DateTime)
    duration_minutes = Column(Float)
    
    # Context information
    instruction_text = Column(Text)
    instruction_awareness = Column(String)  # explicit, implicit, unknown
    context_cues = Column(Text)  # JSON
    
    # Familiarization and breaks
    familiarization_trials = Column(Integer)
    block_breaks = Column(Text)  # JSON
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    experiment = relationship("Experiment", back_populates="sessions")
    blocks = relationship("Block", back_populates="session", cascade="all, delete-orphan")


class Block(Base):
    """Block-level metadata."""
    __tablename__ = 'blocks'
    
    id = Column(String, primary_key=True)  # e.g., EXP001_S01_B01
    session_id = Column(String, ForeignKey('sessions.id'), nullable=False)
    block_number = Column(Integer, nullable=False)
    
    # Block characteristics
    block_type = Column(String)  # baseline, adaptation, washout
    num_trials = Column(Integer)
    
    # Perturbation parameters
    rotation_magnitude_deg = Column(Float)
    rotation_direction = Column(String)  # CW, CCW
    force_field_strength = Column(Float)
    force_field_type = Column(String)
    
    # Feedback parameters
    feedback_type = Column(String)  # visual, haptic, auditory, none
    feedback_delay_ms = Column(Float)
    cursor_visible = Column(Boolean)
    cursor_noise_sd_mm = Column(Float)
    
    # Timing
    trial_duration_ms = Column(Float)
    inter_trial_interval_ms = Column(Float)
    
    # Reward structure
    reward_type = Column(String)  # points, money, none
    reward_schedule = Column(String)
    
    # Motor noise model (optional)
    motor_noise_model = Column(Text)  # JSON
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="blocks")
    trials = relationship("Trial", back_populates="block", cascade="all, delete-orphan")


class Trial(Base):
    """Trial-level metadata."""
    __tablename__ = 'trials'
    
    id = Column(String, primary_key=True)  # e.g., EXP001_S01_B01_T001
    block_id = Column(String, ForeignKey('blocks.id'), nullable=False)
    trial_number = Column(Integer, nullable=False)
    
    # Trial-level parameters (override block defaults if needed)
    rotation_magnitude_deg = Column(Float)
    feedback_delay_ms = Column(Float)
    cursor_visible = Column(Boolean)
    reward_given = Column(Boolean)
    
    # Trial timing
    trial_onset_time_ms = Column(Float)
    trial_duration_ms = Column(Float)
    
    # Trial outcome (if available from logs)
    endpoint_error_mm = Column(Float)
    movement_time_ms = Column(Float)
    peak_velocity_mm_s = Column(Float)
    reaction_time_ms = Column(Float)
    trial_excluded = Column(Boolean, default=False)
    exclusion_reason = Column(String)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    block = relationship("Block", back_populates="trials")


class Provenance(Base):
    """Provenance tracking for extracted parameters."""
    __tablename__ = 'provenance'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(String, ForeignKey('experiments.id'), nullable=False)
    
    # Source information
    repo_url = Column(String)
    repo_commit_hash = Column(String)
    file_path = Column(String)
    file_content_hash = Column(String)
    source_type = Column(String)  # code, config, log, pdf, manual
    
    # Extraction metadata
    extractor_version = Column(String)
    extraction_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # LLM usage (if applicable)
    llm_provider = Column(String)  # claude, openai, qwen, none
    llm_model = Column(String)
    llm_temperature = Column(Float)
    llm_prompt = Column(Text)
    llm_response = Column(Text)
    llm_cost_usd = Column(Float)
    
    # Conflict information
    conflict_detected = Column(Boolean, default=False)
    conflict_resolution_policy = Column(String)
    alternative_values = Column(Text)  # JSON
    
    # Relationships
    experiment = relationship("Experiment", back_populates="provenance_records")


class ManualOverride(Base):
    """Manual overrides of extracted parameters."""
    __tablename__ = 'manual_overrides'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(String, ForeignKey('experiments.id'), nullable=False)
    parameter_name = Column(String, nullable=False)
    
    # Override details
    original_value = Column(String)
    override_value = Column(String)
    override_reason = Column(Text)
    override_by = Column(String)  # username or RA identifier
    override_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Approval tracking
    approved_by = Column(String)
    approval_timestamp = Column(DateTime)
    
    # Relationships
    experiment = relationship("Experiment", back_populates="manual_overrides")


# Database initialization and connection utilities
class Database:
    """Database connection and session management."""
    
    def __init__(self, db_path: str = "./out/designspace.db"):
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Create all tables in the database."""
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self):
        """Get a new database session."""
        return self.SessionLocal()
    
    def execute_sql_file(self, sql_file_path: str):
        """Execute SQL from a file (for schema.sql)."""
        with open(sql_file_path, 'r') as f:
            sql = f.read()
        
        with self.engine.connect() as conn:
            # Split by semicolon and execute each statement
            for statement in sql.split(';'):
                statement = statement.strip()
                if statement:
                    conn.execute(statement)
            conn.commit()
