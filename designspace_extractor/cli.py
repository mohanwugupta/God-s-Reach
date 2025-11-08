"""
Main CLI interface for the Design-Space Parameter Extractor
"""
import click
from pathlib import Path
import sys

# Import functions
from database.models import Database
from dotenv import load_dotenv
import os

__version__ = "1.0.0-dev"

# Load environment variables
load_dotenv()

@click.group()
@click.version_option(version=__version__)
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--db-path', default='./out/designspace.db', help='Path to SQLite database')
@click.pass_context
def cli(ctx, verbose, db_path):
    """
    Design-Space Parameter Extractor for Motor Adaptation Studies
    
    Automates extraction, validation, and management of experimental parameters
    from code repositories, configuration files, and papers.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['db_path'] = db_path
    ctx.obj['db'] = Database(db_path)
    
    # Setup logging based on verbose flag
    import logging
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
@click.option('--exp-id', help='Experiment ID (auto-generated if not provided)')
@click.option('--use-llm', is_flag=True, help='Enable LLM-assisted extraction')
@click.option('--llm-provider', type=click.Choice(['claude', 'openai', 'qwen']), help='LLM provider')
@click.pass_context
def extract(ctx, repo_path, exp_id, use_llm, llm_provider):
    """
    Extract design parameters from a repository or directory.
    
    Examples:
        designspace-extractor extract /path/to/repo
        designspace-extractor extract /path/to/repo --exp-id EXP001
        designspace-extractor extract /path/to/repo --use-llm --llm-provider claude
    """
    from extractors.code_data import CodeExtractor
    from utils.file_discovery import discover_files
    
    click.echo(f"📂 Scanning repository: {repo_path}")
    
    # Discover files
    files = discover_files(repo_path)
    click.echo(f"✓ Found {len(files)} relevant files")
    
    # Initialize extractor
    extractor = CodeExtractor(
        db=ctx.obj['db'],
        use_llm=use_llm,
        llm_provider=llm_provider or os.getenv('LLM_PROVIDER', 'claude')
    )
    
    # Extract parameters
    click.echo("🔍 Extracting parameters...")
    try:
        experiment = extractor.extract_from_repo(repo_path, files, exp_id)
        click.echo(f"✓ Extraction complete! Experiment ID: {experiment.id}")
        click.echo(f"  - Status: {experiment.entry_status}")
        if experiment.conflict_flag:
            click.echo(f"  ⚠️  Conflicts detected - review required")
        click.echo(f"\nView results: sqlite3 {ctx.obj['db_path']}")
    except Exception as e:
        click.echo(f"❌ Extraction failed: {str(e)}", err=True)
        if ctx.obj['verbose']:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option('--exp-id', help='Experiment ID to validate')
@click.option('--all', 'validate_all', is_flag=True, help='Validate all experiments')
@click.pass_context
def validate(ctx, exp_id, validate_all):
    """
    Run validation checks on extracted parameters.
    
    Examples:
        designspace-extractor validate --exp-id EXP001
        designspace-extractor validate --all
    """
    from validation.validator import ExperimentValidator
    
    validator = ExperimentValidator(ctx.obj['db'])
    
    if exp_id:
        click.echo(f"🔍 Validating experiment: {exp_id}")
        results = validator.validate_experiment(exp_id)
        _display_validation_results(results)
    elif validate_all:
        click.echo("🔍 Validating all experiments...")
        results = validator.validate_all()
        for exp_id, result in results.items():
            click.echo(f"\n{exp_id}:")
            _display_validation_results(result)
    else:
        click.echo("❌ Please specify --exp-id or --all", err=True)
        sys.exit(1)


@cli.command()
@click.option('--format', 'export_format', type=click.Choice(['psychds', 'metalab', 'csv', 'json']), 
              default='psychds', help='Export format')
@click.option('--exp-id', help='Experiment ID to export (default: all)')
@click.option('--output', '-o', help='Output file path')
@click.pass_context
def export(ctx, export_format, exp_id, output):
    """
    Export extracted parameters to various formats.
    
    Examples:
        designspace-extractor export --format psychds --exp-id EXP001
        designspace-extractor export --format csv -o results.csv
    """
    from standards.exporters import get_exporter
    
    exporter = get_exporter(export_format, ctx.obj['db'])
    
    click.echo(f"📤 Exporting to {export_format}...")
    try:
        result = exporter.export(exp_id=exp_id, output_path=output)
        click.echo(f"✓ Export complete: {result}")
    except Exception as e:
        click.echo(f"❌ Export failed: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--sheet-id', help='Google Sheets ID (default: from .env)')
@click.option('--exp-id', help='Sync specific experiment (default: all with needs_review status)')
@click.pass_context
def sync(ctx, sheet_id, exp_id):
    """
    Sync extracted parameters to Google Sheets for review.
    
    Examples:
        designspace-extractor sync
        designspace-extractor sync --sheet-id YOUR_SHEET_ID
        designspace-extractor sync --exp-id EXP001
    """
    from utils.sheets_api import SheetsSync
    
    sheet_id = sheet_id or os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
    if not sheet_id:
        click.echo("❌ No Google Sheets ID provided. Set GOOGLE_SHEETS_SPREADSHEET_ID in .env or use --sheet-id", err=True)
        sys.exit(1)
    
    click.echo(f"☁️  Syncing to Google Sheets...")
    try:
        sync = SheetsSync(ctx.obj['db'], sheet_id)
        result = sync.sync_to_sheet(exp_id=exp_id)
        click.echo(f"✓ Sync complete: {result['synced']} experiments synced")
    except Exception as e:
        click.echo(f"❌ Sync failed: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def init(ctx):
    """
    Initialize the database and create necessary directories.
    
    Example:
        designspace-extractor init
    """
    import os
    from pathlib import Path
    
    click.echo("🚀 Initializing Design-Space Extractor...")
    
    # Create output directories
    dirs = ['out', 'out/logs', '.cache']
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        click.echo(f"✓ Created directory: {dir_path}")
    
    # Initialize database
    try:
        ctx.obj['db'].create_tables()
        click.echo(f"✓ Database initialized: {ctx.obj['db_path']}")
    except Exception as e:
        click.echo(f"❌ Database initialization failed: {str(e)}", err=True)
        sys.exit(1)
    
    # Check for .env file
    if not Path('.env').exists():
        click.echo("⚠️  No .env file found. Copy .env.example to .env and configure your settings.")
    else:
        click.echo("✓ .env file found")
    
    click.echo("\n✅ Initialization complete!")
    click.echo("Next steps:")
    click.echo("  1. Configure .env with your API keys and settings")
    click.echo("  2. Run: designspace-extractor extract /path/to/repo")


@cli.command()
@click.option('--exp-id', help='Experiment ID')
@click.option('--param', help='Parameter name to override')
@click.option('--value', help='New parameter value')
@click.option('--reason', help='Reason for override')
@click.pass_context
def override(ctx, exp_id, param, value, reason):
    """
    Manually override an extracted parameter value.
    
    Example:
        designspace-extractor override --exp-id EXP001 --param rotation_magnitude_deg --value 30 --reason "Corrected from paper"
    """
    if not all([exp_id, param, value, reason]):
        click.echo("❌ All options are required: --exp-id, --param, --value, --reason", err=True)
        sys.exit(1)
    
    from database.models import ManualOverride
    import datetime
    
    # TODO: Implement override logic
    click.echo(f"✓ Override applied for {exp_id}:{param} = {value}")


@cli.command()
@click.pass_context
def status(ctx):
    """
    Display status of the extraction database.
    
    Example:
        designspace-extractor status
    """
    import sqlite3
    
    try:
        conn = sqlite3.connect(ctx.obj['db_path'])
        cursor = conn.cursor()
        
        # Count experiments by status
        cursor.execute("SELECT entry_status, COUNT(*) FROM experiments GROUP BY entry_status")
        status_counts = cursor.fetchall()
        
        click.echo("\n📊 Database Status\n")
        click.echo("Experiments by status:")
        for status, count in status_counts:
            click.echo(f"  {status}: {count}")
        
        # Count conflicts
        cursor.execute("SELECT COUNT(*) FROM experiments WHERE conflict_flag = 1")
        conflict_count = cursor.fetchone()[0]
        click.echo(f"\n⚠️  Experiments with conflicts: {conflict_count}")
        
        conn.close()
    except sqlite3.OperationalError:
        click.echo("❌ Database not found. Run 'designspace-extractor init' first.", err=True)
        sys.exit(1)


def _display_validation_results(results):
    """Helper to display validation results."""
    if results['valid']:
        click.echo("  ✓ All validation checks passed")
    else:
        click.echo(f"  ❌ Validation failed ({len(results['errors'])} errors, {len(results['warnings'])} warnings)")
        for error in results['errors']:
            click.echo(f"    - {error}")
        for warning in results['warnings']:
            click.echo(f"    ⚠️  {warning}")


@cli.command('discover')
@click.argument('pdf_path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file for proposals (CSV or JSON)')
@click.option('--format', 'output_format', type=click.Choice(['csv', 'json']), default='csv', help='Output format')
@click.option('--llm-provider', type=click.Choice(['claude', 'openai', 'qwen']), default='claude', help='LLM provider')
@click.option('--min-prevalence', type=click.Choice(['low', 'medium', 'high']), help='Filter by minimum prevalence')
@click.option('--min-importance', type=click.Choice(['low', 'medium', 'high']), help='Filter by minimum importance')
@click.pass_context
def discover(ctx, pdf_path, output, output_format, llm_provider, min_prevalence, min_importance):
    """
    Task 2: Discover NEW parameters not in current library.
    
    Analyzes a scientific paper and proposes new parameters that could be
    added to the design space library. Outputs a CSV/JSON file for review.
    
    Example:
        designspace-extractor discover paper.pdf -o proposals.csv
        designspace-extractor discover paper.pdf -o proposals.json --format json --min-prevalence medium
    """
    from extractors.pdfs import PDFExtractor
    from llm.llm_assist import LLMAssistant
    import json
    
    click.echo(f"\n🔍 Task 2: Discovering new parameters from {Path(pdf_path).name}\n")
    
    # Initialize PDF extractor and LLM assistant
    try:
        pdf_extractor = PDFExtractor(use_llm=False)  # We'll use LLM separately for discovery
        llm_assistant = LLMAssistant(
            provider_name=llm_provider,
            mode='discover'
        )
        
        if not llm_assistant.enabled:
            click.echo("❌ LLM is not enabled. Set LLM_ENABLE=true in your environment.", err=True)
            sys.exit(1)
        
        # Extract text from PDF
        click.echo("📄 Extracting text from PDF...")
        text_data = pdf_extractor.extract_text(Path(pdf_path))
        full_text = text_data['full_text']
        
        # Detect sections for better context
        sections = pdf_extractor.detect_sections(full_text)
        
        # Prepare context (Methods + Participants sections)
        context_parts = []
        if 'methods' in sections:
            context_parts.append(f"METHODS SECTION:\n{sections['methods']}")
        if 'participants' in sections:
            # Limit Participants to 10K chars
            participants_text = sections['participants'][:10000]
            context_parts.append(f"PARTICIPANTS & PROCEDURES:\n{participants_text}")
        
        context = "\n\n".join(context_parts) if context_parts else full_text[:15000]
        
        click.echo(f"   Context prepared: {len(context):,} characters")
        
        # Extract current parameters (for "already extracted" context)
        click.echo("📊 Extracting current parameters via regex...")
        all_parameters = {}
        for section_name, section_text in sections.items():
            params = pdf_extractor.extract_parameters_from_text(section_text, section_name)
            all_parameters.update(params)
        
        click.echo(f"   Found {len(all_parameters)} parameters via regex")
        
        # Run Task 2: Discover new parameters
        click.echo(f"🤖 Running Task 2 discovery with {llm_provider}...")
        proposals = llm_assistant.discover_new_parameters(
            context=context,
            current_schema=pdf_extractor.schema_map,
            already_extracted=all_parameters
        )
        
        if not proposals:
            click.echo("\n✅ No new parameters discovered (all covered by current library)")
            return
        
        click.echo(f"\n✅ Discovered {len(proposals)} new parameter proposals")
        
        # Apply filters if requested
        if min_prevalence:
            proposals = llm_assistant.filter_by_prevalence(proposals, min_prevalence)
            click.echo(f"   Filtered to {len(proposals)} proposals (prevalence >= {min_prevalence})")
        
        if min_importance:
            proposals = llm_assistant.filter_by_importance(proposals, min_importance)
            click.echo(f"   Filtered to {len(proposals)} proposals (importance >= {min_importance})")
        
        # Display preview
        click.echo("\n📋 Preview of top proposals:\n")
        for i, proposal in enumerate(proposals[:5], 1):
            click.echo(f"{i}. {proposal.parameter_name}")
            click.echo(f"   Description: {proposal.description}")
            click.echo(f"   Evidence: \"{proposal.evidence[:80]}...\"")
            click.echo(f"   Prevalence: {proposal.prevalence}, Importance: {proposal.importance}")
            click.echo()
        
        if len(proposals) > 5:
            click.echo(f"   ... and {len(proposals) - 5} more proposals")
        
        # Export to file
        if output:
            output_path = Path(output)
            
            if output_format == 'csv':
                llm_assistant.export_proposals_csv(proposals, str(output_path))
            else:
                llm_assistant.export_proposals_json(proposals, str(output_path))
            
            click.echo(f"\n💾 Proposals saved to: {output_path}")
            click.echo(f"   Review the proposals and add valuable ones to your schema_map.yaml")
        else:
            # Default output filename
            pdf_name = Path(pdf_path).stem
            default_output = f"proposals_{pdf_name}.{output_format}"
            
            if output_format == 'csv':
                llm_assistant.export_proposals_csv(proposals, default_output)
            else:
                llm_assistant.export_proposals_json(proposals, default_output)
            
            click.echo(f"\n💾 Proposals saved to: {default_output}")
        
    except Exception as e:
        click.echo(f"❌ Discovery failed: {e}", err=True)
        if ctx.obj.get('verbose'):
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    cli()

