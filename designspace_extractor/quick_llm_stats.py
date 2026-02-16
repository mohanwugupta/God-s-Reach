import json

# Load results with utf-8 encoding
with open('batch_processing_results.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

total = 0
llm = 0

for paper in results:
    if not paper.get('success'):
        continue
    
    result = paper['extraction_result']
    
    if result.get('is_multi_experiment'):
        for exp in result.get('experiments', []):
            for param_name, param_data in exp.get('parameters', {}).items():
                total += 1
                if param_data.get('method') == 'llm_assisted':
                    llm += 1
    else:
        for param_name, param_data in result.get('parameters', {}).items():
            total += 1
            if param_data.get('method') == 'llm_assisted':
                    llm += 1

regex = total - llm

print(f"\n{'='*50}")
print("LLM CONTRIBUTION ANALYSIS")
print(f"{'='*50}")
print(f"\nTotal parameters extracted: {total}")
print(f"  LLM-assisted: {llm} ({(llm/total)*100:.1f}%)")
print(f"  Regex-based:  {regex} ({(regex/total)*100:.1f}%)")
print(f"\n{'='*50}\n")
