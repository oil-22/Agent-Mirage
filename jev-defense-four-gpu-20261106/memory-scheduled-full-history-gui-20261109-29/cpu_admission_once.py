"""New carryover integration boundaries; no HTTP, models or browser imports."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import traceback
import uuid

HERE = Path(__file__).resolve().parent
PACKAGE = HERE / 'runtime-package-linked02'
OLD = HERE.parent / 'full-history-gui-development-20261109-23/runtime-package'
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
read = lambda path: json.loads(Path(path).read_bytes())


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2); stream.write('\n')


def main():
    claim = HERE / 'CPU-admission-intent.json'
    save(claim, {'time': time.time(), 'once_only': True, 'manifest_sha256': sha(PACKAGE / 'manifest.json')})
    out = HERE / ('CPU-admission-' + str(time.time_ns())); out.mkdir()
    checks = []
    try:
        manifest = read(PACKAGE / 'manifest.json')
        for name, expected in manifest['files'].items():
            assert sha(PACKAGE / name) == expected, name
        for path in PACKAGE.rglob('*.py'):
            compile(path.read_text(encoding='utf8'), str(path), 'exec')
        checks.append('complete_frozen_package_compiles_and_SHA_matches')
        sys.path[:0] = [str(PACKAGE), str(PACKAGE / 'release')]
        from protocol import RunBudget
        from complete_actor_history import CompleteAcceptedActorHistory
        from defense.core import Controller, Journal, Limits
        import carryover_runtime as c
        from gui_transport import GUIQwen
        plan, state = read(PACKAGE / 'plan.json'), read(PACKAGE / 'carryover/state.json')
        assert plan == read(OLD / 'plan.json') and len(plan['queue']) == 32
        assert plan['queue'][0]['run_id'] == state['original_track']
        assert state['initial_transport_counts'] == {'actor': 11, 'judge': 34, 'evidence': 0}
        old_manifest = read(OLD / 'manifest.json')
        for name, expected in old_manifest['files'].items():
            if name.startswith('release/') or name in ['bounded_auxiliary.py', 'fixed-prompt.txt', 'bounded_schema.py', 'stateless_boundary.py']:
                assert sha(PACKAGE / name) == expected, name
        checks.append('original32queue_full_release_prompts_auxiliary_and_strict_validators_unchanged')

        def rejects(callback, label):
            try:
                callback()
            except (AssertionError, ValueError):
                checks.append(label)
            else:
                raise AssertionError('Unsafe boundary allowed: ' + label)

        budget = RunBudget(plan, state)
        run = state['original_track']
        begin = {'trajectory_id': run, 'request_id': uuid.uuid4().hex}
        budget.admit('/begin', begin)
        assert budget.counts == state['initial_transport_counts']
        request = {'trajectory_id': run, 'decision_index': 12, 'attempt_index': 35,
                   'request_id': uuid.uuid4().hex, 'payload': {'operation': 'judge'}}
        budget.admit('/', request)
        assert budget.counts == {'actor': 11, 'judge': 35, 'evidence': 0}
        checks.append('first_new_judge_is35_and_spent_OOM_and_linked26_are_charged')
        rejects(lambda: budget.admit('/', {**request, 'request_id': state['disallowed_prior_request_ids'][0], 'attempt_index': 36}), 'old_request_UUID_rejected')
        rejects(lambda: budget.admit('/', {**request, 'request_id': uuid.uuid4().hex, 'attempt_index': 1}), 'silent_budget_reset_rejected')
        rejects(lambda: budget.admit('/evidence', {**request, 'request_id': uuid.uuid4().hex, 'attempt_index': 1}), 'auxiliary_disabled_first_track_enforced')
        budget.counts['judge'] = 140
        rejects(lambda: budget.admit('/', {**request, 'request_id': uuid.uuid4().hex, 'attempt_index': 141}), 'original140judge_cap_enforced')
        budget.admit('/end', {'trajectory_id': run, 'request_id': uuid.uuid4().hex,
            'status': 'completed', 'terminal_receipt_sha256': '0' * 64})
        budget.admit('/begin', {'trajectory_id': plan['queue'][1]['run_id'], 'request_id': uuid.uuid4().hex})
        assert budget.counts == {'actor': 0, 'judge': 0, 'evidence': 0}
        checks.append('only_first_unfinished_track_carries_counts_next31start_zero')
        transport = GUIQwen.__new__(GUIQwen)
        transport.set_run(run, None)
        assert transport.attempts == state['initial_transport_counts']
        transport.set_run(plan['queue'][1]['run_id'], None)
        assert transport.attempts == {'actor': 0, 'judge': 0, 'evidence': 0}
        checks.append('real_transport_hydration_agrees_with_server_budget')
        frozen = (PACKAGE / 'carryover/checkpoint/last-actually-delivered.png').read_bytes()
        c.require_same_live_image(frozen, state['original_current_image_sha256'])
        rejects(lambda: c.require_same_live_image(frozen + b'x', state['original_current_image_sha256']), 'changed_live_capture_cannot_reuse_old_verdict_or_action')

        def forbidden(*args, **kwargs):
            raise RuntimeError('No new model call allowed during carryover CPU integration')

        limits = plan['limits']
        controller = Controller(forbidden, Journal(out / 'journal'), 'joint', Limits(
            max_recaptures=2, max_regenerations=2, max_actor_calls=70, max_verifier_calls=140,
            wait_seconds=tuple(limits['wait_seconds']), probe_current_targets=True,
            probe_target_alignment=True, full_completion_history=True, probe_completion=True,
            probe_history_reports=True, probe_observation_readiness=True))
        system = read(PACKAGE / 'carryover/checkpoint/accepted-actual-history.json')['system']
        transcript = CompleteAcceptedActorHistory(system)
        hydrated = c.hydrate_history(PACKAGE, transcript, controller)
        assert hydrated['sequence'] == 10 and len(controller.reference_bank) == 10
        assert len(transcript.messages) == 20 and len(transcript.accepted) == 10
        checks.append('all20actual_messages10reference_frames_and_Controller_state_restored')
        native_source = ast.parse((PACKAGE / 'native-parser-source.py').read_text(encoding='utf8'))
        parse = next(n for n in native_source.body if isinstance(n, ast.FunctionDef) and n.name == 'parse')
        namespace = {'json': json, 're': re}
        exec(compile(ast.Module(body=[parse], type_ignores=[]), 'source-native-parse', 'exec'), namespace)

        def parser(text):
            payload = namespace['parse'](text)
            return {'name': payload['type'], 'parsed': True, 'executor_fallback_wait': False,
                    'payload': payload, 'coordinate_space': 'normalized_1000'}

        initial = c.original_view(read(PACKAGE / 'carryover/checkpoint/0044/payload.json')['view'])
        result = c.pending_decision(PACKAGE, controller, initial, transcript, parser, controller.log)
        assert result['status'] == 'accepted' and controller.actor_calls == 11 and controller.verifier_calls == 34
        transcript.commit_accepted(result)
        assert len(transcript.messages) == 22 and len(transcript.accepted) == 11
        events = [json.loads(line) for line in (out / 'journal/events.jsonl').read_bytes().splitlines()]
        assert not any(row['kind'] == 'candidate' for row in events)
        assert sum(row['kind'] == 'carryover_replay_candidate' for row in events) == 1
        assert not any(row['kind'] == 'action_executed' for row in events)
        checks.append('new_real_helper_replays_only_cached_sources_no_duplicate_candidate_or_action')
        checks.append('pending11accepted_full_history_committed_without_new_model_or_budget_spend')
        for name in ['actor', 'parser', 'public', 'recapture']:
            get = lambda path: next(n for n in ast.walk(ast.parse(path.read_text(encoding='utf8'))) if isinstance(n, ast.FunctionDef) and n.name == name)
            assert ast.dump(get(PACKAGE / 'run_independent_gui.py'), include_attributes=False) == ast.dump(get(OLD / 'run_independent_gui.py'), include_attributes=False), name
        checks.append('actual_actor_native_parser_public_context_and_recapture_function_AST_unchanged')
        receipt = {'schema': 'new-linked29-carryover-integration-CPU-admission-v1',
            'passed': True, 'time': time.time(), 'manifest_sha256': sha(PACKAGE / 'manifest.json'),
            'checks': checks, 'check_count': len(checks), 'actual_model_GUI_scorer_paid_calls': 0,
            'live_restoration_and_new_auxiliary_schedule_generation_unproven': True,
            'launch_ready_requires_actual_ownership_and_live_capture_binding': True}
        save(out / 'receipt.json', receipt)
        save(out / 'seal.json', {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()})
        save(HERE / 'CPU-admission.json', {'receipt': str(out / 'receipt.json'), 'receipt_sha256': sha(out / 'receipt.json'),
                                         'manifest_sha256': sha(PACKAGE / 'manifest.json'), 'passed': True})
        print(json.dumps({'passed': True, 'checks': len(checks), 'receipt': str(out / 'receipt.json'), 'model_GUI_calls': 0}))
    except BaseException:
        save(out / 'failure.json', {'traceback': traceback.format_exc(), 'checks_passed': checks, 'new_model_GUI_scorer_paid_calls': 0})
        save(out / 'failure-seal.json', {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()})
        raise


if __name__ == '__main__':
    main()
