import collections,json,pathlib
r=pathlib.Path('/data/researcher/attention-audit-20261031/inputs')
summaries=list(r.glob('attention-experiment/_shared/**/corpus/**/summary_info.json'))
print('conditions',collections.Counter(json.loads(p.read_text()).get('condition') for p in summaries))
for p in summaries[:1]:
 f=next(q for q in p.parent.glob('*.json') if q.stem.isdigit())
 d=json.loads(f.read_text());print('CORPUS ROW',f,list(d));print(json.dumps(d,ensure_ascii=False)[:9000])
pp=list(r.glob('attention-experiment/_shared/**/frozen-source-inputs*/*.json'))
print('frozen',len(pp))
for p in pp[:1]:print('FROZEN ROW',p,p.read_text()[:6000])
for p in summaries:
 d=json.loads(p.read_text())
 if d['condition']=='control':print('CONTROL CORPUS',p.parent.name,d)
