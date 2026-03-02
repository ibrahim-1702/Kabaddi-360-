"""
Generate context.json from results.json for a specific session
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from llm_feedback import generate_context, load_raw_scores, save_context

session_id = '039ae972-178d-4520-86ff-b7c9b02d5d6b'
results_path = Path('data/results') / session_id / 'results.json'
context_path = Path('data/results') / session_id / 'context.json'

print(f'Loading results from: {results_path}')
results = load_raw_scores(results_path)

print('Generating context...')
context = generate_context(results)

print(f'Saving context to: {context_path}')
save_context(context, context_path)

print(f'\n✅ Context generated successfully!')
print(f'📄 File: {context_path}')
print(f'📊 Size: {context_path.stat().st_size} bytes')
