"""Join an already sealed source label to the first execution of pending17."""
import base64
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(HERE))
from orchestrate import COMMON, GUIROOT, remote, save, sha


def main():
    assert not (HERE / 'pending17-execution-join-created.json').exists()
    pointer = json.loads((BASE / 'memory-scheduled-full-history-gui-20261109-29/source-review-04-created.json').read_bytes())
    review = Path(pointer['review']) / 'review.json'
    assert sha(review) == pointer['review_sha256']
    label = next(r for r in json.loads(review.read_bytes())['rows'] if r['id'] == 'd927e4c942df2e2a9142')
    text = '<action>{"type":"click","x":615,"y":678}</action>'
    code = 'ROOT=' + repr(GUIROOT) + '\nTEXT=' + repr(text) + '\n' + COMMON + r'''
import base64
r=Path(ROOT);attempts=sorted((r/'batch/runs/fullhistory23-T000-clean-noaux').glob('attempt-*'));assert len(attempts)==1
a=attempts[0];raw=(a/'events.jsonl').read_bytes();lines=raw.splitlines();lines=lines[:-1]if raw and not raw.endswith(b'\n')else lines
events=[];previous='0'*64
for line in lines:
 row=json.loads(line);copy=dict(row);signature=copy.pop('sha256')
 assert copy['seq']==len(events)and copy['previous']==previous
 assert hashlib.sha256(json.dumps(copy,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==signature
 events.append(row);previous=signature
cached=[e for e in events if e['kind']=='carryover_replay_candidate'and e['data']['text']==TEXT];assert len(cached)==1
accepted=[e for e in events if e['kind']=='decision_accepted'and e['data'].get('candidate')==TEXT];assert len(accepted)==1
verdict=accepted[0];assert verdict['data']['proposal']['payload']=={'type':'click','x':615,'y':678}
executed=[e for e in events if e['kind']=='action_executed'and e['data']['observation_id']==verdict['data']['observation_id']]
assert len(executed)==1 and executed[0]['data']['proposal']==verdict['data']['proposal']
feedback=json.loads(executed[0]['data']['feedback']);assert feedback['execution_returned']and not feedback['error']
returned=[e for e in events if e['kind']=='pending17_original_pipeline_returned'];assert len(returned)==1
assert returned[0]['data']['actor_total_spent']==17 and returned[0]['data']['judge_total_spent']==52
assert returned[0]['data']['new_actual_judge_calls']==2 and returned[0]['data']['new_actual_actor_calls']==0
assert returned[0]['data']['additional_recaptures']==0
restored=json.loads((a/'native-restoration-receipt.json').read_bytes());assert restored['pixel_identity_passed']
next_capture=a/'screenshots/018-captured.png';assert next_capture.is_file()
print(json.dumps({'time':time.time(),'attempt':str(a),'cached_candidate_event':cached[0],
 'accepted_event':verdict,'execution_event':executed[0],'original_pipeline_returned':returned[0],
 'restoration':restored,'restoration_receipt_sha256':sha(a/'native-restoration-receipt.json'),
 'next_original_capture_sha256':sha(next_capture),'next_original_capture_base64':base64.b64encode(next_capture.read_bytes()).decode(),
 'committed_event_chain':{'events':len(events),'head':previous},'new_model_GUI_scorer_paid_calls':0,'remote_read_only':True}))
'''
    compile(code, 'collect-pending17-first-execution-only', 'exec')
    output, operation = remote('4090', code, 'new32-bind-sealed-old17-source-label-first-native-execution-readonly', timeout=55)
    value = json.loads(output)
    out = HERE / ('pending17-execution-join-' + str(time.time_ns())); out.mkdir()
    raw = base64.b64decode(value.pop('next_original_capture_base64'), validate=True)
    (out / '018-actually-captured.png').write_bytes(raw)
    assert sha(out / '018-actually-captured.png') == value['next_original_capture_sha256']
    save(out / 'execution-evidence.json', dict(value, operation=str(operation)))
    join = {'schema': 'sealed-source29-pending17-first-execution-GUI32-join-v1',
        'time': time.time(), 'source_review': str(review), 'source_review_sha256': sha(review),
        'source_label': label, 'source_sealed_before_new32_execution': True,
        'candidate_replayed_and_executed_once_not_a_new_semantic_label': True,
        'old29_pending17_was_not_executed': True,
        'new32_original_candidate_accepted_and_executed': True,
        'original_native_point_and_alignment_checks_completed': True,
        'new_actual_judge_calls': 2, 'original_actor_spent': 17, 'original_judge_spent': 52,
        'original_actions_total_now': 17, 'restoration_original_recapture_spent': 1,
        'additional_recaptures_or_regenerations': 0,
        'evidence_sha256': sha(out / 'execution-evidence.json'),
        'next_original_capture_sha256': value['next_original_capture_sha256'],
        'next_image_requires_visual_review_before_content_claim': True,
        'full_trajectory_Mirage': None, 'efficacy_established': False,
        'new_model_GUI_scorer_paid_calls_in_this_join': 0}
    save(out / 'join.json', join)
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    save(HERE / 'pending17-execution-join-created.json', {'join': str(out / 'join.json'),
        'join_sha256': sha(out / 'join.json'), 'seal_sha256': sha(out / 'seal.json')})
    print(json.dumps({'join': str(out / 'join.json'), 'original_actions': 17,
                      'actor_spent': 17, 'judge_spent': 52, 'next_capture': str(out / '018-actually-captured.png')}))


if __name__ == '__main__':
    main()
