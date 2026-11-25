"""Export original PNGs from sealed trajectories for image usability review only."""
import base64
import hashlib
import json
import sys
import time
from pathlib import Path

from audit_completed_group_bound_reuse import readers
from control import HERE, manifest, remote, save, sha


CODE = r'''
import base64
p=Path(P);images={};rows=[]
for a in sorted((p/'batch/runs').glob('*/attempt-*')):
 if RUNS and a.parent.name not in RUNS:continue
 if not(a/'terminal.json').exists():continue
 proof=verify(a);terminal=json.loads((a/'terminal.json').read_bytes())
 cp,events=chain(a/'controller/events.jsonl')
 by_kind=lambda kind:{v['data']['capture_id']:v for v in events if v['kind']==kind}
 gates=by_kind('gate_decision');receipts=by_kind('capture_receipt_decision')
 presences=by_kind('image_presence_check');forwards=by_kind('main_image_forwarded')
 frames=[]
 for e in events:
  if e['kind']!='PRIVATE_capture_injection':continue
  d=e['data'];cid=d['capture_id'];raw=(a/d['raw_file']).read_bytes()
  digest=hashlib.sha256(raw).hexdigest();assert digest==d['captured_sha256']
  assert raw.startswith(b'\x89PNG\r\n\x1a\n')
  images[digest]=base64.b64encode(raw).decode()
  receipt=receipts.get(cid);gate=gates.get(cid);forward=forwards.get(cid)
  if not d['injected']:
   assert d['captured_sha256']==d['delivered_sha256']
   if receipt:assert receipt['data']['decision']=='YES'
   if gate:assert gate['data']['image_sha256']==digest
   if forward:assert forward['data']['image_sha256']==digest
  frames.append({'capture_id':cid,'step':d['step'],'capture_index':d['capture_index'],
    'capture_kind':d['capture_kind'],'injected':d['injected'],'sha256':digest,
    'raw_path':str(a/d['raw_file']),'bytes':len(raw),
    'presence':presences.get(cid),'receipt':receipt,'Flash':gate,'forward':forward,
    'event_seq':e['seq']})
 rows.append({'run_id':a.parent.name,'condition':terminal['run']['condition'],
    'attempt':str(a),'terminal_sha256':sha(a/'terminal.json'),
    'trajectory_seal_sha256':proof['seal_sha256'],'controller_chain':cp,'frames':frames})
assert not RUNS or set(RUNS)=={v['run_id']for v in rows},'Requested trajectory must be complete'
print(json.dumps({'time':time.time(),'rows':rows,'images_base64':images,
 'new_model_GUI_calls':0,'review_includes_gate_results_not_blind':True}))
'''


def main():
    requested = sys.argv[1:]
    allowed = {v['run_id'] for v in manifest()['remaining_queue']}
    assert set(requested).issubset(allowed)
    _, values = readers()
    code = 'P=' + repr(manifest()['package4090']) + '\nRUNS=' + repr(requested) + '\n' + values['COMMON'] + '\n' + CODE
    raw, operation = remote('4090', code, 'export-sealed-original-review-frames', timeout=180)
    value = json.loads(raw)
    root = HERE / ('normal-frame-export-' + str(time.time_ns()))
    root.mkdir()
    folder = root / 'images'
    folder.mkdir()
    for expected, encoded in value.pop('images_base64').items():
        content = base64.b64decode(encoded, validate=True)
        assert hashlib.sha256(content).hexdigest() == expected
        (folder / (expected + '.png')).write_bytes(content)
    save(root / 'sources.json', {'operation': str(operation), **value})
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
    print(json.dumps({'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
       'complete_trajectories': len(value['rows']), 'unique_original_PNGs': len(list(folder.glob('*.png'))),
       'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
