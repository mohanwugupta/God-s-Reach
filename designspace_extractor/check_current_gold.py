#!/usr/bin/env python3
"""Check current gold standard sheet contents."""
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
print(f"Headers: {reader.fieldnames}\n")

print("Rows with study_id:")
for i, row in enumerate(rows):
    study_id = row.get('study_id', '').strip()
    if study_id:
        print(f"\nRow {i+1}: {study_id}")
        # Show first few populated fields
        count = 0
        for key, val in row.items():
            if val and val.strip() and key != 'study_id' and count < 5:
                print(f"  {key}: {val[:50]}...")
                count += 1
