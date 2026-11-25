"""Read-only terminal preservation and bounded SHA audit; never retries a run."""
import concurrent.futures
import json
from pathlib import Path
import time

import orchestrate as current


CHAIN = r'''
def chain(path):
 previous='0'*64;counts={};n=0;digest=hashlib.sha256();size=0
 with path.open('rb')as stream:
  for line in stream:
   digest.update(line);size+=len(line)
   assert line.endswith(b'\n'),'Terminal chain has partial final line'
   event=json.loads(line);signature=event.pop('sha256')
   assert event['seq']==n and event['previous']==previous
   assert hashlib.sha256(json.dumps(event,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==signature
   previous=signature;counts[event['kind']]=counts.get(event['kind'],0)+1;n+=1
 return {'events':n,'head':previous,'counts':counts,'bytes':size,'file_sha256':digest.hexdigest()}

def preserve(path):
 st=path.stat();value={'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'sha256':sha(path)}
 assert path.stat().st_size==st.st_size and path.stat().st_mtime_ns==st.st_mtime_ns
 return value

r=Path(ROOT);out={'time':time.time(),'host':HOST,'read_only':True,'new_model_GUI_scorer_calls':0}
assert sha(Path(PACKAGE)/'manifest.json')==EXPECTED
out['manifest_sha256']=EXPECTED
out['files']={}
if HOST=='3090':
 for name in ['worker/terminal.json','worker/failure.json','worker/status.json','worker/process.json','launcher-process.json','exit.json','worker.log','terminal-manifest.json']:
  p=r/name
  if p.is_file():out['files'][name]=preserve(p)
 out['journal']=chain(r/'worker/journal/events.jsonl')
 out['critical_request_full_SHA_audits']=[]
 for name in ['0015','0017','0133','0134']:
  folder=r/'worker/requests'/name
  seal=json.loads((folder/'seal.json').read_bytes());files={}
  for filename,expected in seal.items():
   item=preserve(folder/filename);assert item['sha256']==expected,filename;files[filename]=item
  out['critical_request_full_SHA_audits'].append({'request':name,'seal_sha256':sha(folder/'seal.json'),'files':files})
 out['request_metadata_inventory']=[]
 for folder in sorted((r/'worker/requests').glob('*')):
  if not folder.is_dir():continue
  wire=json.loads((folder/'external-wire.json').read_bytes());payload=wire['payload']
  op='evidence'if'image_base64'in payload else payload['operation']
  record={'request':folder.name,'operation':op,'trajectory_id':wire['trajectory_id'],'seal_sha256':sha(folder/'seal.json'),'failure':(folder/'failure.json').is_file()}
  native=folder/'native-call.json'
  if native.is_file():
   value=json.loads(native.read_bytes())
   record['native_call_sha256']=sha(native)
   record['native_summary']={k:v for k,v in value.items()if k in ['input_tokens','output_tokens','new_tokens','eos','ended_with_eos','max_new_tokens','seconds','generated_tokens','input_length','output_length','generated_length','eos_reached']}
  out['request_metadata_inventory'].append(record)
else:
 for name in ['control/runner.log','control/exit.json','control/runner-process.json','batch/status.json','batch/uncaught-failure.json']:
  p=r/name
  if p.is_file():out['files'][name]=preserve(p)
 out['runs']=[]
 for run in sorted((r/'batch/runs').glob('*')):
  for attempt in sorted(run.glob('attempt-*')):
   row={'run_id':run.name,'attempt':attempt.name,'files':{}}
   event=attempt/'events.jsonl'
   if event.is_file():row['chain']=chain(event);row['files']['events.jsonl']={'bytes':row['chain']['bytes'],'sha256':row['chain']['file_sha256']}
   for p in sorted(attempt.rglob('*')):
    if p.is_file()and p!=event:row['files'][str(p.relative_to(attempt))]=preserve(p)
   row['all_terminal_files_full_SHA_verified_this_audit']=True
   out['runs'].append(row)
print(json.dumps(out,ensure_ascii=True))
'''


def one(host, target):
    root=current.OUTPUT if host=='3090'else current.GUIROOT
    package=current.REMOTE_PACKAGE if host=='3090'else current.GUIROOT
    code=('HOST='+repr(host)+'\nROOT='+repr(root)+'\nPACKAGE='+repr(package)
          +'\nEXPECTED='+repr(current.sha(current.PACKAGE/'manifest.json'))+'\n'+current.COMMON+CHAIN)
    raw,operation=current.remote(host,code,'postexit-terminal-and-critical-failure-SHA-chain-audit',timeout=55)
    value=json.loads(raw)
    current.save(target/(host+'.json'),value)
    current.save(target/(host+'-operation.json'),{'path':str(operation)})
    return value


def main():
    current.admitted()
    target=current.HERE/('postexit-preservation-'+str(time.time_ns()));target.mkdir()
    results={};errors={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
        jobs={pool.submit(one,host,target):host for host in ['3090','4090']}
        for job in concurrent.futures.as_completed(jobs):
            host=jobs[job]
            try:results[host]=job.result()
            except Exception as exc:errors[host]={'type':type(exc).__name__,'message':str(exc),'inspection_failure_not_model_failure':True}
    current.save(target/'scope.json',{'source_sha256':current.sha(Path(__file__)),
        'critical_service_receipts_only_full_binary_SHA_other_requests_metadata_only':True,
        'all_GUI_terminal_files_and_chains_full_SHA': '4090'in results,
        'errors':errors,'new_model_GUI_scorer_calls':0})
    current.save(target/'seal.json',{p.name:current.sha(p)for p in target.iterdir()if p.is_file()})
    report={'evidence':str(target),'errors':errors}
    for host,value in results.items():
        if host=='3090':report[host]={'journal':value['journal'],'requests':len(value['request_metadata_inventory']),
          'failed':[p['request']for p in value['request_metadata_inventory']if p['failure']],
          'critical_full_SHA':[p['request']for p in value['critical_request_full_SHA_audits']]}
        else:report[host]=[{'run_id':p['run_id'],'files':len(p['files']),'chain':p.get('chain')}for p in value['runs']]
    print(json.dumps(report,ensure_ascii=True))


if __name__=='__main__':main()
