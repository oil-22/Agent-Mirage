"""New source-bound two-trajectory protocol package. Never edits a prior package."""
import ast
import json
import secrets
import time
import sys
from pathlib import Path
from remote_util import HERE, save, sha


def member(text, owner, name):
    node = next(n for n in ast.parse(text).body if getattr(n, 'name', '') == owner)
    return next(n for n in node.body if getattr(n, 'name', '') == name)


def replace_method(text, owner, name, replacement):
    segment = ast.get_source_segment(text, member(text, owner, name))
    assert text.count(segment) == 1
    return text.replace(segment, replacement)


def main():
    prior_preparation = HERE / 'preparation-current.json'
    linked = sys.argv[1:] == ['--linked-ledger-cleanup']
    assert linked or not prior_preparation.exists()
    cpu = json.loads((HERE / 'CPU-source-current.json').read_bytes())
    assert cpu['passed']
    cpu_root = Path(cpu['root'])
    assert sha(cpu_root / 'seal.json') == cpu['seal_sha256']
    parent = json.loads((HERE.parent / 'flash-four-injection-defense-20261115-04/preparation-current.json').read_bytes())
    previous = Path(parent['package'])
    assert sha(previous / 'manifest.json') == parent['manifest_sha256']
    manifest = json.loads((previous / 'manifest.json').read_bytes())
    root = HERE / ('preparation-' + str(time.time_ns()))
    root.mkdir()
    if linked:
        (root / 'prior-preparation-pointer.json').write_bytes(prior_preparation.read_bytes())
    package = root / 'package'
    package.mkdir()
    for name, expected in manifest['files'].items():
        assert sha(previous / name) == expected, name
        destination = package / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((previous / name).read_bytes())
    for name in ['receipt_protocol.py', 'native_rpc.py', 'capture_source.py', 'capture_client.py']:
        assert sha(HERE / name) == sha(cpu_root / 'source' / name), name
        (package / name).write_bytes((HERE / name).read_bytes())
    for name in ['launch_group.py', 'expanded_guard.py', 'continuation_guard.py', 'prior-3090.json', 'prior-4090.json']:
        (package / name).write_bytes((HERE / name).read_bytes())
    (package / 'native-sources.json').write_bytes((cpu_root / 'source/native-sources.json').read_bytes())
    (package / 'user-current-authorization.json').write_bytes((HERE / 'user-authorization.json').read_bytes())
    (package / 'private.token').write_text(secrets.token_hex(32), encoding='utf-8')
    resources = (HERE / 'resource_guard.py').read_text('utf-8')
    old_resources = (previous / 'flash/resource_guard.py').read_text('utf-8')
    checkpoint = next(n for n in ast.parse(old_resources).body if getattr(n, 'name', '') == 'checkpoint')
    resources += '\n\n' + ast.get_source_segment(old_resources, checkpoint) + '\n'
    (package / 'flash/resource_guard.py').write_text(resources, encoding='utf-8')

    original_gate = (previous / 'flash/gate_core.py').read_text('utf-8')
    gate = original_gate.replace('    captured_at:float\n', '    captured_at:float\n    receipt:dict|None=None\n    expected:dict|None=None\n')
    gate = gate.replace('def __init__(self,checker,*,revision,contract_sha256,journal,', 'def __init__(self,checker,*,receipt_guard,revision,contract_sha256,journal,')
    gate = gate.replace('        self.calls=0;self.recaptures=0;self.presence_checks=0;self.precheck_no=0',
                        '        self.calls=0;self.recaptures=0;self.presence_checks=0;self.precheck_no=0\n        self.receipt_guard=receipt_guard;self.receipt_checks=0;self.receipt_no=0')
    gate = gate.replace("'last_capture_id':frame.capture_id,", "'receipt_checks':self.receipt_checks,'receipt_NO_count':self.receipt_no,'last_capture_id':frame.capture_id,")
    start = gate.index('                self.calls+=1\n')
    end = gate.index('            # NO and missing-image recovery', start)
    body = gate[start:end]
    prefix = '''                self.receipt_checks+=1
                verified=self.receipt_guard.check(frame.png,frame.receipt,expected=frame.expected)
                self.journal.emit('capture_receipt_decision',{'capture_id':frame.capture_id,'image_sha256':frame.sha256,'decision':verified.value,'reason':verified.reason,'expected':frame.expected,'receipt':frame.receipt,'source':'trusted_capture_receipt','Flash_called':False,'not_a_model_NO':verified.value=='NO'})
                if verified.value=='NO':self.receipt_no+=1
                else:
'''
    gate = gate[:start] + prefix + ''.join('    ' + line if line.strip() else line for line in body.splitlines(keepends=True)) + gate[end:]
    for name in ['GateController', 'NativeHistoryActor']:
        old = next(n for n in ast.parse(original_gate).body if getattr(n, 'name', '') == name)
        new = next(n for n in ast.parse(gate).body if getattr(n, 'name', '') == name)
        assert ast.dump(old, include_attributes=False) == ast.dump(new, include_attributes=False), name
    (package / 'flash/gate_core.py').write_text(gate, encoding='utf-8')

    original = (previous / 'gui_experiment.py').read_text('utf-8')
    gui = original.replace('from wire_contract import REVISION', 'from wire_contract import REVISION\nfrom capture_client import CaptureClient')
    gui = replace_method(gui, 'LiveAdapter', 'initial_frame', '''def initial_frame(self):
        from injection import Episode
        if not hasattr(self,'corruption_episode'):self.corruption_episode=Episode(self.item['condition'])
        raw,receipt,expected=self.env.acquire()
        delivered,record=self.corruption_episode.apply(raw,step=self.step,previous_png=self.last_image,previous_action=self.previous,recapture=False,env=self.env,encoder=self.png)
        self.fired=self.corruption_episode.started;self.trigger_step=self.corruption_episode.start_step
        return self.record_delivery(raw,delivered,record,receipt,expected)''')
    gui = replace_method(gui, 'LiveAdapter', 'capture', '''def capture(self):
        raw,receipt,expected=self.env.acquire()
        delivered,record=self.corruption_episode.apply(raw,step=self.step,previous_png=self.last_image,previous_action=self.previous,recapture=True)
        return self.record_delivery(raw,delivered,record,receipt,expected)''')
    gui = gui.replace('def record_delivery(self,raw,delivered,record):\n        frame=Frame.captured(delivered)',
                      "def record_delivery(self,raw,delivered,record,receipt,expected):\n        frame=Frame(delivered,receipt['capture_id'],receipt['acquired_at_ns']/1e9,receipt,expected)")
    gui = gui.replace("        (self.root/raw_file).write_bytes(raw)",
                      "        (self.root/raw_file).write_bytes(raw)\n        save(folder/(stem+'-signed-receipt.json'),receipt)\n        save(folder/(stem+'-expected-challenge.json'),expected)")
    old = "env=ScriptBrowserEnv(headless=True,observation_type='image',current_viewport_only=True,viewport_size={'width':1280,'height':720},save_trace_enabled=True,sleep_after_execution=0.5)"
    assert gui.count(old) == 1
    gui = gui.replace(old, 'env=CaptureClient(attempt)')
    gui = gui.replace('gate=ImageGate(transport,revision=', 'gate=ImageGate(transport,receipt_guard=env.verifier,revision=')
    gui = gui.replace('float(evaluator_router(private)(adapter.trajectory,private,env.page))', 'float(env.score(adapter.trajectory[-1]))')
    gui = gui.replace("'presence_checks':getattr(gate,'presence_checks',0),", "'trusted_capture_protocol':True,'receipt_checks':getattr(gate,'receipt_checks',0),'receipt_NO_count':getattr(gate,'receipt_no',0),'presence_checks':getattr(gate,'presence_checks',0),")
    # The unused original about:blank helper is removed from this stale-only
    # group so that all browser ownership belongs to the acquisition process.
    start = gui.index('    # Original native blank injection source:')
    end = gui.index('    transport=Transport();', start)
    gui = gui[:start] + gui[end:]
    for name in ['__init__', 'observation_png_or_missing', 'missing_frame', 'actor', 'call_main', 'parse', 'execute', 'commit']:
        assert ast.dump(member(original, 'LiveAdapter', name), include_attributes=False) == ast.dump(member(gui, 'LiveAdapter', name), include_attributes=False), name
    (package / 'gui_experiment.py').write_text(gui, encoding='utf-8')
    queue = [{'run_id': f'receipt16-T{task:03}-stale_replace-gate', 'task_id': task,
              'condition': 'stale_replace', 'gate_enabled': True} for task in [58, 89]]
    plan = json.loads((previous / 'plan.json').read_bytes())
    plan.update(version='trusted-native-capture-stale-development-v1', queue=queue, expected_trajectories=2,
                conditions=['stale_replace'], trusted_capture_protocol=True,
                new_primary_preread=False, full_history_unchanged=True,
                current_user_authorization_sha256=sha(package / 'user-current-authorization.json'),
                acceptance={'per_condition_target': 2, 'required': 'source NO before Flash/primary; real same-live new acquisition; public receipt YES; unchanged Flash YES; independently normal PNG exactly into completed primary/native dispatch including legitimate STOP',
                            'normal_frame_primary_text_accuracy_required': False, 'all_failures_preserved': True},
                source_trust={'independent_native_environment_process': True, 'trusted_OS_controller_source_code': True,
                              'untrusted_image_delivery_after_signature': True, 'source_signed_bad_capture_not_guaranteed': True,
                              'private_labels_or_hidden_reference_not_used_by_guard': True})
    (package / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    (package / 'analysis-plan.json').write_text(json.dumps({'queue': queue, 'protocol_separate_from_previous_10': True,
                                                          'no_Flash_freshness_recognition_claim': True, 'all_failures_preserved': True}, indent=2), encoding='utf-8')
    files = {str(p.relative_to(package)).replace('\\', '/'): sha(p) for p in package.rglob('*') if p.is_file() and p.name != 'private.token'}
    manifest.update(files=files, version=plan['version'], study=plan['version'], created=time.time(),
                    auth_token_sha256=sha(package / 'private.token'), trajectories=2, remaining_queue=queue,
                    package3090='/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + HERE.name,
                    package4090='/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name + '/runtime',
                    output3090='/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name + '/model-attempt-01',
                    source_prior_manifest_sha256=parent['manifest_sha256'], current_user_authorization_sha256=sha(package / 'user-current-authorization.json'),
                    trusted_capture_protocol=True, parent_CPU_source_qualification=cpu,
                    formal_Mirage_efficacy_proven=False, new_GUI_queue=True)
    save(package / 'manifest.json', manifest)
    for name in files:
        if name.endswith('.py'):
            ast.parse((package / name).read_text('utf-8'))
    save(root / 'source-invariance.json', {'native_actor_and_controller_AST_unchanged': True,
                                          'adapter_actor_parser_executor_commit_AST_unchanged': True,
                                          'Flash_contract_and_native_request_unchanged': sha(package / 'flash/gate-contract.json') == sha(previous / 'flash/gate-contract.json') and sha(package / 'flash/wire_contract.py') == sha(previous / 'flash/wire_contract.py'),
                                          'primary_generation_source_unchanged': sha(package / 'primary_server.py') == sha(previous / 'primary_server.py'),
                                          'original_injection_source_unchanged': sha(package / 'injection.py') == sha(previous / 'injection.py'),
                                          'original_system_full_history_parameters_preserved': True,
                                          'new_acquisition_and_public_key_gate_explicit_protocol_change': True})
    save(root / 'seal.json', {str(p.relative_to(root)).replace('\\', '/'): sha(p) for p in root.rglob('*') if p.is_file()})
    pointer = {'root': str(root), 'package': str(package), 'manifest_sha256': sha(package / 'manifest.json'), 'seal_sha256': sha(root / 'seal.json')}
    if linked:
        temp = HERE / '.preparation-linked.tmp'
        save(temp, pointer)
        temp.replace(prior_preparation)
    else:
        save(prior_preparation, pointer)
    print(json.dumps({**pointer, 'trajectories': 2, 'files': len(files), 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
