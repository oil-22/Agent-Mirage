"""Read-only continuation of a sealed native-input audit.

Prior raw tensors are referenced at their recorded verification times. Their
remote seal identities and journal prefixes are checked again; newly sealed
requests retain the original complete raw-file/native-input checks. This is
not a new full rehash of the old corpus. No live experiment source is edited.
"""
import argparse
import ast
import base64
import hashlib
import json
import time
from pathlib import Path

from control import HERE, OUT, R3090, R4090, remote, save, sha
from capture_live_evidence import COMMON


def verify_local_seal(root):
    expected = json.loads((root / 'seal.json').read_bytes())
    assert expected and all(sha(root / n) == h for n, h in expected.items())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', type=Path, required=True)
    args = parser.parse_args()
    prior = args.base.resolve()
    assert prior.parent == HERE and prior.is_dir()
    verify_local_seal(prior)
    previous = json.loads((prior / '3090.json').read_bytes())
    previous_summary = json.loads((prior / 'summary.json').read_bytes())
    original = HERE / 'capture_live_evidence.py'
    tree = ast.parse(original.read_text(encoding='utf8'))
    values = [n.value for n in ast.walk(tree)
              if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    main_sources = [v for v in values if v.startswith('\nimport subprocess\np=Path(PACKAGE);')]
    gui_sources = [v for v in values if v.startswith("\nr=Path(ROOT);out={'time':time.time(),'UID':os.getuid(),'new_GUI_actions_by_inspector':0")]
    assert len(main_sources) == len(gui_sources) == 1
    original_source = main_sources[0]
    old_main_loop = "for d in sorted((r/'primary/requests').iterdir()):"
    old_flash_loop = "for d in sorted((p/'flash/service/requests').iterdir()):"
    assert original_source.count(old_main_loop) == original_source.count(old_flash_loop) == 1
    main_loop = "for d in [r/'primary/requests'/name for name in REQUEST_NAMES]:"
    source = original_source.replace(old_main_loop, main_loop)
    source = source.replace(old_flash_loop, "for d in [p/'flash/service/requests'/name for name in FLASH_NAMES]:")
    boundary = '''for record in BOUNDARIES:
 d=Path(record['folder']);s=json.loads((d/'seal.json').read_bytes())
 assert sha(d/'seal.json')==record['seal_sha256']
 for name in ['wire-request.bin','body.json','response.json']:
  assert sha(d/name)==s[name]
 w=json.loads((d/'wire-request.bin').read_bytes());b=json.loads((d/'body.json').read_bytes());a=json.loads((d/'response.json').read_bytes())
 assert w['body']==b and w['request_id']==record['request_id']
 history[w['run_id']]=b['messages']+[{'role':'assistant','content':a['text']}]
'''
    source = source.replace(main_loop, boundary + main_loop)
    # These assertions are additional to all of the original per-request checks.
    source += '''
'''
    source = source.replace("print(json.dumps(out))", '''
gpu_rows={int(v.split(',')[0].strip()):v.split(',')[1].strip()for v in out['GPU'].splitlines()}
gpu_by_uuid={uuid:index for index,uuid in gpu_rows.items()}
out['actual_compute_processes']=[]
for line in out['compute'].splitlines():
 uuid,pid,memory=[v.strip()for v in line.split(',')]
 index=gpu_by_uuid[uuid];actual=identity(int(pid));owner=out['processes']['Flash'if index==7 else'primary']['actual']
 assert all(actual[k]==owner[k]for k in ['pid','uid','command','start_ticks'])
 out['actual_compute_processes'].append({'physical_GPU':index,'uuid':uuid,'used_mib':memory,'actual':actual})
storage=os.statvfs(r)
out['storage_free_bytes']=storage.f_bavail*storage.f_frsize
print(json.dumps(out))''')
    compile(COMMON + source, '<unchanged-checks-with-incremental-selection>', 'exec')

    dest = HERE / ('live-evidence-incremental-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'inspector-source.py').write_bytes(Path(__file__).read_bytes())
    (dest / 'remote-source-template.py').write_text(COMMON + source, encoding='utf8')
    prior_main = previous['sealed_main_requests']
    prior_flash = previous['sealed_Flash_requests']
    old_main = {Path(v['folder']).name: v for v in prior_main}
    assert len(old_main) == len(prior_main)
    old_flash = {v['request_id']: v for v in prior_flash}
    prefix = {'main': previous_summary['main_chain'], 'Flash': previous_summary['Flash_chain']}
    code = ('ROOT=' + repr(OUT) + '\nPACKAGE=' + repr(R3090) + '\n'
            'OLD_MAIN=' + repr({n: v['seal_sha256'] for n, v in old_main.items()}) + '\n'
            'OLD_FLASH=' + repr({n: v['seal_sha256'] for n, v in old_flash.items()}) + '\n'
            'PREFIX=' + repr(prefix) + '\n' + COMMON + '''
r=Path(ROOT);p=Path(PACKAGE);rows=[]
for d in sorted((r/'primary/requests').iterdir()):
 if not(d/'seal.json').exists():continue
 w=json.loads((d/'wire-request.bin').read_bytes())
 rows.append({'name':d.name,'run_id':w['run_id']})
for name,h in OLD_MAIN.items():assert sha(r/'primary/requests'/name/'seal.json')==h
for name,h in OLD_FLASH.items():assert sha(p/'flash/service/requests'/name/'seal.json')==h
proofs={}
for label,path in [('main',r/'primary/journal/events.jsonl'),('Flash',p/'flash/service/journal/events.jsonl')]:
 proof,events=chain(path);n=PREFIX[label]['verified_prefix_events']
 assert len(events)>=n
 head=hashlib.sha256(canonical(events[n-1])).hexdigest()if n else'0'*64
 assert head==PREFIX[label]['head']
 proofs[label]={'previous_prefix_events':n,'previous_head':head,'current':proof}
print(json.dumps({'time':time.time(),'main':rows,'Flash':[d.name for d in sorted((p/'flash/service/requests').iterdir())if(d/'seal.json').exists()], 'old_remote_seal_identities_verified':{'main':len(OLD_MAIN),'Flash':len(OLD_FLASH)},'journal_prefix_links':proofs,'old_raw_tensors_rehashed':False}))
''')
    raw, op = remote('3090', code, 'incremental-audit-prior-seals-and-prefixes', timeout=55)
    snapshot = json.loads(raw)
    assert set(old_main).issubset({v['name'] for v in snapshot['main']})
    assert set(old_flash).issubset(set(snapshot['Flash']))
    save(dest / 'snapshot.json', {'result': snapshot, 'operation': str(op)})
    save(dest / 'audit-binding.json', {
        'previous_audit': str(prior), 'previous_seal_sha256': sha(prior / 'seal.json'),
        'previous_summary_sha256': sha(prior / 'summary.json'),
        'previous_raw_check_times_are_retained': True,
        'old_raw_tensors_rehashed_in_this_increment': False,
        'original_inspector_sha256': sha(original), 'this_inspector_sha256': sha(Path(__file__)),
        'per_new_request_checks': 'Original full raw seal, native input IDs/pixels/grid and first-forward equality, full history extension, fixed template, generation IDs/EOS/reply; actual processes/locks/chain and GPU identities also checked.',
        'service_prompt_or_experiment_sources_changed': False,
        'new_model_GUI_calls': 0, 'final_full_postexit_rehash_still_required': True})
    additions = [v for v in snapshot['main'] if v['name'] not in old_main]
    new_flash_names = [n for n in snapshot['Flash'] if n not in old_flash]
    all_main = list(prior_main)
    last_per_run = {v['run_id']: v for v in prior_main}
    last_audit = None
    chunks = [[v] for v in additions] or [[]]
    for index, chunk in enumerate(chunks):
        boundaries = [last_per_run[run] for run in sorted({v['run_id'] for v in chunk})
                      if run in last_per_run]
        final = index == len(chunks) - 1
        code = ('PACKAGE=' + repr(R3090) + '\nOUTPUT=' + repr(OUT) + '\n'
                'REQUEST_NAMES=' + repr([v['name'] for v in chunk]) + '\n'
                'FLASH_NAMES=' + repr(new_flash_names if final else []) + '\n'
                'BOUNDARIES=' + repr(boundaries) + '\n' + COMMON + source)
        raw, op = remote('3090', code, 'incremental-native-audit-' + str(index), timeout=55)
        result = json.loads(raw)
        assert len(result['sealed_main_requests']) == len(chunk)
        save(dest / ('batch-%05d.json' % index), {'result': result, 'operation': str(op)})
        all_main.extend(result['sealed_main_requests'])
        for row in result['sealed_main_requests']:
            last_per_run[row['run_id']] = row
        last_audit = result
        print(json.dumps({'new_main_verified': len(all_main) - len(prior_main),
                          'new_main_snapshot_expected': len(additions),
                          'prior_raw_verification_referenced': len(prior_main)}), flush=True)
    assert last_audit is not None
    main_value = dict(last_audit)
    main_value['sealed_main_requests'] = all_main
    main_value['sealed_Flash_requests'] = prior_flash + last_audit['sealed_Flash_requests']
    assert len(all_main) == len(snapshot['main'])
    assert len(main_value['sealed_Flash_requests']) == len(snapshot['Flash'])
    main_value['cumulative_verification_is_linked_not_fresh_full_rehash'] = True
    save(dest / '3090.json', main_value)
    raw, op = remote('4090', 'ROOT=' + repr(R4090) + '\n' + COMMON + gui_sources[0],
                     'incremental-audit-GUI-bindings', timeout=55)
    gui = json.loads(raw)
    first = gui.get('first_image')
    if first:
        data = base64.b64decode(first.pop('base64'))
        (dest / 'first-delivered.png').write_bytes(data)
        assert hashlib.sha256(data).hexdigest() == first['sha256']
    save(dest / '4090.json', gui)
    save(dest / '4090-operation.json', {'operation': str(op)})
    flashes = {v['request_id']: v for v in main_value['sealed_Flash_requests']}
    mains = {v['request_id']: v for v in all_main}
    flash_bound, main_bound, later_main, later_flash = [], [], [], []
    for controller in gui['controllers']:
        for forwarded in controller['forwarded_images']:
            rid = forwarded['gate_request_id']
            if rid is None:
                continue
            if rid not in flashes:
                later_flash.append(rid)
                continue
            assert flashes[rid]['decision'] == 'YES'
            assert flashes[rid]['image_sha256'] == forwarded['image_sha256']
            flash_bound.append(rid)
        for forwarded, request in zip(controller['forwarded_images'], controller['actor_requests']):
            rid = request['request_id']
            if rid not in mains:
                later_main.append(rid)
                continue
            actual = mains[rid]
            assert actual['body_sha256'] == request['body_sha256']
            assert actual['current_image_sha256'] == forwarded['image_sha256']
            main_bound.append(rid)
    summary = {
        'prior_audit': str(prior), 'prior_seal_sha256': sha(prior / 'seal.json'),
        'new_raw_main_replies_verified': len(additions),
        'new_raw_Flash_replies_verified': len(new_flash_names),
        'prior_raw_main_replies_referenced': len(prior_main),
        'prior_raw_Flash_replies_referenced': len(prior_flash),
        'cumulative_verified_main_replies': len(all_main),
        'cumulative_verified_Flash_replies': len(flashes),
        'YES_forwarded_bindings_verified': len(flash_bound),
        'actual_main_input_image_bindings_verified': len(main_bound),
        'later_GUI_main_requests_not_in_snapshot': later_main,
        'later_GUI_Flash_requests_not_in_snapshot': later_flash,
        'main_chain': last_audit['main_chain'], 'Flash_chain': last_audit['Flash_chain'],
        'actual_processes': last_audit['processes'],
        'storage_free_bytes': last_audit['storage_free_bytes'],
        'environment_action_events': sum(len(c['environment_actions']) for c in gui['controllers']),
        'GUI_status': gui['status_snapshot'],
        'snapshot_time': snapshot['time'], 'audit_finished_time': time.time(),
        'old_raw_tensors_rehashed_in_this_increment': False,
        'not_an_atomic_multi_host_snapshot': True,
        'final_full_postexit_rehash_still_required': True,
        'new_model_GUI_calls_by_inspector': 0, 'Mirage_reduction': None}
    save(dest / 'summary.json', summary)
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'evidence': str(dest), **summary}))


if __name__ == '__main__':
    main()
