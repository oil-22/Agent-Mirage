import collections,gzip,json,pathlib,re
root=pathlib.Path('/data/researcher/attention-audit-20261031')
groups=collections.defaultdict(list)
for line in gzip.open(root/'members.jsonl.gz','rt'):
    name,size,typ,link=json.loads(line)
    if not name.startswith('mirage-trace/') or not re.search(r'/requests/\d+\.json$',name):continue
    if not any(s in name for s in ['/Qwen3.5-9B/','/Qwen3.8-27B/']):continue
    groups[name.rsplit('/requests/',1)[0]].append(name)
out=[]
for key,names in sorted(groups.items()):
    out.append({'trajectory':key,'requests':len(names),'steps':sorted(int(pathlib.PurePosixPath(n).stem) for n in names)})
(root/'trajectories.json').write_text(json.dumps(out,indent=2))
counts=collections.Counter('/'.join(x['trajectory'].split('/')[:4]) for x in out)
print(json.dumps(counts,indent=2))
print('baseline-like')
for row in out:
    if any(s in row['trajectory'].lower() for s in ['baseline','control','native','clean']):print(row['trajectory'],row['requests'])
