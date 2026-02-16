# God's Reach: Automated Design-Space Extraction System

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production-brightgreen)](https://github.com/mohanwugupta/God-s-Reach)

## Abstract

**God's Reach** is an end-to-end research engineering system designed to automate the extraction of experimental design parameters from scientific literature and codebases. By synthesizing deterministic static analysis with Large Language Model (LLM) inference, the system transforms unstructured PDFs and heterogeneous code repositories into structured, queryable datasets. This project enables large-scale meta-analyses of motor adaptation studies by quantifying the "design space" of the field—revealing trends, gaps, and methodological inconsistencies across decades of research.

The pipeline features a modular extractor architecture, conflict resolution engines, automated validation against gold-standard datasets, and scalable deployment capabilities via Docker and SLURM workload managers.

---

## Key Highlights for Engineers

- **Scalable Architecture**: Designed for both local prototyping and high-performance cluster computing (HPC) using SLURM batch processing.
- **Hybrid AI/Deterministic Pipeline**: Combines precise AST parsing (for code) and layout-aware OCR (for PDFs) with semantic LLM inference (Claude, Qwen, GPT-4) to maximize F1 scores on extraction tasks.
- **Production Standards**: Includes comprehensive unit testing, type hints, structured logging, and containerization (Docker) for reproducibility.
- **Data Integrity**: Implements rigorous provenance tracking, confidence scoring for every extracted parameter, and automated validation against known "gold standard" truth sets.

## System Architecture

The system is organized into modular components to decouple ingestion, extraction, and storage logic:

```mermaid
graph TD
    A[Input Sources] --> B[Ingestion Layer]
    B --> C{Extraction Engine}
    C -->|PDFs| D[Layout-Aware OCR]
    C -->|Code| E[AST & Static Analysis]
    D --> F[LLM Inference Agent]
    E --> G[Deterministic Mapper]
    F --> H[Conflict Resolution & Validation]
    G --> H
    H --> I[Structured Database (SQLite)]
    I --> J[Downstream Analysis & Dashboards]
```

### Core Components

- **`designspace_extractor`**: The core Python package containing the business logic.
- **`extractors/`**: Specialized modules for handling different data modalities (PDF text, Python code, JSON configs).
- **`llm/`**: Abstraction layer for LLM providers, managing prompt context, token limits, and structured JSON output generation.
- **`database/`**: ORM-based persistence layer (SQLAlchemy) enabling complex queries on experiment metadata.

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (optional, for containerized execution)

### Local Setup

1. **Clone and Setup Environment**
   ```bash
   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate
   
   # Install dependencies
   pip install -r designspace_extractor/requirements.txt
   ```

2. **Configuration**
   ```bash
   # Configure environment variables (API keys, DB path)
   cp designspace_extractor/.env.example .env
   # Edit .env to add your LLM API keys (if using AI features)
   ```

3. **Run Extraction**
   
   Process a single paper or repository:
   ```bash
   # Run the CLI tool
   python -m designspace_extractor.cli extract ./papers/example_paper.pdf
   ```

   Run a batch job across the corpus:
   ```bash
   # Launch the batch processor
   python designspace_extractor/run_batch_extraction.py --input ./papers --output ./results
   ```

### HPC / Cluster Deployment

For processing large corpora, use the provided SLURM scripts:

```bash
cd slurm
sbatch run_batch_extraction.sh
```

## Evaluation & Metrics

The system's performance is continuously benchmarked against a manually curated "Gold Standard" dataset.

- **Precision**: >90% on structured parameter identification.
- **Recall**: >85% across varied PDF layouts.
- **Throughput**: ~15 seconds per paper (on GPU-accelerated nodes).

See [`docs/EXTRACTION_SUMMARY_REPORT.md`](docs/EXTRACTION_SUMMARY_REPORT.md) for detailed performance breakdowns.

## Documentation

Extensive documentation is available in the `docs/` directory:

- [**Implementation Summary**](docs/IMPLEMENTATION_SUMMARY.py): High-level code walkthrough.
- [**LLM Integration Guide**](docs/LLM_INTEGRATION_FIX_SUMMARY.md): details on the prompt engineering and context management strategies.
- [**Database Schema**](docs/DATABASE_INTEGRATION_GUIDE.md): Entity-relationship diagrams and schema explanations.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

