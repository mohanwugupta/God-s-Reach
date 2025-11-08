"""
Prompt construction for LLM verification and discovery.

Loads templates from prompts directory and formats them with context.
Consolidates prompt loading and building functionality.
"""
import json
import logging
from pathlib import Path
from string import Template
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class PromptLoader:
    """Load and format prompt templates from files."""
    
    def __init__(self, prompts_dir: Optional[str] = None):
        """
        Initialize prompt loader.
        
        Args:
            prompts_dir: Directory containing prompt templates (default: llm/prompts/)
        """
        if prompts_dir is None:
            # Default to prompts/ subdirectory relative to this file
            current_file = Path(__file__).resolve()
            prompts_dir = current_file.parent / "prompts"
        
        self.prompts_dir = Path(prompts_dir)
        
        if not self.prompts_dir.exists():
            raise FileNotFoundError(f"Prompts directory not found: {self.prompts_dir}")
        
        # Cache loaded templates
        self._cache: Dict[str, Template] = {}
    
    def load_template(self, template_name: str) -> Template:
        """
        Load a prompt template from file.
        
        Args:
            template_name: Name of template file (without .txt extension)
            
        Returns:
            string.Template object for variable substitution
        """
        if template_name in self._cache:
            return self._cache[template_name]
        
        template_path = self.prompts_dir / f"{template_name}.txt"
        
        if not template_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_text = f.read()
        
        template = Template(template_text)
        self._cache[template_name] = template
        
        return template
    
    def format_prompt(self, template_name: str, **kwargs) -> str:
        """
        Load and format a prompt template with variables.
        
        Args:
            template_name: Name of template file (without .txt extension)
            **kwargs: Variables to substitute in template
            
        Returns:
            Formatted prompt string
        """
        template = self.load_template(template_name)
        
        try:
            return template.substitute(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required variable in template '{template_name}': {e}")


class PromptBuilder:
    """Build prompts from templates."""
    
    def __init__(self, prompts_dir: Optional[str] = None):
        """
        Initialize prompt builder.
        
        Args:
            prompts_dir: Directory containing prompt templates (optional)
        """
        self.loader = PromptLoader(prompts_dir)
    
    def build_batch_verification_prompt(self, extracted_params: Dict[str, Any],
                                       context: str, study_type: str,
                                       num_experiments: int) -> str:
        """
        Build batch verification prompt from template.
        
        Args:
            extracted_params: Parameters extracted by deterministic methods
            context: Paper content for verification
            study_type: Type of study (between/within/mixed)
            num_experiments: Number of experiments in paper
            
        Returns:
            Formatted verification prompt
        """
        # Convert params to JSON string
        params_json = json.dumps(extracted_params, indent=2)
        
        # Calculate dynamic context limit based on available content
        context_limit = self._calculate_context_limit('batch', len(context))
        context_truncated = context[:context_limit] if len(context) > context_limit else context
        
        return self.loader.format_prompt(
            'verify_batch',
            extracted_params=params_json,
            context=context_truncated,
            study_type=study_type,
            num_experiments=num_experiments
        )
    
    def build_single_parameter_prompt(self, parameter_name: str, context: str,
                                     description: str = "") -> str:
        """
        Build single parameter inference prompt.
        
        Args:
            parameter_name: Name of parameter to infer
            context: Paper content
            description: Optional parameter description
            
        Returns:
            Formatted single-parameter prompt
        """
        context_limit = self._calculate_context_limit('single', len(context))
        context_truncated = context[:context_limit] if len(context) > context_limit else context
        
        return self.loader.format_prompt(
            'verify_single',
            parameter_name=parameter_name,
            context=context_truncated,
            description=description or "No description available"
        )
    
    def build_missed_params_prompt(self, current_schema: Dict[str, Any],
                                   already_extracted: Dict[str, Any],
                                   context: str) -> str:
        """
        Build Task 1 prompt: Find library parameters that regex missed.
        
        Args:
            current_schema: Current parameter library/schema
            already_extracted: Parameters already extracted by regex
            context: Paper content
            
        Returns:
            Formatted Task 1 prompt
        """
        # Format schema as readable list
        schema_list = []
        for category, params in current_schema.items():
            schema_list.append(f"\n[{category.upper()}]")
            if isinstance(params, dict):
                for param_name, param_info in params.items():
                    desc = param_info.get('description', 'No description') if isinstance(param_info, dict) else 'No description'
                    schema_list.append(f"  - {param_name}: {desc}")
            else:
                schema_list.append(f"  {params}")
        
        schema_text = '\n'.join(schema_list)
        
        # Format already extracted
        if already_extracted:
            extracted_text = '\n'.join(f"- {k}: {v.get('value', v) if isinstance(v, dict) else v}" 
                                      for k, v in already_extracted.items())
        else:
            extracted_text = "None"
        
        context_limit = self._calculate_context_limit('batch', len(context))
        context_truncated = context[:context_limit] if len(context) > context_limit else context
        
        return self.loader.format_prompt(
            'task1_missed_params',
            current_schema=schema_text,
            already_extracted=extracted_text,
            context=context_truncated
        )
    
    def build_new_params_prompt(self, current_schema: Dict[str, Any],
                                already_extracted: Optional[Dict[str, Any]],
                                context: str) -> str:
        """
        Build Task 2 prompt: Discover entirely NEW parameters not in library.
        
        Args:
            current_schema: Current parameter library/schema
            already_extracted: Parameters already extracted (to avoid duplicates)
            context: Paper content
            
        Returns:
            Formatted Task 2 prompt
        """
        # Format schema as readable list
        schema_list = []
        for category, params in current_schema.items():
            schema_list.append(f"\n[{category.upper()}]")
            if isinstance(params, dict):
                for param_name in params.keys():
                    schema_list.append(f"  - {param_name}")
            else:
                schema_list.append(f"  {params}")
        
        schema_text = '\n'.join(schema_list)
        
        # Format already extracted
        if already_extracted:
            extracted_text = '\n'.join(f"- {k}: {v.get('value', v) if isinstance(v, dict) else v}" 
                                      for k, v in already_extracted.items())
        else:
            extracted_text = "None"
        
        context_limit = self._calculate_context_limit('discovery', len(context))
        context_truncated = context[:context_limit] if len(context) > context_limit else context
        
        return self.loader.format_prompt(
            'task2_new_params',
            current_schema=schema_text,
            already_extracted=extracted_text,
            context=context_truncated
        )
    
    def build_discovery_prompt(self, context: str, study_type: str,
                               num_experiments: int,
                               already_extracted: Optional[Dict[str, Any]] = None) -> str:
        """
        Build parameter discovery prompt from template (legacy - uses old discovery.txt).
        
        DEPRECATED: Use build_new_params_prompt() for Task 2 instead.
        
        Args:
            context: Paper content
            study_type: Type of study
            num_experiments: Number of experiments
            already_extracted: Parameters already extracted (to avoid duplicates)
            
        Returns:
            Formatted discovery prompt
        """
        # Prepare already_extracted context
        if already_extracted:
            extracted_list = '\n'.join(f"- {k}: {v}" for k, v in already_extracted.items())
        else:
            extracted_list = "None"
        
        context_limit = self._calculate_context_limit('discovery', len(context))
        context_truncated = context[:context_limit] if len(context) > context_limit else context
        
        return self.loader.format_prompt(
            'discovery',
            context=context_truncated,
            study_type=study_type,
            num_experiments=num_experiments,
            already_extracted=extracted_list
        )
    
    def _calculate_context_limit(self, context_type: str, total_available: int) -> int:
        """
        Calculate appropriate context limit based on type and available content.
        
        Args:
            context_type: 'batch', 'single', 'discovery', 'task1', or 'task2'
            total_available: Total characters available in context
            
        Returns:
            Recommended character limit
        """
        base_limits = {
            'batch': 12000,     # Methods + key verification
            'single': 8000,     # Focused parameter inference  
            'discovery': 15000, # Broad parameter discovery (legacy)
            'task1': 12000,     # Task 1: Find missed library params
            'task2': 15000      # Task 2: Discover new params
        }
        
        # Use up to 80% of context window, but not more than available
        max_safe = int(32768 * 0.8 * 3.75)  # ~98K chars (80% of 32K tokens)
        recommended = min(base_limits.get(context_type, 12000), max_safe, total_available)
        
        return max(recommended, 1000)  # Minimum 1000 chars
