import json
import pathlib
root = pathlib.Path('/data/researcher/attention-audit-20261031/extracted/attention-experiment')
out = {}
for p in root.rglob('*'):
    if not p.is_file():
        continue
    rel = str(p.relative_to(root))
    if 'crossmodel-injection-attention' in rel and (p.suffix == '.md' or p.name in ['attention-summary.json','summary-complete.json','campaign-status-latest.json','glm-attention-plan.json','glm-scale-frozen-plan.json','qwen27-analysis-completed-current.json','summary.json']):
        if p.stat().st_size < 4_000_000:
            out[rel] = p.read_text()
pathlib.Path('/data/researcher/attention-audit-20261031/evidence-bundle.json').write_text(json.dumps(out,ensure_ascii=False))
print('bundled',len(out))
