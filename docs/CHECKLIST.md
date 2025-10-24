# 📋 Getting Started Checklist

Use this checklist to get the Design-Space Parameter Extractor up and running.

## ☐ Installation & Setup

### Prerequisites
- [ ] Python 3.11 installed and in PATH
- [ ] Git installed (if cloning from repository)
- [ ] Terminal/PowerShell access
- [ ] Text editor (VS Code, Notepad++, etc.)

### Basic Setup (Required)
- [ ] Navigate to project directory
- [ ] Create virtual environment: `python -m venv venv`
- [ ] Activate virtual environment: `.\venv\Scripts\Activate.ps1`
  - If blocked, run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- [ ] Upgrade pip: `python -m pip install --upgrade pip`
- [ ] Install requirements: `pip install -r requirements.txt`
- [ ] Copy .env file: `copy .env.example .env`
- [ ] Edit .env with basic settings
- [ ] Initialize database: `python -m designspace_extractor init`
- [ ] Test CLI: `python -m designspace_extractor --help`

### Verify Installation
- [ ] Run test extraction: `python -m designspace_extractor extract .\validation\test_repo --exp-id TEST001`
- [ ] Check database: `python -m designspace_extractor status`
- [ ] Validate results: `python -m designspace_extractor validate --exp-id TEST001`
- [ ] Export test data: `python -m designspace_extractor export --format csv -o test.csv`

---

## ☐ Google Sheets Integration (Optional)

### Setup Google Cloud Project
- [ ] Go to [Google Cloud Console](https://console.cloud.google.com/)
- [ ] Create new project or select existing
- [ ] Enable Google Sheets API
- [ ] Create Service Account
- [ ] Download credentials as `credentials.json`
- [ ] Place credentials.json in project root

### Configure Spreadsheet
- [ ] Open your Google Sheets spreadsheet
- [ ] Copy Spreadsheet ID from URL: `1nc34GT31emdpVJw7Vq-1cRI7_TtJ8Tdj`
- [ ] Share spreadsheet with service account email (from credentials.json)
- [ ] Give Editor permissions
- [ ] Update .env with Spreadsheet ID

### Test Sync
- [ ] Run sync: `python -m designspace_extractor sync`
- [ ] Check spreadsheet for data
- [ ] Verify row count matches database

---

## ☐ LLM Integration (Optional)

### Claude (Anthropic) Setup
- [ ] Sign up at [Anthropic](https://console.anthropic.com/)
- [ ] Create API key
- [ ] Add to .env: `ANTHROPIC_API_KEY=sk-ant-...`
- [ ] Set `LLM_ENABLE=true` in .env
- [ ] Set `LLM_PROVIDER=claude` in .env
- [ ] Test: `python -m designspace_extractor extract path\to\repo --use-llm`

### Monitor Usage
- [ ] Check LLM usage log: `.\out\logs\llm_usage.log`
- [ ] Monitor budget: Check cumulative_spend in log
- [ ] Adjust budget cap in .env if needed

---

## ☐ Test with Your Data

### First Real Repository
- [ ] Choose a small repository to start
- [ ] Run extraction: `python -m designspace_extractor extract "C:\path\to\repo" --exp-id YOUR001`
- [ ] Check what was extracted: `python -m designspace_extractor status`
- [ ] Validate: `python -m designspace_extractor validate --exp-id YOUR001`
- [ ] Export results: `python -m designspace_extractor export --format json -o results.json`
- [ ] Review `results.json` for accuracy

### Check Extraction Quality
- [ ] How many files were discovered?
- [ ] How many parameters were extracted?
- [ ] Are the values correct?
- [ ] Were there conflicts flagged?
- [ ] What parameters were missed?

### Note Issues
- [ ] Document missed parameters
- [ ] Note false positives
- [ ] Identify file types not yet supported
- [ ] List improvements needed

---

## ☐ Process Multiple Repositories

### Batch Processing
- [ ] Create a list of repository paths
- [ ] Write a script to process each:
  ```powershell
  $repos = @(
      "C:\repos\repo1",
      "C:\repos\repo2",
      "C:\repos\repo3"
  )
  
  foreach ($repo in $repos) {
      python -m designspace_extractor extract $repo
  }
  ```
- [ ] Review all results in database
- [ ] Check for common issues

---

## ☐ Review and Validation

### Manual Review in Google Sheets
- [ ] Sync all experiments: `python -m designspace_extractor sync`
- [ ] Open Google Sheet
- [ ] Review flagged conflicts
- [ ] Update entry_status column
- [ ] Add manual corrections if needed

### Data Quality Checks
- [ ] Check distribution of parameter values
- [ ] Identify outliers
- [ ] Look for patterns in missing data
- [ ] Verify equipment types make sense
- [ ] Check sample sizes are realistic

---

## ☐ Advanced Configuration

### Customize Parameter Mappings
- [ ] Review `mapping/schema_map.yaml`
- [ ] Add lab-specific parameter names to `mapping/synonyms.yaml`
- [ ] Add custom regex patterns to `mapping/patterns.yaml`
- [ ] Test with: `python -m designspace_extractor extract path\to\repo`

### Adjust Conflict Resolution
- [ ] Review `mapping/conflict_resolution.yaml`
- [ ] Adjust source precedence if needed
- [ ] Add parameter-specific rules
- [ ] Set tolerance levels

---

## ☐ Documentation & Sharing

### Document Your Workflow
- [ ] Note which repositories were processed
- [ ] Document any manual corrections
- [ ] Track validation results
- [ ] Note common issues and solutions

### Share with Team
- [ ] Share Google Sheet with collaborators
- [ ] Train RAs on validation workflow
- [ ] Document lab-specific procedures
- [ ] Create troubleshooting guide

---

## ☐ Future Development (Later)

### When Gold Standard is Ready
- [ ] Run validation against gold standard
- [ ] Calculate F1 scores per parameter
- [ ] Identify weak spots
- [ ] Iterate on extraction rules

### MATLAB Support (If Needed)
- [ ] Install MATLAB or Octave
- [ ] Configure MATLAB Engine API
- [ ] Test MATLAB extraction
- [ ] Implement `extractors/matlab_bridge.py`

### JavaScript Support (If Needed)
- [ ] Install Node.js
- [ ] Install Babel: `npm install -g @babel/parser`
- [ ] Implement `extractors/js_babel.py`
- [ ] Test on jsPsych experiments

### PDF Support (If Needed)
- [ ] Set up GROBID server
- [ ] Implement `extractors/pdfs.py`
- [ ] Test on paper PDFs
- [ ] Configure VLM for figures

---

## 🎯 Success Criteria

You'll know the system is working when:
- ✅ Extraction runs without errors
- ✅ Database contains expected experiments
- ✅ Parameters have reasonable values
- ✅ Confidence scores make sense
- ✅ Conflicts are properly flagged
- ✅ Google Sheets syncs successfully
- ✅ Exports generate valid files

---

## 🆘 Getting Help

If you run into issues:
1. Check `.\out\logs\extractor.log` for errors
2. Review relevant documentation:
   - [QUICKSTART.md](QUICKSTART.md) - Quick guide
   - [INSTALL.md](INSTALL.md) - Detailed installation
   - [README.md](README.md) - Project overview
   - [ROADMAP.md](ROADMAP.md) - Development plan
3. Check the PRD for specifications
4. Review code comments in relevant modules

---

## 📊 Progress Tracking

Current Status:
- [ ] Basic setup complete
- [ ] Test extraction successful
- [ ] Real data extraction tested
- [ ] Google Sheets configured
- [ ] LLM features tested
- [ ] Multiple repos processed
- [ ] Validation workflow established
- [ ] Ready for production use

---

**Last Updated:** 2025-10-20  
**Your Next Step:** Complete "Installation & Setup" section above! 🚀
