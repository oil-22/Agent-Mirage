import collections,gzip,json,pathlib
root=pathlib.Path('/data/researcher/attention-audit-20261031')
rows=[json.loads(x) for x in gzip.open(root/'members.jsonl.gz','rt')]
print('EXPERIMENT GROUPS')
for k,v in json.loads((root/'scan-result.json').read_text())['groups'].items():
    if any(s in k for s in ['Qwen3.8','Qwen3.5','GLM','_shared']):print(k,v)
print('SELECTED EXAMPLES')
categories={
 'admin':[r for r in rows if r[0].startswith('_admin/')],
 'crossmodel-requests':[r for r in rows if 'crossmodel-injection-attention' in r[0] and any(s in r[0] for s in ['source-request','scale-inputs','frozen-source-inputs'])],
 'qwen-trace':[r for r in rows if r[0].startswith('mirage-trace/Qwen3.5-9B/') and '/requests/' in r[0] and r[0].endswith('.json')],
 'history':[r for r in rows if r[0].startswith('attention-experiment/') and any(s in r[0] for s in ['history-length','position','timing'])],
}
for k,v in categories.items():
    print(k,len(v));print(json.dumps(v[:10],indent=2))
out=root/'inventory-categories.json';out.write_text(json.dumps(categories))
