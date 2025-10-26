#!/usr/bin/env python3
"""Quick diagnostic to see what's in the gold standard sheet."""
import urllib.request
import csv

spreadsheet_id = "1nc34GT31emdpVJw7Vq-1cRI7_TtJ8Tdj"
gid = "486594143"
csv_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"

print(f"Fetching: {csv_url}\n")

with urllib.request.urlopen(csv_url) as response:
    content = response.read().decode('utf-8')

lines = content.splitlines()
reader = csv.DictReader(lines)

print("Column headers:")
print(reader.fieldnames)
print("\n" + "="*80)

print("\nFirst 5 rows:")
for i, row in enumerate(reader):
    if i >= 5:
        break
    print(f"\nRow {i+1}:")
    for key, val in row.items():
        if val:
            print(f"  {key}: {val}")
