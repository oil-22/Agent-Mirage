"""Audit one sealed finished GUI trajectory while the remaining new queue runs."""
import ast
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from audit_completed_group import readers, frame_routes
from protocol_audit_components import SOURCE_READER
from control import HERE, PACKAGE, manifest, remote, save, sha


def call(root, name, host, code):
    original_result = REUSE_ROOT / (name + '.json')
    if name in {'Controller', 'trusted-source-receipts', 'request-bindings'} and original_result.exists():
        reused = verified_original_result(original_result)
        save(root / (name + '.json'), reused)
        return reused['result']
    raw, operation = remote(host, code, 'finished-trajectory-linked-' + name, timeout=180)
    value = json.loads(raw)
    save(root / (name + '.json'), {'operation': str(operation), 'result': value})
    return value


def main():
    run = sys.argv[1]
    assert run in {v['run_id'] for v in manifest()['remaining_queue']}
    assert not list(HERE.glob('trajectory-audit-' + run + '-*/seal.json')), 'Use the completed immutable trajectory audit'
    root = HERE / ('trajectory-audit-' + run + '-' + str(time.time_ns()))
    root.mkdir()
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    m = manifest()
    source, values = readers()
    prefix = 'P=' + repr(m['package4090']) + '\nRUN=' + repr(run) + '\n' + values['COMMON']
    controller = call(root, 'Controller', '4090', prefix + r'''
p=Path(P);attempts=list((p/'batch/runs'/RUN).glob('attempt-*'));assert len(attempts)==1
a=attempts[0];proof=verify(a);terminal=json.loads((a/'terminal.json').read_bytes());cp,events=chain(a/'controller/events.jsonl')
assert terminal['run']['run_id']==RUN
print(json.dumps({**proof,'attempt':str(a),'terminal':terminal,'terminal_sha256':sha(a/'terminal.json'),'chain':cp,'events':events}))
''')
    call(root, 'trusted-source-receipts', '4090', 'RUN_FILTER='+repr(run)+'\n'+prefix+SOURCE_READER)
    primary_ids = [v['request_id'] for v in controller['terminal']['actor_receipts']]
    flash_ids = [v['request_id'] for v in controller['terminal']['Flash_replies']]
    prefix = 'P=' + repr(m['package3090']) + '\nO=' + repr(m['output3090']) + '\nRUN=' + repr(run) + '\n' + values['COMMON']
    discovery = call(root, 'request-bindings', '3090', prefix + '\nIDS=' + repr(primary_ids) + '\nFIDS=' + repr(flash_ids) + '\n' + r'''
p=Path(P);o=Path(O);names=[];global_map={}
for q in sorted((o/'primary/requests').iterdir()):
 if not(q/'response.json').exists()or not(q/'seal.json').exists():continue
 response=json.loads((q/'response.json').read_bytes())
 if response['request_id']not in IDS:continue
 names.append(q.name)
 seal=json.loads((q/'seal.json').read_bytes())
 global_map.update({'primary/requests/'+q.name+'/'+n:h for n,h in seal.items()})
 global_map['primary/requests/'+q.name+'/seal.json']=sha(q/'seal.json')
assert len(names)==len(IDS)
for rid in FIDS:
 q=p/'flash/service/requests'/rid;seal=json.loads((q/'seal.json').read_bytes())
 global_map.update({'flash/service/requests/'+rid+'/'+n:h for n,h in seal.items()})
 global_map['flash/service/requests/'+rid+'/seal.json']=sha(q/'seal.json')
print(json.dumps({'primary_names':names,'Flash_names':FIDS,'global':global_map}))
''')
    mains, flashes = [], []
    old_primary = verified_original_result(REUSE_ROOT / 'primary-000.json')
    mains.extend(old_primary['result']['requests'])
    reused_names = {Path(v['folder']).name for v in mains}
    assert len(reused_names) == len(mains) == 8
    assert reused_names <= set(discovery['primary_names'])
    save(root / 'verified-completed-read-reuse.json', {'source': str(REUSE_ROOT), 'primary_requests': len(mains),
                                                     'request_ids': [v['request_id'] for v in mains],
                                                     'preservation_seal_sha256': PRESERVATION_SHA})
    discovery['primary_names'] = [v for v in discovery['primary_names'] if v not in reused_names]
    for kind, names, reader in [('primary', discovery['primary_names'], values['PRIMARY']), ('Flash', discovery['Flash_names'], values['FLASH'])]:
        for i in range(0, len(names), 1):
            result = call(root, kind + '-%03d' % i, '3090', prefix + '\nGLOBAL=' + repr(discovery['global']) + '\nNAMES=' + repr(names[i:i + 1]) + '\n' + reader)
            (mains if kind == 'primary' else flashes).extend(result['requests'])
    checker = HERE.parent / 'flash-resource-continuation-20261115-linked12/controller_audit_reader.py'
    function = next(n for n in ast.parse(checker.read_text('utf8')).body if isinstance(n, ast.FunctionDef) and n.name == 'check_controller')
    namespace = {'hashlib': hashlib}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(checker), 'exec'), namespace)
    parse_node = next(n for n in ast.parse((PACKAGE / 'native-parser-source.py').read_text('utf8')).body if isinstance(n, ast.FunctionDef) and n.name == 'parse')
    parsers = {'json': json, 're': re}
    exec(compile(ast.Module(body=[parse_node], type_ignores=[]), 'original-native-parser', 'exec'), parsers)
    controller['chain']['verified_prefix_events'] = controller['chain']['events']
    bound = {'terminal_sha256': controller['terminal_sha256'], 'seal_sha256': controller['seal_sha256'],
             'event_chain_head': controller['chain']['head'], 'event_chain_count': controller['chain']['events']}
    byid = {v['request_id']: v for v in mains}
    fb = {v['request_id']: v for v in flashes}
    binding = namespace['check_controller'](controller, byid, fb, bound, parsers['parse'])
    route = frame_routes(controller, byid, fb)
    save(root / 'request-results.json', {'primary': mains, 'Flash': flashes})
    save(root / 'summary.json', {'run_id': run, 'binding': binding, 'route': route,
                                'primary_replies': len(mains), 'Flash_replies': len(flashes),
                                'precheck_NO': controller['terminal']['precheck_NO_count'],
                                'full_wire_tensors_original_history_EOS_probabilities_verified': True,
                                'GUI_terminal_sealed': True, 'group_still_running_at_audit': False,
                                'whole_group_postexit_audit_pending': True, 'linked_read_only_IO_repair': True, 'new_model_GUI_calls': 0})
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
    print(json.dumps({'audit': str(root), 'run_id': run, 'primary': len(mains), 'Flash': len(flashes),
                      'precheck_NO': controller['terminal']['precheck_NO_count'],
                      'recovery_loop_verified_pending_independent_image_join': route['wire_bound_recovery_loop'],
                      'whole_group_postexit_audit_pending': True}))



REUSE_ROOT = Path('D:\\MultiModel\\jev-defense-four-gpu-20261106\\flash-trusted-capture-protocol-20261116-06\\trajectory-audit-receipt16-T089-stale_replace-gate-1794809123623714200')
PRESERVATION_ROOT = Path('D:\\MultiModel\\jev-defense-four-gpu-20261106\\flash-trusted-capture-protocol-20261116-06\\audit-IO-repair-1794809502101204700')
PRESERVATION_SHA = 'e66ddd823b2ab2bbab4c2ca0460f2daec1b2eb86ee4286e3f3b333cce9d5d780'

def verified_original_result(path):
    assert sha(PRESERVATION_ROOT / 'seal.json') == PRESERVATION_SHA
    preserved = json.loads((PRESERVATION_ROOT / 'seal.json').read_bytes())
    relative = 'failed-audit/' + path.name
    assert sha(path) == preserved[relative]
    cached = json.loads(path.read_bytes())
    operation = Path(cached['operation'])
    for name, expected in json.loads((operation / 'seal.json').read_bytes()).items():
        assert sha(operation / name) == expected
    assert json.loads((operation / 'receipt.json').read_bytes())['returncode'] == 0
    assert json.loads((operation / 'stdout.txt').read_bytes()) == cached['result']
    return cached


if __name__ == '__main__':
    main()
