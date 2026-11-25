"""Authorized one-shot safe pause; no changes to old experiment code/results."""
import hashlib,json,os,pathlib,pwd,shutil,signal,time
R=pathlib.Path('/home/researcher/agent-mirage-mechanism-scale-20261020')
P=pathlib.Path('/home/researcher/mirage-defense-pilot-20261023')
def H(b):return hashlib.sha256(b).hexdigest()
uid=pwd.getpwnam('whz').pw_uid
def proc(pid):
 p=pathlib.Path('/proc')/str(pid)
 assert p.stat().st_uid==uid
 return dict(pid=pid,cmdline=p.joinpath('cmdline').read_bytes().replace(b'\0',b' ').decode(),cwd=str(p.joinpath('cwd').resolve()),stat=p.joinpath('stat').read_text())
specs=[('internvl','interleaved-qwen27-status-v3.json','interleaved_qwen27_v3.py','run_history_assays_v2.py'),('qwen9','interleaved-pipeline-status-v21.json','interleaved_pipeline_v21.py','run_value_full.py')]
snap=P/('old-queue-preservation-'+str(time.time_ns()));snap.mkdir(parents=True,exist_ok=False)
rows=[]
for folder,status,scheduler,worker in specs:
 root=R/folder;j=json.loads((root/status).read_text());parent=proc(j['pid']);child=proc(j['worker_pid'])
 assert scheduler in parent['cmdline'] and worker in child['cmdline']
 assert parent['cwd']==str(root) and child['cwd']==str(root)
 assert int(child['stat'].split()[3])==j['pid']
 dest=snap/folder;dest.mkdir();files=[]
 # Preserve all top-level metadata/logs and current slice, never rewrite originals.
 paths=[p for p in root.iterdir() if p.is_file() and p.suffix in {'.json','.jsonl','.py','.log'}]
 paths+=list(pathlib.Path(j['slice']).rglob('*'))
 for p in paths:
  if not p.is_file():continue
  raw=p.read_bytes();rel=p.relative_to(root);out=dest/rel;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
  files.append(dict(path=str(p),bytes=len(raw),sha256=H(raw)))
 # Summary inventory of immutable completion markers, without duplicating large tensors.
 markers=[]
 for p in root.rglob('*.json'):
  if any(k in p.name.lower() for k in ['complete','summary','receipt']):
   raw=p.read_bytes();markers.append(dict(path=str(p),bytes=len(raw),sha256=H(raw)))
 row=dict(folder=folder,parent=parent,worker=child,status=j,files=files,completion_markers=markers)
 rows.append(row)
receipt=dict(time=time.time(),authorization='User: pause old mechanism queues; prioritize defense',snapshot=str(snap),queues=rows)
(snap/'before.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
# Revalidate identities immediately before each signal. Stop dispatch first.
for row in rows:
 for who in ['parent','worker']:
  now=proc(row[who]['pid']);assert now['cmdline']==row[who]['cmdline'] and now['cwd']==row[who]['cwd']
 os.kill(row['parent']['pid'],signal.SIGSTOP)
 os.kill(row['worker']['pid'],signal.SIGUSR1)
 row['signals']={'parent':'SIGSTOP','worker':'SIGUSR1','time':time.time()}
receipt['phase']='safe_boundary_stop_requested'
(snap/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
(P/'pause-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
print(json.dumps(dict(snapshot=str(snap),phase=receipt['phase'],queues=[dict(folder=x['folder'],parent=x['parent']['pid'],worker=x['worker']['pid'],preserved=len(x['files']),markers=len(x['completion_markers']))for x in rows])))
