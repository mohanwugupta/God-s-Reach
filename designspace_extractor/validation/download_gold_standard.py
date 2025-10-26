#!/usr/bin/env python3
"""
Download gold standard from Google Sheets to local CSV file.
Run this on a machine with internet access (e.g., login node) before running validation on compute nodes.
"""
import urllib.request
import sys
import os
from pathlib import Path

def download_gold_standard(spreadsheet_id, gid, output_file):
    """Download gold standard CSV from Google Sheets."""
    csv_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
    
    print(f"📥 Downloading gold standard from Google Sheets...")
    print(f"   URL: {csv_url}")
    print(f"   Output: {output_file}")
    
    try:
        with urllib.request.urlopen(csv_url) as response:
            content = response.read().decode('utf-8')
        
        # Create output directory if needed
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Count entries
        lines = content.splitlines()
        num_entries = len(lines) - 1  # Subtract header
        
        print(f"✅ Downloaded {num_entries} entries")
        print(f"   Saved to: {output_file}")
        print(f"\n💡 You can now use this file for offline validation:")
        print(f"   python validation/validator_public.py --local-file {output_file} --results results.json")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR downloading gold standard: {e}")
        print(f"\nTroubleshooting:")
        print(f"  1. Check internet connection")
        print(f"  2. Verify spreadsheet ID: {spreadsheet_id}")
        print(f"  3. Ensure sheet GID is correct: {gid}")
        print(f"  4. Check if spreadsheet is publicly accessible")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Download gold standard from Google Sheets for offline use'
    )
    parser.add_argument(
        '--spreadsheet-id',
        default='1nc34GT31emdpVJw7Vq-1cRI7_TtJ8Tdj',
        help='Google Sheets ID (default: 1nc34GT31emdpVJw7Vq-1cRI7_TtJ8Tdj)'
    )
    parser.add_argument(
        '--gid',
        default='486594143',
        help='Sheet GID (default: 486594143)'
    )
    parser.add_argument(
        '--output',
        default='validation/gold_standard.csv',
        help='Output CSV file path (default: validation/gold_standard.csv)'
    )
    args = parser.parse_args()
    
    success = download_gold_standard(args.spreadsheet_id, args.gid, args.output)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
