import gzip,json,pathlib
r=pathlib.Path('/data/researcher/attention-audit-20261031');rows=[json.loads(x) for x in gzip.open(r/'members.jsonl.gz','rt')]
pp=[a for a in rows if a[0].startswith('mirage-trace/Qwen3.5-9B/VisualWebArena__buttons_only/')]
print('members',len(pp))
for a in pp[:30]:print(a)
for a in pp:
 if any(s in a[0] for s in ['ledger','injection','002.png','002.json','step_2','step_002']):
  print('MATCH',a)
  if sum(1 for b in pp[:pp.index(a)] if 'MATCH' in b[0])>8:break
  if 'ledger' in a[0]:break
