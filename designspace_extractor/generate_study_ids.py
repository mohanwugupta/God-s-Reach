#!/usr/bin/env python3
"""Generate study_id values for the gold standard based on author+year."""
import urllib.request
import csv
import re

url = 'https://docs.google.com/spreadsheets/d/1nc34GT31emdpVJw7Vq-1cRI7_TtJ8Tdj/export?format=csv&gid=486594143'

with urllib.request.urlopen(url) as response:
    content = response.read().decode('utf-8')

lines = content.splitlines()
reader = csv.DictReader(lines)
rows = list(reader)

print("SUGGESTED study_id VALUES:")
print("="*100)
print("\nCopy these into the 'study_id' column of your Google Sheet:\n")

for i, row in enumerate(rows, 1):
    title = row.get('title', '').strip()
    authors = row.get('authors', '').strip()
    year = row.get('year', '').strip()
    
    if not title or not year:
        print(f"Row {i}: [SKIP - missing title or year]")
        continue
    
    # Extract first author's last name
    if authors:
        # Handle formats like "Taylor, Ivry" or "McDougle, Bond, Taylor"
        first_author = authors.split(',')[0].strip()
        # Handle "et al"
        first_author = first_author.replace(' et al', '').strip()
        # Remove any extra spaces
        first_author = re.sub(r'\s+', '', first_author)
    else:
        # Try to extract from title
        match = re.search(r'^([A-Z][a-z]+)', title)
        first_author = match.group(1) if match else f"Unknown{i}"
    
    # Check if this is an experiment-specific row (has "EXP" in title)
    exp_match = re.search(r'EXP\s*(\d+)', title, re.IGNORECASE)
    if exp_match:
        exp_num = exp_match.group(1)
        study_id = f"{first_author}{year}_EXP{exp_num}"
    else:
        study_id = f"{first_author}{year}"
    
    print(f"Row {i}: {study_id:<30} | {title[:60]}")

print("\n" + "="*100)
print("\nINSTRUCTIONS:")
print("1. Copy the study_id values above")
print("2. Paste them into column A (study_id) of your Google Sheet")
print("3. Re-run the validator")
print("\nNOTE: Some papers may need manual adjustment if there are multiple experiments")
print("      without 'EXP' in the title (e.g., add _EXP1, _EXP2 suffixes manually)")
