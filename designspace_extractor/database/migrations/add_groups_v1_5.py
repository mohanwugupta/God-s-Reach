"""
Migration Script: Add Groups Support (Schema v1.4 -> v1.5)

This migration adds:
1. Group table for experimental groups/conditions
2. extraction_level field to Experiment table
3. Default groups for existing experiments (backward compatibility)

Usage:
    python -m database.migrations.add_groups_v1_5 <database_path>
"""

import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.models import Base, Experiment, Group, DatabaseConnection


def migrate_to_v1_5(db_path: str, create_default_groups: bool = True):
    """
    Migrate database from schema v1.4 to v1.5.
    
    Args:
        db_path: Path to the SQLite database file
        create_default_groups: If True, create default groups for existing experiments
    """
    print(f"Starting migration to schema v1.5...")
    print(f"Database: {db_path}")
    
    # Connect to database
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Step 1: Create groups table
        print("\n[1/3] Creating groups table...")
        Base.metadata.create_all(bind=engine, tables=[Group.__table__])
        print("   ✓ Groups table created")
        
        # Step 2: Add extraction_level column to experiments table
        print("\n[2/3] Updating experiments table...")
        try:
            # Check if column already exists
            result = session.execute("PRAGMA table_info(experiments)").fetchall()
            columns = [row[1] for row in result]
            
            if 'extraction_level' not in columns:
                # SQLite doesn't support ALTER TABLE ADD COLUMN with DEFAULT properly
                # So we add it and then update
                session.execute("ALTER TABLE experiments ADD COLUMN extraction_level VARCHAR DEFAULT 'experiment'")
                session.execute("UPDATE experiments SET extraction_level = 'experiment' WHERE extraction_level IS NULL")
                session.commit()
                print("   ✓ Added extraction_level column")
            else:
                print("   ✓ extraction_level column already exists")
        except Exception as e:
            print(f"   ! Warning: Could not add extraction_level column: {e}")
            print("     (Column may already exist)")
        
        # Step 3: Create default groups for existing experiments
        if create_default_groups:
            print("\n[3/3] Creating default groups for existing experiments...")
            experiments = session.query(Experiment).all()
            print(f"   Found {len(experiments)} existing experiments")
            
            groups_created = 0
            for exp in experiments:
                # Check if experiment already has groups
                existing_groups = session.query(Group).filter(Group.experiment_id == exp.id).count()
                
                if existing_groups == 0:
                    # Create single "default" group inheriting experiment parameters
                    default_group = Group(
                        id=f"{exp.id}_DEFAULT",
                        experiment_id=exp.id,
                        group_number=1,
                        group_name="Default",
                        group_label="Experiment-level",
                        group_type="experiment_level",
                        
                        # Inherit demographics
                        sample_size_n=exp.sample_size_n,
                        age_mean=exp.age_mean,
                        age_sd=exp.age_sd,
                        
                        # Mark as experiment-level extraction
                        extraction_confidence="high",
                        extraction_method="migration",
                        needs_manual_review=False,
                        
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    session.add(default_group)
                    groups_created += 1
            
            session.commit()
            print(f"   ✓ Created {groups_created} default groups")
        else:
            print("\n[3/3] Skipping default group creation")
        
        # Update schema version
        print("\n[4/4] Updating schema version...")
        session.execute("UPDATE experiments SET schema_version = '1.5' WHERE schema_version = '1.4'")
        session.commit()
        print("   ✓ Schema version updated to 1.5")
        
        # Summary
        print("\n" + "="*60)
        print("MIGRATION COMPLETE")
        print("="*60)
        
        # Count groups
        total_groups = session.query(Group).count()
        total_experiments = session.query(Experiment).count()
        
        print(f"Total experiments: {total_experiments}")
        print(f"Total groups: {total_groups}")
        print(f"Average groups per experiment: {total_groups/total_experiments:.1f}")
        
        # Group types distribution
        group_types = session.execute(
            "SELECT group_type, COUNT(*) FROM groups GROUP BY group_type"
        ).fetchall()
        print("\nGroup types:")
        for gtype, count in group_types:
            print(f"  - {gtype}: {count}")
        
        print("\n✓ Database successfully migrated to schema v1.5")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        session.rollback()
        raise
    
    finally:
        session.close()


def rollback_migration(db_path: str):
    """
    Rollback migration from v1.5 to v1.4.
    WARNING: This will delete all group data!
    
    Args:
        db_path: Path to the SQLite database file
    """
    print(f"Rolling back migration from v1.5 to v1.4...")
    print(f"Database: {db_path}")
    print("\n⚠️  WARNING: This will delete all group data!")
    
    confirm = input("Are you sure you want to proceed? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Rollback cancelled.")
        return
    
    # Connect to database
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Count groups before deletion
        group_count = session.query(Group).count()
        print(f"\nDeleting {group_count} groups...")
        
        # Drop groups table
        session.execute("DROP TABLE IF EXISTS groups")
        session.commit()
        print("   ✓ Groups table dropped")
        
        # Remove extraction_level column (SQLite limitation: can't drop columns easily)
        print("\n   ! Note: extraction_level column cannot be easily removed in SQLite")
        print("     It will remain but will be ignored by v1.4 schema")
        
        # Update schema version
        print("\nUpdating schema version to 1.4...")
        session.execute("UPDATE experiments SET schema_version = '1.4'")
        session.commit()
        print("   ✓ Schema version reverted to 1.4")
        
        print("\n✓ Rollback complete")
        
    except Exception as e:
        print(f"\n✗ Rollback failed: {e}")
        session.rollback()
        raise
    
    finally:
        session.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Migrate database to schema v1.5 (add groups support)'
    )
    parser.add_argument(
        'db_path',
        type=str,
        help='Path to the SQLite database file'
    )
    parser.add_argument(
        '--skip-default-groups',
        action='store_true',
        help='Skip creating default groups for existing experiments'
    )
    parser.add_argument(
        '--rollback',
        action='store_true',
        help='Rollback migration from v1.5 to v1.4 (WARNING: deletes group data!)'
    )
    
    args = parser.parse_args()
    
    if args.rollback:
        rollback_migration(args.db_path)
    else:
        migrate_to_v1_5(args.db_path, create_default_groups=not args.skip_default_groups)
