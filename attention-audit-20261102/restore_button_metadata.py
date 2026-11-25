import gzip,json,pathlib,subprocess,tarfile,time,os
r=pathlib.Path('/data/researcher/attention-audit-20261031');out=pathlib.Path('/data/researcher/attention-audit-20261102/native-button-metadata');out.mkdir(parents=True,exist_ok=True)
rows=[json.loads(x) for x in gzip.open(r/'members.jsonl.gz','rt')];by={x[0]:x for x in rows}
selected={n for n,s,t,l in rows if n.startswith('mirage-trace/Qwen3.5-9B/VisualWebArena__buttons_only/') and n.endswith(('model_delivery.jsonl','summary_info.json'))}
while True:
 more={by[n][3] for n in selected if by[n][2]=='1'}
 if more<=selected:break
 selected.update(more)
target={n for n in selected if by[n][2]=='0'};done=set();start=time.time()
proc=subprocess.Popen(['pigz','-dc','/data/researcher/Agent-Mirage-Archive-20261029/Agent-Mirage-20261029.tar.gz'],stdout=subprocess.PIPE)
with tarfile.open(fileobj=proc.stdout,mode='r|') as tar:
 for m in tar:
  if m.name not in target:continue
  p=pathlib.PurePosixPath(m.name);assert not p.is_absolute() and '..' not in p.parts
  f=out/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read());done.add(m.name)
  (out/'progress.json').write_text(json.dumps({'done':len(done),'target':len(target),'seconds':round(time.time()-start)}))
  if done==target:break
proc.terminate();proc.wait()
def resolve(n):return resolve(by[n][3]) if by[n][2]=='1' else out/n
for n in selected:
 if by[n][2]=='1':
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True)
  if not p.exists():os.link(resolve(n),p)
(out/'complete.json').write_text(json.dumps({'regular_files':len(done),'selected':len(selected),'seconds':round(time.time()-start)}))
print('restored',len(selected))
