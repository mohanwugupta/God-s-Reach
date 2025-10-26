#!/usr/bin/env python3
"""Check gold standard for ANY populated data."""
import urllib.request
import csv

url = 'https://docs.google.com/spreadsheets/d/1nc34GT31emdpVJw7Vq-1cRI7_TtJ8Tdj/export?format=csv&gid=486594143'

print(f"Fetching: {url}\n")

with urllib.request.urlopen(url) as response:
    content = response.read().decode('utf-8')

lines = content.splitlines()
reader = csv.DictReader(lines)

rows = list(reader)
print(f"Found {len(rows)} total rows")
print(f"Headers ({len(reader.fieldnames)} columns): {reader.fieldnames[:15]}...\n")

print("="*100)
print("ALL ROWS WITH ANY DATA:")
print("="*100)

for i, row in enumerate(rows):
    # Check if row has ANY non-empty values
    populated_fields = {k: v for k, v in row.items() if v and v.strip()}
    
    if populated_fields:
        print(f"\nRow {i+1}:")
        for key, val in populated_fields.items():
            print(f"  {key}: {val}")
