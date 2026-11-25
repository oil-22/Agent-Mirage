"""New finite source-bound click-scope and stateless auxiliary development.

No actor, GUI task, scorer, network model API, or old terminal is invoked.
"""
import argparse
import ast
import base64
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'release')]
from model_runtime import load_runtime, save, sha, canonical, digest
from resource_gate import assert_owned_resources, identity, same_identity
from defense.core import Controller, Journal, Limits, PublicView, VisibleImage, ValidationError
from exploratory_action_scope import with_exploratory_action_scope
import bounded_auxiliary
import image_evidence as contract

LEASE = Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')


def main(args):
    assert sha(args.manifest) == args.manifest_sha256
    manifest = json.loads(args.manifest.read_bytes())
    package = args.manifest.parent
    for name, expected in manifest['files'].items():
        assert sha(package / name) == expected, name
    plan = json.loads((package / 'controls-plan.json').read_bytes())
    assert plan['limits'] == {'auxiliary': 3, 'judge': 32, 'actor': 0, 'GUI': 0,
                              'scorer': 0, 'paid_API': 0, 'format_retries_per_judge_control': 1}
    assert [row['id'] for row in plan['auxiliary']] == ['U01', 'U02', 'U03']
    assert [row['id'] for row in plan['judges']] == ['E%02d' % i for i in range(1, 9)]
    assert plan['conditions'] == ['prior_G_unchanged', 'same_G_plus_final_exploratory_click_scope']
    assert os.getuid() == 1033 and os.environ['CUDA_VISIBLE_DEVICES'] == '4,5,6,7'
    assert not args.output.exists()
    args.output.mkdir()
    root = args.output
    me = identity(os.getpid())
    launcher = json.loads(os.environ['MIRAGE_JEV_LAUNCHER_IDENTITY'])
    assert same_identity(identity(os.getppid()), launcher)
    save(root / 'process.json', me)
    journal = Journal(root / 'journal')
    started = time.time()
    attempts = {'auxiliary': [], 'judge': []}
    completions = {'auxiliary': [], 'judge': []}
    results, error = [], None

    def resource(empty=False):
        assert not (root.parent / 'stop-requested.json').exists()
        proof = assert_owned_resources(LEASE, manifest['expected_holder'],
                                        {me['pid']: me, launcher['pid']: launcher}, empty)
        journal.append('actual_resource_check', proof)
        return proof

    def status(phase, **extra):
        temporary = root / '.status.tmp'
        temporary.write_bytes(canonical({'phase': phase, 'time': time.time(),
                                         'attempted': attempts, 'completed': completions, **extra}))
        temporary.replace(root / 'status.json')

    try:
        resource(True)
        mutex = Path(json.loads(LEASE.read_bytes())['inference_lock']).open('a')
        fcntl.flock(mutex, fcntl.LOCK_EX | fcntl.LOCK_NB)
        status('loading')
        runtime = load_runtime(package, root, journal, resource, manifest, me)
        engine, torch = runtime['engine'], runtime['torch']
        support, audit = runtime['support'], runtime['audited_generation']
        auxiliary, processor, generation = runtime['auxiliary_model'], runtime['auxiliary_processor'], runtime['generation']
        token_data = bounded_auxiliary.prepare(processor, generation, root, package)
        auxiliary_root = root / 'auxiliary'
        auxiliary_root.mkdir()
        call_ids = []
        for row in plan['auxiliary']:
            resource()
            assert len(attempts['auxiliary']) < 3
            source = package / row['path']
            assert sha(source) == row['sha256']
            request = json.loads(source.read_bytes())
            raw = contract.validate_image_only_request(request)
            target = auxiliary_root / row['id']
            target.mkdir()
            save(target / 'request.json', request)
            (target / 'original.png').write_bytes(raw)
            attempts['auxiliary'].append(row['id'])
            status('auxiliary_generating', case=row['id'])
            journal.append('auxiliary_request', {'case': row['id'], 'request_sha256': sha(target / 'request.json'),
                                                'independent_invocation_no_reply_reuse': True})
            support.reset_memory(torch)
            began = time.perf_counter()
            text, actual, utf8_roundtrip = bounded_auxiliary.generate(
                auxiliary, processor, generation, torch, audit, token_data, raw, target)
            lifecycle = json.loads((target / 'stateless-context-discarded.json').read_bytes())
            assert lifecycle['actual_first_forward_cache_length'] == 0
            assert lifecycle['all_observed_cache_objects_released']
            assert lifecycle['call_id'] not in call_ids
            call_ids.append(lifecycle['call_id'])
            result = {'id': row['id'], 'natural_EOS': actual['natural_EOS'], 'semantic_pass': None,
                      'seconds_including_instrumentation': time.perf_counter() - began,
                      'actual_forward_empty_cache_and_release_passed': True}
            response = {'request_sha256': digest(contract.canonical(request)),
                        'image_sha256': request['image_sha256'], 'model': request['model'],
                        'revision': request['revision'], 'raw_output': text, 'natural_eos': actual['natural_EOS']}
            save(target / 'response.json', response)
            try:
                if not utf8_roundtrip:
                    raise contract.EvidenceContractError('Native byte output failed strict UTF8 roundtrip')
                packet = contract.actor_packet(request, text, actual['natural_EOS'])
                save(target / 'packet.json', packet)
                result['format_contract_valid'] = True
            except contract.EvidenceContractError as failure:
                result.update(format_contract_valid=False, error=str(failure), no_retry=True)
                save(target / 'contract-failure.json', result)
            completions['auxiliary'].append(result)
            resource()
            save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
            journal.append('auxiliary_reply_sealed', {'case': row['id'], 'seal_sha256': sha(target / 'seal.json')})
            torch.cuda.empty_cache()

        tree = ast.parse((package / 'native-parser-source.py').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'parse')
        namespace = {'json': json, 're': re}
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'native-parser-source.py', 'exec'), namespace)
        parse = namespace['parse']
        judge_root = root / 'judges'
        judge_root.mkdir()
        current = {'id': None, 'condition': None, 'proposal': None, 'calls': 0}

        def judge(system, view, candidate):
            resource()
            assert len(attempts['judge']) < 32 and current['calls'] < 2
            current['calls'] += 1
            actual_system = (with_exploratory_action_scope(system, current['proposal'])
                             if current['condition'] == plan['conditions'][1] else system)
            number = '%02d' % (len(attempts['judge']) + 1)
            target = judge_root / number
            target.mkdir()
            request = {'case': current['id'], 'condition': current['condition'],
                       'system': actual_system, 'controller_system_before_condition': system,
                       'public': view.data(),
                       'images': [{'raw_base64': base64.b64encode(image.raw).decode(), 'role': image.role}
                                  for image in view.images],
                       'candidate': candidate, 'strict_native_output_cap': 4096}
            save(target / 'request.json', request)
            attempts['judge'].append({'case': current['id'], 'condition': current['condition'], 'request': number})
            status('judge_generating', case=current['id'], condition=current['condition'], request=number)
            journal.append('actual_condition_judge_request', {
                'case': current['id'], 'condition': current['condition'], 'request': number,
                'request_sha256': sha(target / 'request.json'),
                'actual_system_utf8_sha256': digest(actual_system.encode()),
                'controller_system_utf8_sha256': digest(system.encode())})
            support.reset_memory(torch)
            began = time.perf_counter()
            with audit(engine.model, engine.processor, target):
                text = engine.judge(actual_system, view, candidate, receipt=target / 'generation.json')
            actual = json.loads((target / 'actual-generation.json').read_bytes())
            (target / 'raw-output.txt').write_text(text, encoding='utf8')
            save(target / 'response.json', {'text': text, 'natural_EOS': actual['natural_EOS'],
                                           'seconds_including_instrumentation': time.perf_counter() - began})
            resource()
            save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
            completions['judge'].append({'case': current['id'], 'condition': current['condition'],
                                         'request': number, 'natural_EOS': actual['natural_EOS']})
            journal.append('judge_reply_sealed', {'request': number, 'seal_sha256': sha(target / 'seal.json')})
            assert actual['natural_EOS'], 'Original4096 nonEOS terminal preserved; no output-cap extension'
            return text

        for row in plan['judges']:
            frozen_path = package / row['path']
            assert sha(frozen_path) == row['sha256']
            frozen = json.loads(frozen_path.read_bytes())
            public = frozen['view']
            view = PublicView(public['observation_id'], public['messages'],
                              tuple(VisibleImage(base64.b64decode(image['raw_base64']), image['role'])
                                    for image in public['images']), public['recent_action'],
                              public['execution_feedback'], public['observed_at'])
            candidate = frozen['candidate']
            native = parse(candidate)
            proposal = {'name': native['type'], 'parsed': True, 'executor_fallback_wait': False,
                        'payload': native, 'coordinate_space': 'normalized_1000'}
            for condition in plan['conditions']:
                current.update(id=row['id'], condition=condition, proposal=proposal, calls=0)
                journal.observation(view, audience='new_constructed_pair_same_full_view')
                controller = Controller(judge, journal, 'post_only',
                                        Limits(max_verifier_calls=2, max_format_retries=1), sleeper=lambda _: None)
                before = len(attempts['judge'])
                try:
                    verdict = controller.inspect('verify', view, candidate, proposal)
                    result = {'id': row['id'], 'condition': condition,
                              'format_citation_contract_valid': True, 'verdict': verdict, 'semantic_pass': None}
                except ValidationError as failure:
                    result = {'id': row['id'], 'condition': condition,
                              'format_citation_contract_valid': False, 'error': str(failure), 'semantic_pass': None}
                result.update(actual_judge_calls=len(attempts['judge']) - before,
                              GUI_action_executed=False, actor_feedback_or_full_GUI_tested=False)
                save(root / (row['id'] + '-' + condition + '-result.json'), result)
                results.append(result)
                journal.append('new_paired_control_terminal', result)
                torch.cuda.empty_cache()
        status('completed')
        save(root / 'summary.json', {'status': 'completed', 'paired_judge_controls': results,
                                    'auxiliary': completions['auxiliary'],
                                    'actual_auxiliary_calls': len(attempts['auxiliary']),
                                    'actual_judge_calls': len(attempts['judge']),
                                    'actor_GUI_scorer_paid_calls': 0,
                                    'old_semantic_terminal_controls_reexecuted': False,
                                    'semantic_efficacy_or_GUI_release_established': False})
    except BaseException as failure:
        error = {'type': type(failure).__name__, 'traceback': traceback.format_exc(),
                 'resource_evidence': getattr(failure, 'resource_evidence', None), 'no_automatic_retry': True}
        save(root / 'failure.json', error)
        journal.append('failure_preserved', error)
        status('failure')
    finally:
        journal.append('worker_terminal', {'status': 'failure' if error else 'completed'})
        save(root / 'terminal.json', {'status': 'failure' if error else 'completed',
                                     'attempted': attempts, 'completed': completions, 'error': error,
                                     'started': started, 'ended': time.time(),
                                     'actor_GUI_scorer_paid_calls': 0})
        save(root / 'worker-manifest.json', {p.relative_to(root).as_posix(): sha(p)
                                            for p in root.rglob('*') if p.is_file()})
    return 1 if error else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    try:
        code = main(arguments)
    except BaseException:
        failed = HERE / 'pre-admission-failures' / str(time.time_ns())
        failed.mkdir(parents=True, exist_ok=False)
        save(failed / 'failure.json', {'traceback': traceback.format_exc(), 'no_automatic_retry': True})
        code = 1
    raise SystemExit(code)
