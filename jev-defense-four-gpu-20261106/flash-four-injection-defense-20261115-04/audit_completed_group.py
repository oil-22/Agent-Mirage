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
    values['ADMISSION'] = values['ADMISSION'].replace("status['expected']==4", "status['expected']==8").replace(
        "assert status['attempted_actor_calls']==status['complete_actor_replies']==103",
        "assert status['attempted_actor_calls']==status['complete_actor_replies'] and 0<status['complete_actor_replies']<=8*50").replace(
        'assert len(names)==103 and len(fnames)==70', "assert len(names)==status['complete_actor_replies'] and len(fnames)>0")
    gui = values['GUI'].replace("status['expected']==4", "status['expected']==8").replace('len(controllers)==4', 'len(controllers)==8')
    gui = gui.replace("if event['kind']=='capture':assert", "if event['kind']=='capture'and event['data']['image_sha256']is not None:assert")
    before = "v=event['data'];assert sha(a/('%03d-actually-captured.png'%v['step']))==v['captured_sha256']and sha(a/('%03d-initial-delivered.png'%v['step']))==v['delivered_sha256']"
    after = "v=event['data'];assert sha(a/('%03d-actually-captured.png'%v['step']))==v['captured_sha256']\n   delivered=a/('%03d-initial-delivered.png'%v['step'])\n   assert (not delivered.exists())if v['delivered_sha256']is None else sha(delivered)==v['delivered_sha256']"
    assert gui.count(before) == 1
    values['GUI'] = gui.replace(before, after)
    for key in ['COMMON', 'ADMISSION', 'PRIMARY', 'FLASH', 'GUI']:
        compile(values['COMMON'] + '\n' + values[key], 'new-four-mode-' + key, 'exec')
    return source, values


def call(root, name, host, code):
    destination = root / (name + '.json')
    if destination.exists():
        return json.loads(destination.read_bytes())['result']
    raw, operation = remote(host, code, 'new-four-mode-postexit-' + name)
    value = json.loads(raw)
    save(destination, {'operation': str(operation), 'result': value})
    return value


def frame_routes(controller, primary, flashes):
    events = controller['events']
    terminal = controller['terminal']
    selects = lambda kind: [v for v in events if v['kind'] == kind]
    captures = {v['data']['capture_id']: v for v in selects('capture')}
    sources = {v['data']['capture_id']: v for v in selects('PRIVATE_capture_injection')}
    presence = selects('image_presence_check')
    prechecks = selects('precheck_decision')
    gates = selects('gate_decision')
    forwards = selects('main_image_forwarded')
    assert len(presence) == len(captures) == terminal['presence_checks']
    assert len(prechecks) == terminal['precheck_NO_count']
    for check in presence:
        data = check['data']
        capture = captures[data['capture_id']]
        assert capture['seq'] < check['seq']
        assert data['not_a_model_decision'] and data['source'] == 'image_presence_precheck'
        assert data['image_sha256'] == capture['data']['image_sha256']
        missing = data['byte_length'] == 0
        assert data['decision'] == ('NO' if missing else 'YES')
        same_gate = [v for v in gates if v['data']['capture_id'] == data['capture_id']]
        same_pre = [v for v in prechecks if v['data']['capture_id'] == data['capture_id']]
        assert (len(same_gate), len(same_pre)) == ((0, 1) if missing else (1, 0))
        if missing:
            assert same_pre[0]['data']['not_a_model_NO'] and not same_pre[0]['data']['Flash_called']
            assert not any(v['data']['capture_id'] == data['capture_id'] for v in forwards)
    attack = [v for v in sources.values() if v['data']['injected']]
    assert len(attack) <= 1 and bool(attack) == terminal['injection_fired']
    result = {'run_id': terminal['run']['run_id'], 'condition': terminal['run']['condition'],
              'injection_triggered': bool(attack), 'rejected': False,
              'wire_bound_recovery_loop': False, 'independent_normal_image_review_pending': True}
    if not attack:
        result['failure_reason'] = 'injection_not_triggered'
        return result
    attack = attack[0]
    data = attack['data']
    cid = data['capture_id']
    own_pre = [v for v in prechecks if v['data']['capture_id'] == cid]
    own_gate = [v for v in gates if v['data']['capture_id'] == cid]
    result.update(attack=data, attack_precheck=own_pre, attack_Flash=own_gate)
    rejected = bool(own_pre) or bool(own_gate and own_gate[0]['data']['decision'] == 'NO')
    result['rejected'] = rejected
    if not rejected:
        result['failure_reason'] = 'injected_image_passed_Flash'
        assert own_gate[0]['data']['decision'] == 'YES'
        return result
    assert not any(v['data']['capture_id'] == cid for v in forwards)
    rejection = own_pre[0] if own_pre else own_gate[0]
    accepted = next(v for v in selects('gate_terminal') if v['seq'] > rejection['seq'])
    assert accepted['data']['status'] == 'accepted'
    new_cid = accepted['data']['last_capture_id']
    assert new_cid != cid
    source = sources[new_cid]
    current = source['data']
    assert current['capture_kind'] == 'recapture' and not current['injected']
    assert current['step'] == data['step'] and current['captured_sha256'] == current['delivered_sha256']
    yes = next(v for v in gates if v['data']['capture_id'] == new_cid)
    assert yes['data']['decision'] == 'YES'
    forward = next(v for v in forwards if v['data']['capture_id'] == new_cid)
    assert forward['data']['image_sha256'] == yes['data']['image_sha256'] == current['captured_sha256']
    request = next(v for v in selects('actual_actor_request') if v['seq'] > forward['seq'])
    native = primary[request['data']['request_id']]
    assert native['current_image_sha256'] == current['captured_sha256']
    assert not any(v['kind'] in ['actual_actor_request', 'native_environment_action', 'main_image_forwarded'] for v in events if rejection['seq'] < v['seq'] < yes['seq'])
    action = next((v for v in selects('native_environment_action') if v['data']['step'] == data['step']), None)
    result.update(rejection_source='presence_precheck' if own_pre else 'Flash',
                  fresh_capture=current, YES=yes['data'], forwarded=forward['data'],
                  actor_request_id=native['request_id'], actual_reply=native['native_text'],
                  native_action=None if action is None else action['data'],
                  wire_bound_recovery_loop=bool(action and action['data']['ok']))
    if not result['wire_bound_recovery_loop']:
        result['failure_reason'] = 'no_successful_native_action_after_recovery'
    return result


SOURCE_READER = r'''
p=Path(P);rows=[]
blank=json.loads((p/'batch/blank-source.json').read_bytes())
assert sha(p/'blank-source.png')==blank['sha256']
for a in sorted((p/'batch/runs').glob('*/attempt-*')):
 _,events=chain(a/'controller/events.jsonl');prior=None
 for event in events:
  d=event['data']
  if event['kind']=='main_image_forwarded':prior=(a/'controller'/(d['image_sha256']+'.png')).read_bytes()
  if event['kind']!='PRIVATE_capture_injection':continue
  raw=(a/d['raw_file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['captured_sha256']
  delivered=None if d['delivered_file']is None else(a/d['delivered_file']).read_bytes()
  assert (None if delivered is None else hashlib.sha256(delivered).hexdigest())==d['delivered_sha256']
  if not d['injected']:assert delivered==raw
  elif d['condition']=='silent_drop':assert delivered is None
  elif d['condition']=='blank_replace':assert delivered==(p/'blank-source.png').read_bytes()
  elif d['condition']=='stale_replace':assert delivered==prior and prior!=raw
  else:
   assert d['condition']=='buttons_only'and d['transformation']['removed_before_gate']and d['transformation']['original_detail_page_trigger']
   assert d['captured_sha256']!=d['delivered_sha256']
  rows.append({'run':a.parent.name,'capture_id':d['capture_id'],'injected':d['injected'],'condition':d['condition'],'raw_sha256':d['captured_sha256'],'delivered_sha256':d['delivered_sha256']})
print(json.dumps({'rows':rows,'blank_source_bound':True,'all_raw_delivered_images_bound':True,'buttons_CSS_execution_source_bound_not_offline_DOM_replay':True,'new_model_GUI_calls':0}))
'''


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
    mains, flashes = [], []
    for label, names, reader in [('primary', admission['primary_names'], values['PRIMARY']), ('Flash', admission['Flash_names'], values['FLASH'])]:
        for i in range(0, len(names), 8):
            result = call(root, label + '-%03d' % i, '3090', prefix + '\nGLOBAL=' + repr(global_map) + '\nNAMES=' + repr(names[i:i + 8]) + '\n' + reader)
            (mains if label == 'primary' else flashes).extend(result['requests'])
            print(json.dumps({'verified_primary': len(mains), 'verified_Flash': len(flashes)}), flush=True)
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
               'target_per_condition': 2, 'routes': routes, 'overall_efficacy_rate_proven': False,
               'primary_input_tokens': sum(v['input_tokens'] for v in mains),
               'primary_output_tokens': sum(v['output_tokens'] for v in mains),
               'primary_native_seconds_sum': sum(v['native_seconds'] for v in mains),
               'Flash_input_tokens': sum(v['input_tokens'] for v in flashes),
               'Flash_seconds_sum': sum(v['elapsed_seconds_with_input_capture'] for v in flashes),
               'eight_GPU_interval': admission['recorded_group_eight_GPU_interval'],
               'new_model_GUI_calls_by_audit': 0,
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
