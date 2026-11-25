"""Run only the 19 admitted new Flash inputs, once each; no primary/GUI calls.

Never invoke this against an old terminal or replay a completed fingerprint.
"""
import argparse
import base64
import json
from pathlib import Path
import time
import traceback

from defense.core import Journal, canonical, digest
from flash_policy import FlashClient, MODEL, REVISION


def save(path, value):
    with path.open('x', encoding='utf8') as file:
        json.dump(value, file, ensure_ascii=False, indent=2)


def main(a):
    a.root.mkdir(parents=True, exist_ok=False)
    seal = json.loads((a.frozen/'seal.json').read_bytes())
    for name, expected in seal.items():
        assert digest((a.frozen/name).read_bytes()) == expected, name
    plan = json.loads((a.frozen/'plan.json').read_bytes())
    assert plan['revision']==REVISION and plan['model']==MODEL
    assert plan['max_new_flash_calls']==19 and len(plan['requests'])==19
    (a.root/'plan.json').write_bytes((a.frozen/'plan.json').read_bytes())
    client = FlashClient(a.url, a.token_file)
    journal = Journal(a.root/'journal')
    outcomes, error = [], None
    try:
        for item in plan['requests']:
            raw = (a.frozen/item['wire']).read_bytes()
            assert digest(raw) == item['wire_sha256']
            request = json.loads(raw)
            assert digest(canonical({k:v for k,v in request.items() if k!='request_id'})) == item['fingerprint_excluding_request_id']
            assert digest(base64.b64decode(request['image_base64'])) == item['image_sha256']
            assert list(request['options']) == item['native_option_order']
            directory = a.root/item['case_id'];directory.mkdir()
            (directory/'actual-wire-request.json').write_bytes(raw)
            journal.append('flash_preflight_request', {'case_id':item['case_id'],
                'request_sha256':digest(raw), 'fingerprint':item['fingerprint_excluding_request_id'],
                'image_sha256':item['image_sha256']})
            try:
                response = client.send_raw(raw)
            except Exception:
                failure = {'error':traceback.format_exc(), 'case_id':item['case_id'],
                    'actual_model_call_count':None, 'semantic_pass':None,
                    'automatic_retry':False}
                save(directory/'transport-failure.json',failure)
                journal.append('flash_preflight_failure',failure)
                raise
            save(directory/'response.json',response)
            journal.append('flash_preflight_reply', {'case_id':item['case_id'],
                'response_sha256':digest(canonical(response)),
                'remote_receipt':response['receipt'], 'answer':response['answer']})
            outcomes.append({'case_id':item['case_id'], 'answer':response['answer'],
                'probabilities':response['probabilities'], 'receipt':response['receipt'],
                'response_sha256':digest(canonical(response))})
            save(directory/'seal.json',{p.name:digest(p.read_bytes()) for p in directory.iterdir()
                                       if p.is_file()})
            print(json.dumps({'case_id':item['case_id'],'replies':len(outcomes),
                              'answer':response['answer']}),flush=True)
    except Exception:
        error = traceback.format_exc()
    finally:
        save(a.root/'summary.json', {'terminal':True, 'status':'completed' if error is None else 'failed',
            'complete_replies':len(outcomes), 'max_new_flash_calls':19,
            'unattempted_requests':len(plan['requests'])-len(outcomes)-(error is not None),
            'actual_model_calls_require_remote_audit':True, 'error':error,
            'rows':outcomes,'same_known_task_nonblind_development':True,
            'semantic_passes':None,'GUI_actions':0,'primary_27B_calls':0,'paid_API_calls':0,
            'formal_release':False,'automatic_retry':False,'time':time.time()})
        save(a.root/'terminal-sha256.json',{str(p.relative_to(a.root)).replace('\\','/'):digest(p.read_bytes())
                                          for p in a.root.rglob('*') if p.is_file()})
    if error:
        raise SystemExit('New Flash preflight failed; terminal preserved; do not rerun completed inputs')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--frozen',type=Path,required=True);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--url',required=True);p.add_argument('--token-file',type=Path,required=True)
    main(p.parse_args())
