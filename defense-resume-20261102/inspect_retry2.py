"""Read-only process, held-lock and immutable receipt inspection."""
import hashlib,json,pathlib,subprocess,time
B=pathlib.Path('/home/researcher/defense-resume-20261102-retry2')
launch=json.loads((B/'launch.json').read_bytes());R=pathlib.Path(launch['attempt'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def proc(record):
 p=pathlib.Path('/proc')/str(record['pid'])
 if not p.exists():return {'pid':record['pid'],'exists':False}
 cmd=(p/'cmdline').read_bytes().decode().replace(chr(0),' ')
 locks=[]
 for f in (p/'fdinfo').iterdir():
  try:
   rows=[s for s in f.read_text().splitlines()if s.startswith('lock:')]
   if rows:locks.append({'fd':f.name,'target':str((p/'fd'/f.name).resolve()),'locks':rows})
  except OSError:pass
 return {'pid':record['pid'],'exists':True,'uid':p.stat().st_uid,'command':cmd,'start_ticks':(p/'stat').read_text().split()[21],'expected_identity':p.stat().st_uid==record['uid'] and cmd==record['command'] and (p/'stat').read_text().split()[21]==record['start_ticks'],'held_locks':locks}
out={'time':time.time(),'attempt':str(R),'orchestrator':proc(launch['orchestrator']),'service':proc(launch['service']),'files':{},'requests':[]}
for n in ['worker-launch.json','worker-exit.json','reservation.json','orchestrator-failure.json','service/status.json','service/actual-device-audit.json','controls/status.json','controls/summary.json','controls/failure.json','controls/w05-result.json','controls/w06-result.json','controls/w08-result.json']:
 p=R/n
 if p.exists():out['files'][n]=json.loads(p.read_bytes())
if 'worker-launch.json'in out['files']:out['worker']=proc(out['files']['worker-launch.json'])
for p in sorted((R/'service/requests').glob('*')):
 d={'id':p.name,'request_sha256':sha(p/'request.json'),'response':(p/'response.json').exists(),'failure':(p/'failure.json').exists()}
 for n in ['generation.json','response.json','failure.json']:
  if (p/n).exists():
   x=json.loads((p/n).read_bytes())
   if n=='generation.json':x={k:v for k,v in x.items()if k not in ['input_ids','generated_ids','text','messages']};x['input_tokens']=len(json.loads((p/n).read_bytes()).get('input_ids',[]));x['output_tokens']=len(json.loads((p/n).read_bytes()).get('generated_ids',[]))
   d[n]=x
 f=p/'generated-token-progress.jsonl'
 if f.exists():
  rows=f.read_text().splitlines()
  if rows:d['progress']=json.loads(rows[-1])
 out['requests'].append(d)
for n in ['postexit-sha256.json','controls/terminal-sha256.json']:
 p=R/n
 if p.exists():
  seal=json.loads(p.read_bytes());out[n]={'sha256':sha(p),'files':len(seal),'mismatches':[k for k,h in seal.items()if not (p.parent/k).exists()or sha(p.parent/k)!=h]}
out['gpu_compute']=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_memory','--format=csv,noheader'],text=True)
out['worker_log_tail']=(R/'controls/worker.log').read_text()[-4000:]
dest=B/('inspection-'+str(time.time_ns())+'.json');dest.write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({'inspection':str(dest),**out},ensure_ascii=False))
