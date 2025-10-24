# Installation and Setup Guide

## Prerequisites

- Python 3.11 or higher
- Git
- (Optional) MATLAB R2021a or higher for MATLAB file parsing
- (Optional) Node.js for JavaScript parsing

## Step 1: Clone or Navigate to the Project

```bash
cd "c:\Users\sheik\Box\ResearchProjects\God's-Reach\designspace_extractor"
```

## Step 2: Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you get an execution policy error, run:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Step 3: Install Dependencies

```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

## Step 4: Configure Environment

```powershell
# Copy example environment file
copy .env.example .env

# Edit .env with your settings
notepad .env
```

### Required Configuration

Update `.env` with your settings:

```ini
# Google Sheets (use the IDs from your URLs)
GOOGLE_SHEETS_SPREADSHEET_ID=1nc34GT31emdpVJw7Vq-1cRI7_TtJ8Tdj
GOOGLE_SHEETS_WORKSHEET_NAME=Sheet1

# LLM Configuration
ANTHROPIC_API_KEY=your_api_key_here
LLM_ENABLE=false  # Set to true when ready

# Database
DATABASE_PATH=./out/designspace.db
```

### Google Sheets Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Sheets API
4. Create Service Account credentials
5. Download credentials as `credentials.json`
6. Place in project root directory
7. Share your spreadsheet with the service account email

## Step 5: Initialize Database

```powershell
# Initialize the database and directories
python -m designspace_extractor init
```

This will:
- Create the SQLite database
- Create output directories
- Verify configuration

## Step 6: Test Installation

```powershell
# Check if CLI works
python -m designspace_extractor --help

# Check database status
python -m designspace_extractor status
```

## Step 7: (Optional) Set up Docker

If you prefer to use Docker:

```powershell
# Build Docker image
docker build -t designspace-extractor .

# Run with Docker
docker run -v ${PWD}/out:/app/out designspace-extractor --help
```

## Usage Examples

### Extract from a Repository

```powershell
# Basic extraction
python -m designspace_extractor extract C:\path\to\repo

# With specific experiment ID
python -m designspace_extractor extract C:\path\to\repo --exp-id EXP001

# With LLM assistance (after enabling)
python -m designspace_extractor extract C:\path\to\repo --use-llm
```

### View Database Status

```powershell
python -m designspace_extractor status
```

### Validate Extracted Data

```powershell
# Validate specific experiment
python -m designspace_extractor validate --exp-id EXP001

# Validate all
python -m designspace_extractor validate --all
```

### Export Data

```powershell
# Export to CSV
python -m designspace_extractor export --format csv -o results.csv

# Export to Psych-DS
python -m designspace_extractor export --format psychds --exp-id EXP001

# Export to JSON
python -m designspace_extractor export --format json -o experiments.json
```

### Sync to Google Sheets

```powershell
# Sync all experiments needing review
python -m designspace_extractor sync

# Sync specific experiment
python -m designspace_extractor sync --exp-id EXP001
```

## Troubleshooting

### Import Errors

If you see import errors, make sure:
1. Virtual environment is activated
2. All dependencies are installed: `pip install -r requirements.txt`
3. You're running from the project root directory

### Database Not Found

If you see "Database not found" error:
```powershell
python -m designspace_extractor init
```

### Google Sheets Authentication

If Google Sheets sync fails:
1. Verify `credentials.json` is in the project root
2. Check that the spreadsheet is shared with the service account email
3. Verify the spreadsheet ID in `.env` is correct

### LLM Issues

If LLM features fail:
1. Check API keys are set in `.env`
2. Verify `LLM_ENABLE=true` in `.env`
3. Check API quotas and budget limits

## Development

### Running Tests

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=designspace_extractor

# Run specific test file
pytest validation/tests/test_validator.py
```

### Code Formatting

```powershell
# Format code
black .

# Check linting
flake8

# Type checking
mypy .
```

## Next Steps

1. ✅ **Set up your environment** - Complete the steps above
2. 📝 **Configure Google Sheets** - Set up your review spreadsheet
3. 🧪 **Test with a sample repo** - Try extracting from a small test repository
4. 🔬 **Review extracted data** - Check the database and Google Sheets
5. 🚀 **Scale up** - Process your full collection of repositories

## Support

For issues or questions:
- Check the [PRD](../docs/automated_design_space_extractor_prd.md)
- Review [GOVERNANCE.md](../docs/GOVERNANCE.md)
- Open an issue in the project repository
