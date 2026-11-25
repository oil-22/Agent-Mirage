import gzip,json,os,pathlib,re
root=pathlib.Path('/data/researcher/attention-audit-20261031');out=root/'inputs'
rows=[json.loads(x) for x in gzip.open(root/'members.jsonl.gz','rt')];byname={r[0]:r for r in rows}
def resolve(n):
    r=byname[n]
    if r[2]=='1':return resolve(r[3])
    return out/n
linked=0;missing=[]
for n,size,typ,link in rows:
    if typ!='1':continue
    if '/_embedded-input-images/' not in n and not (n.startswith('mirage-trace/') and any(s in n for s in ['/Qwen3.5-9B/','/Qwen3.8-27B/']) and re.search(r'/requests/\d+(?:-response)?\.json$',n)):continue
    p=out/n;s=resolve(link)
    if p.exists():continue
    if s.exists():
        p.parent.mkdir(parents=True,exist_ok=True);os.link(s,p);linked+=1
    else:missing.append([n,str(s)])
(root/'restored-links-audit.json').write_text(json.dumps({'linked':linked,'missing':missing},indent=2))
print('linked',linked,'missing',len(missing),'images_missing',sum('/_embedded-input-images/' in x[0] for x in missing))
