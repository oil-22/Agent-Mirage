"""Read-only post-exit verification; preserve receipts, never restart a terminal."""
import concurrent.futures,json,time
from control import HERE,R3090,R4090,OUT,remote,save,sha

COMMON=r'''
import hashlib,json,os,subprocess,time
from pathlib import Path
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return {'pid':pid,'exists':False}
 try:
  s=(p/'stat').read_text().rsplit(')',1)[1].split()
  return {'pid':pid,'exists':True,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
 except FileNotFoundError:return {'pid':pid,'exists':False,'exited_during_read':True}
def inspect_record(p):
 v=load(p);record=v.get('identity',v);a=identity(record['pid'])
 same=a.get('exists',False)and all(a.get(k)==record[k]for k in ['uid','command','start_ticks'])and a.get('state')not in ['Z','X']
 return {'record':record,'actual':a,'same_live_process':same}
def chain(p):
 rows=[json.loads(s)for s in Path(p).read_text().splitlines()];previous='0'*64;counts={}
 for n,row in enumerate(rows):
  h=row.pop('sha256');assert row['seq']==n and row['previous']==previous
  assert hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==h
  previous=h;counts[row['kind']]=counts.get(row['kind'],0)+1
 return {'events':len(rows),'head':previous,'kinds':counts}
'''

def inspect3090():
 code='PACKAGE='+repr(R3090)+'\nOUTPUT='+repr(OUT)+'\n'+COMMON+r'''
p=Path(PACKAGE);r=Path(OUTPUT);out={'time':time.time(),'new_model_GUI_calls':0,'processes':{}}
for name,f in [('primary',r/'primary/process.json'),('Flash',p/'flash/service/process.json'),('launcher',r/'launcher-process.json')]:
 out['processes'][name]=inspect_record(f)
 assert not out['processes'][name]['same_live_process'],'Run is live; use live inspector instead.'
leasefile=p.parent.parent/'resource-attempt-20261106-01/lease.json';lease=load(leasefile);h=lease['holder'];a=identity(h['pid'])
out['holder']={'record':h,'actual':a,'identity_matches':all(a.get(k)==h[k]for k in ['uid','command','start_ticks'])}
if out['holder']['identity_matches']:
 for l in lease['lock_records']:
  q=Path('/proc',str(h['pid']));fd=q/'fd'/str(l['fd'])
  assert os.readlink(fd)==l['path']and fd.stat().st_ino==l['inode']and 'WRITE '+str(h['pid'])in(q/'fdinfo'/str(l['fd'])).read_text()
 out['holder']['held_locks_verified']=len(lease['lock_records'])
seal=load(r/'postexit-seal.json')
for n,h in seal.items():
 f=p/n if n.startswith('flash/service/')else r/n
 assert sha(f)==h,n
out['model_postexit_seal']={'path':str(r/'postexit-seal.json'),'sha256':sha(r/'postexit-seal.json'),'all_files_verified':len(seal)}
manifest=load(p/'manifest.json')
for n,h in manifest['files'].items():assert sha(p/n)==h,n
out['frozen_runtime_sources_verified']=len(manifest['files']);out['manifest_sha256']=sha(p/'manifest.json')
out['main_chain']=chain(r/'primary/journal/events.jsonl');out['Flash_chain']=chain(p/'flash/service/journal/events.jsonl')
out['requests']=[]
for d in sorted((r/'primary/requests').iterdir()):
 s=load(d/'seal.json');assert all(sha(d/n)==h for n,h in s.items())
 w=load(d/'wire-request.bin');b=w['body'];prepared=load(d/'prepared.json');first=load(d/'first-forward.json')
 for k in prepared:assert all(prepared[k][f]==first[k][f]for f in ['shape','dtype','bytes','sha256'])
 one={'directory':str(d),'request_id':w['request_id'],'run_id':w['run_id'],'decision':w['decision_index'],'wire_sha256':sha(d/'wire-request.bin'),'seal_sha256':sha(d/'seal.json'),'input_tokens':prepared['input_ids']['shape'][-1],'history_messages':len(b['messages']),'image_count':sum(1 for m in b['messages']if isinstance(m.get('content'),list)for x in m['content']if x.get('type')=='image_url'),'sealed_files':len(s),'forward_count':load(d/'forward-count.json')}
 if(d/'response.json').exists():
  g=load(d/'actual-generation.json');native=load(d/'native-call.json');response=load(d/'response.json')
  assert native['generated_ids']==g['output_ids']and g['natural_EOS']and response['request_sha256']==one['wire_sha256']
  one.update({'result':'natural_EOS','output_tokens':g['output_tokens']})
 else:
  one.update({'result':'technical_failure','failure':load(d/'failure.json'),'first_forward':first,'generation_effective':load(d/'effective-generation.json'),'admission_before':load(d/'admission-before.json'),'original_files':sorted(s)})
 out['requests'].append(one)
out['Flash_replies']=[]
for d in sorted((p/'flash/service/requests').iterdir()):
 s=load(d/'seal.json');assert all(sha(d/n)==h for n,h in s.items())
 v=load(d/'response.json');out['Flash_replies'].append({'request_id':v['request_id'],'decision':v['decision'],'image_sha256':v['image_sha256'],'seal_sha256':sha(d/'seal.json')})
for name,f in [('primary_status',r/'primary/status.json'),('primary_terminal',r/'primary/terminal.json'),('group_exit',r/'exit.json'),('primary_exit',r/'primary-exit.json'),('Flash_terminal',p/'flash/service/terminal.json')]:
 if f.exists():out[name]=load(f)
out['GPU_current']=subprocess.check_output(['nvidia-smi','--id=4,5,6,7','--query-gpu=index,uuid,memory.used,memory.free','--format=csv,noheader,nounits'],text=True)
out['compute_current']=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
print(json.dumps(out))
'''
 raw,op=remote('3090',code,'postexit-full-model-seals-and-failed-request',timeout=55)
 return '3090',json.loads(raw),op

def inspect4090():
 code='ROOT='+repr(R4090)+'\n'+COMMON+r'''
r=Path(ROOT);out={'time':time.time(),'new_model_GUI_calls':0,'processes':{}}
for n in ['control/process.json','control/runner-process.json']:
 out['processes'][n]=inspect_record(r/n);assert not out['processes'][n]['same_live_process'],'GUI remains live.'
control=load(r/'control/postexit-seal.json')
for n,h in control.items():assert sha(r/'control'/n)==h,n
out['control_postexit_seal']={'sha256':sha(r/'control/postexit-seal.json'),'all_files_verified':len(control)}
seal=load(r/'control/batch-terminal-seal.json')
for n,h in seal.items():assert sha(r/'batch'/n)==h,n
out['batch_postexit_seal']={'sha256':sha(r/'control/batch-terminal-seal.json'),'all_files_verified':len(seal)}
out['terminals']=[]
for f in sorted((r/'batch/runs').glob('*/attempt-*/terminal.json')):
 t=load(f);c=chain(f.parent/'controller/events.jsonl')
 if(f.parent/'seal.json').exists():
  s=load(f.parent/'seal.json');assert all(sha(f.parent/n)==h for n,h in s.items())
 else:s={}
 assert c['kinds'].get('actual_actor_reply',0)==len(t['actor_receipts'])
 assert c['kinds'].get('native_environment_action',0)==t.get('environment_actions',c['kinds'].get('native_environment_action',0))
 out['terminals'].append({'path':str(f),'terminal_sha256':sha(f),'terminal':t,'event_chain':c,'per_attempt_seal_files_verified':len(s),'covered_by_batch_postexit_seal':str(f.relative_to(r/'batch'))in seal})
out['batch_status_historical_snapshot']=load(r/'batch/status.json');out['GUI_uncaught_failure']=load(r/'GUI-uncaught-failure.json');out['control_exit']=load(r/'control/exit.json')
print(json.dumps(out))
'''
 raw,op=remote('4090',code,'postexit-full-GUI-seals-and-terminals',timeout=55)
 return '4090',json.loads(raw),op

def main():
 dest=HERE/('postexit-evidence-'+str(time.time_ns()));dest.mkdir()
 data={}
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
  futures=[pool.submit(fn)for fn in [inspect3090,inspect4090]]
  for future in concurrent.futures.as_completed(futures):
   host,value,operation=future.result();save(dest/(host+'.json'),value);save(dest/(host+'-operation.json'),{'operation':str(operation)});data[host]=value
 m=data['3090'];g=data['4090'];terminals=g['terminals']
 complete=[t for t in terminals if not t['terminal']['infrastructure_failure']]
 failed=[t for t in terminals if t['terminal']['infrastructure_failure']]
 summary={'read_time':max(m['time'],g['time']),'phase':'stopped_on_technical_failure','expected':32,'normal_terminals':len(complete),'technical_terminals':len(failed),'unstarted':32-len(terminals),'actor_attempts':len(m['requests']),'complete_actor_replies':sum(q['result']=='natural_EOS'for q in m['requests']),'actor_technical_failures':sum(q['result']=='technical_failure'for q in m['requests']),'Flash_replies':len(m['Flash_replies']),'Flash_YES':sum(q['decision']=='YES'for q in m['Flash_replies']),'Flash_NO':sum(q['decision']=='NO'for q in m['Flash_replies']),'environment_actions':sum(t['event_chain']['kinds'].get('native_environment_action',0)for t in terminals),'normal_results':[{'run':t['terminal']['run'],'outcome':t['terminal']['outcome'],'official_reward':t['terminal']['official_reward']}for t in complete],'failed_requests':[q for q in m['requests']if q['result']=='technical_failure'],'full_model_postexit_files_verified':m['model_postexit_seal']['all_files_verified'],'full_GUI_postexit_files_verified':g['batch_postexit_seal']['all_files_verified'],'all_original_model_and_GUI_processes_exited':True,'Mirage_reduction':None,'new_model_GUI_calls_by_inspection':0}
 save(dest/'summary.json',summary);save(dest/'seal.json',{p.name:sha(p)for p in dest.iterdir()if p.is_file()})
 print(json.dumps({'evidence':str(dest),**{k:v for k,v in summary.items()if k!='failed_requests'},'failed_requests_summary':[{k:q[k]for k in ['directory','run_id','decision','input_tokens','history_messages','image_count','forward_count']}for q in summary['failed_requests']]}))
if __name__=='__main__':main()
