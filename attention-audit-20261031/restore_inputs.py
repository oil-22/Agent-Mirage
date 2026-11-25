import gzip,json,pathlib,re,subprocess,tarfile,time
root=pathlib.Path('/data/researcher/attention-audit-20261031')
out=root/'inputs'
out.mkdir(exist_ok=True)
rows=[json.loads(x) for x in gzip.open(root/'members.jsonl.gz','rt')]
selected={r[0] for r in rows if r[0].startswith('mirage-trace/') and any(s in r[0] for s in ['/Qwen3.5-9B/','/Qwen3.8-27B/']) and re.search(r'/requests/\d+(?:-response)?\.json$',r[0])}
selected.update(r[0] for r in rows if '/_embedded-input-images/' in r[0])
selected.update(r[0] for r in rows if '/crossmodel-injection-attention-20261025/' in r[0] and r[0].endswith('.json') and any(s in r[0] for s in ['frozen-source-inputs','input-metadata','source-request']))
selected.update(r[0] for r in rows if '/agent-mirage-mechanism-scale-20261020/' in r[0] and r[0].endswith('.json') and any(s in r[0] for s in ['/export-full-v1/runs/','/corpus/','/full-corpus-v1/']) and r[1]<2_000_000)
proc=subprocess.Popen(['pigz','-dc','/data/researcher/Agent-Mirage-Archive-20261029/Agent-Mirage-20261029.tar.gz'],stdout=subprocess.PIPE)
done=0;started=time.time();links={}
with tarfile.open(fileobj=proc.stdout,mode='r|') as tar:
    for m in tar:
        if m.name not in selected:continue
        p=pathlib.PurePosixPath(m.name)
        if p.is_absolute() or '..' in p.parts:raise ValueError(m.name)
        target=out/p;target.parent.mkdir(parents=True,exist_ok=True)
        if m.isfile():
            with tar.extractfile(m) as f,target.open('wb') as g:
                while b:=f.read(4*1024*1024):g.write(b)
        elif m.islnk():links[m.name]=m.linkname
        done+=1
        if done%5000==0:
            (root/'restore-progress.json').write_text(json.dumps({'selected':len(selected),'restored':done,'seconds':round(time.time()-started),'current':m.name}))
for name,source in links.items():
    p=out/name;s=out/source
    if s.exists():p.hardlink_to(s)
    else:print('unresolved link',name,source,flush=True)
rc=proc.wait()
(root/'restore-result.json').write_text(json.dumps({'complete':rc==0,'selected':len(selected),'restored':done,'seconds':round(time.time()-started)}))
print('complete',done,flush=True)
