"""Linked inspector-only repair: unchanged evidence checks in four-request batches.

No service, model call, GUI operation, prompt or experimental source is modified.
Each audited batch has its own immutable receipt. This is a time-bounded corpus
snapshot, not a claim that independently read hosts share one atomic timestamp.
"""
import ast
import base64
import json
import time
from pathlib import Path
from control import HERE, R3090, R4090, OUT, remote, save, sha
from capture_live_evidence import COMMON

original = HERE / 'capture_live_evidence.py'
tree = ast.parse(original.read_text(encoding='utf8'))
constants = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
main_candidates = [s for s in constants if s.startswith('\nimport subprocess\np=Path(PACKAGE);')]
gui_candidates = [s for s in constants if s.startswith("\nr=Path(ROOT);out={'time':time.time(),'UID':os.getuid(),'new_GUI_actions_by_inspector':0")]
assert len(main_candidates) == len(gui_candidates) == 1
main_source, gui_source = main_candidates[0], gui_candidates[0]
old_main_loop = "for d in sorted((r/'primary/requests').iterdir()):"
old_flash_loop = "for d in sorted((p/'flash/service/requests').iterdir()):"
assert main_source.count(old_main_loop) == main_source.count(old_flash_loop) == 1
bounded_source = main_source.replace(old_main_loop, "for d in [r/'primary/requests'/name for name in REQUEST_NAMES]:")
bounded_source = bounded_source.replace(old_flash_loop, "for d in ([p/'flash/service/requests'/name for name in FLASH_NAMES]):")
marker = old_main_loop.replace(old_main_loop, "for d in [r/'primary/requests'/name for name in REQUEST_NAMES]:")
boundary_code = '''for boundary in BOUNDARIES:
 d=Path(boundary);s=json.loads((d/'seal.json').read_bytes())
 for name in ['wire-request.bin','body.json','response.json']:
  assert sha(d/name)==s[name]
 w=json.loads((d/'wire-request.bin').read_bytes());b=json.loads((d/'body.json').read_bytes());a=json.loads((d/'response.json').read_bytes())
 assert w['body']==b
 history[w['run_id']]=b['messages']+[{'role':'assistant','content':a['text']}]
'''
bounded_source = bounded_source.replace(marker, boundary_code + marker)

dest = HERE / ('live-evidence-bounded-' + str(time.time_ns()))
dest.mkdir()
preserved = HERE / 'live-audit-timeout-preservation-1794651399280592600'
assert (preserved / 'seal.json').exists()
for name, expected in json.loads((preserved / 'seal.json').read_bytes()).items():
    assert sha(preserved / name) == expected
save(dest / 'repair-binding.json', {
    'previous_failed_inspector': str(preserved), 'previous_seal_sha256': sha(preserved / 'seal.json'),
    'original_inspector_sha256': sha(original), 'linked_inspector_sha256': sha(Path(__file__)),
    'only_repair': 'Same original SHA/input/lock/history/chain assertions, main requests batched4 and explicit cross-batch history boundary preloads; Flash checked once.',
    'all_original_checks_retained': True, 'new_model_GUI_calls': 0,
    'experiment_sources_changed': False, 'new_attempt_type': 'read-only evidence inspector'
})
code = 'ROOT=' + repr(OUT) + '\nPACKAGE=' + repr(R3090) + '\n' + r'''
import json,time
from pathlib import Path
r=Path(ROOT);p=Path(PACKAGE);rows=[]
for d in sorted((r/'primary/requests').iterdir()):
 if not(d/'seal.json').exists():continue
 w=json.loads((d/'wire-request.bin').read_bytes())
 rows.append({'name':d.name,'run_id':w['run_id']})
print(json.dumps({'time':time.time(),'main':rows,'Flash':[d.name for d in sorted((p/'flash/service/requests').iterdir())if(d/'seal.json').exists()]}))
'''
raw, operation = remote('3090', code, 'bounded-audit-frozen-request-list')
snapshot = json.loads(raw)
save(dest / 'request-list.json', {'snapshot': snapshot, 'operation': str(operation)})
requests = snapshot['main']
assert requests
all_main = []
last_per_run = {}
last_audit = None
for begin in range(0, len(requests), 4):
    chunk = requests[begin:begin+4]
    boundaries = [str(Path(OUT).as_posix() + '/primary/requests/' + last_per_run[run])
                  for run in sorted(set(v['run_id'] for v in chunk)) if run in last_per_run]
    # POSIX paths are remote strings; do not resolve them on the Windows host.
    final = begin + len(chunk) == len(requests)
    code = ('PACKAGE=' + repr(R3090) + '\nOUTPUT=' + repr(OUT) + '\n'
            'REQUEST_NAMES=' + repr([v['name'] for v in chunk]) + '\n'
            'FLASH_NAMES=' + repr(snapshot['Flash'] if final else []) + '\n'
            'BOUNDARIES=' + repr(boundaries) + '\n' + COMMON + bounded_source)
    raw, operation = remote('3090', code, 'bounded-full-evidence-batch-' + str(begin), timeout=55)
    audit = json.loads(raw)
    assert len(audit['sealed_main_requests']) == len(chunk)
    save(dest / ('batch-%05d.json' % begin), {'result': audit, 'operation': str(operation)})
    all_main.extend(audit['sealed_main_requests'])
    last_audit = audit
    for row in chunk:
        last_per_run[row['run_id']] = row['name']
    print(json.dumps({'verified_main_snapshot_prefix': len(all_main), 'expected_at_snapshot': len(requests), 'batch_size': len(chunk)}), flush=True)
main = dict(last_audit)
main['sealed_main_requests'] = all_main
main['main_request_checks_batched_times_in_receipts'] = True
save(dest / '3090.json', main)

code = 'ROOT=' + repr(R4090) + '\n' + COMMON + gui_source
raw, operation = remote('4090', code, 'bounded-audit-actual-GUI-actions')
gui = json.loads(raw)
first_image = gui.get('first_image')
if first_image:
    data = base64.b64decode(first_image.pop('base64'))
    (dest / 'first-delivered.png').write_bytes(data)
    assert sha(dest / 'first-delivered.png') == first_image['sha256']
save(dest / '4090.json', gui)
save(dest / '4090-operation.json', {'operation': str(operation)})
forwarded = {row['gate_request_id']: row for c in gui['controllers'] for row in c['forwarded_images'] if row['gate_request_id'] is not None}
flashes = {row['request_id']: row for row in main['sealed_Flash_requests']}
main_by_id = {row['request_id']: row for row in main['sealed_main_requests']}
bound, newer, actor_bindings = [], [], []
for rid, row in forwarded.items():
    if rid not in flashes:
        newer.append(rid)
        continue
    assert flashes[rid]['decision'] == 'YES' and flashes[rid]['image_sha256'] == row['image_sha256']
    bound.append(rid)
for c in gui['controllers']:
    for forwarded_image, request in zip(c['forwarded_images'], c['actor_requests']):
        actual = main_by_id.get(request['request_id'])
        if actual is None:
            continue
        assert actual['body_sha256'] == request['body_sha256'] and actual['current_image_sha256'] == forwarded_image['image_sha256']
        actor_bindings.append(request['request_id'])
summary = {
    'verified_main_replies': len(all_main), 'verified_Flash_replies': len(flashes),
    'YES_forwarded_bindings_verified': len(bound),
    'actual_main_input_image_bindings_verified': len(actor_bindings),
    'later_GUI_events_beyond_main_snapshot_not_joined': newer,
    'environment_action_events': sum(len(c['environment_actions']) for c in gui['controllers']),
    'main_chain': main['main_chain'], 'Flash_chain': main['Flash_chain'],
    'actual_processes': main['processes'], 'GUI_status': gui['status_snapshot'],
    'new_model_GUI_calls_by_inspector': 0, 'Mirage_reduction': None,
    'corpus_snapshot_time': snapshot['time'], 'audit_finished_time': time.time(),
    'time_bounded_batches': True, 'not_an_atomic_multi_host_snapshot': True,
    'repair_binding': str(dest / 'repair-binding.json')
}
save(dest / 'summary.json', summary)
save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
print(json.dumps({'evidence': str(dest), **summary}))
