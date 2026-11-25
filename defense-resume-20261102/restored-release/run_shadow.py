"""Real local27B verifier preflight. Archived decisions, NO GUI recovery claims."""
import argparse,base64,fcntl,json,os,time,traceback
from pathlib import Path
from defense.core import PublicView,VisibleImage,Journal,Controller,digest
from defense.prompts import SCREEN,VERIFY
from defense.qwen_backend import LocalQwen

def save(p,v):
 t=p.with_suffix('.tmp');t.write_text(json.dumps(v,ensure_ascii=False,indent=2));t.replace(p)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--limit',type=int,default=2);a=ap.parse_args()
 a.root.mkdir(parents=True,exist_ok=True)
 lock=(a.root/'run.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 manifest=json.loads((a.inputs/'shadow-manifest.json').read_text())
 status={'pid':os.getpid(),'phase':'loading','scope':'archived_verifier_preflight','completed_cases':0,'failed_cases':0,'expected_cases':min(a.limit,len(manifest['cases'])),'started':time.time(),'semantic_accuracy':None,'defense_reduction':None}
 save(a.root/'status.json',status)
 model=LocalQwen('/data/llms/Qwen3.8-27B',a.root/'runtime.json')
 expected={'config.json':'191e0af232104ed8b65258cf3fb2b842e288008baca7633c11b82a1ac7203aab','model.safetensors.index.json':'77042094076611b69791a610065f28b7013b8c621795fa86ddccc8bac7d1b9df','preprocessor_config.json':'27225450ac9c6529872ee1924fcb0962ff5634834f817040f444118116f4e516','generation_config.json':'e70c136c1b78ddc1fb0905bac8e733a4dc448d4f852a5dd75143fffc70be550e'}
 assert model.runtime['metadata_sha256']==expected,'Model metadata drift'
 for case in manifest['cases'][:a.limit]:
  folder=a.inputs/case['task'];request=folder/'request.json';response=folder/'response.json'
  assert digest(request.read_bytes())==case['request_sha256']and digest(response.read_bytes())==case['response_sha256']
  attempt=a.root/'attempts'/case['task']/str(time.time_ns());log=Journal(attempt)
  body=json.loads(request.read_text());candidate=json.loads(response.read_text())['choices'][0]['message']['content']
  images=[]
  for m in body['messages']:
   if not isinstance(m['content'],list):continue
   for b in m['content']:
    if b['type']=='image_url':
     url=b['image_url']['url']if isinstance(b['image_url'],dict)else b['image_url'];raw=base64.b64decode(url.split(',',1)[1])
     images.append(VisibleImage(raw,'current'if digest(raw)==case['delivered_sha256']else'reference'))
  assert sum(x.role=='current'for x in images)==1
  view=PublicView(case['task']+'-s'+str(case['step']),body['messages'],tuple(images),observed_at=case['archive_observed_at'])
  log.observation(view);log.append('archived_candidate',{'text':candidate,'request_sha256':case['request_sha256']})
  status.update(phase='checking',task=case['task'],attempt=str(attempt),updated=time.time());save(a.root/'status.json',status)
  try:
   call=0
   def judge(system,public,proposed=None):
    nonlocal call
    call+=1
    return model.judge(system,public,proposed,receipt=attempt/f'call-{call:03}-generation.json')
   controller=Controller(judge,log)
   screen=controller.inspect('screen',view);log.append('screen',screen)
   verdict=controller.inspect('verify',view,candidate);log.append('verdict',verdict)
   result={'screen':screen,'verdict':verdict,'verifier_calls':controller.verifier_calls,'semantic_mirage':None,'live_recaptures':0,'environment_actions':0,'no_accuracy_or_reduction_claim':True}
   save(attempt/'complete.json',result);status['completed_cases']+=1
  except Exception:
   failure={'traceback':traceback.format_exc(),'semantic_mirage':None};save(attempt/'failure.json',failure);log.append('failure',failure);status['failed_cases']+=1
   # Preflight stops on first fault. Preserve original output, do not repair silently.
   status.update(phase='preflight_failed',updated=time.time());save(a.root/'status.json',status);raise
  save(a.root/'status.json',status)
 status.update(phase='completed',updated=time.time());save(a.root/'status.json',status)
if __name__=='__main__':main()
