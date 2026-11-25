"""Copy an existing post-action observation after a sealed source/outcome join."""
import argparse
import base64
import json
from pathlib import Path
import re
import time

from orchestrate import HERE, GUIROOT, remote, save, sha
from join_source_reviews import verify_seal


SOURCE = r'''
from pathlib import Path
import base64,hashlib,json,time
root=Path(ROOT).resolve();attempt=Path(ATTEMPT).resolve()
assert attempt.parent.parent==root/'batch/runs'
raw=(attempt/'events.jsonl').read_bytes();raw=raw[:raw.rfind(b'\n')+1]
events=[];previous='0'*64
canonical=lambda v:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
for line in raw.splitlines():
 e=json.loads(line);sig=e.pop('sha256')
 assert e['seq']==len(events)and e['previous']==previous and hashlib.sha256(canonical(e)).hexdigest()==sig
 e['sha256']=sig;events.append(e);previous=sig
candidate=next(e for e in events if e['kind']=='candidate'and e['sha256']==CANDIDATE)
accepted=next(e for e in events if e['sha256']==ACCEPTED)
executed=next(e for e in events if e['sha256']==EXECUTED)
assert candidate['seq']<accepted['seq']<executed['seq']
assert accepted['kind']=='decision_accepted'and accepted['data']['candidate']==candidate['data']['text']
assert executed['kind']=='action_executed'and executed['data']['proposal']==accepted['data']['proposal']
assert executed['data']['observation_id']==accepted['data']['observation_id']
next_observation=next((e for e in events[executed['seq']+1:]if e['kind']=='observation'),None)
result={'time':time.time(),'read_only':True,'candidate_event_sha256':CANDIDATE,
 'accepted_event_sha256':ACCEPTED,'executed_event_sha256':EXECUTED,
 'journal_snapshot':{'events':len(events),'head':previous,'complete_prefix_sha256':hashlib.sha256(raw).hexdigest()},
 'new_model_GUI_capture_agent_action_scorer_calls':0,'task_completion_not_established':True}
if next_observation is None:result['existing_postexecution_observation_available']=False
else:
 public=next_observation['data']['public'];image=next(im for im in public['images']if im['role']=='current')
 picture=(attempt/(image['sha256']+'.image')).read_bytes()
 assert hashlib.sha256(picture).hexdigest()==image['sha256']
 result.update(existing_postexecution_observation_available=True,
  next_observation_event_sha256=next_observation['sha256'],next_observation_id=public['observation_id'],
  next_observation_current_image=image,original_capture_png_base64=base64.b64encode(picture).decode())
print(json.dumps(result,ensure_ascii=False))
'''


def main(joinpath, ident):
    assert re.fullmatch(r'[0-9a-f]{20}', ident)
    assert joinpath.parent.parent == HERE
    verify_seal(joinpath.parent)
    joined = json.loads(joinpath.read_bytes())
    assert joined['all_source_labels_sealed_before_this_join']
    row = next(row for row in joined['rows'] if row['id'] == ident)
    assert row['accepted'] and row['executed']
    assert len(row['accepted_events']) == len(row['executed_events']) == 1
    pointer = HERE / ('postexecution-frame-' + ident + '-created.json')
    assert not pointer.exists(), 'A collected original frame must not be overwritten'
    prefix = ('ROOT=' + repr(GUIROOT) + '\nATTEMPT=' + repr(row['original_attempt'])
              + '\nCANDIDATE=' + repr(row['candidate_event_sha256'])
              + '\nACCEPTED=' + repr(row['accepted_events'][0]['sha256'])
              + '\nEXECUTED=' + repr(row['executed_events'][0]['sha256']) + '\n')
    output, operation = remote('4090', prefix + SOURCE, 'linked31-read-existing-postexecution-frame-' + ident, timeout=55)
    result = json.loads(output)
    if not result['existing_postexecution_observation_available']:
        print(json.dumps(dict(existing_postexecution_observation_available=False, operation=str(operation))))
        return
    picture = base64.b64decode(result.pop('original_capture_png_base64'), validate=True)
    root = HERE / ('postexecution-frame-' + ident + '-' + str(time.time_ns()))
    root.mkdir()
    filename = 'original-postexecution.png'
    (root / filename).write_bytes(picture)
    assert sha(root / filename) == result['next_observation_current_image']['sha256']
    result.update(remote_operation=str(operation), source_sealed_execution_join=str(joinpath),
                  source_sealed_execution_join_sha256=sha(joinpath), image_requires_visual_review=True)
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(root / 'receipt.json', result)
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    authority = dict(root=str(root), receipt_sha256=sha(root / 'receipt.json'),
                     seal_sha256=sha(root / 'seal.json'), image_sha256=sha(root / filename))
    save(pointer, authority)
    print(json.dumps(authority, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--join', type=Path, required=True)
    parser.add_argument('--id', required=True)
    args = parser.parse_args()
    main(args.join.resolve(), args.id)
