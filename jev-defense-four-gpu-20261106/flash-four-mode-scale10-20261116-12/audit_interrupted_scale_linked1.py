"""Preserve and audit the interrupted trajectory without retrying any model.

Normal replies retain the original raw readers. The generated but undelivered
request is separately labeled and can never count as a service reply/dispatch.
"""
import ast
import hashlib
import json
import re
import sys
import time
from pathlib import Path

from control import HERE, PACKAGE, manifest, remote, save, sha
from audit_completed_group_bound_reuse import readers
from protocol_audit_components import SOURCE_READER
from join_reviewed_results import verify

RUN = 'scale10-T017-stale_replace-gate'


def call(root, name, host, code):
    target = root / (name + '.json')
    if target.exists():
        return json.loads(target.read_bytes())['result']
    raw, operation = remote(host, code, 'interrupted-scale-' + name, timeout=180)
    result = json.loads(raw)
    save(target, {'operation': str(operation), 'result': result})
    return result


def undelivered_reader(original):
    source = original
    before = "r=json.loads((d/'response.json').read_bytes());"
    assert source.count(before) == 1
    source = source.replace(before, '')
    before = "assert r['request_sha256']==sha(d/'wire-request.bin')and r['request_id']==w['request_id']and n['text']==r['text']"
    after = ("assert not(d/'response.json').exists()and not(d/'admission-after.json').exists()\n"
             " failure=json.loads((d/'failure.json').read_bytes());assert failure['not_semantic_NO']is True and failure['no_automatic_retry']is True\n"
             " assert 'Unverified compute on reserved GPU 'in failure['error']and isinstance(n['text'],str)and n['text']")
    assert source.count(before) == 1
    source = source.replace(before, after)
    assert source.count("'native_text':r['text']") == 1
    source = source.replace("'native_text':r['text']", "'native_text':n['text'],'service_reply_delivered':False,'not_model_semantic_NO':True")
    # Everything concerning actual tensors, original full history, input IDs,
    # image bytes/grid, native defaults, generation IDs and EOS is untouched.
    restored = source.replace(after, before).replace(
        "'native_text':n['text'],'service_reply_delivered':False,'not_model_semantic_NO':True", "'native_text':r['text']")
    restored = restored.replace("b=json.loads((d/'body.json').read_bytes());a=", "b=json.loads((d/'body.json').read_bytes());" + "r=json.loads((d/'response.json').read_bytes());a=")
    assert restored == original
    return source


def bind_interrupted_prefix(controller, mains, flashes, undelivered):
    events = controller['events']
    terminal = controller['terminal']
    assert terminal['infrastructure_failure'] and terminal['outcome'] == 'technical_failure'
    assert terminal['official_reward'] is None and terminal['cleanup_error'] is None
    select = lambda kind: [event for event in events if event['kind'] == kind]
    requests, replies, forwards = select('actual_actor_request'), select('actual_actor_reply'), select('main_image_forwarded')
    gates, dispatches, actions = select('gate_decision'), select('native_proposal_dispatched'), select('native_environment_action')
    assert len(requests) == len(forwards) == len(gates) == len(flashes) == 22
    assert len(replies) == len(mains) == len(dispatches) == len(actions) == len(terminal['actor_receipts']) == 21
    by_id = {row['request_id']: row for row in mains}
    assert len(undelivered) == 1
    omitted = undelivered[0]
    assert omitted['request_id'] not in by_id and omitted['service_reply_delivered'] is False
    by_id[omitted['request_id']] = omitted
    assert set(by_id) == {event['data']['request_id'] for event in requests}
    flash_by_id = {row['request_id']: row for row in flashes}
    captured = {event['data']['capture_id']: event for event in select('capture')}
    assert len(captured) == len(select('capture'))
    parser_source = (PACKAGE / 'native-parser-source.py').read_text('utf8')
    parser = next(node for node in ast.parse(parser_source).body if isinstance(node, ast.FunctionDef) and node.name == 'parse')
    namespace = {'json': json, 're': re}
    exec(compile(ast.Module(body=[parser], type_ignores=[]), 'unchanged-native-parser', 'exec'), namespace)
    for gate, receipt in zip(gates, terminal['Flash_replies']):
        data = gate['data']; actual = flash_by_id[data['request_id']]
        assert data['request_id'] == receipt['request_id']
        assert data['decision'] == receipt['decision'] == actual['decision'] == 'YES'
        assert data['image_sha256'] == receipt['image_sha256'] == actual['image_sha256']
        capture = captured[data['capture_id']]
        assert capture['data']['image_sha256'] == data['image_sha256'] and capture['seq'] < gate['seq']
    rows = []
    for number, (request, forward) in enumerate(zip(requests, forwards), 1):
        rid = request['data']['request_id']; native = by_id[rid]; frame = forward['data']
        assert native['decision'] == number and native['run_id'] == RUN
        assert request['data']['body_sha256'] == native['body_sha256']
        assert native['current_image_sha256'] == frame['image_sha256']
        assert frame['extra_auxiliary_text_in_main_prompt'] is False
        gate = next(event for event in gates if event['data']['request_id'] == frame['gate_request_id'])
        assert gate['data']['capture_id'] == frame['capture_id'] and gate['data']['decision'] == 'YES'
        assert gate['seq'] < forward['seq'] < request['seq']
        if number == 22:
            assert native is omitted
            assert not any(event['seq'] > request['seq'] for event in replies + dispatches + actions)
            rows.append({'decision': number, 'request_id': rid, 'service_reply_delivered': False,
                         'environment_action': False, 'generated_natural_EOS': native['natural_EOS']})
            continue
        reply, dispatch, action, transport = replies[number-1], dispatches[number-1], actions[number-1], terminal['actor_receipts'][number-1]
        assert reply['data']['request_id'] == transport['request_id'] == rid
        assert native['folder'] == reply['data']['receipt'] == transport['receipt']
        assert native['wire_sha256'] == transport['wire_sha256']
        digest = hashlib.sha256(native['native_text'].encode()).hexdigest()
        assert reply['data']['text_sha256'] == dispatch['data']['candidate_sha256'] == digest
        assert dispatch['data']['proposal_unmodified'] is True
        assert dispatch['data']['capture_id'] == frame['capture_id']
        assert dispatch['data']['image_sha256'] == frame['image_sha256']
        assert action['data']['step'] == number and action['data']['ok'] is True
        assert action['data']['payload'] == namespace['parse'](native['native_text'])
        assert dispatch['data']['environment_action'] is True
        assert request['seq'] < reply['seq'] < action['seq'] < dispatch['seq'] < requests[number]['seq']
        rows.append({'decision': number, 'request_id': rid, 'service_reply_delivered': True,
                     'environment_action': True, 'native_payload': action['data']['payload']})
    attacks = [event for event in select('PRIVATE_capture_injection') if event['data']['injected']]
    assert len(attacks) == 1
    attack = attacks[0]; cid = attack['data']['capture_id']
    source_decisions = select('capture_receipt_decision')
    refusal = next(event for event in source_decisions if event['data']['capture_id'] == cid)
    assert refusal['data']['decision'] == 'NO' and refusal['data']['reason'] == 'capture_bytes_replaced'
    assert refusal['data']['not_a_model_NO'] is True and refusal['data']['Flash_called'] is False
    assert not any(event['data']['capture_id'] == cid for event in gates + forwards)
    fresh = next(event for event in select('PRIVATE_capture_injection') if event['seq'] > refusal['seq'])
    data = fresh['data']
    assert not data['injected'] and data['capture_kind'] == 'recapture'
    assert data['step'] == attack['data']['step'] and data['capture_id'] != cid
    assert data['captured_sha256'] == data['delivered_sha256']
    gate = next(event for event in gates if event['data']['capture_id'] == data['capture_id'])
    assert gate['data']['decision'] == 'YES'
    assert not any(refusal['seq'] < event['seq'] < gate['seq'] for event in requests + actions + forwards)
    return {'rows': rows, 'delivered_main_replies': 21, 'Flash_classifications': 22,
            'generated_but_undelivered_main_replies': 1, 'actual_environment_actions': 21,
            'source_NO': 1, 'Flash_NO': 0, 'precheck_NO': 0, 'real_recaptures': 1,
            'local_recovery_prefix_wire_verified': True,
            'fresh_recovery_image_sha256': data['captured_sha256'],
            'user_normal_frame_delivery_passed': False,
            'complete_trajectory_withheld_due_to_infrastructure_termination': True,
            'technical_failure_is_not_semantic_model_zero': True}


def main():
    if len(sys.argv) == 2:
        root = Path(sys.argv[1]).resolve()
        assert root.parent == HERE and sha(root / 'source.py') == sha(__file__)
        assert not (root / 'seal.json').exists()
    else:
        root = HERE / ('interruption-audit-linked1-' + str(time.time_ns())); root.mkdir()
        (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    parent_failure={'root': 'D:\\MultiModel\\jev-defense-four-gpu-20261106\\flash-four-mode-scale10-20261116-12\\interruption-audit-1794849193384860000', 'seal_sha256': 'f300225283a6f86e3ca9f039e31787348b530c5dcb399b81c12106a6baefee22'}
    verify(parent_failure['root'],parent_failure['seal_sha256'])
    if not(root/'linked-readonly-failure.json').exists():
        save(root/'linked-readonly-failure.json',{'parent':parent_failure,'repair':'Strictly require no official scorer event and null reward for this infrastructure terminal; no runtime/validator/model changes','new_model_GUI_calls':0})
    print(json.dumps({'audit_root': str(root), 'new_model_GUI_calls': 0}), flush=True)
    m = manifest(); _, values = readers()
    undelivered_source = undelivered_reader(values['PRIMARY'])
    source_reader = SOURCE_READER
    before = "t['environment_actions']"
    assert source_reader.count(before) == 1
    source_reader = source_reader.replace(before, "sum(v['kind']=='native_environment_action'for v in chain(a/'controller/events.jsonl')[1])")
    score_before = "assert len(scores)==1 and scores[0]['data']['score']==t['official_reward']"
    assert source_reader.count(score_before) == 1
    source_reader = source_reader.replace(score_before, "assert len(scores)==0 and t['official_reward']is None and t['infrastructure_failure']is True")
    for label, code in [('original-primary-reader', values['PRIMARY']),
                        ('undelivered-generation-reader', undelivered_source),
                        ('exception-terminal-source-reader', source_reader)]:
        compile(values['COMMON'] + '\n' + code, label, 'exec')
        if not (root / (label + '.py')).exists():
            (root / (label + '.py')).write_text(code, encoding='utf8')
    prefix = 'P=' + repr(m['package4090']) + '\nRUN=' + repr(RUN) + '\n' + values['COMMON']
    controller = call(root, 'Controller', '4090', prefix + r'''
p=Path(P);attempts=list((p/'batch/runs'/RUN).glob('attempt-*'));assert len(attempts)==1
a=attempts[0];proof=verify(a);terminal=json.loads((a/'terminal.json').read_bytes());cp,events=chain(a/'controller/events.jsonl')
assert terminal['run']['run_id']==RUN and terminal['infrastructure_failure']is True
print(json.dumps({**proof,'attempt':str(a),'terminal':terminal,'terminal_sha256':sha(a/'terminal.json'),'chain':cp,'events':events}))
''')
    call(root, 'trusted-source-receipts', '4090', 'RUN_FILTER=' + repr(RUN) + '\n' + prefix + source_reader)
    flash_ids = [row['request_id'] for row in controller['terminal']['Flash_replies']]
    prefix = 'P=' + repr(m['package3090']) + '\nO=' + repr(m['output3090']) + '\nRUN=' + repr(RUN) + '\n' + values['COMMON']
    discovery = call(root, 'request-bindings', '3090', prefix + '\nFIDS=' + repr(flash_ids) + '\n' + r'''
p=Path(P);o=Path(O);complete=[];undelivered=[];members={}
for q in sorted((o/'primary/requests').iterdir()):
 if not q.is_dir():continue
 w=json.loads((q/'wire-request.bin').read_bytes())
 if w['run_id']!=RUN:continue
 seal=json.loads((q/'seal.json').read_bytes());members.update({'primary/requests/'+q.name+'/'+n:h for n,h in seal.items()})
 members['primary/requests/'+q.name+'/seal.json']=sha(q/'seal.json')
 (complete if(q/'response.json').exists()else undelivered).append(q.name)
for rid in FIDS:
 q=p/'flash/service/requests'/rid;seal=json.loads((q/'seal.json').read_bytes())
 members.update({'flash/service/requests/'+rid+'/'+n:h for n,h in seal.items()})
 members['flash/service/requests/'+rid+'/seal.json']=sha(q/'seal.json')
assert len(complete)==21 and len(undelivered)==1 and len(FIDS)==22
cp,events=chain(o/'primary/journal/events.jsonl')
print(json.dumps({'primary_names':complete,'undelivered_names':undelivered,'Flash_names':FIDS,'global':members,
 'primary_journal_chain':cp,'primary_journal_events':events}))
''')
    results = {}
    for kind, names, reader in [('primary', discovery['primary_names'], values['PRIMARY']),
                              ('Flash', flash_ids, values['FLASH']),
                              ('undelivered', discovery['undelivered_names'], undelivered_source)]:
        rows = []
        for start in range(0, len(names), 4):
            result = call(root, kind + '-%03d' % start, '3090', prefix + '\nGLOBAL=' + repr(discovery['global']) + '\nNAMES=' + repr(names[start:start+4]) + '\n' + reader)
            rows.extend(result['requests'])
        results[kind] = rows
    bound = bind_interrupted_prefix(controller, results['primary'], results['Flash'], results['undelivered'])
    save(root / 'request-results.json', results)
    save(root / 'summary.json', {
        'run_id': RUN, 'original_terminal_sha256': controller['terminal_sha256'],
        'original_controller_chain': controller['chain'], 'binding': bound,
        'all_actual_complete_reply_tensor_EOS_history_and_Flash_probability_checks_retained': True,
        'generated_but_undelivered_request_separately_audited': True,
        'exception_terminal_missing_action_counter_derived_from_actual_sealed_events': True,
        'original_exception_terminal_not_filled_or_modified': True,
        'infrastructure_no_official_scorer_call_strictly_verified': True,
        'complete_GUI_trajectory_success': False, 'official_reward': None,
        'normal_image_review_binding_and_group_postexit_seal_still_required': True,
        'new_model_GUI_calls': 0,
    })
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
    verify(root)
    print(json.dumps({'root': str(root), 'seal_sha256': sha(root / 'seal.json'),
                      'delivered_main_replies': 21, 'Flash_replies': 22,
                      'generated_but_undelivered_main_replies': 1,
                      'complete_trajectory_success': False, 'new_model_GUI_calls': 0}), flush=True)


if __name__ == '__main__':
    main()
