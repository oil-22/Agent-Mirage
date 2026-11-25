import collections,gzip,json,pathlib,re
root=pathlib.Path('/data/researcher/attention-audit-20261031')
rows=[json.loads(x) for x in gzip.open(root/'members.jsonl.gz','rt')]
print('POSSIBLE MASK CODE')
for n,size,typ,link in rows:
 if n.endswith('.py') and any(s in n.lower() for s in ['injection','intervention','mask','buttons','crossmodel']):print(n,size,typ,link)
print('REQUEST EXAMPLES')
inputs=root/'inputs'
ds=json.loads((root/'trajectories.json').read_text())
for kind in ['control','blank_replace','buttons_only']:
 r=next(r for r in ds if r['trajectory'].endswith('/'+kind) and '/OSWorld' in r['trajectory'])
 d=inputs/r['trajectory']/'requests'
 print(r)
 for step in r['steps'][:3]:
  p=d/f'{step:03d}.json';j=json.loads(p.read_text());print(str(p),list(j),str(j)[:600])
  rp=d/f'{step:03d}-response.json'
  if rp.exists():print('RESPONSE',str(json.loads(rp.read_text()))[:2000])
print('SHARED CORPUS FILES')
for p in inputs.glob('attention-experiment/_shared/**/*'):
 if p.is_file() and p.suffix=='.json':print(str(p.relative_to(inputs)),p.stat().st_size)
