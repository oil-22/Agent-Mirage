"""Explicit user stop: UID/start-time checked signals and owned container stops only."""
import os,pwd,json,signal,subprocess,time,hashlib,shutil
from pathlib import Path
uid=os.getuid();assert pwd.getpwuid(uid).pw_name=='whz'
root=Path.home()/('all-process-user-stop-'+str(time.time_ns()));root.mkdir()
def save(n,value):
 with(root/n).open('x')as f:json.dump(value,f,indent=2)
def row(pid):
 p=Path('/proc')/str(pid)
 try:
  stat=(p/'stat').read_text();fields=stat[stat.rfind(')')+2:].split();uids=[int(x)for x in next(x for x in(p/'status').read_text().splitlines()if x.startswith('Uid:')).split()[1:]]
  return {'pid':pid,'uids':uids,'state':fields[0],'ppid':int(fields[1]),'start_ticks':fields[19],'argv':[x.decode(errors='replace')for x in(p/'cmdline').read_bytes().split(b'\0')if x]}
 except(OSError,StopIteration):return None
def owned():
 return [r for r in(row(int(p.name))for p in Path('/proc').iterdir()if p.name.isdigit())if r and uid in r['uids']]
protected=set();p=os.getpid()
while p>0 and p not in protected:
 protected.add(p);v=row(p)
 if not v:break
 p=v['ppid']
before=owned();save('processes-before.json',before);save('protected-control-ancestry.json',sorted(protected));signals=[];errors=[];containers=[]
def run(args,timeout=15):
 v=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 return {'returncode':v.returncode,'stdout':v.stdout.decode(errors='replace'),'stderr':v.stderr.decode(errors='replace')}
# Only exact pre-inspected IDs with current matching ownership evidence.
for identity in OWNED_CONTAINERS:
 try:
  c=json.loads(subprocess.check_output(['docker','inspect',identity]))[0];assert c['Id']==identity
  labels=c['Config'].get('Labels')or {};proven=False
  for key in ['com.docker.compose.project.config_files','com.docker.compose.project.working_dir']:
   for raw in labels.get(key,'').split(','):
    if not raw:continue
    f=Path(raw)
    try:proven=proven or(f.stat().st_uid==uid and any(str(f.resolve()).startswith(prefix)for prefix in ['/home/researcher/','/data/researcher/','/opt/whz/']))
    except OSError:pass
  assert proven,'Container ownership no longer matches'
  item={'id':identity,'name':c['Name'],'was_running':c['State']['Running'],'original_restart_policy':c['HostConfig']['RestartPolicy']}
  if c['HostConfig']['RestartPolicy']['Name']!='no':item['prevent_restart']=run(['docker','update','--restart=no',identity])
  if c['State']['Running']:item['stop']=run(['docker','stop','--time','5',identity],timeout=12)
  item['running_after']=json.loads(subprocess.check_output(['docker','inspect',identity]))[0]['State']['Running'];assert not item['running_after'];containers.append(item)
 except Exception as e:errors.append({'container':identity,'error':repr(e)})
save('containers-stopped.json',containers)
def send(original,sig):
 current=row(original['pid'])
 if not current or current['start_ticks']!=original['start_ticks']or uid not in current['uids']or current['pid']in protected or current['state']=='Z':return
 try:os.kill(current['pid'],sig);signals.append({'pid':current['pid'],'start_ticks':current['start_ticks'],'signal':int(sig),'argv':current['argv']})
 except OSError as e:errors.append({'pid':current['pid'],'error':str(e)})
for pass_index in range(3):
 targets=[r for r in owned()if r['pid']not in protected and r['state']!='Z']
 if not targets:break
 # Stop user managers/supervisors and then their remaining processes.
 targets.sort(key=lambda r:0 if any('systemd'in x or 'supervis'in x for x in r['argv'])else 1)
 for r in targets:send(r,signal.SIGTERM)
 time.sleep(2)
 for r in targets:send(r,signal.SIGKILL)
 time.sleep(1)
after=owned();save('processes-after.json',after);save('signals.json',signals)
# Preserve service logs plus full request/reply/source-file SHA chain after stopping.
service_seals=[]
for raw in OWNED_SERVICE_ROOTS:
 r=Path(raw)
 if not r.exists():continue
 assert r.stat().st_uid==uid
 files={}
 for f in r.rglob('*'):
  if not f.is_file()or f.is_symlink():continue
  h=hashlib.sha256()
  with f.open('rb')as stream:
   for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
  files[str(f.relative_to(r))]=h.hexdigest()
 for name in ['worker.log','status.json']:
  f=r/name
  if f.exists():shutil.copy2(str(f),str(root/('service-'+name)))
 service_seals.append({'root':str(r),'sha256':files})
save('service-seals.json',service_seals)
gpu=run(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader'])
summary={'time':time.time(),'uid':uid,'login':'whz','root':str(root),'user_instruction':'Stop all my processes on servers','protected_control_ancestry_only':sorted(protected),'signals':len(signals),'distinct_processes_signalled':len(set(x['pid']for x in signals)),'remaining_noncontrol_live':[r for r in after if r['pid']not in protected and r['state']!='Z'],'remaining_zombies':[r for r in after if r['state']=='Z'],'owned_containers':containers,'errors':errors,'gpu_after':gpu,'no_deletion_or_site_reset':True,'no_auto_resume':True}
save('summary.json',summary);save('preservation-sha256.json',{f.name:hashlib.sha256(f.read_bytes()).hexdigest()for f in root.iterdir()if f.is_file()})
print(json.dumps(summary))
