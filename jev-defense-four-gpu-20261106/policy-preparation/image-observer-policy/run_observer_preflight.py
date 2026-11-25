"""Send only sealed neutral image observer inputs once; no main model or GUI."""
import argparse,base64,json,time,traceback
from pathlib import Path
from defense.core import Journal,canonical,digest
from image_observer import ObserverClient,MODEL,REVISION,QUESTIONS,STATE


def save(path,value):
    with path.open('x',encoding='utf8')as f:json.dump(value,f,ensure_ascii=False,indent=2)


def main(a):
    a.root.mkdir(parents=True,exist_ok=False)
    for name,sha in json.loads((a.frozen/'seal.json').read_bytes()).items():assert digest((a.frozen/name).read_bytes())==sha,name
    plan=json.loads((a.frozen/'plan.json').read_bytes())
    assert plan['revision']==REVISION and plan['model']==MODEL
    cap=plan['max_new_flash_calls'];assert type(cap)is int and 1<=cap<=60 and len(plan['requests'])==cap
    (a.root/'plan.json').write_bytes((a.frozen/'plan.json').read_bytes())
    client=ObserverClient(a.url,a.token_file);journal=Journal(a.root/'journal')
    outcomes=[];attempted=0;error=None
    try:
        for item in plan['requests']:
            raw=(a.frozen/item['wire']).read_bytes();assert digest(raw)==item['wire_sha256']
            body=json.loads(raw)
            assert digest(canonical({k:v for k,v in body.items()if k!='request_id'}))==item['fingerprint_excluding_request_id']
            assert digest(base64.b64decode(body['image_base64'],validate=True))==item['image_sha256']
            assert body['state']==STATE and body['questions']==QUESTIONS and list(body['questions'])==list(QUESTIONS)
            assert all(list(body['questions'][k]['criteria'])==list(QUESTIONS[k]['criteria'])for k in QUESTIONS)
            root=a.root/item['case_id'];root.mkdir();(root/'actual-wire-request.json').write_bytes(raw)
            journal.append('image_observer_preflight_request',{'case_id':item['case_id'],
                'wire_sha256':digest(raw),'image_sha256':item['image_sha256']})
            attempted+=1
            try:response=client.send_raw(raw)
            except Exception:
                if client.last_response_raw is not None:(root/'actual-wire-failed-response.json').write_bytes(client.last_response_raw)
                save(root/'failure.json',{'traceback':traceback.format_exc(),'automatic_retry':False,'semantic_pass':None})
                raise
            (root/'actual-wire-response.json').write_bytes(client.last_response_raw)
            save(root/'response.json',response)
            row={'case_id':item['case_id'],'image_sha256':item['image_sha256'],'answers':response['answers'],
                'usage':response['usage'],'receipt':response['receipt'],
                'response_sha256':digest(canonical(response))}
            journal.append('image_observer_preflight_reply',row);outcomes.append(row)
            save(root/'seal.json',{p.name:digest(p.read_bytes())for p in root.iterdir()if p.is_file()})
            print(json.dumps({'case_id':item['case_id'],'complete_replies':len(outcomes),
                'choices':{k:v['choice']for k,v in response['answers'].items()}}),flush=True)
    except Exception:error=traceback.format_exc()
    finally:
        save(a.root/'summary.json',{'terminal':True,'status':'completed'if error is None else'failed',
            'complete_replies':len(outcomes),'attempted_requests':attempted,'max_new_flash_calls':cap,
            'unattempted_requests':cap-attempted,'actual_model_calls_require_remote_audit':True,
            'error':error,'rows':outcomes,'same_known_source_nonblind_development':True,
            'semantic_passes':None,'GUI_actions':0,'primary_27B_calls':0,'paid_API_calls':0,
            'formal_release':False,'automatic_retry':False,'time':time.time()})
        save(a.root/'terminal-sha256.json',{str(p.relative_to(a.root)).replace('\\','/'):digest(p.read_bytes())for p in a.root.rglob('*')if p.is_file()})
    if error:raise SystemExit('Observer preflight failed and preserved; do not rerun terminal inputs')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['frozen','root','token-file']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--url',required=True);main(p.parse_args())
