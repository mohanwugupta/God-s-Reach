"""Debug script to check perturbation_schedule extraction"""
import re
from pathlib import Path
from extractors.pdfs import PDFExtractor

# Initialize extractor
extractor = PDFExtractor()

# Find Taylor 2014 PDF
papers_dir = Path(r"c:\Users\sheik\Box\ResearchProjects\God-s-Reach\papers")
taylor_pdf = papers_dir / "3023.full.pdf"

print(f"Extracting from: {taylor_pdf}")
print("-" * 80)

# Extract text
text_result = extractor.extract_text(taylor_pdf)
text = text_result['full_text']

# Load patterns
import yaml
patterns_file = Path("mapping/patterns.yaml")
patterns_data = yaml.safe_load(open(patterns_file))
pdf_patterns = patterns_data.get('pdf', {})

# Check perturbation_schedule patterns
sched_patterns = pdf_patterns.get('perturbation_schedule', [])
print(f"\nFound {len(sched_patterns)} perturbation_schedule patterns")
print("\nTesting patterns:")
print("=" * 80)

for i, pattern in enumerate(sched_patterns):
    print(f"\nPattern {i+1}: {pattern[:80]}...")
    matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
    print(f"  Matches: {len(matches)}")
    
    for j, match in enumerate(matches[:3]):  # Show first 3 matches
        value = match.group(1) if match.groups() else match.group(0)
        context_start = max(0, match.start() - 50)
        context_end = min(len(text), match.end() + 50)
        context = text[context_start:context_end]
        print(f"    Match {j+1}: '{value}'")
        print(f"    Context: ...{context}...")
        print()

# Also check schedule_blocking for comparison
print("\n" + "=" * 80)
print("SCHEDULE_BLOCKING patterns:")
print("=" * 80)
blocking_patterns = pdf_patterns.get('schedule_blocking', [])
for i, pattern in enumerate(blocking_patterns):
    print(f"\nPattern {i+1}: {pattern}")
    matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
    print(f"  Matches: {len(matches)}")
    
    for j, match in enumerate(matches[:3]):
        value = match.group(1) if match.groups() else match.group(0)
        context_start = max(0, match.start() - 50)
        context_end = min(len(text), match.end() + 50)
        context = text[context_start:context_end]
        print(f"    Match {j+1}: '{value}'")
        print(f"    Context: ...{context}...")
        print()

# Now run full extraction and see what we get
print("\n" + "=" * 80)
print("FULL EXTRACTION RESULT:")
print("=" * 80)
result = extractor.extract_from_file(taylor_pdf)
if 'parameters' in result:
    params = result['parameters']
    if 'perturbation_schedule' in params:
        ps = params['perturbation_schedule']
        print(f"\nperturbation_schedule: {ps.get('value')}")
        print(f"  Confidence: {ps.get('confidence')}")
        print(f"  Source: {ps.get('source_name')}")
        print(f"  Method: {ps.get('method')}")
        print(f"  Evidence: {ps.get('evidence', '')[:100]}")
    else:
        print("\nperturbation_schedule: NOT EXTRACTED")
else:
    print("\nNo parameters found!")
