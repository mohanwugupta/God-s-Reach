"""
Google Sheets integration for collaborative review.
Syncs extracted parameters to Google Sheets for human validation.
"""
import os
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class SheetsSync:
    """Sync database records to Google Sheets for review."""
    
    def __init__(self, db, spreadsheet_id: str):
        """
        Initialize Sheets sync.
        
        Args:
            db: Database instance
            spreadsheet_id: Google Sheets spreadsheet ID
        """
        self.db = db
        self.spreadsheet_id = spreadsheet_id
        self.service = None
        
        # Lazy import to avoid requiring credentials if not using Sheets
        try:
            from google.oauth2.credentials import Credentials
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            # Try to load credentials
            creds_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE', 'credentials.json')
            if os.path.exists(creds_file):
                credentials = service_account.Credentials.from_service_account_file(
                    creds_file,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                self.service = build('sheets', 'v4', credentials=credentials)
                logger.info("Google Sheets API initialized")
            else:
                logger.warning(f"Credentials file not found: {creds_file}")
                
        except ImportError:
            logger.warning("Google API libraries not installed. Install with: pip install google-api-python-client google-auth")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets API: {e}")
    
    def sync_to_sheet(self, exp_id: Optional[str] = None, worksheet_name: str = None) -> Dict[str, Any]:
        """
        Sync experiments to Google Sheets.
        
        Args:
            exp_id: Optional experiment ID to sync (default: all with needs_review status)
            worksheet_name: Name of worksheet to sync to
            
        Returns:
            Dictionary with sync results
        """
        if not self.service:
            raise RuntimeError("Google Sheets API not initialized. Check credentials.")
        
        worksheet_name = worksheet_name or os.getenv('GOOGLE_SHEETS_WORKSHEET_NAME', 'Experiments')
        
        # Get experiments to sync
        session = self.db.get_session()
        try:
            from database.models import Experiment
            
            if exp_id:
                experiments = session.query(Experiment).filter_by(id=exp_id).all()
            else:
                # Sync all experiments that need review
                experiments = session.query(Experiment).filter_by(entry_status='needs_review').all()
            
            if not experiments:
                logger.info("No experiments to sync")
                return {'synced': 0, 'status': 'success'}
            
            # Convert to rows
            header = [
                'Experiment ID', 'Name', 'Study Type', 'Lab', 'Sample Size',
                'Rotation (deg)', 'Feedback Delay (ms)', 'Equipment',
                'Conflict Flag', 'Status', 'Created', 'Updated'
            ]
            
            rows = [header]
            for exp in experiments:
                row = [
                    exp.id,
                    exp.name,
                    exp.study_type or '',
                    exp.lab_name or '',
                    str(exp.sample_size_n) if exp.sample_size_n else '',
                    str(exp.rotation_magnitude_deg) if hasattr(exp, 'rotation_magnitude_deg') else '',
                    '',  # feedback_delay_ms (would need to get from blocks)
                    exp.equipment_manipulandum_type or '',
                    'Yes' if exp.conflict_flag else 'No',
                    exp.entry_status,
                    exp.created_at.isoformat() if exp.created_at else '',
                    exp.updated_at.isoformat() if exp.updated_at else ''
                ]
                rows.append(row)
            
            # Write to sheet
            body = {
                'values': rows
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f'{worksheet_name}!A1',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logger.info(f"Synced {len(experiments)} experiments to Google Sheets")
            
            return {
                'synced': len(experiments),
                'status': 'success',
                'updated_range': result.get('updatedRange')
            }
            
        except Exception as e:
            logger.error(f"Failed to sync to Google Sheets: {e}")
            raise
        finally:
            session.close()
    
    def pull_from_sheet(self, worksheet_name: str = None) -> List[Dict[str, Any]]:
        """
        Pull updated data from Google Sheets.
        
        Args:
            worksheet_name: Name of worksheet to pull from
            
        Returns:
            List of updated experiment records
        """
        if not self.service:
            raise RuntimeError("Google Sheets API not initialized")
        
        worksheet_name = worksheet_name or os.getenv('GOOGLE_SHEETS_WORKSHEET_NAME', 'Experiments')
        
        # Read from sheet
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f'{worksheet_name}!A1:Z1000'
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            logger.info("No data in sheet")
            return []
        
        # Parse rows
        header = values[0]
        records = []
        
        for row in values[1:]:
            # Pad row to match header length
            row = row + [''] * (len(header) - len(row))
            record = dict(zip(header, row))
            records.append(record)
        
        logger.info(f"Pulled {len(records)} records from Google Sheets")
        return records
    
    def update_experiment_status(self, exp_id: str, new_status: str):
        """
        Update experiment status in database from Sheet review.
        
        Args:
            exp_id: Experiment ID
            new_status: New status value
        """
        session = self.db.get_session()
        try:
            from database.models import Experiment
            
            exp = session.query(Experiment).filter_by(id=exp_id).first()
            if exp:
                exp.entry_status = new_status
                session.commit()
                logger.info(f"Updated {exp_id} status to {new_status}")
            else:
                logger.warning(f"Experiment not found: {exp_id}")
                
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update experiment status: {e}")
            raise
        finally:
            session.close()
