# Example Test Repository for Design-Space Extractor

This directory contains example files that can be used to test the extractor.

## Files

- `experiment_config.json` - JSON configuration file with experiment parameters
- `run_experiment.py` - Python script with parameter definitions
- `README.md` - This file

## Expected Extraction

The extractor should identify:
- rotation_magnitude_deg: 30
- sample_size_n: 20
- feedback_delay_ms: 100
- num_trials: 80
- equipment_manipulandum_type: vbot_planar

## Usage

```bash
python -m designspace_extractor extract ./validation/test_repo --exp-id TEST001
```
