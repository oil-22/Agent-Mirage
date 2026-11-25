"""Stop only this verified idle service after external GPU conflict; preserve postexit seal."""
import hashlib,json,os,pathlib,signal,time
B=pathlib.Path(__file__).resolve().parent;run=B/'services/style-01';launch=json.loads((run/'launch.json').read_bytes());pid=launch['pid'];proc=pathlib.Path('/proc')/str(pid)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert proc.stat().st_uid==1033
assert proc.joinpath('cmdline').read_bytes().replace(b'\0',b' ').decode().strip()==' '.join(launch['command'])
assert proc.joinpath('stat').read_text().split()[21]==json.loads((run/'runtime/process.json').read_bytes())['start_ticks']
requests=list((run/'runtime/requests').iterdir());assert len(requests)==19
for d in requests:
    assert (d/'response.json').exists() and (d/'seal.json').exists()
    assert all(sha(d/n)==h for n,h in json.loads((d/'seal.json').read_bytes()).items())
import subprocess
gpu=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
pids={int(line.split(',')[1]) for line in gpu.splitlines() if line.split(',')[0].strip()==launch['gpu']['uuid']}
assert pid in pids and any(pathlib.Path('/proc',str(p)).stat().st_uid!=1033 for p in pids if p!=pid)
event={'pid':pid,'uid':1033,'exact_command':launch['command'],'time':time.time(),'reason':'External user began sharing this previously exclusive GPU; user chose to wait for exclusive GPU; 19 completed replies preserved, no in-flight request','gpu_query':gpu,'model_calls':19,'resource_conflict_not_model_failure':True}
with(run/'suspension-before-stop.json').open('x') as f:json.dump(event,f,indent=2)
os.kill(pid,signal.SIGTERM)
deadline=time.time()+10
while proc.exists() and proc.joinpath('stat').read_text().split()[2]!='Z' and time.time()<deadline:time.sleep(.1)
assert not proc.exists() or proc.joinpath('stat').read_text().split()[2]=='Z','Owned service did not exit'
with(run/'postexit-seal.json').open('x') as f:json.dump({str(p.relative_to(run)):sha(p) for p in run.rglob('*') if p.is_file() and p.name!='postexit-seal.json'},f,indent=2)
print(json.dumps({'stopped_owned_pid':pid,'preserved_replies':19,'foreign_processes_changed':False,'seal':str(run/'postexit-seal.json')}))
