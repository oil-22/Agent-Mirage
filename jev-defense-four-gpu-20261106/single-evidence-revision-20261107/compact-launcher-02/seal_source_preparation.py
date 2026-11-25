"""Seal only the code preparation; do not construct a run manifest."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
entries = [{'file': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
           for p in sorted(HERE.iterdir()) if p.is_file() and p.name != 'source-preparation-seal.json']
with (HERE / 'source-preparation-seal.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump({'mode': 'code_only_all_run_source_proofs_pending', 'files': entries,
               'model_GPU_GUI_stage_submit_network_calls': 0}, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'files': len(entries),
                  'source_preparation_seal_sha256': hashlib.sha256((HERE / 'source-preparation-seal.json').read_bytes()).hexdigest()}))
