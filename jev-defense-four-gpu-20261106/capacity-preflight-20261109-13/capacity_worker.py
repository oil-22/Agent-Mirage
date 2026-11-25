"""Two-call GPU-only technical preflight; never resumes the failed GUI batch."""
import argparse
import base64
import fcntl
import json
import os
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'release')]
from model_runtime import load_runtime, save, sha, canonical
from resource_gate import assert_owned_resources, identity, same_identity
from defense.core import Journal, PublicView, VisibleImage
import image_evidence as contract
import bounded_auxiliary

LEASE = Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')


def main(a):
    assert sha(a.manifest) == a.manifest_sha256
    manifest = json.loads(a.manifest.read_bytes()); package = a.manifest.parent
    for name, expected in manifest['files'].items():
        assert sha(package / name) == expected, name
    assert manifest['limits'] == {'auxiliary': 1, 'judge': 1, 'actor': 0, 'GUI': 0,
                                  'scorer': 0, 'paid_API': 0, 'format_retries': 0}
    assert os.getuid() == 1033 and os.environ['CUDA_VISIBLE_DEVICES'] == '4,5,6,7'
    assert not a.output.exists(); a.output.mkdir()
    root = a.output; me = identity(os.getpid())
    launcher = json.loads(os.environ['MIRAGE_JEV_LAUNCHER_IDENTITY'])
    assert same_identity(identity(os.getppid()), launcher)
    save(root / 'process.json', me); journal = Journal(root / 'journal')
    attempted = []; completed = []; error = None; started = time.time()

    def resource(empty=False):
        assert not (root.parent / 'stop-requested.json').exists()
        proof = assert_owned_resources(LEASE, manifest['expected_holder'],
                                       {me['pid']: me, launcher['pid']: launcher}, empty)
        journal.append('actual_resource_check', proof)
        return proof

    def status(phase):
        p = root / '.status.tmp'
        p.write_bytes(canonical({'phase': phase, 'time': time.time(),
                                 'attempted': attempted, 'completed': completed}))
        p.replace(root / 'status.json')

    try:
        resource(True)
        mutex = Path(json.loads(LEASE.read_bytes())['inference_lock']).open('a')
        fcntl.flock(mutex, fcntl.LOCK_EX | fcntl.LOCK_NB)
        status('loading')
        rt = load_runtime(package, root, journal, resource, manifest, me)
        engine, torch, audit = rt['engine'], rt['torch'], rt['audited_generation']
        support, aux_support = rt['support'], rt['aux_support']
        auxiliary, processor, generation = rt['auxiliary_model'], rt['auxiliary_processor'], rt['generation']
        token_data = bounded_auxiliary.prepare(processor, generation, root, package)
        target = root / 'auxiliary/A01'; target.mkdir(parents=True)
        raw = (package / 'new-auxiliary-full.png').read_bytes()
        auxref = json.loads((package / 'auxiliary-identity-reference.json').read_bytes())['base_model']
        request = contract.build_image_only_request(raw, auxref['repo'], auxref['revision'])
        assert contract.validate_image_only_request(request) == raw
        save(target / 'request.json', request); (target / 'original.png').write_bytes(raw)
        resource(); attempted.append('auxiliary/A01'); status('auxiliary_generating')
        journal.append('new_auxiliary_request', {'request_sha256': sha(target / 'request.json'),
                                               'complete_image_sha256': sha(target / 'original.png')})
        support.reset_memory(torch); began = time.perf_counter()
        text, actual, utf8 = bounded_auxiliary.generate(auxiliary, processor, generation, torch,
                                                       audit, token_data, raw, target)
        save(target / 'response.json', {'text': text, 'actual_natural_EOS': actual['natural_EOS'],
                                       'seconds_including_instrumentation': time.perf_counter() - began})
        lifecycle = json.loads((target / 'stateless-context-discarded.json').read_bytes())
        assert lifecycle['actual_first_forward_cache_length'] == 0
        assert lifecycle['all_observed_cache_objects_released']
        contract_valid = False
        try:
            if not utf8:
                raise contract.EvidenceContractError('Native UTF8 roundtrip failed')
            packet = contract.actor_packet(request, text, actual['natural_EOS'])
            save(target / 'packet.json', packet); contract_valid = True
        except contract.EvidenceContractError as exc:
            save(target / 'contract-failure.json', {'error': str(exc), 'no_retry': True})
        completed.append({'call': 'auxiliary/A01', 'natural_EOS': actual['natural_EOS'],
                          'format_contract_valid': contract_valid, 'semantic_pass': None})
        save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
        journal.append('auxiliary_reply_sealed', {'seal_sha256': sha(target / 'seal.json')})
        torch.cuda.empty_cache()

        # This original request failed at prefill with zero generated tokens.
        # Exactly one linked technical attempt is permitted; no trajectory resumes.
        original = package / 'original0178'
        payload = json.loads((original / 'payload.json').read_bytes())
        assert payload['operation'] == 'judge'
        assert set(payload) == {'candidate', 'operation', 'system', 'view'}
        frozen = payload['view']
        view = PublicView(frozen['observation_id'], frozen['messages'],
                          tuple(VisibleImage(base64.b64decode(im['raw_base64']), im['role'])
                                for im in frozen['images']), frozen['recent_action'],
                          frozen['execution_feedback'], frozen['observed_at'])
        assert len(view.images) == 4
        expected_tensors = json.loads((original / 'prepared.json').read_bytes())
        expected_generation = json.loads((original / 'effective-generation.json').read_bytes())
        assert expected_tensors['input_ids']['shape'] == [1, 20382]
        assert expected_generation['max_new_tokens'] == 4096
        target = root / 'judge/J01'; target.mkdir(parents=True)
        (target / 'payload.json').write_bytes((original / 'payload.json').read_bytes())
        original_apply = engine.processor.apply_chat_template
        original_generate = engine.model.generate
        before_forward = {'passed': False}; generation_check = {'passed': False}

        def exact_apply(*args, **kwargs):
            tensors = original_apply(*args, **kwargs)
            assert set(tensors) == set(expected_tensors)
            records = {}
            for name, tensor in tensors.items():
                row = aux_support.tensor_record(tensor, torch, target, 'exact_CPU_' + name,
                                                'independent_original_failed_request_binding')
                assert all(row[k] == expected_tensors[name][k]
                           for k in ['shape', 'dtype', 'bytes', 'sha256']), name
                records[name] = row
            save(target / 'original-input-equality-before-first-forward.json',
                 {'passed': True, 'tensors': records, 'original_complete_images': 4,
                  'original_input_tokens': 20382, 'input_truncation_or_image_edits': False})
            before_forward['passed'] = True
            return tensors

        def exact_generate(*args, **kwargs):
            assert before_forward['passed']
            assert kwargs['generation_config'].to_dict() == expected_generation
            save(target / 'original-generation-configuration-equality.json',
                 {'passed': True, 'all_effective_native_generation_fields_equal': True,
                  'output_cap': 4096, 'precision': 'bfloat16', 'attention': 'sdpa',
                  'placement_may_change_numerical_outputs': True})
            generation_check['passed'] = True
            return original_generate(*args, **kwargs)

        resource(); attempted.append('judge/J01'); status('judge_generating')
        journal.append('linked_original_zero_token_OOM_request',
                       {'original_payload_sha256': sha(original / 'payload.json'),
                        'original_input_ids_sha256': expected_tensors['input_ids']['sha256'],
                        'one_technical_attempt_only': True, 'old_GUI_resumed': False})
        engine.processor.apply_chat_template = exact_apply
        engine.model.generate = exact_generate
        support.reset_memory(torch); began = time.perf_counter()
        try:
            with audit(engine.model, engine.processor, target):
                reply = engine.judge(payload['system'], view, payload['candidate'],
                                     receipt=target / 'generation.json')
        finally:
            engine.processor.apply_chat_template = original_apply
            engine.model.generate = original_generate
        actual = json.loads((target / 'actual-generation.json').read_bytes())
        assert before_forward['passed'] and generation_check['passed']
        (target / 'raw-output.txt').write_text(reply, encoding='utf8')
        save(target / 'response.json', {'text': reply, 'natural_EOS': actual['natural_EOS'],
                                       'seconds_including_instrumentation': time.perf_counter() - began})
        assert actual['natural_EOS'] and actual['input_tokens'] == 20382
        completed.append({'call': 'judge/J01', 'natural_EOS': True,
                          'original_input_and_effective_generation_equal': True,
                          'semantic_pass': None, 'GUI_trajectory_recovered': False})
        resource()
        save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
        journal.append('linked_capacity_reply_sealed', {'seal_sha256': sha(target / 'seal.json')})
        status('completed')
        save(root / 'summary.json', {'completed': completed, 'actual_calls': 2,
              'both_models_remained_resident_on_four_authorized_GPUs': True,
              'exact_failed_prefill_input_completed': True, 'old_trajectory_resumed': False,
              'all_future_full_history_inputs_fit_proven': False, 'defense_efficacy_established': False})
    except BaseException as exc:
        error = {'type': type(exc).__name__, 'traceback': traceback.format_exc(),
                 'resource_evidence': getattr(exc, 'resource_evidence', None), 'no_retry': True}
        save(root / 'failure.json', error); journal.append('failure_preserved', error); status('failure')
    finally:
        journal.append('worker_terminal', {'status': 'failure' if error else 'completed'})
        save(root / 'terminal.json', {'status': 'failure' if error else 'completed',
              'attempted': attempted, 'completed': completed, 'error': error,
              'started': started, 'ended': time.time(), 'new_actor_GUI_scorer_paid_calls': 0})
        save(root / 'worker-manifest.json', {p.relative_to(root).as_posix(): sha(p)
                                             for p in root.rglob('*') if p.is_file()})
    return 1 if error else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    a = parser.parse_args()
    try:
        exit_code = main(a)
    except BaseException:
        p = HERE / 'pre-admission-failures' / str(time.time_ns()); p.mkdir(parents=True)
        save(p / 'failure.json', {'traceback': traceback.format_exc(), 'no_retry': True})
        exit_code = 1
    raise SystemExit(exit_code)
