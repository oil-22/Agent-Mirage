import gzip,json,pathlib,subprocess,tarfile,time
root=pathlib.Path('/data/researcher/attention-audit-20261031');out=root/'inputs'
rows=[json.loads(x) for x in gzip.open(root/'members.jsonl.gz','rt')];byname={x[0]:x for x in rows}
links={x[0]:x[3] for x in rows if '/_embedded-input-images/' in x[0] and x[2]=='1'}
selected=set(links.values())
while True:
    more={byname[n][3] for n in selected if byname[n][2]=='1'}
    if more<=selected:break
    selected.update(more)
proc=subprocess.Popen(['pigz','-dc','/data/researcher/Agent-Mirage-Archive-20261029/Agent-Mirage-20261029.tar.gz'],stdout=subprocess.PIPE)
started=time.time();done=0
with tarfile.open(fileobj=proc.stdout,mode='r|') as tar:
    for m in tar:
        if m.name not in selected or not m.isfile():continue
        p=pathlib.PurePosixPath(m.name)
        assert not p.is_absolute() and '..' not in p.parts
        target=out/p;target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            with tar.extractfile(m) as f,target.open('wb') as g:
                while b:=f.read(1024*1024):g.write(b)
        done+=1
        if done==sum(byname[n][2]=='0' for n in selected):break
proc.terminate();proc.wait()
def resolve(n):
    r=byname[n]
    if r[2]=='1':return resolve(r[3])
    return out/n
for n,s in links.items():
    p=out/n;p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():p.hardlink_to(resolve(s))
(root/'image-link-restore.json').write_text(json.dumps({'links':len(links),'targets':done,'seconds':round(time.time()-started),'complete':True}))
