"""Postexit full raw audit, with separate missing-image and Flash refusals."""
import ast
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from control import HERE, PACKAGE, manifest, remote, save, sha


def readers():
    source = HERE.parent / 'flash-injection-first-defense-20261115-01/audit_completed_group.py'
    values = {}
    for node in ast.parse(source.read_text('utf8')).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            values[node.targets[0].id] = node.value.value
    common = values['COMMON']
    common = common.replace('key=(str(p),s.st_size,s.st_mtime_ns)', 'key=(str(p),s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)')
    common = common.replace('assert p.stat()==s,str(p)', 'after=p.stat();assert (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)==(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns),str(p)')
    values['COMMON'] = common
    values['ADMISSION'] = values['ADMISSION'].replace("status['expected']==4", "status['expected']==26").replace(
        "assert status['attempted_actor_calls']==status['complete_actor_replies']==103",
        "assert status['attempted_actor_calls']==status['complete_actor_replies'] and 0<status['complete_actor_replies']<=26*70").replace(
        'assert len(names)==103 and len(fnames)==70', "assert len(names)==status['complete_actor_replies'] and len(fnames)>0")
    gui = values['GUI'].replace("status['expected']==4", "status['expected']==26").replace('len(controllers)==4', 'len(controllers)==26')
    gui = gui.replace("if event['kind']=='capture':assert", "if event['kind']=='capture'and event['data']['image_sha256']is not None:assert")
    before = "v=event['data'];assert sha(a/('%03d-actually-captured.png'%v['step']))==v['captured_sha256']and sha(a/('%03d-initial-delivered.png'%v['step']))==v['delivered_sha256']"
    after = "v=event['data'];assert sha(a/('%03d-actually-captured.png'%v['step']))==v['captured_sha256']\n   delivered=a/('%03d-initial-delivered.png'%v['step'])\n   assert (not delivered.exists())if v['delivered_sha256']is None else sha(delivered)==v['delivered_sha256']"
    assert gui.count(before) == 1
    values['GUI'] = gui.replace(before, after)
    anchor = " assert len(trace)==1 and trace[0]['past_key_values']is None and trace[0]['use_cache']is False"
    assert values['FLASH'].count(anchor) == 1
    values['FLASH'] = values['FLASH'].replace(anchor, anchor + "\n text=(d/'actual-input-text.txt').read_text();assert contract['question']in text and contract['state']in text and all(v in text for v in contract['options'].values())")
    for key in ['COMMON', 'ADMISSION', 'PRIMARY', 'FLASH', 'GUI']:
        compile(values['COMMON'] + '\n' + values[key], 'new-trusted-capture-' + key, 'exec')
    return source, values


def call(root, name, host, code):
    destination = root / (name + '.json')
    if destination.exists():
        return json.loads(destination.read_bytes())['result']
    raw, operation = remote(host, code, 'new-four-mode-source-postexit-' + name, timeout=180)
    value = json.loads(raw)
    save(destination, {'operation': str(operation), 'result': value})
    return value


from protocol_audit_components import frame_routes, SOURCE_READER


def main():
    assert not (HERE / 'completed-group-audit-current.json').exists()
    source, values = readers()
    if len(sys.argv) > 1:
        root = Path(sys.argv[1]).resolve()
        assert root.parent == HERE and sha(root / 'source.py') == sha(__file__) and not (root / 'seal.json').exists()
    else:
        root = HERE / ('completed-group-audit-' + str(time.time_ns()))
        root.mkdir()
        (root / 'source.py').write_bytes(Path(__file__).read_bytes())
        (root / 'reader-source.py').write_bytes(source.read_bytes())
    print(json.dumps({'audit_root': str(root)}), flush=True)
    m = manifest()
    prefix = 'P=' + repr(m['package3090']) + '\nO=' + repr(m['output3090']) + '\nMANIFEST=' + repr(sha(PACKAGE / 'manifest.json')) + '\n' + values['COMMON']
    admission = call(root, 'admission', '3090', prefix + values['ADMISSION'])
    global_map = admission['global']
    from bound_request_audit_reuse import load
    mains, flashes = load(root, admission)
    print(json.dumps({'verified_primary': len(mains), 'verified_Flash': len(flashes), 'exact_request_raw_proofs_bound_to_fresh_full_final_seal': True}), flush=True)
    others = {name: value for name, value in global_map.items() if not name.startswith(('primary/requests/', 'flash/service/requests/'))}
    call(root, 'other-members', '3090', prefix + '\nROWS=' + repr(others) + '\n' + "p=Path(P);o=Path(O)\nfor n,h in ROWS.items():assert sha((p if n.startswith('flash/service/')else o)/n)==h,n\nprint(json.dumps({'verified':len(ROWS)}))")
    gui_prefix = 'P=' + repr(m['package4090']) + '\nMANIFEST=' + repr(sha(PACKAGE / 'manifest.json')) + '\n' + values['COMMON']
    gui = call(root, 'GUI', '4090', gui_prefix + values['GUI'])
    call(root, 'injection-sources', '4090', gui_prefix + SOURCE_READER)
    checker = HERE.parent / 'flash-resource-continuation-20261115-linked12/controller_audit_reader.py'
    function = next(n for n in ast.parse(checker.read_text('utf8')).body if isinstance(n, ast.FunctionDef) and n.name == 'check_controller')
    namespace = {'hashlib': hashlib}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(checker), 'exec'), namespace)
    parse_function = next(n for n in ast.parse((PACKAGE / 'native-parser-source.py').read_text('utf8')).body if isinstance(n, ast.FunctionDef) and n.name == 'parse')
    parsers = {'json': json, 're': re}
    exec(compile(ast.Module(body=[parse_function], type_ignores=[]), 'original-native-parse', 'exec'), parsers)
    byid = {v['request_id']: v for v in mains}
    fb = {v['request_id']: v for v in flashes}
    bindings, routes = [], []
    for controller in gui['controllers']:
        controller['chain']['verified_prefix_events'] = controller['chain']['events']
        bound = {'terminal_sha256': controller['terminal_sha256'], 'seal_sha256': controller['seal_sha256'],
                 'event_chain_head': controller['chain']['head'], 'event_chain_count': controller['chain']['events']}
        bindings.append(namespace['check_controller'](controller, byid, fb, bound, parsers['parse']))
        routes.append(frame_routes(controller, byid, fb))
    assert sum(len(v['actor_requests']) for v in bindings) == len(byid) == len(mains)
    assert sum(len(v['Flash_requests']) for v in bindings) == len(fb) == len(flashes)
    sealed = {v['data']['request_id']: v['data']['seal_sha256'] for v in admission['primary_events'] if v['kind'] == 'actor_reply_sealed'}
    assert sealed == {v['request_id']: v['seal_sha256'] for v in mains}
    final = call(root, 'final-identities', '3090', prefix + values['ADMISSION'])
    assert final['global_seal_sha256'] == admission['global_seal_sha256'] and final['primary_chain'] == admission['primary_chain'] and final['Flash_chain'] == admission['Flash_chain']
    summary = {'processed_GUI_trajectories': len(bindings), 'actual_primary_replies_verified': len(mains),
               'actual_Flash_replies_verified': len(flashes), 'Flash_YES': sum(v['decision'] == 'YES' for v in flashes),
               'Flash_NO': sum(v['decision'] == 'NO' for v in flashes),
               'precheck_NO': sum(c['terminal']['precheck_NO_count'] for c in gui['controllers']),
               'full_wire_input_tensors_history_EOS_probability_seal_chain_and_actions_verified': True,
               'all_model_GUI_launcher_processes_verified_exited': True,
               'wire_bound_recovery_loops_pending_image_review': sum(v['wire_bound_recovery_loop'] for v in routes),
               'target_per_condition': 5, 'routes': routes, 'overall_efficacy_rate_proven': False,
               'primary_input_tokens': sum(v['input_tokens'] for v in mains),
               'primary_output_tokens': sum(v['output_tokens'] for v in mains),
               'primary_native_seconds_sum': sum(v['native_seconds'] for v in mains),
               'Flash_input_tokens': sum(v['input_tokens'] for v in flashes),
               'Flash_seconds_sum': sum(v['elapsed_seconds_with_input_capture'] for v in flashes),
               'eight_GPU_interval': admission['recorded_group_eight_GPU_interval'],
               'new_model_GUI_calls_by_audit': 0,'receipt_NO':sum(c['terminal']['receipt_NO_count']for c in gui['controllers']),'user_frame_wire_loops_pending_image_review':sum(v['user_normal_frame_delivery_wire_verified']for v in routes),
               'terminals': [c['terminal'] for c in gui['controllers']]}
    save(root / 'native-and-Flash.json', {'primary': mains, 'Flash': flashes})
    save(root / 'Controller-bindings.json', {'bindings': bindings, 'reader_sha256': sha(checker)})
    save(root / 'summary.json', summary)
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
    save(HERE / 'completed-group-audit-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps({'completed_audit': str(root), 'primary': len(mains), 'Flash': len(flashes),
                      'loops_pending_image_review': summary['wire_bound_recovery_loops_pending_image_review']}), flush=True)


if __name__ == '__main__':
    main()
