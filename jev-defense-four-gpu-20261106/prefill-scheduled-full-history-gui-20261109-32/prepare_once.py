"""Prepare the new prefill-residency GUI continuation and unchanged 32-track plan."""
import copy
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OLD = BASE / 'memory-scheduled-full-history-gui-20261109-29/runtime-package-linked02'
CAPACITY = BASE / 'prefill-residency-recovery-20261109-31'
OUT = HERE / 'runtime-package'
EXPORTED = Path('D:/MultiModel/j29evidence/1794228241952080200')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_bytes())


def save(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf8') as f:
        json.dump(v, f, ensure_ascii=False, indent=2); f.write('\n')


def one(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after)


def main():
    assert not OUT.exists() and not (HERE / 'preparation.json').exists()
    old = read(OLD / 'manifest.json')
    assert sha(OLD / 'manifest.json') == 'bced549e679b03e286e2663a34f17b2319b2b35f0ef09397a8f39404073ee8a0'
    for n, h in old['files'].items():
        assert sha(OLD / n) == h, n
    checkpoint = Path(read(HERE / 'checkpoint-created.json')['checkpoint'])
    for n, h in read(checkpoint / 'seal.json').items():
        assert sha(checkpoint / n) == h, n
    collection = Path(read(CAPACITY / 'terminal-collection-created.json')['collection'])
    assert read(collection / 'audit.json')['passed']
    OUT.mkdir()
    for n in old['files']:
        if n.startswith('carryover/') or n in ['admission.json']:
            continue
        target = OUT / n; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OLD / n, target)
    shutil.copyfile(HERE / 'carryover_runtime.py', OUT / 'carryover_runtime.py')
    shutil.copyfile(CAPACITY / 'runtime-package/prefill_residency.py', OUT / 'prefill_residency.py')
    assert sha(OUT / 'model_runtime.py') == sha(CAPACITY / 'runtime-package/model_runtime.py')
    assert sha(OUT / 'resident_schedule.py') == sha(CAPACITY / 'runtime-package/resident_schedule.py')
    carry = OUT / 'carryover'; carry.mkdir()
    shutil.copytree(checkpoint, carry / 'checkpoint')
    shutil.copyfile(collection / 'original/worker/judge/J01/raw-output.txt', carry / 'linked31-raw-output.txt')
    shutil.copyfile(collection / 'audit.json', carry / 'linked31-technical-audit.json')
    requirements = read(checkpoint / 'requirements.json')
    navigation = read(HERE / 'navigation-provenance.json')
    scroll = read(HERE / 'scroll-markers-provenance.json')
    assert '1815' in scroll['snapshot_scroll_values'][-1]['fragment']
    state = read(OLD / 'carryover/state.json')
    for key in ['accepted_history_sha256', 'pending_candidate_event_sha256', 'original_current_image_sha256']:
        state[key] = requirements[key]
    old_gui = EXPORTED / '4090/output/batch/runs/fullhistory23-T000-clean-noaux/attempt-1794227118456197872'
    events = [json.loads(line) for line in (old_gui / 'events.jsonl').read_bytes().splitlines()]
    state['disallowed_prior_request_ids'] = sorted(set(state['disallowed_prior_request_ids']) |
        {e['data']['body']['request_id'] for e in events if e['kind'].endswith('_request')
         and isinstance(e['data'].get('body'), dict) and 'request_id' in e['data']['body']})
    state.update(original_actor_spent=17, original_judge_spent=50, original_auxiliary_spent=0,
        initial_transport_counts={'actor': 17, 'judge': 50, 'evidence': 0},
        next_new_actor_attempt=18, next_new_judge_attempt=51, original_actions_executed=16,
        first_pending_decision=17, controller_valid_state={}, navigation_urls=navigation['original_navigation_urls'],
        scroll_xy=[0, 1815], last_pointer_pixels=[598 / 1000 * 1280, 678 / 1000 * 720],
        original_private_trajectory=navigation['private_trajectory'],
        original_private_trajectory_sha256=navigation['private_trajectory_sha256'],
        original_trace=navigation['trace_file'], original_trace_sha256=navigation['trace_sha256'],
        original_track_multiple_infrastructure_interruptions=True,
        all_future_arms_same_native_device_map_and_prefill_weight_schedule=True)
    assert [e['data']['claims'] for e in events if e['kind'] == 'state_supported'][-1] == {}
    save(carry / 'state.json', state)

    server = (OLD / 'gpu_server.py').read_text(encoding='utf8')
    server = one(server, 'schedule=ResidentSchedule(runtime,root,journal,resource)',
        'schedule=ResidentSchedule(runtime,root,journal,resource)\n        from prefill_residency import PrefillResidency\n        prefill=PrefillResidency(runtime,schedule,root,journal,resource)')
    (OUT / 'gpu_server.py').write_text(server.replace('19139', '19140'), encoding='utf8')
    launcher = (OLD / 'launch_gui_service_once.py').read_text(encoding='utf8')
    (OUT / 'launch_gui_service_once.py').write_text(launcher.replace(OLD.parent.name, HERE.name), encoding='utf8')
    runner = (OLD / 'run_independent_gui.py').read_text(encoding='utf8')
    runner = one(runner, 'first_step=11;environment_actions=10', 'first_step=17;environment_actions=16')
    runner = one(runner, 'carryover.pending_decision(package,controller,initial,transcript,parser,log) if linked and step==11',
        'carryover.pending_decision(package,controller,initial,transcript,parser,log,actor,recapture) if linked and step==17')
    runner = one(runner, "result['original_prefix_actions_carried']=10 if linked else 0", "result['original_prefix_actions_carried']=16 if linked else 0")
    runner = one(runner, "result['original_prefix_actor_calls_carried']=11 if linked else 0", "result['original_prefix_actor_calls_carried']=17 if linked else 0")
    runner = one(runner, "result['original_prefix_judge_calls_carried_including_OOM_and26']=34 if linked else 0",
        "result['original_prefix_judge_calls_carried_including_OOM_and26_and31']=50 if linked else 0")
    (OUT / 'run_independent_gui.py').write_text(runner, encoding='utf8')
    token = secrets.token_urlsafe(48).encode()
    (OUT / 'private.token').write_bytes(token)
    save(OUT / 'admission.json', {'admit_new_GUI_development': True, 'formal_efficacy': False,
        'linked31_technical_audit_sha256': sha(collection / 'audit.json'),
        'original_environment_admission_reused': True, 'same_live_identity_required_before_pending17': True,
        'original_caps_and_strict_Controller_retained': True,
        'authorization': 'Existing sustained goal, owned4-7; unfinished technical continuation and original31unstarted tracks.'})
    for p in OUT.rglob('*.py'):
        compile(p.read_text(encoding='utf8'), str(p), 'exec')
    for n, h in old['files'].items():
        if n.startswith('release/'):
            assert sha(OUT / n) == h, n
    manifest = {k: copy.deepcopy(v) for k, v in old.items() if k not in ['files', 'worker_source_sha256', 'auth_token_sha256']}
    manifest.update(schema='GUI32-original-fullhistory-native-prefill-residency-continuation-v1',
        outputs='/home/researcher/jev-defense-four-gpu-20261106/' + HERE.name,
        GUI_output='/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name + '/batch',
        model_url='http://192.0.2.11:19140', auth_token_sha256=hashlib.sha256(token).hexdigest(),
        worker_source_sha256=sha(OUT / 'gpu_server.py'), carryover_state_sha256=sha(carry / 'state.json'),
        original29_manifest_sha256=sha(OLD / 'manifest.json'), linked31_manifest_sha256=sha(CAPACITY / 'runtime-package/manifest.json'),
        linked31_audit_sha256=sha(collection / 'audit.json'),
        previous_goal_turn_classification='progress: actual linked31 handle was confirmed completed, changing next action to terminal audit and GUI restoration',
        deployment_tradeoff='All actual forwards retain native GPU4-7 devices/BF16/SDPA; idle weights travel through RAM during complete prefill, then all restore for native decoding. Transfers and four reserved GPUs count. Both future arms identical. No future-capacity or output-bitwise or efficacy claim. Interrupted prefix requires sensitivity analysis.',
        files={p.relative_to(OUT).as_posix(): sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name != 'private.token'})
    save(OUT / 'manifest.json', manifest)
    save(HERE / 'preparation.json', {'time': time.time(), 'manifest_sha256': sha(OUT / 'manifest.json'),
        'files': len(manifest['files']), 'new_model_GUI_scorer_paid_calls': 0, 'launch_ready': False,
        'original32queue_unchanged': read(OUT / 'plan.json') == read(OLD / 'plan.json')})
    print(json.dumps({'package': str(OUT), 'manifest_sha256': sha(OUT / 'manifest.json'),
                      'carried': state['initial_transport_counts'], 'launch_ready': False}))


if __name__ == '__main__':
    main()
