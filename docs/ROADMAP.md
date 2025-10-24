# Development Roadmap

## Current Status: Phase 1A MVP - Foundation Complete ✅

---

## Phase 0: Governance & Gold Standard (In Progress)
**Duration:** 2-4 weeks | **Your Active Work**

### Your Action Items
- [ ] Complete gold standard annotation (20 repos)
- [ ] Recruit 3 expert raters
- [ ] Calculate inter-rater reliability (κ>0.8)
- [ ] Document decision tree for implicit parameters
- [ ] Review and approve `GOVERNANCE.md`
- [ ] Review and approve `docs/llm_policy.md`

### Gate Criteria
- ✅ κ ≥ 0.75 inter-rater agreement
- ✅ Decision tree documented

---

## Phase 1A: MVP (Just Completed) ✅
**Duration:** 4 weeks | **Status:** COMPLETE

### Completed Components
- ✅ Project structure and configuration
- ✅ Database schema with full provenance
- ✅ CLI interface with all major commands
- ✅ Python/JSON extraction with AST parsing
- ✅ File discovery system
- ✅ Parameter mapping and normalization
- ✅ Conflict resolution engine
- ✅ Google Sheets integration
- ✅ LLM integration framework
- ✅ CSV/JSON/Psych-DS exporters
- ✅ Basic validation
- ✅ Complete documentation

### Testing Needed
- [ ] Test extraction on real repositories
- [ ] Verify database integrity
- [ ] Test Google Sheets sync (once credentials are set up)
- [ ] Validate parameter mappings with real data
- [ ] Test export formats

### Gate Criteria
- [ ] Overall F1 ≥ 0.70 (pending gold standard)
- [ ] Successfully extract from 5 diverse repos

---

## Phase 1B: Conflict Resolution & Temporal Schema
**Duration:** 4 weeks | **Status:** NEXT

### Planned Work
- [ ] **Enhanced Conflict Resolution**
  - [ ] Implement weighted average for numeric params
  - [ ] Add fuzzy matching for string values
  - [ ] Build conflict review UI in Google Sheets
  - [ ] Add conflict visualization

- [ ] **Temporal Schedule Structure**
  - [ ] Implement `schedule_structure` JSON builder
  - [ ] Extract epoch/block transitions from code
  - [ ] Parse timeline from logs
  - [ ] Validate temporal consistency

- [ ] **Context Transitions**
  - [ ] Extract instruction changes
  - [ ] Track feedback modifications
  - [ ] Capture contextual cues over time

- [ ] **Review Interface**
  - [ ] Enhanced Google Sheets UI with dropdowns
  - [ ] Conflict highlighting
  - [ ] Bulk approval workflows
  - [ ] Change tracking

### Deliverables
- Enhanced conflict resolution with visual review
- Complete temporal schedule extraction
- Production-ready Sheets interface

### Gate Criteria
- [ ] Conflict resolution reduces manual review by 50%
- [ ] Temporal extraction accuracy >85%

---

## Phase 2: Full Validation Suite
**Duration:** 6 weeks | **Status:** FUTURE

### Planned Work
- [ ] **MATLAB Bridge**
  - [ ] Implement MATLAB Engine API integration
  - [ ] Add Octave fallback parser
  - [ ] Parse MATLAB structs and cell arrays
  - [ ] Handle MATLAB-specific syntax

- [ ] **JavaScript Parser**
  - [ ] Integrate @babel/parser
  - [ ] Handle ES6+ syntax
  - [ ] Parse jsPsych experiments
  - [ ] Extract from React components

- [ ] **PDF Extraction**
  - [ ] Set up GROBID server
  - [ ] Implement PDF text extraction
  - [ ] Add VLM (GPT-4V) fallback for figures
  - [ ] Parse methods sections

- [ ] **Comprehensive Benchmarking**
  - [ ] Implement per-parameter metrics
  - [ ] Cross-lab validation tests
  - [ ] Adversarial test suite
  - [ ] Longitudinal consistency tests

- [ ] **CI/CD Pipeline**
  - [ ] GitHub Actions workflow
  - [ ] Automated testing
  - [ ] F1 non-regression gates
  - [ ] Docker build and push

### Deliverables
- Full extraction support for Python, MATLAB, JS, PDFs
- Comprehensive validation metrics
- Automated testing pipeline

### Gate Criteria
- [ ] Cross-lab F1 drop ≤ 0.15 vs. in-lab
- [ ] All target metrics from PRD Table 7 met
- [ ] CI gates passing

---

## Phase 3: Multi-Lab Beta & Exporters
**Duration:** 4+ weeks | **Status:** FUTURE

### Planned Work
- [ ] **Partner Lab Onboarding**
  - [ ] Onboard 3 partner labs
  - [ ] Train RAs on workflow
  - [ ] Collect feedback
  - [ ] Iterate on usability

- [ ] **Advanced Exporters**
  - [ ] MetaLab format exporter
  - [ ] PsychMADS format exporter
  - [ ] Cognitive Atlas task/contrast mapping
  - [ ] BIDS events.tsv generator

- [ ] **HED Integration**
  - [ ] Implement MotorAdaptation HED library
  - [ ] Generate HED tags from parameters
  - [ ] Validate HED compliance
  - [ ] Export HED-annotated events

- [ ] **Plugin System**
  - [ ] KinArm plugin (XML/HDF5)
  - [ ] Custom equipment plugins
  - [ ] Lab-specific extractors

- [ ] **Dashboard (Optional)**
  - [ ] Parameter explorer with Plotly/Streamlit
  - [ ] Co-occurrence networks
  - [ ] Timeline visualization
  - [ ] Coverage heatmaps

### Deliverables
- Multi-lab validated system
- Complete standards compliance
- HED tagging
- Optional visualization dashboard

### Gate Criteria
- [ ] ≥ 3 partner labs actively using
- [ ] Community governance operational
- [ ] 100% HED/BIDS/Psych-DS compliance

---

## Future Extensions (Phase 4+)

### Advanced Features
- [ ] **Preregistration Generator**
  - Auto-generate preregistration templates from schema

- [ ] **Methods Section Generator**
  - Reverse-map schema to prose methods sections

- [ ] **Teaching Module**
  - Educational materials for reproducible neuroscience

- [ ] **API Server**
  - REST API for programmatic access
  - Web interface for non-CLI users

- [ ] **Phase 2 Expansion: Motor Sequence Learning**
  - Extend schema for motor sequence tasks
  - New parameter categories
  - Additional validation metrics

### Research Integration
- [ ] Integration with neuroimaging repositories
- [ ] Link to neural data analysis pipelines
- [ ] Meta-analysis aggregation tools

---

## Immediate Next Steps (Your Tasks)

### This Week
1. **Test the MVP**
   ```powershell
   # Install and test
   pip install -r requirements.txt
   python -m designspace_extractor init
   python -m designspace_extractor extract .\validation\test_repo
   ```

2. **Verify Output**
   - Check database contents
   - Validate extracted parameters
   - Review provenance records

3. **Try Real Data**
   - Extract from one of your real repositories
   - Check what parameters are found
   - Note what's missing

### This Month
1. **Set up Google Sheets**
   - Get service account credentials
   - Share your spreadsheet
   - Test sync functionality

2. **Configure LLM (Optional)**
   - Get Claude API key
   - Test LLM-assisted extraction
   - Review budget and costs

3. **Provide Feedback**
   - What parameters are being missed?
   - Are there false positives?
   - What file types are most important?

---

## Questions to Consider

As you test the system, think about:

1. **Parameter Coverage**: Are we missing important parameters?
2. **File Type Priority**: Which file types (MATLAB, JS, PDF) are most urgent?
3. **Validation Needs**: What validation checks are most critical?
4. **Workflow**: How does this fit into your RA workflow?
5. **Partner Labs**: Who should we recruit for multi-lab testing?

---

## Success Metrics Dashboard

### Phase 1A (Current)
- [x] Project structure complete
- [x] Database operational
- [x] Basic extraction working
- [ ] Tested on real data
- [ ] F1 baseline established

### Overall Project Goals
- [ ] ≥ 80% parameters correctly extracted (200 repos)
- [ ] ≥ 0.85 overall F1 score
- [ ] ≥ 95% schema coverage for motor adaptation
- [ ] ≥ 3 partner labs actively using
- [ ] 100% HED/BIDS/Psych-DS compliance
- [ ] Full provenance and reproducibility

---

**Last Updated:** 2025-10-20  
**Current Phase:** 1A Complete, Testing Phase  
**Next Milestone:** Phase 1B Planning (after testing and feedback)
