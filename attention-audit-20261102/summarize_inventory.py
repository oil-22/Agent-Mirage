import collections,gzip,json,pathlib
root=pathlib.Path('/data/researcher/attention-audit-20261031');inputs=root/'inputs'
for pattern in ['attention-experiment/_shared/**/frozen-source-inputs/**/*.json','attention-experiment/_shared/**/corpus/**/summary_info.json','attention-experiment/_shared/**/export-full-v1/runs/**/*.json']:
 pp=list(inputs.glob(pattern));print('PATTERN',pattern,'count',len(pp))
 for p in pp[:2]:
  d=json.loads(p.read_text());print(str(p.relative_to(inputs)),str(d)[:3500])
rows=[json.loads(x) for x in gzip.open(root/'members.jsonl.gz','rt')]
print('CODE COUNT',collections.Counter(pathlib.PurePosixPath(n).suffix for n,s,t,l in rows if t=='0').most_common(15))
print('METADATA MEMBERS')
pp=[r for r in rows if '/crossmodel-injection-attention-20261025/' in r[0] and any(w in r[0] for w in ['frozen-source-input','source-request','input-metadata','manifest'])]
for r in pp[:12]:print(r)
print('CORPUS SUMMARY AGGREGATE')
pp=list(inputs.glob('attention-experiment/_shared/**/corpus/**/summary_info.json'))
print('summaries',len(pp))
print(collections.Counter(str(json.loads(p.read_text()).get('benchmark',json.loads(p.read_text()).get('app','?'))) for p in pp))
