"""One exact unfinished GUI29 judge attempt; original budget, no extra probes."""
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
from resident_schedule import ResidentSchedule
from prefill_residency import PrefillResidency

LEASE = Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')


def main(a):
    assert sha(a.manifest) == a.manifest_sha256
    m = json.loads(a.manifest.read_bytes()); package = a.manifest.parent
    for name, expected in m['files'].items():
        assert sha(package / name) == expected, name
    assert m['limits'] == {'auxiliary': 0, 'judge': 1, 'actor': 0, 'GUI': 0, 'scorer': 0,
                           'paid_API': 0, 'format_retries': 0}
    assert os.getuid() == 1033 and os.environ['CUDA_VISIBLE_DEVICES'] == '4,5,6,7'
    assert not a.output.exists(); a.output.mkdir()
    root = a.output; me = identity(os.getpid())
    launcher = json.loads(os.environ['MIRAGE_JEV_LAUNCHER_IDENTITY'])
    assert same_identity(identity(os.getppid()), launcher)
    save(root / 'process.json', me)
    journal = Journal(root / 'journal')
    error = None; started = time.time(); attempted = completed = 0; runtime = None

    def resource(empty=False):
        assert not (root.parent / 'stop-requested.json').exists()
        proof = assert_owned_resources(LEASE, m['expected_holder'], {me['pid']: me, launcher['pid']: launcher}, empty)
        journal.append('actual_resource_check', proof)
        return proof

    def status(phase):
        p = root / '.status.tmp'
        p.write_bytes(canonical({'phase': phase, 'time': time.time(), 'attempted': attempted,
                                 'completed': completed, 'original_judge_attempts_spent': 49,
                                 'total_linked_judge_attempts_spent': 49 + attempted,
                                 'judge_cap': 140, 'no_GUI_resumed': True}))
        p.replace(root / 'status.json')

    try:
        resource(True)
        mutex = Path(json.loads(LEASE.read_bytes())['inference_lock']).open('a')
        fcntl.flock(mutex, fcntl.LOCK_EX | fcntl.LOCK_NB)
        available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
                             if line.startswith('MemAvailable:'))) * 1024
        assert available >= 64 * 1024**3, 'Insufficient RAM for idle BF16 weights; no CPU inference fallback'
        save(root / 'host_storage_admission.json', {'available_RAM_bytes': available,
                                                   'minimum_RAM_bytes': 64 * 1024**3,
                                                   'CPU_model_inference_allowed': False})
        status('loading')
        runtime = load_runtime(package, root, journal, resource, m, me)
        engine, torch, audit = runtime['engine'], runtime['torch'], runtime['audited_generation']
        scheduler = ResidentSchedule(runtime, root, journal, resource)
        prefill = PrefillResidency(runtime, scheduler, root, journal, resource)
        original = package / 'original0021'
        payload = json.loads((original / 'payload.json').read_bytes())
        assert payload['operation'] == 'judge'
        v = payload['view']
        view = PublicView(v['observation_id'], v['messages'],
                          tuple(VisibleImage(base64.b64decode(im['raw_base64']), im['role']) for im in v['images']),
                          v['recent_action'], v['execution_feedback'], v['observed_at'])
        expected = json.loads((original / 'prepared.json').read_bytes())
        cfg = json.loads((original / 'effective-generation.json').read_bytes())
        assert len(view.images) == 17 and expected['input_ids']['shape'] == [1, 32184]
        assert cfg['max_new_tokens'] == 4096
        target = root / 'judge/J01'; target.mkdir(parents=True)
        (target / 'payload.json').write_bytes((original / 'payload.json').read_bytes())
        before_apply, before_generate = engine.processor.apply_chat_template, engine.model.generate
        checks = {'input': False, 'configuration': False}

        def exact_apply(*args, **kwargs):
            tensors = before_apply(*args, **kwargs)
            assert set(tensors) == set(expected)
            records = {}
            for key, tensor in tensors.items():
                row = runtime['aux_support'].tensor_record(tensor, torch, target, 'exact_CPU_' + key,
                                                           'exact_original0021_binding_before_first_forward')
                assert all(row[field] == expected[key][field] for field in ['shape', 'dtype', 'bytes', 'sha256']), key
                records[key] = row
            save(target / 'original-input-equality-before-first-forward.json', {
                'passed': True, 'tensors': records, 'complete_images': 17, 'complete_tokens': 32184,
                'no_input_truncation_or_image_edit': True})
            checks['input'] = True
            return tensors

        def exact_generate(*args, **kwargs):
            assert checks['input']
            assert kwargs['generation_config'].to_dict() == cfg
            scheduler.assert_primary_resident()
            save(target / 'original-generation-equality.json', {
                'passed': True, 'all_native_effective_fields_equal': True, 'BF16_SDPA': True,
                'output_cap': 4096, 'placement_numerical_output_bitwise_identity_not_guaranteed': True})
            checks['configuration'] = True
            return before_generate(*args, **kwargs)

        resource(); attempted = 1; status('exact_original_judge_generating')
        journal.append('linked_original0021_technical_request', {
            'payload_sha256': sha(original / 'payload.json'), 'original_generated_tokens': 0,
            'prior_judge_attempts_spent': 49, 'this_attempt_index': 50, 'judge_cap': 140,
            'same_pending_actor_candidate_not_regenerated': True, 'GUI_or_actions_reexecuted': False})
        engine.processor.apply_chat_template, engine.model.generate = exact_apply, exact_generate
        runtime['support'].reset_memory(torch); began = time.perf_counter()
        try:
            with audit(engine.model, engine.processor, target):
                reply = engine.judge(payload['system'], view, payload['candidate'], receipt=target / 'generation.json')
        finally:
            engine.processor.apply_chat_template, engine.model.generate = before_apply, before_generate
        generated = json.loads((target / 'actual-generation.json').read_bytes())
        assert all(checks.values()) and generated['natural_EOS']
        assert scheduler.primary_calls == generated['actual_forward_calls'] and scheduler.auxiliary_calls == 0
        save(target / 'response.json', {'text': reply, 'natural_EOS': True,
                                       'seconds_including_instrumentation': time.perf_counter() - began})
        (target / 'raw-output.txt').write_text(reply, encoding='utf8')
        save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
        journal.append('exact_request_reply_sealed', {'seal_sha256': sha(target / 'seal.json')})
        completed = 1; resource(); status('completed')
        save(root / 'summary.json', {'actual_calls': 1, 'actual_judge_calls': 1, 'natural_EOS': True,
            'same_original_full_request_and_effective_generation': True,
            'original_judge_spent': 49, 'linked_judge_spent': 50, 'judge_cap': 140,
            'original_actor_spent': 17, 'actor_cap': 70, 'original_executed_actions': 16,
            'auxiliary_generation_calls': 0, 'GUI_actions_or_scorer_paid_calls': 0,
            'only_GPU_model_forwards': True, 'idle_weight_RAM_staging': True,
            'GUI_continuation_or_defense_efficacy_established': False})
    except BaseException as exc:
        error = {'type': type(exc).__name__, 'traceback': traceback.format_exc(),
                 'resource_evidence': getattr(exc, 'resource_evidence', None), 'no_automatic_retry': True}
        save(root / 'failure.json', error)
        if runtime is not None:
            save(root / 'failure-memory.json', runtime['support'].memory(runtime['torch']))
        journal.append('technical_failure_preserved', error); status('technical_failure')
    finally:
        journal.append('worker_terminal', {'technical_failure': error is not None, 'actual_attempts': attempted})
        save(root / 'terminal.json', {'status': 'technical_failure' if error else 'completed',
              'actual_attempts': attempted, 'completed': completed, 'error': error,
              'started': started, 'ended': time.time(), 'no_GUI_continuation': True})
        save(root / 'worker-manifest.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
    return 1 if error else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(main(parser.parse_args()))

