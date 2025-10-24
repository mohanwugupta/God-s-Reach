# Automated Design-Space Parameter Extractor

**Version:** 1.3  
**Python:** 3.11+  
**Status:** Phase 1A - MVP Development

## Overview

Automated extraction, mapping, validation, and storage of experimental design parameters across motor adaptation studies. Transforms heterogeneous experimental scripts and papers into structured, standards-compliant metadata.

## Features

- 🔍 **Automated Extraction**: Python, MATLAB, JavaScript, JSON, and PDF parsing
- 🗄️ **Structured Storage**: SQLite database with full provenance tracking
- 🔄 **Conflict Resolution**: Intelligent parameter reconciliation with configurable policies
- 📊 **Standards Compliance**: HED, BIDS, Psych-DS, Cognitive Atlas integration
- 🤖 **LLM-Assisted** (Optional): Claude/Qwen for implicit parameter inference
- 📈 **Google Sheets Sync**: Collaborative review interface

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd designspace_extractor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Docker Installation

```bash
docker build -t designspace-extractor .
docker run -v $(pwd)/out:/app/out designspace-extractor --help
```

### Basic Usage

```bash
# Extract from a repository
python -m designspace_extractor extract /path/to/repo

# Extract with LLM assistance
python -m designspace_extractor extract /path/to/repo --use-llm

# Validate extraction results
python -m designspace_extractor validate --experiment-id EXP001

# Export to Psych-DS
python -m designspace_extractor export --format psychds --experiment-id EXP001

# Sync to Google Sheets
python -m designspace_extractor sync --sheet-id <your-sheet-id>
```

## Project Structure

```
designspace_extractor/
├── cli.py                      # Main CLI interface
├── __main__.py                 # Package entry point
├── extractors/                 # Code/data extraction modules
│   ├── code_data.py           # Python/JSON extractor
│   ├── pdfs.py                # PDF parser (GROBID + VLM)
│   ├── matlab_bridge.py       # MATLAB/Octave parser
│   ├── js_babel.py            # JavaScript parser
│   └── kinarm_plugin.py       # KinArm-specific extractor
├── utils/                      # Utility modules
│   ├── conflict_resolution.py # Conflict resolution engine
│   ├── sheets_api.py          # Google Sheets integration
│   └── io_helpers.py          # I/O utilities
├── mapping/                    # Schema mapping & normalization
│   ├── schema_map.yaml        # Parameter mapping definitions
│   ├── synonyms.yaml          # Alias mappings
│   ├── patterns.yaml          # Regex patterns for extraction
│   └── conflict_resolution.yaml # Conflict resolution policies
├── database/                   # Database layer
│   ├── models.py              # SQLAlchemy models
│   └── schema.sql             # Database schema
├── hed/                        # HED tagging & validation
├── standards/                  # Standards exporters
├── validation/                 # Validation & benchmarking
├── llm/                        # LLM integration
└── out/                        # Output directory
```

## Configuration

Key configuration options in `.env`:

- **Google Sheets**: Set `GOOGLE_SHEETS_SPREADSHEET_ID` and credentials
- **LLM**: Choose provider (`claude`, `openai`, `qwen`) and set API keys
- **MATLAB**: Set `MATLAB_AVAILABLE=true` if MATLAB Engine is installed
- **Performance**: Adjust `EXTRACTION_WORKERS` for parallelization

## Development

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=designspace_extractor

# Format code
black .

# Type checking
mypy .
```

## Documentation

- [PRD](../docs/automated_design_space_extractor_prd.md)
- [Governance](../docs/GOVERNANCE.md)
- [LLM Policy](../docs/llm_policy.md)
- [Gold Standard Protocol](validation/gold_standard_protocol.md)

## Roadmap

- ✅ **Phase 0**: Governance & Gold Standard (In Progress)
- 🔄 **Phase 1A**: MVP - Python/JSON extraction + SQLite (Current)
- ⏳ **Phase 1B**: Conflict resolution + temporal schema
- ⏳ **Phase 2**: Full validation suite + MATLAB bridge
- ⏳ **Phase 3**: Multi-lab beta + exporters

## License

[To be determined]

## Citation

[To be added]

## Contact

PI: Mohan Gupta / Princeton Lab  
For questions or contributions, please open an issue.
