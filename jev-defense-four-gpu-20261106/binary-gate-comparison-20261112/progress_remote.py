from pathlib import Path
import hashlib,json,os,subprocess,time
R=Path('/home/researcher/jev-defense-four-gpu-20261106/binary-gate-comparison-20261112')
def ident(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return {'pid':pid,'absent':True}
 s=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
out={'time':time.time(),'models':{},'compute':subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)}
for name in ['flash','neohorse','style']:
 r=R/'results'/name
 v={'started':r.exists(),'completed_requests':len(list((r/'requests').glob('*/response.json'))),'failures':[]}
 for p in (r/'requests').glob('*/failure.json'):v['failures'].append(json.loads(p.read_bytes()))
 for n in ['process.json','loaded.json','terminal.json']:
  p=r/n
  if p.is_file():
   x=json.loads(p.read_bytes());v[n]=x
   if n=='process.json':v['actual_process']=ident(x['pid'])
 log=R/(name+'-worker.log')
 if log.exists():v['log_tail']=log.read_bytes()[-1100:].decode(errors='replace')
 out['models'][name]=v
for n in ['terminal.json','launcher-failure.json']:
 p=R/n
 if p.exists():out[n]=json.loads(p.read_bytes())
print(json.dumps(out,ensure_ascii=False))
