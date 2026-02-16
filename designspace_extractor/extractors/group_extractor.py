"""
Group-level parameter and results extraction module.

This module extends the PDFExtractor to support extracting parameters
and results at the experimental group/condition level, in addition to
experiment-level extraction.

Usage:
    from extractors.group_extractor import GroupExtractor
    
    extractor = GroupExtractor(extract_level='group')
    result = extractor.extract_from_file(pdf_path)
    # Returns: {'groups': [{group_name, parameters, results}, ...]}
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class GroupExtractionMixin:
    """
    Mixin class providing group-level extraction methods for PDFExtractor.
    
    This adds the ability to:
    1. Detect experimental groups/conditions in papers
    2. Extract group-specific parameters
    3. Extract group-level results (means, SDs, statistical tests)
    4. Map parameters and results to specific groups
    """
    
    def _detect_groups(self, text: str, methods_section: str = None) -> Dict[str, Any]:
        """
        Detect experimental groups/conditions in the paper.
        
        Args:
            text: Full paper text
            methods_section: Methods section text (more focused search)
            
        Returns:
            {
                'num_groups': int,
                'group_names': List[str],
                'detection_confidence': float,
                'detection_method': str
            }
        """
        # Prefer methods section for group detection
        search_text = methods_section if methods_section else text
        
        result = {
            'num_groups': 0,
            'group_names': [],
            'detection_confidence': 0.0,
            'detection_method': 'none'
        }
        
        # Get group patterns from loaded patterns.yaml
        if not hasattr(self, 'patterns') or 'groups' not in self.patterns:
            logger.warning("Group patterns not found in patterns.yaml")
            return result
        
        group_patterns = self.patterns['groups']
        
        # Method 1: Direct group count detection
        for pattern in group_patterns.get('group_identification', []):
            matches = re.findall(pattern, search_text, re.IGNORECASE | re.MULTILINE)
            if matches:
                # Extract number from match
                for match in matches:
                    if isinstance(match, tuple):
                        num_str = match[0]
                    else:
                        num_str = match
                    
                    try:
                        num_groups = int(num_str)
                        if num_groups > 1 and num_groups <= 10:  # Sanity check
                            result['num_groups'] = num_groups
                            result['detection_confidence'] = 0.8
                            result['detection_method'] = 'explicit_count'
                            break
                    except ValueError:
                        continue
                
                if result['num_groups'] > 0:
                    break
        
        # Method 2: Extract group names
        group_names_set = set()
        
        for pattern in group_patterns.get('group_names', []):
            matches = re.findall(pattern, search_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # Extract group name from capture group
                    group_name = match[-1] if len(match) > 1 else match[0]
                else:
                    group_name = match
                
                # Clean group name
                group_name = group_name.strip().strip(',').strip()
                if group_name and len(group_name) > 2:
                    # Capitalize first letter
                    group_name = group_name[0].upper() + group_name[1:].lower()
                    group_names_set.add(group_name)
        
        # Convert set to sorted list
        result['group_names'] = sorted(list(group_names_set))
        
        # If we found group names but no explicit count, infer count
        if len(result['group_names']) > 1 and result['num_groups'] == 0:
            result['num_groups'] = len(result['group_names'])
            result['detection_confidence'] = 0.6
            result['detection_method'] = 'inferred_from_names'
        
        # Validate: if count and names mismatch, log warning
        if result['num_groups'] > 0 and len(result['group_names']) > 0:
            if result['num_groups'] != len(result['group_names']):
                logger.warning(
                    f"Group count mismatch: detected {result['num_groups']} groups "
                    f"but found {len(result['group_names'])} names: {result['group_names']}"
                )
                # Trust explicit count more than inferred names
                if result['detection_method'] == 'explicit_count':
                    result['detection_confidence'] = 0.7
        
        logger.info(
            f"Group detection: {result['num_groups']} groups found "
            f"(method: {result['detection_method']}, confidence: {result['detection_confidence']:.2f})"
        )
        if result['group_names']:
            logger.info(f"  Group names: {result['group_names']}")
        
        return result
    
    def _extract_group_names(self, text: str, num_expected: int = None) -> List[str]:
        """
        Extract group/condition names from text.
        
        Args:
            text: Text to search
            num_expected: Expected number of groups (helps validation)
            
        Returns:
            List of group names
        """
        detection_result = self._detect_groups(text)
        return detection_result['group_names']
    
    def _extract_group_sample_sizes(self, text: str, group_names: List[str]) -> Dict[str, int]:
        """
        Extract sample sizes for each group.
        
        Args:
            text: Full text or methods section
            group_names: List of known group names
            
        Returns:
            Dictionary mapping group_name -> sample_size
        """
        group_n = {}
        
        if not hasattr(self, 'patterns') or 'groups' not in self.patterns:
            return group_n
        
        patterns = self.patterns['groups'].get('group_sample_size', [])
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    # Pattern typically captures (group_name, n) or (n, group_name)
                    # Try both orders
                    try:
                        n = int(match[0])
                        group_name = match[1]
                    except ValueError:
                        try:
                            n = int(match[1])
                            group_name = match[0]
                        except ValueError:
                            continue
                    
                    # Normalize group name
                    group_name = group_name.strip().strip(',').strip()
                    group_name = group_name[0].upper() + group_name[1:].lower() if group_name else ""
                    
                    # Check if this matches one of our known groups
                    for known_group in group_names:
                        if group_name.lower() in known_group.lower() or known_group.lower() in group_name.lower():
                            group_n[known_group] = n
                            logger.debug(f"Found sample size for {known_group}: n={n}")
                            break
        
        return group_n
    
    def _extract_group_parameters(self, text: str, group_name: str,
                                  experiment_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Extract parameters specific to a particular group.
        
        Args:
            text: Full text to search
            group_name: Name of the group to extract parameters for
            experiment_params: Experiment-level parameters (for inheritance)
            
        Returns:
            Dictionary of group-specific parameters
        """
        # Start with experiment-level defaults
        group_params = experiment_params.copy() if experiment_params else {}
        
        # Get group-specific context patterns
        if not hasattr(self, 'patterns') or 'groups' not in self.patterns:
            return group_params
        
        context_patterns = self.patterns['groups'].get('group_parameter_context', [])
        
        # Find text segments mentioning this group
        group_segments = []
        for pattern in context_patterns:
            matches = re.finditer(pattern.replace('([A-Z][a-z]+)', f'({re.escape(group_name)})'), 
                                text, re.IGNORECASE)
            for match in matches:
                # Extract sentence containing the match
                start = max(0, match.start() - 200)
                end = min(len(text), match.end() + 200)
                segment = text[start:end]
                group_segments.append(segment)
        
        # Extract parameters from group-specific segments
        if group_segments:
            combined_text = ' '.join(group_segments)
            # Use the standard parameter extraction on this focused text
            extracted = self.extract_parameters_from_text(combined_text, 'group_context')
            
            # Override experiment-level parameters with group-specific ones
            for param, data in extracted.items():
                if data['confidence'] > 0.4:  # Only override with confident extractions
                    group_params[param] = data
        
        return group_params
    
    def _extract_group_results(self, text: str, group_name: str = None) -> Dict[str, Any]:
        """
        Extract results (means, SDs, statistics) for a specific group.
        
        Args:
            text: Results section text (or full text)
            group_name: Name of the group (if None, extract all results)
            
        Returns:
            Dictionary of results structured as:
            {
                'measurements': [
                    {'metric': 'adaptation', 'mean': 23.5, 'sd': 4.2, 'n': 15, 'unit': 'deg'},
                    ...
                ],
                'statistics': [
                    {'test': 't-test', 't': 3.45, 'df': 28, 'p': 0.002, 'comparison': '...'},
                    ...
                ]
            }
        """
        results = {
            'measurements': [],
            'statistics': [],
            'comparisons': []
        }
        
        if not hasattr(self, 'patterns') or 'results' not in self.patterns:
            return results
        
        result_patterns = self.patterns['results']
        
        # Focus on text mentioning the group if specified
        search_text = text
        if group_name:
            # Find sentences mentioning this group in results
            group_mentions = []
            sentences = re.split(r'[.!?]+', text)
            for sent in sentences:
                if group_name.lower() in sent.lower():
                    group_mentions.append(sent)
            if group_mentions:
                search_text = ' '.join(group_mentions)
        
        # Extract means and SDs
        for pattern in result_patterns.get('mean_sd_extraction', []):
            matches = re.finditer(pattern, search_text, re.IGNORECASE)
            for match in matches:
                try:
                    groups = match.groups()
                    if len(groups) >= 2:
                        mean_val = float(groups[0])
                        sd_val = float(groups[1])
                        
                        # Try to identify the metric type from context
                        context = search_text[max(0, match.start()-50):match.start()]
                        metric_type = self._identify_metric_type(context)
                        
                        # Extract unit if present
                        unit = self._extract_unit(match.group(0))
                        
                        results['measurements'].append({
                            'metric': metric_type,
                            'mean': mean_val,
                            'sd': sd_val,
                            'unit': unit,
                            'context': context[-30:] if context else ''
                        })
                except (ValueError, IndexError) as e:
                    logger.debug(f"Could not parse mean/SD: {e}")
                    continue
        
        # Extract statistical tests
        for pattern in result_patterns.get('statistical_tests', []):
            matches = re.finditer(pattern, search_text, re.IGNORECASE)
            for match in matches:
                try:
                    stat_result = self._parse_statistical_test(match.group(0), match.groups())
                    if stat_result:
                        results['statistics'].append(stat_result)
                except Exception as e:
                    logger.debug(f"Could not parse statistical test: {e}")
                    continue
        
        # Extract comparisons
        for pattern in result_patterns.get('comparison_phrases', []):
            matches = re.finditer(pattern, search_text, re.IGNORECASE)
            for match in matches:
                try:
                    groups = match.groups()
                    if len(groups) >= 2:
                        results['comparisons'].append({
                            'group_a': groups[0].strip(),
                            'group_b': groups[1].strip() if len(groups) > 1 else None,
                            'context': match.group(0)
                        })
                except Exception as e:
                    logger.debug(f"Could not parse comparison: {e}")
                    continue
        
        logger.debug(
            f"Results extraction for {group_name or 'all'}: "
            f"{len(results['measurements'])} measurements, "
            f"{len(results['statistics'])} statistical tests"
        )
        
        return results
    
    def _identify_metric_type(self, context: str) -> str:
        """Identify the type of metric from context."""
        context_lower = context.lower()
        
        # Check for specific metric keywords
        if 'adaptation' in context_lower:
            if 'early' in context_lower:
                return 'early_adaptation'
            elif 'late' in context_lower:
                return 'late_adaptation'
            return 'adaptation'
        elif 'retention' in context_lower or 'aftereffect' in context_lower:
            return 'retention'
        elif 'washout' in context_lower:
            return 'washout'
        elif 'learning' in context_lower:
            return 'learning_rate'
        elif 'error' in context_lower:
            return 'error'
        elif 'reaction time' in context_lower or ' rt' in context_lower:
            return 'reaction_time'
        elif 'movement time' in context_lower or ' mt' in context_lower:
            return 'movement_time'
        
        return 'unknown'
    
    def _extract_unit(self, text: str) -> Optional[str]:
        """Extract measurement unit from text."""
        units = {
            'deg': 'degrees',
            '°': 'degrees',
            'mm': 'millimeters',
            'ms': 'milliseconds',
            'N': 'newtons',
            'cm': 'centimeters',
            's': 'seconds'
        }
        
        for unit_abbrev, unit_name in units.items():
            if unit_abbrev in text:
                return unit_name
        
        return None
    
    def _parse_statistical_test(self, full_match: str, groups: Tuple) -> Optional[Dict[str, Any]]:
        """Parse a statistical test result into structured format."""
        result = {}
        
        # Detect test type
        if 't(' in full_match.lower() or 't =' in full_match.lower():
            result['test'] = 't-test'
            # Try to extract t, df, p
            try:
                if len(groups) >= 3:
                    result['df'] = int(groups[0]) if groups[0] else None
                    result['t_value'] = float(groups[1]) if groups[1] else None
                    result['p_value'] = float(groups[2]) if groups[2] else None
                elif len(groups) >= 2:
                    result['t_value'] = float(groups[0]) if groups[0] else None
                    result['p_value'] = float(groups[1]) if groups[1] else None
            except (ValueError, IndexError):
                pass
        
        elif 'f(' in full_match.lower() or 'f =' in full_match.lower():
            result['test'] = 'anova'
            # Try to extract F, df1, df2, p
            try:
                if len(groups) >= 4:
                    result['df1'] = int(groups[0]) if groups[0] else None
                    result['df2'] = int(groups[1]) if groups[1] else None
                    result['f_value'] = float(groups[2]) if groups[2] else None
                    result['p_value'] = float(groups[3]) if groups[3] else None
            except (ValueError, IndexError):
                pass
        
        elif 'cohen' in full_match.lower() or ' d =' in full_match.lower():
            result['test'] = 'effect_size'
            result['effect_size_type'] = 'cohens_d'
            try:
                result['effect_size'] = float(groups[0]) if groups and groups[0] else None
            except (ValueError, IndexError):
                pass
        
        elif 'η' in full_match or 'eta' in full_match.lower():
            result['test'] = 'effect_size'
            result['effect_size_type'] = 'eta_squared'
            try:
                result['effect_size'] = float(groups[0]) if groups and groups[0] else None
            except (ValueError, IndexError):
                pass
        
        return result if result else None
    
    def extract_group_level(self, pdf_path, text_data: Dict[str, Any], 
                           use_llm: bool = False) -> Dict[str, Any]:
        """
        Main method to extract group-level parameters and results.
        
        Args:
            pdf_path: Path to PDF file
            text_data: Extracted text data from preprocessor
            use_llm: Whether to use LLM for ambiguous cases
            
        Returns:
            {
                'has_groups': bool,
                'num_groups': int,
                'groups': [
                    {
                        'group_id': str,
                        'group_name': str,
                        'group_number': int,
                        'parameters': dict,
                        'results': dict,
                        'extraction_confidence': float
                    },
                    ...
                ],
                'experiment_parameters': dict,  # Shared/experiment-level
                'extraction_level': 'group'
            }
        """
        full_text = text_data['full_text']
        sections = text_data.get('sections', {})
        
        # Step 1: Detect groups
        methods_text = sections.get('methods', '') or sections.get('procedure', '')
        group_detection = self._detect_groups(full_text, methods_text)
        
        if group_detection['num_groups'] <= 1:
            logger.info("No multiple groups detected - treating as single-group experiment")
            # Return single default group
            experiment_params = self.extract_parameters_from_text(full_text, 'methods')
            return {
                'has_groups': False,
                'num_groups': 1,
                'groups': [{
                    'group_id': f'{pdf_path.stem}_DEFAULT',
                    'group_name': 'All participants',
                    'group_number': 1,
                    'group_type': 'single_group',
                    'parameters': experiment_params,
                    'results': {},
                    'extraction_confidence': 1.0
                }],
                'experiment_parameters': experiment_params,
                'extraction_level': 'experiment'
            }
        
        # Step 2: Extract experiment-level (shared) parameters
        experiment_params = self.extract_parameters_from_text(methods_text or full_text, 'methods')
        
        # Step 3: Extract each group's parameters and results
        groups = []
        for idx, group_name in enumerate(group_detection['group_names'], 1):
            logger.info(f"Extracting parameters for group: {group_name}")
            
            # Get group-specific parameters
            group_params = self._extract_group_parameters(full_text, group_name, experiment_params)
            
            # Get group sample size
            group_n_dict = self._extract_group_sample_sizes(full_text, [group_name])
            group_n = group_n_dict.get(group_name, None)
            
            # Extract results for this group
            results_text = sections.get('results', full_text)
            group_results = self._extract_group_results(results_text, group_name)
            
            groups.append({
                'group_id': f'{pdf_path.stem}_GRP{idx:02d}',
                'group_name': group_name,
                'group_number': idx,
                'group_type': self._infer_group_type(group_name),
                'sample_size_n': group_n,
                'parameters': group_params,
                'results': group_results,
                'extraction_confidence': group_detection['detection_confidence'],
                'extraction_method': 'regex'
            })
        
        # If we expected more groups than we found names for, flag for review
        if len(groups) < group_detection['num_groups']:
            logger.warning(
                f"Expected {group_detection['num_groups']} groups but only extracted "
                f"{len(groups)}. May need manual review."
            )
        
        return {
            'has_groups': True,
            'num_groups': len(groups),
            'groups': groups,
            'experiment_parameters': experiment_params,
            'extraction_level': 'group',
            'detection_confidence': group_detection['detection_confidence']
        }
    
    def _infer_group_type(self, group_name: str) -> str:
        """Infer group type (control, experimental, etc.) from name."""
        name_lower = group_name.lower()
        
        if 'control' in name_lower or 'baseline' in name_lower:
            return 'control'
        elif 'experimental' in name_lower or 'test' in name_lower:
            return 'experimental'
        elif 'sham' in name_lower or 'placebo' in name_lower:
            return 'sham'
        else:
            return 'experimental'  # Default assumption
