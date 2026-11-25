"""Read-only proof of actual new processes, locks, replies, GUI actions and chains."""
import base64,json,time
from pathlib import Path
from control import HERE,R3090,R4090,OUT,remote,save,sha
COMMON=r'''
import base64,hashlib,json,os,sys,time
from pathlib import Path
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def identity(pid):
 p=Path('/proc',str(pid));s=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
def chain(path):
 raw=path.read_bytes();parts=raw.splitlines();partial=bool(raw and not raw.endswith(b'\n'))
 if partial:parts=parts[:-1]
 previous='0'*64;counts={};rows=[]
 for n,line in enumerate(parts):
  row=json.loads(line);h=row.pop('sha256');assert row['seq']==n and row['previous']==previous and hashlib.sha256(canonical(row)).hexdigest()==h
  previous=h;counts[row['kind']]=counts.get(row['kind'],0)+1;rows.append(row)
 return {'verified_prefix_events':len(rows),'head':previous,'kinds':counts,'ignored_partial_last_line':partial},rows
'''
def main():
 target=HERE/('live-evidence-'+str(time.time_ns()));target.mkdir()
 code=COMMON+r'''
import subprocess
p=Path(PACKAGE);r=Path(OUTPUT);out={'time':time.time(),'UID':os.getuid(),'new_model_calls_by_inspector':0,'processes':{},'sealed_main_requests':[],'sealed_Flash_requests':[]};history={}
lease=json.loads((p.parent.parent/'resource-attempt-20261106-01/lease.json').read_bytes());h=lease['holder'];ha=identity(h['pid']);assert all(ha[k]==h[k]for k in ['uid','command','start_ticks']);out['holder_actual']=ha
for label,processfile in [('primary',r/'primary/process.json'),('Flash',p/'flash/service/process.json')]:
 record=json.loads(processfile.read_bytes());actual=identity(record['pid']);assert all(actual[k]==record[k]for k in ['uid','command','start_ticks'])and actual['state']not in ['Z','X']
 for lock in lease['lock_records']:
  proc=Path('/proc',str(record['pid']));fd=proc/'fd'/str(lock['fd']);assert os.readlink(fd)==lock['path']and fd.stat().st_ino==lock['inode']and'WRITE '+str(h['pid'])in(proc/'fdinfo'/str(lock['fd'])).read_text()
 extra=[]
 if label=='primary':
  expanded=json.loads((r/'expanded-lease.json').read_bytes());owner=expanded['holder'];owner_actual=identity(owner['pid'])
  assert all(owner_actual[k]==owner[k]for k in ['uid','command','start_ticks'])and owner_actual['state']not in ['Z','X']
  for lock in expanded['extra_lock_records']:
   proc=Path('/proc',str(record['pid']));fd=proc/'fd'/str(lock['fd'])
   assert os.readlink(fd)==lock['path']and fd.stat().st_ino==lock['inode']and'WRITE '+str(owner['pid'])in(proc/'fdinfo'/str(lock['fd'])).read_text()
  extra=expanded['extra_lock_records']
 out['processes'][label]={'actual':actual,'actual_inherited_held_locks':len(lease['lock_records'])+len(extra)}
for label,path in [('main',r/'primary/journal/events.jsonl'),('Flash',p/'flash/service/journal/events.jsonl')]:out[label+'_chain']=chain(path)[0]
for d in sorted((r/'primary/requests').iterdir()):
 if not(d/'seal.json').exists():continue
 seal=json.loads((d/'seal.json').read_bytes());assert all(sha(d/n)==v for n,v in seal.items())
 wire=json.loads((d/'wire-request.bin').read_bytes());response=json.loads((d/'response.json').read_bytes());actual=json.loads((d/'actual-generation.json').read_bytes());native=json.loads((d/'native-call.json').read_bytes());prepared=json.loads((d/'prepared.json').read_bytes());first=json.loads((d/'first-forward.json').read_bytes())
 assert response['request_sha256']==sha(d/'wire-request.bin')and response['request_id']==wire['request_id'];assert native['generated_ids']==actual['output_ids']and actual['natural_EOS']
 assert native['request_messages_sha256']==hashlib.sha256(canonical(wire['body']['messages'])).hexdigest()
 template=json.loads((p/'actor-template.json').read_bytes());assert{k:v for k,v in wire['body'].items()if k!='messages'}=={k:v for k,v in template.items()if k!='messages'}
 if wire['run_id']in history:assert wire['body']['messages'][:len(history[wire['run_id']])]==history[wire['run_id']]
 history[wire['run_id']]=wire['body']['messages']+[{'role':'assistant','content':response['text']}]
 for k in prepared:
  assert all(prepared[k][f]==first[k][f]for f in ['shape','dtype','bytes','sha256']);assert sha(d/prepared[k]['file'])==prepared[k]['sha256']and sha(d/first[k]['file'])==first[k]['sha256']
 current=wire['body']['messages'][-1]['content'][-1]['image_url']['url'];image=base64.b64decode(current.split(',')[1]);imagehash=hashlib.sha256(image).hexdigest()
 out['sealed_main_requests'].append({'folder':str(d),'request_id':wire['request_id'],'run_id':wire['run_id'],'decision':wire['decision_index'],'wire_sha256':sha(d/'wire-request.bin'),'body_sha256':hashlib.sha256(canonical(wire['body'])).hexdigest(),'seal_sha256':sha(d/'seal.json'),'input_tokens':actual['input_tokens'],'output_tokens':actual['output_tokens'],'natural_EOS':actual['natural_EOS'],'current_image_sha256':imagehash,'history_messages':len(wire['body']['messages']),'actual_tensor_files_verified':True,'native_text':response['text']})
for d in sorted((p/'flash/service/requests').iterdir()):
 if not(d/'seal.json').exists():continue
 seal=json.loads((d/'seal.json').read_bytes());assert all(sha(d/n)==v for n,v in seal.items());response=json.loads((d/'response.json').read_bytes());trace=json.loads((d/'forward-trace.json').read_bytes())
 assert response['request_sha256']==sha(d/'wire-request.bin')and response['image_sha256']==sha(d/'original.png')and len(trace)==1 and trace[0]['past_key_values']is None and trace[0]['use_cache']is False
 out['sealed_Flash_requests'].append({'request_id':response['request_id'],'decision':response['decision'],'image_sha256':response['image_sha256'],'seal_sha256':sha(d/'seal.json'),'native_input':trace[0]['input_ids'],'grid':trace[0]['image_grid_thw']['values']})
out['primary_loaded']=json.loads((r/'primary/loaded.json').read_bytes());out['GPU']=subprocess.check_output(['nvidia-smi','--id=0,1,2,3,4,5,6,7','--query-gpu=index,uuid,memory.used,memory.free','--format=csv,noheader,nounits'],text=True);out['compute']=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
out['primary_status_snapshot']=json.loads((r/'primary/status.json').read_bytes())
print(json.dumps(out))
'''
 code='PACKAGE='+repr(R3090)+'\nOUTPUT='+repr(OUT)+'\n'+code
 raw,operation=remote('3090',code,'audit-actual-main-Flash-bindings',timeout=55);main=json.loads(raw);save(target/'3090.json',main);save(target/'3090-operation.json',{'operation':str(operation)})
 code='ROOT='+repr(R4090)+'\n'+COMMON+r'''
r=Path(ROOT);out={'time':time.time(),'UID':os.getuid(),'new_GUI_actions_by_inspector':0,'processes':{},'controllers':[]}
for n in ['control/process.json','control/runner-process.json']:
 record=json.loads((r/n).read_bytes());actual=identity(record['pid']);assert all(actual[k]==record[k]for k in ['uid','command','start_ticks'])and actual['state']not in ['Z','X'];out['processes'][n]=actual
for events in(r/'batch/runs').glob('*/attempt-*/controller/events.jsonl'):
 c,rows=chain(events);out['controllers'].append({'path':str(events),'chain':c,'forwarded_images':[row['data']for row in rows if row['kind']=='main_image_forwarded'],'actor_requests':[row['data']for row in rows if row['kind']=='actual_actor_request'],'actor_replies':[row['data']for row in rows if row['kind']=='actual_actor_reply'],'environment_actions':[row['data']for row in rows if row['kind']=='native_environment_action'],'latest':rows[-3:]})
out['status_snapshot']=json.loads((r/'batch/status.json').read_bytes())
shots=sorted((r/'batch/runs').glob('*/attempt-*/001-initial-delivered.png'))
if shots:out['first_image']={'file':str(shots[0]),'sha256':sha(shots[0]),'base64':base64.b64encode(shots[0].read_bytes()).decode()}
print(json.dumps(out))
'''
 raw,operation=remote('4090',code,'audit-actual-GUI-actions');gui=json.loads(raw);first_image=gui.get('first_image')
 if first_image:
  rawimage=base64.b64decode(first_image.pop('base64'));(target/'first-delivered.png').write_bytes(rawimage);assert sha(target/'first-delivered.png')==first_image['sha256']
 save(target/'4090.json',gui);save(target/'4090-operation.json',{'operation':str(operation)})
 forwarded={r['gate_request_id']:r for c in gui['controllers']for r in c['forwarded_images']if r['gate_request_id']is not None};Flash={r['request_id']:r for r in main['sealed_Flash_requests']}
 bound=[];newer=[];main_by_id={r['request_id']:r for r in main['sealed_main_requests']};actor_bindings=[]
 for rid,row in forwarded.items():
  if rid not in Flash:newer.append(rid);continue
  assert Flash[rid]['decision']=='YES'and Flash[rid]['image_sha256']==row['image_sha256'];bound.append(rid)
 for c in gui['controllers']:
  for forwarded_image,actor_request in zip(c['forwarded_images'],c['actor_requests']):
   actual=main_by_id.get(actor_request['request_id'])
   if actual is None:continue
   assert actual['body_sha256']==actor_request['body_sha256']and actual['current_image_sha256']==forwarded_image['image_sha256'];actor_bindings.append(actor_request['request_id'])
 summary={'verified_main_replies':len(main['sealed_main_requests']),'verified_Flash_replies':len(main['sealed_Flash_requests']),'YES_forwarded_bindings_verified':len(bound),'actual_main_input_image_bindings_verified':len(actor_bindings),'later_GUI_events_beyond_main_snapshot_not_joined':newer,'environment_action_events':sum(len(c['environment_actions'])for c in gui['controllers']),'main_chain':main['main_chain'],'Flash_chain':main['Flash_chain'],'actual_processes':main['processes'],'GUI_status':gui['status_snapshot'],'new_model_GUI_calls_by_inspector':0,'Mirage_reduction':None}
 save(target/'summary.json',summary);save(target/'seal.json',{p.name:sha(p)for p in target.iterdir()if p.is_file()});print(json.dumps({'evidence':str(target),**summary}))
if __name__=='__main__':main()
