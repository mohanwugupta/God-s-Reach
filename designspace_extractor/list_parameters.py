import json

# Load results
with open('batch_processing_results.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

# Collect all unique parameters
params = set()
for paper in results:
    if paper.get('success'):
        params.update(paper['all_params'])

# Print results
print(f"Total Parameters in Library: {len(params)}\n")
print("="*60)
print("COMPLETE PARAMETER LIBRARY")
print("="*60)
for i, param in enumerate(sorted(params), 1):
    print(f"{i:2d}. {param}")
print("="*60)
