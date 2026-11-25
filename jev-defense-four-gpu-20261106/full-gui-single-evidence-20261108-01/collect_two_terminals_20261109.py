"""Read-only verification and public mirror of the stopped full GUI batch."""
import argparse,base64,hashlib,io,json,time,zipfile
from pathlib import Path
from remote_control import HERE,ROOT3090,ROOT4090,remote,save,sha

CODE=r'''
from pathlib import Path
import base64,collections,hashlib,io,json,os,struct,time,zipfile
r=Path(ROOT)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def chain(p):
 previous='0'*64;events=[]
 for line in p.read_bytes().splitlines():
  v=json.loads(line);s=v.pop('sha256')
  assert v['seq']==len(events) and v['previous']==previous
  assert hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==s
  previous=s;events.append(v)
 return events,{'events':len(events),'head':previous,'all_verified':True}
def absent(p):
 v=json.loads(p.read_bytes());assert not Path('/proc',str(v['pid'])).exists(),str(p)
 return {'recorded_identity':v,'actual_proc_absent':True}
audit={'host':HOST,'time_unix':time.time(),'remote_read_only':True,'model_HTTP_GUI_calls':0}
public=[]
if HOST=='3090':
 audit['processes']={n:absent(r/n) for n in ['launcher-process.json','worker/process.json']}
 manifest=json.loads((r/'terminal-manifest.json').read_bytes());hashes={}
 for n,h in manifest.items():
  p=r/n;actual=sha(p);assert actual==h,n;hashes[n]=actual
 audit['terminal_manifest_sha256']=sha(r/'terminal-manifest.json');audit['remote_terminal_files_SHA_verified']=len(hashes)
 _,audit['journal']=chain(r/'worker/journal/events.jsonl')
 audit['exit']=json.loads((r/'exit.json').read_bytes());audit['terminal']=json.loads((r/'worker/terminal.json').read_bytes())
 counters=collections.Counter();tokens=collections.defaultdict(lambda:{'input':0,'output':0,'seconds_including_instrumentation':0})
 aux=[];calls=[]
 for folder in sorted((r/'worker/requests').iterdir()):
  if not folder.is_dir():continue
  seal=json.loads((folder/'seal.json').read_bytes())
  for n,h in seal.items():assert hashes[(folder/n).relative_to(r).as_posix()]==h,(folder,n)
  response=json.loads((folder/'response.json').read_bytes());payload=json.loads((folder/'payload.json').read_bytes())
  op=response['operation'];wire=(folder/'external-wire.json').read_bytes();body=json.loads(wire)
  assert response['request_id']==body['request_id'] and response['external_wire_sha256']==hashlib.sha256(wire).hexdigest()
  assert payload==body['payload'] and response['payload_sha256']==hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
  prepared=json.loads((folder/'prepared.json').read_bytes());first=json.loads((folder/'first-forward.json').read_bytes())
  assert set(prepared)==set(first)
  for n in prepared:
   assert all(prepared[n][k]==first[n][k] for k in ['shape','dtype','bytes','sha256']),(folder,n)
  actual=json.loads((folder/'actual-generation.json').read_bytes());counters[op]+=1
  counters[op+'_EOS' if actual['natural_EOS'] else op+'_nonEOS']+=1
  tokens[op]['input']+=actual['input_tokens'];tokens[op]['output']+=actual['output_tokens']
  tokens[op]['seconds_including_instrumentation']+=response['seconds_including_instrumentation']
  if op!='evidence':
   native=json.loads((folder/'native-call.json').read_bytes())
   assert native['generated_ids']==actual['output_ids']
   assert prepared['input_ids']['dtype']=='torch.int64'
   input_bytes=struct.pack('<'+'q'*len(native['input_ids']),*native['input_ids'])
   assert hashlib.sha256(input_bytes).hexdigest()==prepared['input_ids']['sha256']
  else:
   error=json.loads((folder/'contract-failure.json').read_bytes()) if (folder/'contract-failure.json').exists() else None
   aux.append({'call':folder.name,'contract_valid':(folder/'evidence-packet.json').exists(),'contract_error':error,
       'natural_EOS':actual['natural_EOS'],'input_tokens':actual['input_tokens'],'output_tokens':actual['output_tokens']})
  calls.append({'call':folder.name,'operation':op,'trajectory_id':body['trajectory_id'],'decision_index':body['decision_index'],
      'attempt_index':body['attempt_index'],'natural_EOS':actual['natural_EOS'],'seal_sha256':sha(folder/'seal.json')})
 audit.update(counts=dict(counters),tokens=dict(tokens),auxiliary=aux,calls=calls,
     all_native_inputIDs_first_forward_outputIDs_and_seals_verified=True,raw_tensor_bytes_mirrored_locally=False)
 for p in r.rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(r)
  if p.suffix in ['.json','.jsonl','.txt','.log','.png','.image'] and 'private' not in p.name.lower():public.append((rel.as_posix(),p))
else:
 audit['processes']={n:absent(r/n) for n in ['control/process.json','control/runner-process.json']}
 manifest=json.loads((r/'control/batch-terminal-manifest.json').read_bytes());hashes={}
 for n,h in manifest.items():
  actual=sha(r/'batch'/n);assert actual==h,n;hashes[n]=actual
 seal=json.loads((r/'control/seal.json').read_bytes())
 for n,h in seal.items():assert sha(r/'control'/n)==h,n
 audit.update(remote_batch_files_SHA_verified=len(hashes),batch_terminal_manifest_sha256=sha(r/'control/batch-terminal-manifest.json'),
     control_seal_sha256=sha(r/'control/seal.json'),control_exit=json.loads((r/'control/exit.json').read_bytes()))
 runs=[]
 for run in sorted((r/'batch/runs').iterdir()):
  for a in sorted(run.glob('attempt-*')):
   ev,journal=chain(a/'events.jsonl')
   terminal=next(a/n for n in ['complete.json','technical-failure.json','failure.json'] if (a/n).exists())
   t=json.loads(terminal.read_bytes());t.pop('calls',None)
   candidates=[e for e in ev if e['kind']=='candidate']
   failures=[e for e in ev if e['kind']=='verifier_format_failure']
   packets=[e for e in ev if e['kind']=='neutral_evidence_packet']
   actions=[e for e in ev if e['kind']=='action_executed']
   runs.append({'run_id':run.name,'attempt':str(a),'terminal_sha256':sha(terminal),'terminal':t,'journal':journal,
       'candidate_count':len(candidates),'execution_count':len(actions),'format_failures':failures,
       'last_candidate':candidates[-1] if candidates else None,'last_verifier_raw':[e for e in ev if e['kind']=='verifier_raw'][-3:],
       'auxiliary_packet_statuses':[e['data'].get('status') for e in packets],
       'auxiliary_failure_details':[e for e in ev if e['kind']=='neutral_evidence_failure'],
       'last_rejections':[e for e in ev if e['kind'] in ['verdict','appearance_absence_source','candidate_claim_origin_check','decision_blocked']][-10:]})
 audit['runs']=runs
 for prefix in ['control','batch']:
  for p in (r/prefix).rglob('*'):
   if not p.is_file() or '.auth' in p.parts or p.name=='official_config.json' or 'PRIVATE' in p.name or p.suffix in ['.pkl','.zip']:continue
   if p.suffix in ['.json','.jsonl','.txt','.log','.png','.image']:public.append((p.relative_to(r).as_posix(),p))
buffer=io.BytesIO()
with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
 for n,p in public:z.writestr(n,p.read_bytes())
audit['public_mirrored_files']={n:sha(p) for n,p in public}
print(json.dumps({'audit':audit,'archive_base64':base64.b64encode(buffer.getvalue()).decode()},ensure_ascii=False))
'''

def main(host):
    code='HOST='+repr(host)+'\nROOT='+repr(ROOT3090 if host=='3090' else ROOT4090)+'\n'+CODE
    out,evidence=remote(host,code,'collect-terminal-'+host,timeout=240)
    value=json.loads(out);target=HERE/'terminal-collections-20261109'/(str(time.time_ns())+'-'+host);target.mkdir(parents=True,exist_ok=False)
    (target/'original').mkdir()
    archive=base64.b64decode(value['archive_base64'])
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for name in z.namelist():assert (target/'original'/name).resolve().is_relative_to((target/'original').resolve())
        z.extractall(target/'original')
    for n,h in value['audit']['public_mirrored_files'].items():assert sha(target/'original'/n)==h,n
    save(target/'audit.json',value['audit']);save(target/'collection.json',{'operation':str(evidence),'archive_sha256':hashlib.sha256(archive).hexdigest(),
        'audit_sha256':sha(target/'audit.json'),'public_files_verified':len(value['audit']['public_mirrored_files']),'remote_read_only':True})
    save(target/'seal.json',{'audit.json':sha(target/'audit.json'),'collection.json':sha(target/'collection.json')})
    print(json.dumps({'host':host,'collection':str(target),'audit_sha256':sha(target/'audit.json'),
        'public_files':len(value['audit']['public_mirrored_files']),
        'verified_remote_terminal_files':value['audit'].get('remote_terminal_files_SHA_verified',value['audit'].get('remote_batch_files_SHA_verified')),
        'counts':value['audit'].get('counts'), 'auxiliary':value['audit'].get('auxiliary'),
        'runs':[{'run_id':r['run_id'],'terminal':r['terminal'],'journal':r['journal']} for r in value['audit'].get('runs',[])]},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('host',choices=['3090','4090']);main(p.parse_args().host)
