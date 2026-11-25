"""Copy the already captured next observation, without a new GUI capture."""
import base64
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'full-history-gui-development-20261109-23'))
from remote_control import remote, save, sha


CODE = r'''
from pathlib import Path
import base64,hashlib,json,os,time
root=Path('/data/researcher/jev-defense-four-gpu-20261106/prefill-scheduled-full-history-gui-20261109-32')
identity=json.loads((root/'control/runner-process.json').read_bytes())
proc=Path('/proc',str(identity['pid']));assert proc.stat().st_uid==identity['uid']==1015
assert (proc/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip()==identity['command']
assert (proc/'stat').read_text().rsplit(')',1)[1].split()[19]==identity['start_ticks']=='121404726'
attempt=root/'batch/runs/fullhistory23-T000-clean-noaux/attempt-1794230110024661434'
raw=(attempt/'events.jsonl').read_bytes();raw=raw[:raw.rfind(b'\n')+1]
events=[];previous='0'*64
canonical=lambda v:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
for line in raw.splitlines():
 e=json.loads(line);sig=e.pop('sha256')
 assert e['seq']==len(events)and e['previous']==previous and hashlib.sha256(canonical(e)).hexdigest()==sig
 e['sha256']=sig;events.append(e);previous=sig
candidate=next(e for e in events if e['kind']=='candidate'and e['sha256'].startswith('c94c66947622a0224b5f'))
accepted=next(e for e in events[candidate['seq']+1:]if e['kind']=='decision_accepted')
assert accepted['data']['candidate']==candidate['data']['text']
executed=next(e for e in events[accepted['seq']+1:]if e['kind']=='action_executed')
assert executed['data']['proposal']==accepted['data']['proposal']
next_observation=next(e for e in events[executed['seq']+1:]if e['kind']=='observation')
public=next_observation['data']['public']
image=next(im for im in public['images']if im['role']=='current')
picture=(attempt/(image['sha256']+'.image')).read_bytes()
assert hashlib.sha256(picture).hexdigest()==image['sha256']
print(json.dumps({'time':time.time(),'read_only':True,'candidate_event_sha256':candidate['sha256'],
 'accepted_event_sha256':accepted['sha256'],'executed_event_sha256':executed['sha256'],
 'next_observation_event_sha256':next_observation['sha256'],'next_observation_id':public['observation_id'],
 'next_observation_current_image':image,'original_capture_png_base64':base64.b64encode(picture).decode(),
 'journal_snapshot':{'events':len(events),'head':previous,'complete_prefix_sha256':hashlib.sha256(raw).hexdigest()},
 'new_model_GUI_capture_agent_action_scorer_calls':0,'not_a_claim_of_task_completion':True},ensure_ascii=False))
'''


if __name__ == '__main__':
    assert not (HERE / 'candidate21-postexecution-frame-created.json').exists()
    joinpath = HERE / 'post-review-join-1794232769637741600/join.json'
    assert sha(joinpath) == json.loads((joinpath.parent / 'seal.json').read_bytes())['join.json']
    output, operation = remote('4090', CODE, 'read-already-captured-next-frame-after-candidate21-execution', timeout=55)
    result = json.loads(output)
    picture = base64.b64decode(result.pop('original_capture_png_base64'), validate=True)
    out = HERE / ('candidate21-postexecution-frame-' + str(time.time_ns()))
    out.mkdir()
    (out / '022-originally-captured.png').write_bytes(picture)
    assert sha(out / '022-originally-captured.png') == result['next_observation_current_image']['sha256']
    result.update(remote_operation=str(operation), source_sealed_execution_join=str(joinpath),
                  source_sealed_execution_join_sha256=sha(joinpath), image_requires_independent_visual_review=True)
    save(out / 'receipt.json', result)
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    save(HERE / 'candidate21-postexecution-frame-created.json', {
        'root': str(out), 'receipt_sha256': sha(out / 'receipt.json'), 'seal_sha256': sha(out / 'seal.json')})
    print(json.dumps({'root': str(out), 'image_sha256': result['next_observation_current_image']['sha256'],
                      'next_observation': result['next_observation_id'], 'new_GUI_captures_or_actions': 0}))
