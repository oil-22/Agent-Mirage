import gzip,json,os,pathlib,subprocess,tarfile,time
root=pathlib.Path('/data/researcher/attention-audit-20261031');out=root/'propagation'
rows=[json.loads(s) for s in gzip.open(root/'members.jsonl.gz','rt')];byname={x[0]:x for x in rows}
selected={n for n,size,typ,link in rows if '/qwen27-propagation-20261020/' in n and n.endswith('.json')}
while True:
    more={byname[n][3] for n in selected if byname[n][2]=='1'}
    if more<=selected:break
    selected.update(more)
proc=subprocess.Popen(['pigz','-dc','/data/researcher/Agent-Mirage-Archive-20261029/Agent-Mirage-20261029.tar.gz'],stdout=subprocess.PIPE)
target_count=sum(byname[n][2]=='0' for n in selected);done=0;started=time.time()
with tarfile.open(fileobj=proc.stdout,mode='r|') as tar:
    for m in tar:
        if m.name not in selected or not m.isfile():continue
        p=pathlib.PurePosixPath(m.name);assert not p.is_absolute() and '..' not in p.parts
        target=out/p;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(tar.extractfile(m).read());done+=1
        if done==target_count:break
proc.terminate();proc.wait()
def resolve(n):
    if byname[n][2]=='1':return resolve(byname[n][3])
    return out/n
for n in selected:
    if byname[n][2]=='1':
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True)
        if not p.exists():os.link(resolve(n),p)
(root/'propagation-restored.json').write_text(json.dumps({'regular_files':done,'selected':len(selected),'seconds':round(time.time()-started)}))
