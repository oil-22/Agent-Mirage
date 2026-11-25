"""Actual process/FD/GPU and SHA-chain inspection, zero model requests."""
import json
from ops import HERE,ROOT,PACKAGE,remote,sha

def main():
    code='ROOT='+repr(ROOT)+'\nPACKAGE='+repr(PACKAGE)+'\nMSHA='+repr(sha(HERE/'controls-package/manifest.json'))+'\n'+r'''
from pathlib import Path
import hashlib,json,os,subprocess,time
r=Path(ROOT);package=Path(PACKAGE);assert hashlib.sha256((package/'manifest.json').read_bytes()).hexdigest()==MSHA
m=json.loads((package/'manifest.json').read_bytes());lease=json.loads(Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json').read_bytes())
def actual(record):
 p=Path('/proc',str(record['pid']))
 if not p.exists():return{'pid':record['pid'],'absent':True}
 v={'pid':record['pid'],'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':(p/'stat').read_text().rsplit(')',1)[1].split()[19]}
 assert all(str(v[k])==str(record[k])for k in v)
 locks=[]
 for row in lease['lock_records']:
  fd=p/'fd'/str(row['fd']);info=(p/'fdinfo'/str(row['fd'])).read_text()
  assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and'WRITE '+str(lease['holder']['pid'])in info
  locks.append(row['path'])
 v['actual_nine_locks']=locks;return v
out={'time':time.time(),'holder':actual(lease['holder']),'zero_new_model_requests':True,'manifest_sha256':MSHA}
for n in ['launcher-process.json','worker/process.json']:
 p=r/n
 if p.is_file():out[n]={'record':json.loads(p.read_bytes()),'actual':actual(json.loads(p.read_bytes()))}
for n in ['exit.json','launcher-failure.json','worker/status.json','worker/terminal.json','worker/failure.json','worker/summary.json']:
 p=r/n
 if p.is_file():out[n]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'value':json.loads(p.read_bytes())}
p=r/'worker/loaded.json'
if p.exists():
 v=json.loads(p.read_bytes());out['loaded']={k:v[k]for k in ['primary_load_seconds','auxiliary_load_seconds','torch','transformers','single_auxiliary','memory','primary_generation_backend_sha256']}
events=r/'worker/journal/events.jsonl'
if events.exists():
 raw=events.read_bytes();lines=raw.splitlines();complete=raw.endswith(b'\n')
 if not complete:lines=lines[:-1]
 prev='0'*64;kinds={};n=0
 for line in lines:
  v=json.loads(line);h=v.pop('sha256');assert v['seq']==n and v['previous']==prev
  assert hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==h
  prev=h;n+=1;kinds[v['kind']]=kinds.get(v['kind'],0)+1
 out['journal']={'complete_entries_verified':n,'head':prev,'all_bytes_end_on_committed_newline':complete,'kinds':kinds,'last_kind':v['kind']if n else None}
out['gpu']=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True)
out['compute']=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
p=r/'worker.log'
if p.exists():out['log']={'bytes':p.stat().st_size,'tail':p.read_bytes()[-4500:].decode(errors='replace')}
print(json.dumps(out,ensure_ascii=False))
'''
    raw,path=remote('3090',code,'inspect-current-controls',timeout=55)
    data=json.loads(raw)
    status=data.get('worker/status.json',{}).get('value')
    print(json.dumps({'evidence':str(path),'actual_worker':data.get('worker/process.json',{}).get('actual'),'status':status,
        'loaded':data.get('loaded'),'terminal':data.get('worker/terminal.json',{}).get('value'),'failure':data.get('worker/failure.json',{}).get('value'),
        'exit':data.get('exit.json',{}).get('value'),'journal':data.get('journal'),'gpu':data['gpu'],'compute':data['compute'],'log_tail':data.get('log',{}).get('tail')},ensure_ascii=False))

if __name__=='__main__':main()
