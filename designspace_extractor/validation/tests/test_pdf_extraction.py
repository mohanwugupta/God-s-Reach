"""
Formal Test Suite for Design-Space Parameter Extractor
Tests PDF extraction, pattern matching, and multi-experiment detection.
"""

import pytest
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from extractors.pdfs import PDFExtractor


class TestPDFExtraction:
    """Test PDF extraction functionality."""
    
    @pytest.fixture
    def extractor(self):
        """Create PDF extractor instance."""
        return PDFExtractor(
            schema_map_path='./mapping/schema_map.yaml',
            patterns_path='./mapping/patterns.yaml',
            synonyms_path='./mapping/synonyms.yaml'
        )
    
    @pytest.fixture
    def bond_taylor_pdf(self):
        """Path to Bond & Taylor 2017 PDF."""
        return Path('../../../papers/Bond and Taylor - 2017 - Structural Learning in a Visuomotor Adaptation Task Is Explicitly Accessible.pdf')
    
    @pytest.fixture
    def bond_taylor_expected(self):
        """Load expected results for Bond & Taylor."""
        with open('./fixtures/bond_taylor_2017_expected.json', 'r') as f:
            return json.load(f)
    
    def test_pdf_text_extraction(self, extractor, bond_taylor_pdf):
        """Test that PDF text can be extracted."""
        text = extractor._extract_text_from_pdf(str(bond_taylor_pdf))
        
        assert text is not None
        assert len(text) > 1000  # Should have substantial text
        assert "visuomotor" in text.lower()
    
    def test_section_detection(self, extractor, bond_taylor_pdf):
        """Test that sections are detected correctly."""
        text = extractor._extract_text_from_pdf(str(bond_taylor_pdf))
        sections = extractor._detect_sections(text)
        
        assert 'methods' in sections or 'participants' in sections
        assert len(sections) > 0
    
    def test_multi_experiment_detection(self, extractor, bond_taylor_pdf, bond_taylor_expected):
        """Test multi-experiment detection."""
        result = extractor.extract_from_file(str(bond_taylor_pdf), detect_multi_experiment=True)
        
        assert result['is_multi_experiment'] == bond_taylor_expected['is_multi_experiment']
        assert result['num_experiments'] == bond_taylor_expected['num_experiments']
    
    def test_shared_methods_detection(self, extractor, bond_taylor_pdf):
        """Test that shared methods sections are detected and distributed."""
        result = extractor.extract_from_file(str(bond_taylor_pdf), detect_multi_experiment=True)
        
        # Both experiments should have methods sections
        for exp in result['experiments']:
            sections = exp.get('detected_sections', [])
            assert 'methods' in sections or 'participants' in sections, \
                f"Experiment {exp.get('experiment_number', 'unknown')} missing methods/participants section"
    
    def test_parameter_extraction_quality(self, extractor, bond_taylor_pdf, bond_taylor_expected):
        """Test that parameters are extracted with minimum quality."""
        result = extractor.extract_from_file(str(bond_taylor_pdf), detect_multi_experiment=True)
        
        for idx, exp in enumerate(result['experiments']):
            expected = bond_taylor_expected['experiments'][idx]
            params = exp.get('parameters', {})
            param_count = len(params)
            
            # Check parameter count is in expected range
            assert expected['min_parameters'] <= param_count <= expected['max_parameters'], \
                f"Experiment {idx + 1}: Got {param_count} params, expected {expected['min_parameters']}-{expected['max_parameters']}"
            
            # Check required parameters are present
            for req_param in expected['required_parameters']:
                assert req_param in params, f"Missing required parameter: {req_param}"
    
    def test_multi_experiment_balance(self, extractor, bond_taylor_pdf, bond_taylor_expected):
        """Test that multi-experiment papers have balanced parameter extraction."""
        result = extractor.extract_from_file(str(bond_taylor_pdf), detect_multi_experiment=True)
        
        param_counts = [len(exp.get('parameters', {})) for exp in result['experiments']]
        variance = max(param_counts) - min(param_counts)
        
        max_variance = bond_taylor_expected['multi_experiment_balance']['max_variance']
        assert variance <= max_variance, \
            f"Parameter count variance {variance} exceeds max {max_variance}. Counts: {param_counts}"


class TestPatternMatching:
    """Test pattern matching functionality."""
    
    @pytest.fixture
    def extractor(self):
        """Create PDF extractor instance."""
        return PDFExtractor(
            schema_map_path='./mapping/schema_map.yaml',
            patterns_path='./mapping/patterns.yaml',
            synonyms_path='./mapping/synonyms.yaml'
        )
    
    def test_demographics_patterns(self, extractor):
        """Test demographics pattern extraction."""
        test_texts = {
            'age_mean': "Participants had a mean age of 24 years",
            'age_sd': "ages ranged from 18-30 years (M=24, SD=3.2)",
            'gender_distribution': "Thirty-five females and twenty-five males participated",
            'sample_size': "Fifteen participants per group"
        }
        
        for param_name, text in test_texts.items():
            matches = extractor._apply_patterns_to_text(text, param_name, 'test_section')
            assert len(matches) > 0, f"Pattern for {param_name} failed to match: {text}"
    
    def test_rotation_patterns(self, extractor):
        """Test rotation parameter extraction."""
        test_texts = {
            'rotation_magnitude_deg': "learned a 45° rotation",
            'rotation_direction': "counterclockwise visuomotor rotation"
        }
        
        for param_name, text in test_texts.items():
            matches = extractor._apply_patterns_to_text(text, param_name, 'test_section')
            assert len(matches) > 0, f"Pattern for {param_name} failed to match: {text}"
    
    def test_trial_count_patterns(self, extractor):
        """Test trial count extraction."""
        test_texts = [
            "320 adaptation trials",
            "present for 320 trials",
            "The adaptation phase consisted of 320 trials"
        ]
        
        for text in test_texts:
            matches = extractor._apply_patterns_to_text(text, 'adaptation_trials', 'test_section')
            if matches:
                value = matches[0]['value']
                assert value == 320 or value == '320', f"Expected 320, got {value}"


class TestMultiExperimentDetection:
    """Test multi-experiment detection and extraction."""
    
    @pytest.fixture
    def extractor(self):
        """Create PDF extractor instance."""
        return PDFExtractor(
            schema_map_path='./mapping/schema_map.yaml',
            patterns_path='./mapping/patterns.yaml',
            synonyms_path='./mapping/synonyms.yaml'
        )
    
    def test_experiment_header_detection(self, extractor):
        """Test that experiment headers are detected."""
        test_text = """
        Introduction
        This is the introduction text.
        
        Experiment 1
        Methods for experiment 1.
        
        Experiment 2
        Methods for experiment 2.
        
        Results
        Combined results.
        """
        
        experiments = extractor.detect_multiple_experiments(test_text)
        assert experiments['is_multi'] == True
        assert experiments['num_experiments'] == 2
    
    def test_roman_numeral_headers(self, extractor):
        """Test Roman numeral experiment headers."""
        test_text = """
        Experiment I
        First experiment.
        
        Experiment II
        Second experiment.
        """
        
        experiments = extractor.detect_multiple_experiments(test_text)
        assert experiments['is_multi'] == True
        assert experiments['num_experiments'] == 2
    
    def test_written_number_headers(self, extractor):
        """Test written number experiment headers."""
        test_text = """
        Experiment One
        First experiment.
        
        Experiment Two
        Second experiment.
        """
        
        experiments = extractor.detect_multiple_experiments(test_text)
        assert experiments['is_multi'] == True
        assert experiments['num_experiments'] == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
