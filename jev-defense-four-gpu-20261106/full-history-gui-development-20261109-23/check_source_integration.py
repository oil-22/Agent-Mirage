"""Exercise actual new GUI callbacks with sealed readings, without inference."""
import ast
import base64
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import uuid

HERE = Path(__file__).resolve().parent
PACKAGE = HERE / 'runtime-package'
BASE = HERE.parent
sys.path[:0] = [str(PACKAGE), str(PACKAGE / 'release')]
from complete_actor_history import CompleteAcceptedActorHistory, HistoryBindingError
from defense.core import PublicView, VisibleImage
from defense.qwen_backend import LocalQwen
from defense.http_backend import RemoteQwen
from gui_transport import GUIQwen, BoundObserver
from protocol import RunBudget
import image_evidence as contract

sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    target = HERE / ('CPU-integration-' + str(time.time_ns()))
    target.mkdir()
    source = ast.parse((PACKAGE / 'run_independent_gui.py').read_text(encoding='utf8'))
    public = next(node for node in ast.walk(source) if isinstance(node, ast.FunctionDef) and node.name == 'public')
    block = next(node for node in source.body if isinstance(node, ast.FunctionDef) and node.name == 'block')
    factory = ast.parse('def factory():\n sequence=0\n latest_public_raw=None\n').body[0]
    factory.body.extend([public, ast.Return(value=ast.Name(id='public', ctx=ast.Load()))])
    module = ast.fix_missing_locations(ast.Module(body=[block, factory], type_ignores=[]))
    template = json.loads((PACKAGE / 'actor-template.json').read_bytes())
    system = template['messages'][0]['content']
    transcript = CompleteAcceptedActorHistory(system)
    namespace = {'base64': base64, 'json': json, 'VisibleImage': VisibleImage, 'PublicView': PublicView,
                 'transcript': transcript, 'env': SimpleNamespace(context=SimpleNamespace(pages=[object()])),
                 'step': 1, 'task': {'intent': 'CPU fixture: inspect the current control'},
                 'previous': None, 'execution_feedback': ''}
    exec(compile(module, 'actual-new-GUI-public-callback', 'exec'), namespace)
    make_public = namespace['factory']()
    scenes = ['T01-object-catalog', 'T03-filled-filter', 'T01-object-catalog']
    frozen = BASE / 'unicode-guard-real-preflight-20261109-18/terminal-collection-1794218465768999100/original/worker/auxiliary'
    outputs = {}
    raws = []
    for scene in scenes:
        folder = frozen / scene
        raw = (folder / 'original.png').read_bytes()
        outputs[hashlib.sha256(raw).hexdigest()] = (folder / 'raw-output.txt').read_text(encoding='utf8')
        raws.append(raw)

    class FakeModel:
        def __init__(self):
            self.requests = []
        def evidence(self, request):
            raw = contract.validate_image_only_request(request)
            assert set(request) == {'image_base64', 'image_sha256', 'model', 'original_size', 'policy', 'prompt', 'prompt_sha256', 'revision'}
            assert request['prompt'] == contract.FIXED_PROMPT
            self.requests.append(copy.deepcopy(request))
            return {'request_sha256': contract.digest(contract.canonical(request)),
                    'image_sha256': hashlib.sha256(raw).hexdigest(), 'model': request['model'],
                    'revision': request['revision'], 'raw_output': outputs[request['image_sha256']], 'natural_eos': True}

    log = SimpleNamespace(append=lambda *_: None)
    model = FakeModel()
    observer = BoundObserver(model, True)
    rows = []
    for index, raw in enumerate(raws, 1):
        namespace['step'] = index
        view = make_public(raw)
        original = copy.deepcopy(view.data())
        body = {key: copy.deepcopy(value) for key, value in template.items() if key != 'messages'}
        body['messages'] = copy.deepcopy(view.messages)
        augmented = observer.augment(body, view, log)
        assert view.data() == original
        image_blocks = [b for m in augmented['messages'] if isinstance(m['content'], list)
                        for b in m['content'] if b.get('type') == 'image_url']
        assert len(image_blocks) == index
        if index > 1:
            current = augmented['messages'][-1]['content']
            assert any(b.get('type') == 'text' and b['text'].endswith(namespace['execution_feedback']) for b in current)
            assert augmented['messages'][1:1 + len(transcript.messages)] == transcript.messages
        # Synthetic actor output is solely an integration fixture, never a model result.
        reply = '<action>{"type":"wait"}</action>'
        transcript.record_actual_reply(augmented, reply)
        proof = transcript.commit_accepted({'status': 'accepted', 'candidate': reply, 'observation_id': view.observation_id})
        rows.append({'step': index, 'actor_image_blocks': len(image_blocks), 'proof': proof,
                     'auxiliary_request_sha256': contract.digest(contract.canonical(model.requests[-1]))})
        namespace['previous'] = {'type': 'wait'}
        namespace['execution_feedback'] = json.dumps({'execution_returned': True, 'result_state': 'not confirmed by execution alone'})
    assert observer.calls == len(model.requests) == 3
    assert model.requests[0] == model.requests[2], 'Repeated same input is a NEW independent request, never reply memoization'
    assert len(observer.failures) == 0
    missing = make_public(None)
    before = len(model.requests)
    missing_body = {key: copy.deepcopy(value) for key, value in template.items() if key != 'messages'}
    missing_body['messages'] = copy.deepcopy(missing.messages)
    unavailable = observer.augment(missing_body, missing, log)
    assert len(model.requests) == before and observer.calls == 3
    assert unavailable['messages'][1:1 + len(transcript.messages)] == transcript.messages

    # Use the actual native transport: every retained image must resolve, and
    # explicit absent public-image bindings must still be rejected.
    engine = LocalQwen.__new__(LocalQwen)
    wires = []
    def capture(messages, max_tokens, path, **kwargs):
        assert max_tokens == 4096
        wires.append(copy.deepcopy(messages))
        return 'CPU_ONLY_NO_MODEL_REPLY'
    engine.generate = capture
    engine.judge('CPU transport only', make_public(raws[-1]), reply)
    assert len(wires) == 1
    broken = replace(copy.deepcopy(make_public(raws[-1])), images=())
    try:
        engine.judge('CPU transport only', broken, reply)
    except ValueError as exc:
        assert 'Message image missing from public image list' in str(exc)
    else:
        raise AssertionError('Missing historical image binding was accepted')
    assert GUIQwen.actor is RemoteQwen.actor and GUIQwen.judge is RemoteQwen.judge

    # Exercise every new queue identity/order using real admission logic, and
    # enforce original per-track caps without actual HTTP/model/GUI execution.
    plan = json.loads((PACKAGE / 'plan.json').read_bytes())
    budget = RunBudget(plan)
    for item in plan['queue']:
        budget.admit('/begin', {'trajectory_id': item['run_id'], 'request_id': uuid.uuid4().hex})
        if item == plan['queue'][0]:
            for number in range(1, 71):
                budget.admit('/', {'trajectory_id': item['run_id'], 'request_id': uuid.uuid4().hex,
                    'decision_index': min(number, 50), 'attempt_index': number, 'payload': {'operation': 'actor'}})
            try:
                budget.admit('/', {'trajectory_id': item['run_id'], 'request_id': uuid.uuid4().hex,
                    'decision_index': 50, 'attempt_index': 71, 'payload': {'operation': 'actor'}})
            except AssertionError:
                pass
            else:
                raise AssertionError('Original 70-actor cap was expanded')
        budget.admit('/end', {'trajectory_id': item['run_id'], 'request_id': uuid.uuid4().hex,
            'status': 'completed', 'terminal_receipt_sha256': '0' * 64})
    assert budget.terminal and len(budget.done) == 32
    assert plan['total_new_primary_call_cap'] == 32 * 210
    assert plan['total_new_auxiliary_call_cap'] == sum(row['observer_enabled'] for row in plan['queue']) * 60
    proof = {'passed': True, 'time': time.time(), 'source_callback_sha256': sha(PACKAGE / 'run_independent_gui.py'),
             'actual_GUI_public_callback_executed': True, 'synthetic_integration_only': True,
             'full_accepted_image_messages_and_executor_feedback_preserved': rows,
             'same_image_three_independent_auxiliary_requests': len(model.requests),
             'no_task_history_candidate_previous_auxiliary_data_in_auxiliary_request': True,
             'missing_image_no_auxiliary_call_full_main_history_retained': True,
             'native_judge_historical_image_binding_and_missing_binding_rejection': True,
             'all_32_queue_identities_and_original_70_actor_cap_exercised': True,
             'real_model_GPU_GUI_scorer_paid_calls': 0, 'capacity_semantic_or_efficacy_proof': False}
    save(target / 'receipt.json', proof)
    save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
    print(json.dumps({'passed': True, 'evidence': str(target), 'receipt_sha256': sha(target / 'receipt.json'),
                      'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
