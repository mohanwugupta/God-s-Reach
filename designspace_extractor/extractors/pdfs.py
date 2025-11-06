"""
PDF extraction module for papers and documentation.
Implements multi-stage extraction: pypdf → pattern matching → optional LLM assistance.

Follows the PRD v1.3 extraction hierarchy:
1. Direct text extraction (pypdf)
2. Pattern-based parameter extraction
3. Optional LLM inference for implicit parameters (with policy controls)

Future enhancement: GROBID for structured parsing, VLM for figures/tables
"""
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

try:
    from pypdf import PdfReader
except ImportError:
    try:
        # Fallback to PyPDF2 if pypdf not available
        from PyPDF2 import PdfReader
    except ImportError:
        PdfReader = None

from utils.io_helpers import compute_file_hash
from database.models import Database, Experiment, Provenance

logger = logging.getLogger(__name__)

__version__ = "1.0.0"


class PDFExtractor:
    """
    Extract experimental parameters from PDF papers and documentation.
    
    Extraction Strategy:
    1. Text Extraction: Use pypdf to extract all text
    2. Section Detection: Identify Methods, Participants, Procedure sections
    3. Pattern Matching: Apply regex patterns for common parameters
    4. Confidence Scoring: Based on extraction method and context
    5. LLM Fallback (Optional): For implicit parameters with confidence < 0.3
    """
    
    # Common section headers in motor adaptation papers
    METHODS_HEADERS = [
        r'^materials?\s+and\s+methods?$',
        r'^methods?$',
        r'^procedures?$',
        r'^experimental\s+(?:design|setup|procedure)$',
        r'^apparatus$',
        r'^participants?\s+and\s+(?:experimental\s+)?apparatus$',
    ]
    
    PARTICIPANTS_HEADERS = [
        r'^participants?$',
        r'^subjects?$',
        r'^sample$',
        r'^demographics?$',
    ]
    
    RESULTS_HEADERS = [
        r'^results?$',
        r'^findings?$',
        r'^data\s+analysis$',
    ]
    
    INTRO_HEADERS = [
        r'^introduction$',
        r'^background$',
    ]
    
    def __init__(self, 
                 schema_map_path: str = None,
                 patterns_path: str = None,
                 synonyms_path: str = None,
                 use_llm: bool = False,
                 llm_provider: str = 'claude',
                 llm_mode: str = 'verify'):
        """
        Initialize PDF extractor.
        
        Args:
            schema_map_path: Path to schema_map.yaml
            patterns_path: Path to patterns.yaml for regex patterns
            synonyms_path: Path to synonyms.yaml
            use_llm: Enable LLM assistance for implicit parameters
            llm_provider: LLM provider (claude, openai, qwen)
            llm_mode: 'fallback' (only low-confidence) or 'verify' (check all parameters)
        """
        if PdfReader is None:
            raise ImportError(
                "pypdf or PyPDF2 required for PDF extraction. "
                "Install with: pip install pypdf"
            )
        
        # Load configurations
        from utils.io_helpers import load_yaml
        self.schema_map = load_yaml(schema_map_path or './mapping/schema_map.yaml')
        self.patterns = load_yaml(patterns_path or './mapping/patterns.yaml')
        self.synonyms = load_yaml(synonyms_path or './mapping/synonyms.yaml')
        
        # Build flattened schema map for quick lookup
        self.flat_schema = {}
        for section_name, section_params in self.schema_map.items():
            for param_name, param_config in section_params.items():
                canonical = param_config.get('canonical', param_name)
                self.flat_schema[param_name] = canonical
                self.flat_schema[canonical] = param_config
                
                # Add aliases from schema
                if 'aliases' in param_config:
                    for alias in param_config['aliases']:
                        self.flat_schema[alias] = canonical
        
        # Build synonym lookup (this adds to the flat schema)
        self.alias_to_canonical = {}
        for canonical, aliases in self.synonyms.items():
            self.alias_to_canonical[canonical] = canonical
            for alias in aliases:
                self.alias_to_canonical[alias] = canonical
        
        # LLM setup
        self.use_llm = use_llm
        self.llm_mode = llm_mode  # 'fallback' or 'verify'
        self.llm_assistant = None
        if use_llm:
            try:
                from llm.llm_assist import LLMAssistant
                logger.info(f"Initializing LLM assistant (provider: {llm_provider}, mode: {llm_mode})")
                self.llm_assistant = LLMAssistant(provider=llm_provider)
                logger.info(f"LLM assistance enabled for PDF extraction (mode: {llm_mode})")
            except Exception as e:
                logger.error(f"Failed to initialize LLM assistant: {e}")
                import traceback
                logger.error(traceback.format_exc())
                self.use_llm = False
    
    def clean_pdf_text(self, text: str) -> str:
        """
        Clean PDF text to handle common extraction issues.
        
        Args:
            text: Raw PDF text
            
        Returns:
            Cleaned text
        """
        # Common PDF encoding issues in scientific papers
        replacements = {
            '/H11011': '~',  # Tilde symbol encoding
            '/H11002': '-',  # Minus/hyphen encoding
            'fe- males': 'females',  # Broken hyphenation
            'fe-males': 'females',
            'partici- pants': 'participants',
            'partici-pants': 'participants',
        }
        
        cleaned = text
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        
        # Fix common broken words at line breaks
        cleaned = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', cleaned)
        
        return cleaned
    
    def extract_text(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract all text from PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with full_text and metadata
        """
        logger.info(f"Extracting text from PDF: {pdf_path}")
        
        try:
            reader = PdfReader(str(pdf_path))
            
            # Extract metadata
            metadata = {}
            if reader.metadata:
                metadata = {
                    'title': reader.metadata.get('/Title', ''),
                    'author': reader.metadata.get('/Author', ''),
                    'subject': reader.metadata.get('/Subject', ''),
                    'creator': reader.metadata.get('/Creator', ''),
                }
            
            # Extract text from all pages
            full_text = []
            page_texts = []
            
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    # Clean the text
                    page_text = self.clean_pdf_text(page_text)
                    full_text.append(page_text)
                    page_texts.append({
                        'page_num': i + 1,
                        'text': page_text,
                        'char_count': len(page_text)
                    })
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {i+1}: {e}")
            
            combined_text = '\n\n'.join(full_text)
            
            return {
                'full_text': combined_text,
                'page_texts': page_texts,
                'page_count': len(reader.pages),
                'metadata': metadata,
                'char_count': len(combined_text),
                'word_count': len(combined_text.split())
            }
            
        except Exception as e:
            logger.error(f"Failed to read PDF {pdf_path}: {e}")
            return {
                'full_text': '',
                'page_texts': [],
                'page_count': 0,
                'metadata': {},
                'error': str(e)
            }
    
    def detect_sections(self, full_text: str) -> Dict[str, str]:
        """
        Detect and extract major sections from paper text.
        Uses both line-by-line and position-based detection.
        
        Args:
            full_text: Complete PDF text
            
        Returns:
            Dictionary mapping section names to their text content
        """
        sections = {}
        
        # First, try to find section boundaries using exact matches
        section_markers = []
        
        # Look for "Materials and Methods" or similar
        for pattern in self.METHODS_HEADERS:
            matches = re.finditer(pattern, full_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                section_markers.append(('methods', match.start(), match.end()))
        
        for pattern in self.PARTICIPANTS_HEADERS:
            matches = re.finditer(pattern, full_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                section_markers.append(('participants', match.start(), match.end()))
        
        for pattern in self.RESULTS_HEADERS:
            matches = re.finditer(pattern, full_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                section_markers.append(('results', match.start(), match.end()))
        
        for pattern in self.INTRO_HEADERS:
            matches = re.finditer(pattern, full_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                section_markers.append(('introduction', match.start(), match.end()))
        
        # Sort by position
        section_markers.sort(key=lambda x: x[1])
        
        # Extract text between markers
        if section_markers:
            for i, (section_name, start, end) in enumerate(section_markers):
                # Find where this section ends (start of next section or end of text)
                if i + 1 < len(section_markers):
                    section_end = section_markers[i + 1][1]
                else:
                    section_end = len(full_text)
                
                # Extract section text (skip the header itself)
                section_text = full_text[end:section_end].strip()
                
                # Merge if section already exists (e.g., multiple "Participants" subsections)
                if section_name in sections:
                    sections[section_name] += '\n\n' + section_text
                else:
                    sections[section_name] = section_text
        
        # Fallback: if no sections found, use line-by-line detection (original method)
        if not sections:
            sections = self._detect_sections_by_line(full_text)
        
        logger.info(f"Detected sections: {list(sections.keys())}")
        return sections
    
    def _detect_sections_by_line(self, full_text: str) -> Dict[str, str]:
        """
        Fallback method: detect sections line by line.
        
        Args:
            full_text: Complete PDF text
            
        Returns:
            Dictionary of sections
        """
        sections = {}
        lines = full_text.split('\n')
        current_section = 'introduction'
        section_buffer = []
        
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
            
            # Check for Methods section
            if any(re.search(pattern, line_clean, re.IGNORECASE) for pattern in self.METHODS_HEADERS):
                if section_buffer:
                    sections[current_section] = '\n'.join(section_buffer)
                current_section = 'methods'
                section_buffer = [line]
                continue
            
            # Check for Participants section
            if any(re.search(pattern, line_clean, re.IGNORECASE) for pattern in self.PARTICIPANTS_HEADERS):
                if section_buffer:
                    sections[current_section] = '\n'.join(section_buffer)
                current_section = 'participants'
                section_buffer = [line]
                continue
            
            # Check for Results section
            if any(re.search(pattern, line_clean, re.IGNORECASE) for pattern in self.RESULTS_HEADERS):
                if section_buffer:
                    sections[current_section] = '\n'.join(section_buffer)
                current_section = 'results'
                section_buffer = [line]
                continue
            
            section_buffer.append(line)
        
        # Add final section
        if section_buffer:
            sections[current_section] = '\n'.join(section_buffer)
        
        return sections
    
    def detect_multiple_experiments(self, full_text: str) -> List[Dict[str, Any]]:
        """
        Detect if PDF contains multiple experiments and extract boundaries.
        
        Args:
            full_text: Complete PDF text
            
        Returns:
            List of experiment dictionaries with:
            - experiment_number: int
            - start_pos: int
            - end_pos: int
            - header: str (matched header text)
            - title: str (experiment title if found)
        """
        experiments = []
        
        # Get multi-experiment patterns
        if 'multi_experiment' not in self.patterns:
            logger.debug("No multi-experiment patterns found in patterns.yaml")
            return experiments
        
        multi_patterns = self.patterns['multi_experiment']
        experiment_headers = multi_patterns.get('experiment_headers', [])
        
        # Number conversion mappings
        roman_map = multi_patterns.get('roman_numerals', {})
        text_map = multi_patterns.get('written_numbers', {})
        
        # Find all experiment boundary markers
        for pattern in experiment_headers:
            matches = re.finditer(pattern, full_text, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                header_text = match.group(0)
                number_str = match.group(1) if match.groups() else None
                
                # Convert experiment number to integer
                exp_number = None
                if number_str:
                    # Try direct int conversion
                    try:
                        exp_number = int(number_str)
                    except ValueError:
                        # Try Roman numeral
                        if number_str.upper() in roman_map:
                            exp_number = roman_map[number_str.upper()]
                        # Try written number
                        elif number_str.lower() in text_map:
                            exp_number = text_map[number_str.lower()]
                
                if exp_number:
                    # Try to extract experiment title (text after the header)
                    title_match = re.search(
                        r':\s*([A-Z][^.\n]{5,80})',
                        full_text[match.end():match.end()+100]
                    )
                    title = title_match.group(1).strip() if title_match else f"Experiment {exp_number}"
                    
                    experiments.append({
                        'experiment_number': exp_number,
                        'start_pos': match.start(),
                        'end_pos': None,  # Will be set below
                        'header': header_text,
                        'title': title
                    })
        
        # Sort by position
        experiments.sort(key=lambda x: x['start_pos'])
        
        # Set end positions (start of next experiment or end of text)
        for i, exp in enumerate(experiments):
            if i + 1 < len(experiments):
                exp['end_pos'] = experiments[i + 1]['start_pos']
            else:
                exp['end_pos'] = len(full_text)
        
        # Remove duplicates (same experiment detected by multiple patterns)
        unique_experiments = []
        seen_numbers = set()
        for exp in experiments:
            if exp['experiment_number'] not in seen_numbers:
                unique_experiments.append(exp)
                seen_numbers.add(exp['experiment_number'])
        
        # Detect shared Methods section that appears after experiment headers
        # This is common in papers with structure: Exp 1 header, Exp 2 header, Methods, Results
        if len(unique_experiments) > 1:
            shared_methods_info = self._detect_shared_methods(full_text, unique_experiments)
            if shared_methods_info:
                # Store shared methods info with experiments
                for exp in unique_experiments:
                    exp['shared_methods_pos'] = shared_methods_info
                logger.info(f"Detected shared Methods section at position {shared_methods_info['start_pos']}")
        
        logger.info(f"Detected {len(unique_experiments)} experiments in PDF")
        return unique_experiments
    
    def _detect_shared_methods(self, full_text: str, experiments: List[Dict[str, Any]]) -> Optional[Dict[str, int]]:
        """
        Detect if there's a shared Methods section after experiment headers.
        
        Common pattern:
          Experiment 1
          [brief overview]
          Experiment 2
          [brief overview]
          Methods          <-- Shared methods for all experiments
          Participants
          ...
          Results Experiment 1
          Results Experiment 2
        
        Args:
            full_text: Complete PDF text
            experiments: List of detected experiments with boundaries
            
        Returns:
            Dict with start_pos and end_pos of shared methods, or None if not found
        """
        if not experiments:
            return None
        
        # Find position after the last experiment header
        last_exp_header_pos = max(exp['start_pos'] for exp in experiments)
        
        # Find the first experiment's end position (where next exp starts)
        first_exp_end = experiments[0]['end_pos']
        
        # Look for Methods section between last experiment header and first Results section
        search_start = last_exp_header_pos
        search_end = min(len(full_text), search_start + 20000)  # Search next 20k chars
        search_region = full_text[search_start:search_end]
        
        # Search for Methods/Participants headers
        methods_patterns = self.METHODS_HEADERS + self.PARTICIPANTS_HEADERS
        methods_match = None
        methods_pattern_used = None
        
        for pattern in methods_patterns:
            match = re.search(pattern, search_region, re.IGNORECASE | re.MULTILINE)
            if match:
                methods_match = match
                methods_pattern_used = pattern
                break
        
        if not methods_match:
            return None
        
        # Calculate absolute position in full text
        methods_start = search_start + methods_match.start()
        
        # Check if this Methods section is AFTER the first experiment's end
        # If so, it's likely a shared methods section
        if methods_start > first_exp_end:
            # Find where shared methods section ends (look for Results or Discussion)
            results_match = re.search(
                r'\n(Results?|Discussion|Experiment\s+\d+\s+Results?)\n',
                full_text[methods_start:methods_start + 15000],
                re.IGNORECASE
            )
            
            if results_match:
                methods_end = methods_start + results_match.start()
            else:
                # If no clear end marker, use a reasonable chunk (5000 chars)
                methods_end = min(methods_start + 5000, len(full_text))
            
            logger.debug(f"Found shared Methods section: {methods_start}-{methods_end} "
                        f"(after first exp end at {first_exp_end})")
            
            return {
                'start_pos': methods_start,
                'end_pos': methods_end,
                'pattern': methods_pattern_used
            }
        
        return None
    
    def extract_parameters_from_text(self, text: str, section_name: str = 'full') -> Dict[str, Any]:
        """
        Extract parameters using pattern matching on text.
        
        Args:
            text: Text to extract from
            section_name: Name of section (for confidence scoring)
            
        Returns:
            Dictionary of extracted parameters with confidence scores
        """
        extracted = {}
        
        # Apply all regex patterns from patterns.yaml
        if 'pdf' in self.patterns:
            pdf_patterns = self.patterns['pdf']
            
            for param_name, pattern_list in pdf_patterns.items():
                canonical = self.normalize_parameter_name(param_name)
                if not canonical:
                    continue
                
                # Try each pattern variant
                patterns = pattern_list if isinstance(pattern_list, list) else [pattern_list]
                all_matches = []
                
                for pattern in patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                    
                    for match in matches:
                        try:
                            # Extract value from capture group
                            value = match.group(1) if match.groups() else match.group(0)
                            
                            # Skip obviously wrong values (like very large numbers from encoding errors)
                            if param_name in ['num_trials', 'baseline_trials', 'adaptation_trials', 'training_trials']:
                                try:
                                    num_val = int(value)
                                    if num_val > 10000:  # Likely an encoding error
                                        continue
                                except:
                                    pass
                            
                            # Get context around match for pattern quality assessment
                            match_start = max(0, match.start() - 50)
                            match_end = min(len(text), match.end() + 50)
                            match_context = text[match_start:match_end]
                            
                            # Normalize and score with context
                            normalized_value, confidence = self.normalize_value(
                                canonical, value, match_context=match_context, 
                                evidence=match.group(0)
                            )
                            
                            # Section boost (empirically calibrated, not arbitrary)
                            # These values will be refined based on validation data
                            section_boost = {
                                'methods': 1.0,
                                'participants': 1.0,
                                'procedure': 1.0,
                                'abstract': 0.95,
                                'results': 0.85,  # Often summary, not exact
                                'discussion': 0.75,
                                'introduction': 0.7,
                            }.get(section_name, 0.9)
                            
                            confidence *= section_boost
                            
                            all_matches.append({
                                'value': normalized_value,
                                'confidence': confidence,
                                'source_name': param_name,
                                'method': 'pdf_pattern_match',
                                'section': section_name,
                                'evidence': match.group(0)[:200]  # Keep evidence snippet
                            })
                        except Exception as e:
                            logger.debug(f"Failed to extract {param_name}: {e}")
                
                # Keep highest confidence extraction for this parameter
                if all_matches:
                    best_match = max(all_matches, key=lambda x: x['confidence'])
                    if canonical not in extracted or best_match['confidence'] > extracted[canonical]['confidence']:
                        extracted[canonical] = best_match
        
        # Common parameter patterns (fallback if not in patterns.yaml)
        common_patterns = self._get_common_patterns()
        for param_name, pattern in common_patterns.items():
            canonical = self.normalize_parameter_name(param_name)
            if canonical and canonical not in extracted:
                matches = list(re.finditer(pattern, text, re.IGNORECASE))
                
                # Filter and score all matches
                valid_matches = []
                for match in matches:
                    try:
                        value = match.group(1)
                        
                        # Skip encoding errors for trial counts
                        if 'trial' in param_name or 'participant' in param_name:
                            try:
                                num_val = int(value)
                                if num_val > 10000:
                                    continue
                            except:
                                pass
                        
                        # Get context around match
                        match_start = max(0, match.start() - 50)
                        match_end = min(len(text), match.end() + 50)
                        match_context = text[match_start:match_end]
                        
                        # Normalize with context
                        normalized_value, base_confidence = self.normalize_value(
                            canonical, value, match_context=match_context,
                            evidence=match.group(0)
                        )
                        
                        # Lower confidence for fallback patterns (not in schema patterns.yaml)
                        confidence = base_confidence * 0.8
                        
                        # Section boost
                        section_boost = {
                            'methods': 1.0,
                            'participants': 1.0,
                            'procedure': 1.0,
                            'abstract': 0.95,
                            'results': 0.85,
                            'discussion': 0.75,
                            'introduction': 0.7,
                        }.get(section_name, 0.9)
                        
                        confidence *= section_boost
                        
                        valid_matches.append({
                            'value': normalized_value,
                            'confidence': confidence,
                            'source_name': param_name,
                            'method': 'pdf_common_pattern',
                            'section': section_name,
                            'evidence': match.group(0)[:200]
                        })
                    except Exception as e:
                        logger.debug(f"Failed common pattern for {param_name}: {e}")
                
                # Take highest confidence match
                if valid_matches:
                    best = max(valid_matches, key=lambda x: x['confidence'])
                    extracted[canonical] = best
        
        # Post-processing: Calculate total sample size from per-group + factorial design
        self._calculate_total_sample_size(extracted, text)
        
        return extracted
    
    def _calculate_total_sample_size(self, extracted: Dict[str, Any], text: str) -> None:
        """
        Calculate total sample size from per-group sample size and factorial design.
        
        If we find:
        - sample_size_per_group (e.g., "15 participants per group")
        - factorial design (e.g., "2-by-2 factorial" = 4 groups)
        
        Then calculate: n_total = sample_size_per_group × num_groups
        
        Args:
            extracted: Dictionary of extracted parameters (modified in place)
            text: Full PDF text for searching design information
        """
        # Check if we have sample_size_per_group but no n_total (or low confidence n_total)
        if 'sample_size_per_group' in extracted:
            per_group = extracted['sample_size_per_group']['value']
            
            try:
                n_per_group = int(per_group)
                
                # Look for factorial design patterns
                num_groups = None
                
                # Pattern 1: "2-by-2 factorial" or "2x2 factorial" = 4 groups
                if re.search(r'2\s*[×x-]\s*by\s*[×x-]?\s*2\s+factorial', text, re.IGNORECASE):
                    num_groups = 4
                    design_evidence = "2-by-2 factorial design"
                
                # Pattern 2: "3x2 factorial" = 6 groups
                elif re.search(r'3\s*[×x-]\s*2\s+factorial', text, re.IGNORECASE):
                    num_groups = 6
                    design_evidence = "3x2 factorial design"
                
                # Pattern 3: "2x3 factorial" = 6 groups
                elif re.search(r'2\s*[×x-]\s*3\s+factorial', text, re.IGNORECASE):
                    num_groups = 6
                    design_evidence = "2x3 factorial design"
                
                # Pattern 4: "four groups" or "4 groups"
                elif re.search(r'(?:four|4)\s+(?:experimental\s+)?groups', text, re.IGNORECASE):
                    num_groups = 4
                    design_evidence = "four groups"
                
                # Pattern 5: "three groups" or "3 groups"
                elif re.search(r'(?:three|3)\s+(?:experimental\s+)?groups', text, re.IGNORECASE):
                    num_groups = 3
                    design_evidence = "three groups"
                
                # If we found a design, calculate total
                if num_groups:
                    calculated_total = n_per_group * num_groups
                    
                    # Check if we should update n_total
                    should_update = False
                    if 'n_total' not in extracted:
                        should_update = True
                    elif extracted['n_total']['value'] == per_group:
                        # n_total incorrectly has per-group value, so update
                        should_update = True
                    elif extracted['n_total']['confidence'] < 0.85:
                        # Low confidence n_total, replace with calculation
                        should_update = True
                    
                    if should_update:
                        extracted['n_total'] = {
                            'value': calculated_total,
                            'confidence': 0.95,  # High confidence for calculated value
                            'source_name': 'calculated_from_factorial',
                            'method': 'factorial_design_calculation',
                            'section': 'methods',
                            'evidence': f'{n_per_group} per group × {design_evidence} = {calculated_total}'
                        }
                        logger.info(f"Calculated total sample size: {n_per_group} per group × {num_groups} groups = {calculated_total}")
                    
                    # Also update sample_size_n if it's the per-group value
                    if 'sample_size_n' in extracted and extracted['sample_size_n']['value'] == per_group:
                        extracted['sample_size_n'] = extracted['n_total'].copy()
                        extracted['sample_size_n']['source_name'] = 'calculated_total'
            
            except (ValueError, TypeError) as e:
                logger.debug(f"Could not calculate total sample size: {e}")
    
    def _get_common_patterns(self) -> Dict[str, str]:
        """
        Get common regex patterns for motor adaptation parameters.
        
        Returns:
            Dictionary of parameter names to regex patterns
        """
        return {
            # Sample size - improved patterns
            'sample_size': r'(?:with\s+)?(\d+)\s+(?:participants?|subjects?|individuals?)\s+(?:per\s+group|in\s+each|total)',
            'n_participants': r'\bn\s*=\s*(\d+)\b',
            'total_participants': r'(?:total\s+of\s+)?(\d+)\s+(?:young\s+)?(?:adults?|participants?|subjects?)',
            
            # Rotation parameters - handle both ° and degree symbols
            'rotation_magnitude': r'(?:learned?\s+a\s+)?(\d+)\s*(?:°|degrees?|deg)?\s*(?:counter-?clockwise|clockwise)?\s*rotation',
            'rotation_angle': r'(?:rotation|rotated)\s+(?:of\s+)?(\d+)\s*(?:°|degrees?|deg)',
            'visuomotor_rotation': r'(?:visuomotor|visual)\s+rotation\s+(?:of\s+)?(\d+)\s*(?:°|degrees?)?',
            
            # Trial counts - more specific contexts
            'adaptation_trials': r'(?:present\s+for\s+|over\s+the\s+course\s+of\s+)?(\d+)\s+trials?(?:\s+in\s+the\s+adaptation|\s+with\s+rotation|\s+during\s+(?:the\s+)?(?:training|adaptation))?',
            'baseline_trials': r'(?:first\s+block\s+of\s+)?(\d+)\s+trials?\s+(?:had\s+veridical|baseline|pre-?training)',
            'training_trials': r'(\d+)\s+trials?\s+(?:of\s+)?(?:training|learning|practice)',
            'num_trials': r'(?:over\s+)?(\d+)\s+trials?(?:\s+(?:in|during|of|with))?',
            
            # Block structure
            'num_blocks': r'(?:divided\s+into\s+)?(\d+)\s+blocks?',
            
            # Demographics - better age extraction
            'age_mean': r'(?:mean\s+age|aged)\s+(\d+(?:\.\d+)?)\s*(?:years?|yr|y\.o\.)',
            'age_range': r'age[sd]?\s+(\d+)\s*[-–—]\s*(\d+)',
            
            # Timing
            'movement_time': r'movement\s+time\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*(?:ms|milliseconds?|s|seconds?)',
            'feedback_delay': r'(?:feedback\s+)?delay\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*(?:ms|milliseconds?|s|seconds?)',
            'trial_duration': r'trial\s+duration\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*(?:ms|milliseconds?|s|seconds?)',
            
            # Equipment
            'manipulandum': r'(?:using|with)\s+(?:a|an|the)\s+(kinarm|vbot|phantom|robotic\s+arm|manipulandum)',
            
            # Perturbation
            'perturbation_type': r'(visuomotor|force\s+field|prism|visual)\s+(?:rotation|perturbation|adaptation)',
            
            # Instruction awareness
            'instruction_type': r'(?:were\s+)?(?:not\s+)?(informed|instructed|told)\s+(?:about|of|to)',
            
            # Gender composition
            'gender_composition': r'(\d+)\s+(?:fe-?\s*males?)[/\\](\d+)\s+(?:males?)',
        }
    
    def normalize_parameter_name(self, name: str) -> Optional[str]:
        """Normalize parameter name to canonical form using synonym map."""
        name_clean = name.lower().strip().replace(' ', '_')
        
        # Check flat schema first
        if name_clean in self.flat_schema:
            result = self.flat_schema[name_clean]
            # If it maps to a string, that's the canonical name
            if isinstance(result, str):
                return result
            # If it maps to a dict, this IS the canonical name
            return name_clean
        
        # Check synonym map
        if name_clean in self.alias_to_canonical:
            return self.alias_to_canonical[name_clean]
        
        return None
    
    def _assess_pattern_quality(self, match_text: str, param_name: str, value: str) -> float:
        """
        Assess pattern quality based on context and specificity.
        
        Args:
            match_text: The full matched text with context
            param_name: Canonical parameter name
            value: The extracted value
            
        Returns:
            Quality multiplier (0.6 - 1.0)
        """
        if not match_text:
            return 0.7  # Neutral if no context
        
        score = 0.6  # Base score for bare numbers
        match_lower = match_text.lower()
        
        # Check for units (strong indicator of specificity)
        unit_patterns = {
            'rotation': [r'°', r'deg(?:ree)?s?', r'rotation'],
            'age': [r'years?', r'yrs?', r'y\.o\.', r'age'],
            'participant': [r'participant', r'subject', r'n\s*='],
            'trial': [r'trials?', r'repetitions?'],
            'distance': [r'\bcm\b', r'\bmm\b', r'\bm\b', r'centimeters?', r'millimeters?'],
            'time': [r'\bms\b', r'\bs\b', r'\bsec(?:ond)?s?', r'minutes?'],
            'velocity': [r'cm/s', r'm/s', r'mm/s'],
            'force': [r'\bN\b', r'newtons?'],
        }
        
        # Boost for units presence
        for param_type, units in unit_patterns.items():
            if param_type in param_name:
                for unit_pattern in units:
                    if re.search(unit_pattern, match_lower):
                        score += 0.25
                        break
        
        # Check for parameter keywords in context
        param_keywords = param_name.replace('_', ' ').split()
        keyword_matches = 0
        for keyword in param_keywords:
            if len(keyword) > 3 and keyword in match_lower:
                keyword_matches += 1
        
        if keyword_matches >= 2:
            score += 0.2
        elif keyword_matches == 1:
            score += 0.1
        
        # Check for strong context verbs (indicates clear statement)
        strong_verbs = [r'\bwas\b', r'\bwere\b', r'\bconsisted\b', r'\bincluded\b', 
                       r'\bperformed\b', r'\bcompleted\b', r'\breceived\b']
        if any(re.search(verb, match_lower) for verb in strong_verbs):
            score += 0.05
        
        # Penalty for ambiguous language
        if re.search(r'approximately|~|around|about|roughly|up to|at least', match_lower):
            score -= 0.1
        
        # Check if it's a bare number (penalize heavily)
        if re.match(r'^\s*\d+\.?\d*\s*$', match_text.strip()):
            score = min(score, 0.6)  # Cap at 0.6 for bare numbers
        
        return max(min(score, 1.0), 0.5)  # Clamp between 0.5 and 1.0
    
    def normalize_value(self, parameter: str, value: str, 
                       match_context: str = '', evidence: str = '') -> Tuple[Any, float]:
        """
        Normalize parameter value and assign evidence-based confidence score.
        
        Args:
            parameter: Canonical parameter name
            value: Raw extracted value
            match_context: Full matched text with context (for pattern quality assessment)
            evidence: The evidence snippet showing the match in context
            
        Returns:
            Tuple of (normalized_value, confidence_score)
        """
        # Text number conversion
        text_to_num = {
            'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
            'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
            'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
            'eighty': 80, 'ninety': 90, 'hundred': 100
        }
        
        # Get parameter schema info from flat schema
        param_info = self.flat_schema.get(parameter, {})
        if isinstance(param_info, str):
            # It's a reference to another parameter
            param_info = self.flat_schema.get(param_info, {})
        param_type = param_info.get('type', 'string')
        
        # Base confidence for type conversion
        base_confidence = 0.75
        
        try:
            # Convert text numbers
            value_lower = str(value).lower()
            if value_lower in text_to_num:
                value = str(text_to_num[value_lower])
            
            if param_type == 'integer':
                normalized = int(float(re.sub(r'[^\d.-]', '', str(value))))
                base_confidence = 0.85  # Reduced from 0.9 - successful parse doesn't guarantee correctness
            elif param_type == 'float':
                normalized = float(re.sub(r'[^\d.-]', '', str(value)))
                base_confidence = 0.85  # Reduced from 0.9
            elif param_type == 'boolean':
                value_lower = str(value).lower()
                normalized = value_lower in ['true', 'yes', '1', 'on', 'enabled']
                base_confidence = 0.85
            elif param_type == 'enum':
                # Check if value matches one of the allowed enum values
                allowed_values = param_info.get('values', [])
                value_lower = str(value).lower()
                for allowed in allowed_values:
                    if value_lower == allowed.lower() or value_lower in allowed.lower():
                        normalized = allowed
                        base_confidence = 0.9
                        break
                else:
                    normalized = value
                    base_confidence = 0.6  # Lower confidence if not exact match
            else:
                normalized = str(value).strip()
                base_confidence = 0.75
            
            # Assess pattern quality if context provided
            if match_context or evidence:
                pattern_quality = self._assess_pattern_quality(
                    match_context or evidence, parameter, str(value)
                )
                confidence = base_confidence * pattern_quality
            else:
                confidence = base_confidence
            
            return normalized, confidence
            
        except Exception as e:
            logger.debug(f"Failed to normalize {parameter}={value}: {e}")
            return value, 0.5
    
    def extract_from_file(self, pdf_path: Path, 
                          use_llm_fallback: bool = None,
                          detect_multi_experiment: bool = True) -> Dict[str, Any]:
        """
        Extract parameters from a PDF file.
        Supports multi-experiment detection.
        
        Args:
            pdf_path: Path to PDF file
            use_llm_fallback: Override instance LLM setting for this extraction
            detect_multi_experiment: Whether to detect multiple experiments in the PDF
            
        Returns:
            Dictionary with:
            - is_multi_experiment: bool
            - experiments: List[Dict] if multi-experiment, else single dict
            - shared_parameters: Dict (for multi-experiment)
            - metadata: Dict
        """
        logger.info(f"Starting PDF extraction: {pdf_path}")
        
        # Override LLM setting if specified
        use_llm = use_llm_fallback if use_llm_fallback is not None else self.use_llm
        
        # Step 1: Extract text
        text_data = self.extract_text(pdf_path)
        if not text_data['full_text']:
            logger.warning(f"No text extracted from {pdf_path}")
            return {'parameters': {}, 'error': 'No text extracted', 'is_multi_experiment': False}
        
        # Step 2: Detect multiple experiments
        experiments_detected = []
        if detect_multi_experiment:
            experiments_detected = self.detect_multiple_experiments(text_data['full_text'])
        
        # Step 3: Extract based on single or multi-experiment
        if experiments_detected and len(experiments_detected) > 1:
            return self._extract_multi_experiment(
                pdf_path, text_data, experiments_detected, use_llm
            )
        else:
            # Single experiment extraction (original behavior)
            return self._extract_single_experiment(
                pdf_path, text_data, use_llm, is_multi=False
            )
    
    def _extract_single_experiment(self, pdf_path: Path, text_data: Dict[str, Any], 
                                   use_llm: bool, is_multi: bool = False,
                                   experiment_text: str = None,
                                   experiment_number: int = None,
                                   experiment_title: str = None) -> Dict[str, Any]:
        """
        Extract parameters from a single experiment (or full PDF if not multi-experiment).
        
        Args:
            pdf_path: Path to PDF file
            text_data: Extracted text data
            use_llm: Whether to use LLM assistance
            is_multi: Whether this is part of a multi-experiment PDF
            experiment_text: Text for specific experiment (if multi-experiment)
            experiment_number: Experiment number (if multi-experiment)
            experiment_title: Experiment title (if multi-experiment)
            
        Returns:
            Dictionary of extracted parameters with metadata
        """
        # Use provided experiment text or full text
        full_text = experiment_text if experiment_text else text_data['full_text']
        
        # Detect sections
        sections = self.detect_sections(full_text)
        
        # Extract parameters from each section
        all_parameters = {}
        
        # Prioritize Methods and Participants sections
        priority_sections = ['methods', 'participants', 'procedure', 'apparatus']
        for section_name in priority_sections:
            if section_name in sections:
                params = self.extract_parameters_from_text(sections[section_name], section_name)
                # Merge with priority to higher confidence
                for param, data in params.items():
                    if param not in all_parameters or data['confidence'] > all_parameters[param]['confidence']:
                        all_parameters[param] = data
        
        # Extract from remaining sections
        for section_name, section_text in sections.items():
            if section_name not in priority_sections:
                params = self.extract_parameters_from_text(section_text, section_name)
                for param, data in params.items():
                    if param not in all_parameters or data['confidence'] > all_parameters[param]['confidence']:
                        all_parameters[param] = data
        
        # LLM fallback for low-confidence parameters (if enabled)
        if use_llm and self.llm_assistant:
            logger.info("🤖 LLM assistance ENABLED - checking for low-confidence parameters")
            print(f"  🤖 LLM assistance active for this paper")
            all_parameters = self._apply_llm_fallback(
                all_parameters,
                full_text,
                sections.get('methods', '')
            )
        elif use_llm and not self.llm_assistant:
            logger.warning("⚠️  LLM enabled but assistant not initialized")
            print(f"  ⚠️  LLM requested but not available")
        else:
            logger.debug("LLM assistance disabled for this extraction")
        
        result = {
            'parameters': all_parameters,
            'metadata': {
                'file_path': str(pdf_path),
                'file_hash': compute_file_hash(str(pdf_path)),
                'pdf_metadata': text_data['metadata'],
                'page_count': text_data['page_count'],
                'word_count': text_data['word_count'],
                'sections_detected': list(sections.keys()),
                'extraction_timestamp': datetime.now().isoformat(),
                'extractor_version': __version__,
                'llm_used': use_llm and self.llm_assistant is not None
            }
        }
        
        # Add experiment-specific metadata if multi-experiment
        if is_multi:
            result['experiment_number'] = experiment_number
            result['experiment_title'] = experiment_title
        else:
            result['is_multi_experiment'] = False
        
        return result
    
    def _extract_multi_experiment(self, pdf_path: Path, text_data: Dict[str, Any],
                                  experiments_detected: List[Dict[str, Any]],
                                  use_llm: bool) -> Dict[str, Any]:
        """
        Extract parameters from a multi-experiment PDF.
        
        Args:
            pdf_path: Path to PDF file
            text_data: Extracted text data
            experiments_detected: List of detected experiment boundaries
            use_llm: Whether to use LLM assistance
            
        Returns:
            Dictionary with experiments list and shared parameters
        """
        logger.info(f"Extracting {len(experiments_detected)} experiments from {pdf_path}")
        
        experiments_results = []
        full_text = text_data['full_text']
        
        # Check if shared methods section was detected
        shared_methods_info = experiments_detected[0].get('shared_methods_pos') if experiments_detected else None
        shared_methods_text = ""
        
        if shared_methods_info:
            shared_methods_text = full_text[shared_methods_info['start_pos']:shared_methods_info['end_pos']]
            logger.info(f"Shared Methods section found ({len(shared_methods_text)} chars), "
                       f"will append to experiments that need it")
        
        # Extract parameters for each experiment
        for exp_info in experiments_detected:
            exp_number = exp_info['experiment_number']
            exp_title = exp_info['title']
            start_pos = exp_info['start_pos']
            end_pos = exp_info['end_pos']
            
            # Extract text for this experiment
            experiment_text = full_text[start_pos:end_pos]
            
            # Check if this experiment's text contains a Methods section
            has_methods = bool(re.search(
                r'\n\s*(Methods?|Participants?|Procedure|Apparatus)\s*\n',
                experiment_text,
                re.IGNORECASE
            ))
            
            # If no methods in experiment text but shared methods exists, append it
            if not has_methods and shared_methods_text:
                logger.info(f"Experiment {exp_number}: No Methods section in boundary, "
                           f"appending shared Methods ({len(shared_methods_text)} chars)")
                # Insert shared methods after the experiment header
                header_end = experiment_text[:200].find('\n') + 1
                if header_end > 0:
                    experiment_text = (experiment_text[:header_end] + 
                                     "\n" + shared_methods_text + 
                                     "\n" + experiment_text[header_end:])
                else:
                    # If can't find header, just append
                    experiment_text = experiment_text + "\n" + shared_methods_text
                
                logger.info(f"Experiment {exp_number}: Updated text length: {len(experiment_text)} chars")
            elif has_methods:
                logger.info(f"Experiment {exp_number}: Has Methods section in its boundary")
            
            # For first experiment, skip intro text before Methods section (if not already handled)
            if exp_number == 1 and not shared_methods_text:
                original_length = len(experiment_text)
                
                # Look for "Methods" or "Participants" header within experiment text
                # Use a more flexible pattern that matches section headers
                methods_match = re.search(
                    r'\n\s*(Methods?|Participants?|Procedure|Apparatus)\s*\n',
                    experiment_text,
                    re.IGNORECASE
                )
                
                if methods_match:
                    methods_start = methods_match.start()
                    logger.info(f"Experiment 1: Found Methods section at position {methods_start}")
                    
                    if methods_start > 100:
                        # Keep the experiment header but skip to methods
                        header_end = experiment_text[:200].find('\n') + 1
                        experiment_text = experiment_text[:header_end] + experiment_text[methods_start:]
                        logger.info(f"Experiment 1: Skipped {methods_start - header_end} chars of intro text")
                        logger.info(f"Experiment 1: Text length {original_length} -> {len(experiment_text)}")
                    else:
                        logger.info(f"Experiment 1: Methods section too close to start ({methods_start} chars), not skipping")
                else:
                    logger.warning(f"Experiment 1: No Methods section found in experiment text (length: {original_length})")
                    # Show first 500 chars for debugging
                    logger.debug(f"First 500 chars: {experiment_text[:500]}")
            
            logger.info(f"Extracting Experiment {exp_number}: {exp_title}")
            
            # Extract parameters for this experiment
            exp_result = self._extract_single_experiment(
                pdf_path=pdf_path,
                text_data=text_data,
                use_llm=use_llm,
                is_multi=True,
                experiment_text=experiment_text,
                experiment_number=exp_number,
                experiment_title=exp_title
            )
            
            experiments_results.append(exp_result)
        
        # Extract shared parameters (from introduction or before first experiment)
        shared_text = full_text[:experiments_detected[0]['start_pos']] if experiments_detected else ""
        shared_sections = self.detect_sections(shared_text)
        shared_parameters = {}
        
        # Look for shared information in intro/general methods
        for section_name in ['introduction', 'methods', 'participants']:
            if section_name in shared_sections:
                params = self.extract_parameters_from_text(shared_sections[section_name], f"shared_{section_name}")
                for param, data in params.items():
                    if param not in shared_parameters or data['confidence'] > shared_parameters[param]['confidence']:
                        shared_parameters[param] = data
        
        return {
            'is_multi_experiment': True,
            'num_experiments': len(experiments_results),
            'experiments': experiments_results,
            'shared_parameters': shared_parameters,
            'metadata': {
                'file_path': str(pdf_path),
                'file_hash': compute_file_hash(str(pdf_path)),
                'pdf_metadata': text_data['metadata'],
                'page_count': text_data['page_count'],
                'word_count': text_data['word_count'],
                'extraction_timestamp': datetime.now().isoformat(),
                'extractor_version': __version__,
                'llm_used': use_llm and self.llm_assistant is not None
            }
        }
    
    
    def _apply_llm_fallback(self, 
                           extracted_params: Dict[str, Any],
                           full_text: str,
                           methods_text: str) -> Dict[str, Any]:
        """
        Apply LLM assistance for parameters with confidence < 0.3.
        Follows LLM policy guidelines.
        
        Args:
            extracted_params: Already extracted parameters
            full_text: Full paper text
            methods_text: Methods section text
            
        Returns:
            Updated parameters with LLM-inferred values
        """
        if not self.llm_assistant or not self.llm_assistant.enabled:
            return extracted_params
        
        params_to_check = []
        
        if self.llm_mode == 'verify':
            # VERIFY MODE: Check ALL extracted parameters + missing critical ones
            logger.info("🤖 LLM VERIFY MODE: Checking all extracted parameters")
            print(f"     🤖 LLM mode: VERIFY (checking all {len(extracted_params)} parameters)")
            
            # Add all extracted parameters for verification
            params_to_check.extend(extracted_params.keys())
            
            # Also add missing critical parameters
            critical_params = self._get_critical_parameters()
            for param in critical_params:
                if param not in extracted_params:
                    params_to_check.append(param)
                    
        else:
            # FALLBACK MODE: Only low-confidence and missing critical
            logger.info("🤖 LLM FALLBACK MODE: Checking low-confidence parameters only")
            
            # Identify parameters that need LLM assistance
            for param, data in extracted_params.items():
                if data['confidence'] < 0.3:
                    params_to_check.append(param)
            
            # Also check for missing critical parameters in schema
            critical_params = self._get_critical_parameters()
            for param in critical_params:
                if param not in extracted_params:
                    params_to_check.append(param)
        
        if not params_to_check:
            logger.info("✅ No parameters require LLM assistance (all confidence >= 0.3)")
            return extracted_params
        
        logger.info(f"🤖 Attempting LLM review for {len(params_to_check)} parameters: {params_to_check}")
        print(f"     🤖 LLM checking: {', '.join(params_to_check[:5])}{'...' if len(params_to_check) > 5 else ''}")
        
        # Use methods section as primary context
        context = methods_text if methods_text else full_text[:5000]  # Limit context size
        
        for param in params_to_check:
            try:
                llm_result = self.llm_assistant.infer_parameter(
                    parameter_name=param,
                    context=context,
                    extracted_params=extracted_params
                )
                
                if llm_result and llm_result.get('value') is not None:
                    # Store LLM result with appropriate metadata
                    extracted_params[param] = {
                        'value': llm_result['value'],
                        'confidence': llm_result.get('confidence_llm', 0.5),
                        'method': 'llm_assisted',
                        'source_name': param,
                        'section': 'llm_inference',
                        'evidence': llm_result.get('evidence', ''),
                        'llm_model': self.llm_assistant.model,
                        'llm_provider': self.llm_assistant.provider
                    }
                    logger.info(f"✅ LLM inferred {param} = {llm_result['value']} (confidence: {llm_result.get('confidence_llm', 0.5):.2f})")
                    print(f"        ✅ {param} = {llm_result['value']}")
                else:
                    logger.debug(f"❌ LLM could not infer {param}")
            
            except Exception as e:
                import traceback
                logger.warning(f"LLM inference failed for {param}: {e}")
                logger.debug(f"[DEBUG] Full traceback:\n{traceback.format_exc()}")
                logger.debug(f"[DEBUG] extracted_params keys: {list(extracted_params.keys()) if extracted_params else 'None'}")
                if extracted_params:
                    logger.debug(f"[DEBUG] Sample param structure: {list(extracted_params.values())[0] if extracted_params else 'None'}")
        
        return extracted_params
    
    def _get_critical_parameters(self) -> List[str]:
        """
        Get list of critical parameters that should be extracted from papers.
        
        Returns:
            List of canonical parameter names
        """
        # Based on PRD Section 6.2 critical metadata
        return [
            'sample_size',
            'rotation_magnitude',
            'num_trials',
            'perturbation_type',
            'feedback_type',
            'age_mean',
            'handedness_criteria',
            'manipulandum_type',
        ]


class CodeExtractor:
    """
    Main extractor class that orchestrates extraction from multiple file types.
    Integrates PDF extraction with existing code/config extraction.
    """
    
    def __init__(self, db: Database, use_llm: bool = False, llm_provider: str = 'claude'):
        """
        Initialize code extractor.
        
        Args:
            db: Database instance
            use_llm: Enable LLM assistance
            llm_provider: LLM provider name
        """
        self.db = db
        self.use_llm = use_llm
        self.llm_provider = llm_provider
        
        # Initialize PDF extractor
        self.pdf_extractor = PDFExtractor(
            use_llm=use_llm,
            llm_provider=llm_provider
        )
    
    def extract_from_repo(self, repo_path: str, files: Dict[str, List[Path]], 
                         exp_id: str = None) -> Experiment:
        """
        Extract parameters from all files in a repository.
        
        Args:
            repo_path: Path to repository
            files: Dictionary of discovered files by type
            exp_id: Experiment ID (auto-generated if None)
            
        Returns:
            Experiment object with extracted parameters
        """
        logger.info(f"Extracting from repository: {repo_path}")
        
        all_parameters = {}
        provenance_records = []
        
        # Extract from PDF files
        if 'pdf' in files and files['pdf']:
            for pdf_file in files['pdf']:
                logger.info(f"Processing PDF: {pdf_file}")
                try:
                    result = self.pdf_extractor.extract_from_file(pdf_file, use_llm_fallback=self.use_llm)
                    
                    # Merge parameters
                    for param, data in result['parameters'].items():
                        # Keep highest confidence value
                        if param not in all_parameters or data['confidence'] > all_parameters[param]['confidence']:
                            all_parameters[param] = data
                    
                    # Record provenance
                    provenance_records.append({
                        'source_file': str(pdf_file),
                        'source_type': 'pdf',
                        'file_hash': result['metadata']['file_hash'],
                        'extractor_version': __version__,
                        'extraction_timestamp': result['metadata']['extraction_timestamp'],
                        'llm_used': result['metadata']['llm_used'],
                        'parameters_extracted': list(result['parameters'].keys())
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to extract from PDF {pdf_file}: {e}")
        
        # TODO: Extract from other file types (Python, JSON, MATLAB, etc.)
        # This would integrate with existing extractors
        
        # Create experiment record
        experiment = self._create_experiment_record(
            repo_path=repo_path,
            exp_id=exp_id,
            parameters=all_parameters,
            provenance=provenance_records
        )
        
        return experiment
    
    def _create_experiment_record(self, 
                                 repo_path: str,
                                 exp_id: str,
                                 parameters: Dict[str, Any],
                                 provenance: List[Dict]) -> Experiment:
        """
        Create experiment record in database.
        
        Args:
            repo_path: Repository path
            exp_id: Experiment ID
            parameters: Extracted parameters
            provenance: Provenance records
            
        Returns:
            Experiment object
        """
        # Generate experiment ID if not provided
        if not exp_id:
            exp_id = f"EXP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Determine entry status based on confidence
        avg_confidence = sum(p['confidence'] for p in parameters.values()) / len(parameters) if parameters else 0
        entry_status = 'needs_review' if avg_confidence < 0.7 else 'validated'
        
        # Check for conflicts (would be implemented in conflict resolution module)
        conflict_flag = False
        
        # Create experiment object (simplified - actual DB integration would go here)
        experiment = type('Experiment', (), {
            'id': exp_id,
            'repo_path': repo_path,
            'parameters': parameters,
            'provenance': provenance,
            'entry_status': entry_status,
            'conflict_flag': conflict_flag,
            'extraction_timestamp': datetime.now().isoformat(),
            'parameter_count': len(parameters),
            'avg_confidence': avg_confidence
        })()
        
        logger.info(f"Created experiment {exp_id} with {len(parameters)} parameters")
        return experiment
