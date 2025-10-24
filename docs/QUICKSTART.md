# Quick Start Guide

Get up and running with the Design-Space Parameter Extractor in 5 minutes!

## 1. Set Up (2 minutes)

```powershell
# Navigate to project
cd "c:\Users\sheik\Box\ResearchProjects\God's-Reach\designspace_extractor"

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -m designspace_extractor init
```

## 2. Configure (1 minute)

```powershell
# Create environment file
copy .env.example .env

# Edit with your Google Sheets ID (optional for now)
notepad .env
```

Minimum configuration for testing (without Google Sheets):
```ini
DATABASE_PATH=./out/designspace.db
LLM_ENABLE=false
```

## 3. Test with Example Data (1 minute)

```powershell
# Extract from test repository
python -m designspace_extractor extract .\validation\test_repo --exp-id TEST001
```

Expected output:
```
📂 Scanning repository: .\validation\test_repo
✓ Found 3 relevant files
🔍 Extracting parameters...
✓ Extraction complete! Experiment ID: TEST001
  - Status: needs_review

View results: sqlite3 ./out/designspace.db
```

## 4. View Results (1 minute)

```powershell
# Check database status
python -m designspace_extractor status

# Validate extraction
python -m designspace_extractor validate --exp-id TEST001

# Export to CSV
python -m designspace_extractor export --format csv -o test_results.csv

# Export to JSON
python -m designspace_extractor export --format json -o test_results.json
```

## 5. Inspect the Database

### Option A: Using SQLite Command Line
```powershell
# Install sqlite3 if needed
# Download from: https://www.sqlite.org/download.html

sqlite3 ./out/designspace.db

# Run queries:
# SELECT * FROM experiments;
# SELECT * FROM provenance;
# .quit
```

### Option B: Using Python
```powershell
python
```

```python
from database.models import Database, Experiment

db = Database('./out/designspace.db')
session = db.get_session()

# Get all experiments
experiments = session.query(Experiment).all()
for exp in experiments:
    print(f"{exp.id}: {exp.name}")
    print(f"  Rotation: {exp.rotation_magnitude_deg}")
    print(f"  Sample size: {exp.sample_size_n}")
    print(f"  Status: {exp.entry_status}")
    print()

session.close()
```

## What Just Happened?

The extractor:
1. ✅ Scanned the test repository
2. ✅ Found Python and JSON files
3. ✅ Extracted parameters using AST parsing (Python) and JSON parsing
4. ✅ Normalized parameter names and values
5. ✅ Stored results in SQLite database with full provenance
6. ✅ Flagged for review (no conflicts in test data)

## Next Steps

### Process Your Own Data

```powershell
# Extract from your repository
python -m designspace_extractor extract "C:\path\to\your\repo" --exp-id YOUR001
```

### Set Up Google Sheets Integration

1. Get Google Sheets credentials (see INSTALL.md)
2. Update `.env` with your spreadsheet ID
3. Sync data:
   ```powershell
   python -m designspace_extractor sync
   ```

### Enable LLM Assistance

1. Get Claude API key from Anthropic
2. Update `.env`:
   ```ini
   ANTHROPIC_API_KEY=your_key_here
   LLM_ENABLE=true
   ```
3. Extract with LLM:
   ```powershell
   python -m designspace_extractor extract path\to\repo --use-llm
   ```

## Troubleshooting

### "Module not found" errors
Make sure virtual environment is activated:
```powershell
.\venv\Scripts\Activate.ps1
```

### "Database not found"
Run initialization:
```powershell
python -m designspace_extractor init
```

### Permission errors on PowerShell
Allow script execution:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Common Commands Reference

```powershell
# Help
python -m designspace_extractor --help
python -m designspace_extractor extract --help

# Extract
python -m designspace_extractor extract <path> [--exp-id ID] [--use-llm]

# Validate
python -m designspace_extractor validate --exp-id <ID>
python -m designspace_extractor validate --all

# Export
python -m designspace_extractor export --format <csv|json|psychds>

# Status
python -m designspace_extractor status

# Sync
python -m designspace_extractor sync [--sheet-id ID]
```

## Success! 🎉

You're now ready to extract design parameters from motor adaptation studies!

For detailed documentation, see:
- [INSTALL.md](INSTALL.md) - Full installation guide
- [README.md](README.md) - Project overview
- [PRD](../docs/automated_design_space_extractor_prd.md) - Full specification
