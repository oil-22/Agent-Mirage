import gzip,hashlib,json,os,pathlib,subprocess,tarfile,time
root=pathlib.Path('/data/researcher/defense-resume-20261102')
out=root/'archive-evidence';out.mkdir(parents=True,exist_ok=True)
idx=pathlib.Path('/data/researcher/attention-audit-20261031/members.jsonl.gz')
rows=[json.loads(s) for s in gzip.open(idx,'rt')];byname={x[0]:x for x in rows}
selected={n for n,size,typ,link in rows if n.startswith('mirage-defence/')}
while True:
    more={byname[n][3] for n in selected if byname[n][2]=='1'}
    if more<=selected:break
    selected.update(more)
(root/'restore-selection.json').write_text(json.dumps(sorted(selected)))
proc=subprocess.Popen(['pigz','-dc','/data/researcher/Agent-Mirage-Archive-20261029/Agent-Mirage-20261029.tar.gz'],stdout=subprocess.PIPE)
target_count=sum(byname[n][2]=='0' for n in selected);done=0;started=time.time();sealed=[]
try:
    with tarfile.open(fileobj=proc.stdout,mode='r|') as tar:
        for m in tar:
            if m.name not in selected or not m.isfile():continue
            p=pathlib.PurePosixPath(m.name);assert not p.is_absolute() and '..' not in p.parts
            target=out/p;target.parent.mkdir(parents=True,exist_ok=True)
            data=tar.extractfile(m).read();target.write_bytes(data);done+=1
            sealed.append({'path':m.name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
            if done%50==0:
                (root/'restore-progress.json').write_text(json.dumps({'restored':done,'selected_regular':target_count,'seconds':round(time.time()-started),'current':m.name}))
            if done==target_count:break
finally:
    proc.terminate();proc.wait()
def resolve(n):
    return resolve(byname[n][3]) if byname[n][2]=='1' else out/n
for n in selected:
    if byname[n][2]=='1':
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True)
        if not p.exists():os.link(resolve(n),p)
(root/'restored-sha256.json').write_text(json.dumps(sealed,indent=2))
(root/'restore-result.json').write_text(json.dumps({'regular_files':done,'expected':target_count,'selected':len(selected),'seconds':round(time.time()-started),'complete':done==target_count}))
print('complete',done,flush=True)
