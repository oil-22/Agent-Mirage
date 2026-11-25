"""Compact read-only progress; process identities and evidence, no inference."""
import json,time
from control import HERE,R3090,R4090,OUT,remote,save
results={}
for host,root in [('3090',OUT),('4090',R4090)]:
 code='ROOT='+repr(root)+'\nPACKAGE='+repr(R3090)+'\n'+r'''
import json,os,time
from pathlib import Path
r=Path(ROOT);p=Path(PACKAGE);out={'time':time.time(),'files':{},'actual_processes':{},'calls_by_inspector':0}
def identity(pid):
 q=Path('/proc',str(pid))
 if not q.exists():return None
 s=(q/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':q.stat().st_uid,'command':(q/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
for n in ['primary/status.json','primary/ready.json','primary/failure.json','primary/terminal.json','exit.json','capacity/lifetime-validation/result.json','capacity/50-image-source-bound-stress/result.json','batch/status.json','batch/summary.json','control/exit.json']:
 f=r/n
 if f.exists():out['files'][n]=json.loads(f.read_bytes())
for n in ['capacity/lifetime-validation/kernel-bitwise-tests.json','capacity/lifetime-validation/baseline-three-cached-steps/invariance-record.json','capacity/lifetime-validation/optimized-three-cached-steps/invariance-record.json','capacity/50-image-source-bound-stress/first-forward.json']:
 if(r/n).exists():out['files'][n]={'exists':True}
for f in [r/'launcher-process.json',r/'primary/process.json',r/'control/process.json',r/'control/runner-process.json']:
 if f.exists():
  v=json.loads(f.read_bytes());a=identity(v['pid']);out['actual_processes'][str(f)]={'record':v,'actual':a,'same_live_process':bool(a and all(a[k]==v[k]for k in ['uid','command','start_ticks'])and a['state']not in ['Z','X'])}
out['sealed_actor_requests']=len(list((r/'primary/requests').glob('*/seal.json')))
if os.getuid()==1033:
 out['sealed_Flash_requests']=len(list((p/'flash/service/requests').glob('*/seal.json')))
 if(p/'flash/service/process.json').exists():
  v=json.loads((p/'flash/service/process.json').read_bytes());out['actual_processes']['Flash']=identity(v['pid'])
if(r/'control/runner.log').exists():out['runner_tail']=(r/'control/runner.log').read_text()[-1000:]
print(json.dumps(out))
'''
 raw,op=remote(host,code,'compact-actual-progress-'+host);results[host]={'result':json.loads(raw),'operation':str(op)}
path=HERE/('progress-'+str(time.time_ns())+'.json');save(path,results)
print(json.dumps({'receipt':str(path),'hosts':results}))
