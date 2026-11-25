"""Freeze a NEW linked service/GUI, carrying all spent calls and full history."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OLDROOT = BASE / 'full-history-gui-development-20261109-23'
OLD = OLDROOT / 'runtime-package'
CAPACITY = BASE / 'memory-scheduled-capacity-20261109-26'
CHECKPOINT = BASE / 'gui-technical-continuation-20261109-27/checkpoint-1794225173767282700'
OUT = HERE / 'runtime-package'
EXPORTED = Path(r'D:\MultiModel\j23evidence/1794223604796828100')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_bytes())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2); stream.write('\n')


def one(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after)


def main():
    assert not OUT.exists() and not (HERE / 'preparation.json').exists()
    old_manifest = read(OLD / 'manifest.json')
    assert sha(OLD / 'manifest.json') == 'cd84bc7135d2a5302a5c5ffa01da10f0f2fde8f2b918339cee94f7abb4d990e7'
    for name, expected in old_manifest['files'].items():
        assert sha(OLD / name) == expected, name
    capacity_pointer = read(CAPACITY / 'terminal-collection-created.json')
    collection = Path(capacity_pointer['collection'])
    assert sha(collection / 'audit.json') == capacity_pointer['audit_sha256']
    assert read(collection / 'audit.json')['passed']
    for name, expected in read(CHECKPOINT / 'seal.json').items():
        assert sha(CHECKPOINT / name) == expected, name
    OUT.mkdir()
    for name in old_manifest['files']:
        target = OUT / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OLD / name, target)
    for name in ['model_runtime.py', 'resident_schedule.py']:
        shutil.copyfile(CAPACITY / 'runtime-package' / name, OUT / name)
    shutil.copyfile(HERE / 'carryover_runtime.py', OUT / 'carryover_runtime.py')
    carry = OUT / 'carryover'; carry.mkdir()
    shutil.copytree(CHECKPOINT, carry / 'checkpoint')
    shutil.copyfile(collection / 'original/worker/judge/J01/raw-output.txt', carry / 'linked26-raw-output.txt')
    shutil.copyfile(collection / 'audit.json', carry / 'linked26-technical-audit.json')
    requirements = read(CHECKPOINT / 'requirements.json')
    events_path = EXPORTED / '4090/output/batch/runs/fullhistory23-T000-clean-noaux/attempt-1794221958077864899/events.jsonl'
    events = [json.loads(line) for line in events_path.read_bytes().splitlines()]
    supported = [row['data']['claims'] for row in events if row['kind'] == 'state_supported']
    assert supported and supported[-1] == {}
    ids = sorted({row['data']['body']['request_id'] for row in events if row['kind'].endswith('_request')
                  and isinstance(row['data'].get('body'), dict) and 'request_id' in row['data']['body']})
    assert len(ids) >= 45 and all(len(value) == 32 for value in ids)
    navigation = read(OLDROOT / 'operations/1794225780980751200-restore27-original-main-frame-navigation-history-readonly/stdout.txt')
    state = {key: requirements[key] for key in ['original_track', 'accepted_history_sha256',
        'pending_candidate_event_sha256', 'original_current_image_sha256']}
    state.update({'schema': 'source-bound-GUI23-original-budget-linked-continuation-v1',
        'original_actor_spent': 11, 'original_judge_spent': 34, 'original_auxiliary_spent': 0,
        'initial_transport_counts': {'actor': 11, 'judge': 34, 'evidence': 0},
        'next_new_actor_attempt': 12, 'next_new_judge_attempt': 35,
        'original_actions_executed': 10, 'first_pending_decision': 11,
        'controller_valid_state': supported[-1], 'disallowed_prior_request_ids': ids,
        'navigation_urls': navigation['original_navigation_urls'], 'scroll_xy': navigation['final_known_scroll_xy'],
        'last_pointer_pixels': [562 / 1000 * 1280, 678 / 1000 * 720],
        'original_private_trajectory': '/data/researcher/jev-defense-four-gpu-20261106/full-history-gui-development-20261109-23/batch/runs/fullhistory23-T000-clean-noaux/attempt-1794221958077864899/private_trajectory.pkl',
        'original_private_trajectory_sha256': 'd0fc3fa2a10ca30a64355acd7821d8d9aceb6bb20437c2d20c789add2331c274',
        'original_trace': '/data/researcher/jev-defense-four-gpu-20261106/full-history-gui-development-20261109-23/batch/runs/fullhistory23-T000-clean-noaux/attempt-1794221958077864899/browser_trace.zip',
        'original_trace_sha256': navigation['trace_sha256'],
        'native_source_SHA': {
            '/data/researcher/jev-defense-validation-20261103/runtime-stage-01/upstream/browser_env/envs.py': 'ee02264f38697944a580bd671987a79712d2f81f76d95ed76dade774ee00d84f',
            '/data/researcher/jev-defense-validation-20261103/runtime-stage-01/upstream/browser_env/processors.py': '577b515f907d29fd0a3a573f2287f179e840df1f4b938022b684a2dc663916ac',
            '/data/researcher/jev-defense-validation-20261103/runtime-stage-01/native/run_reddit_internvl_smoke.py': 'af825cdf46601f4b12efb8fe614f1eb1c924af750a7fbc85bc6a565119267cf7'},
        'all_original_candidates_count_once': True,
        'restoration_mismatch_must_stop_before_action': True,
        'original_track_interrupted_and_mixed_placement': True,
        'both_new_arms_identical_memory_schedule': True})
    save(carry / 'state.json', state)

    protocol = (OLD / 'protocol.py').read_text(encoding='utf8')
    protocol = one(protocol, 'def __init__(self, plan):', 'def __init__(self, plan, carryover):')
    protocol = one(protocol, 'self.ids = set();', "self.carryover = copy.deepcopy(carryover)\n        self.ids = set(carryover['disallowed_prior_request_ids']);")
    protocol = one(protocol, "self.active = item['run_id']; self.counts = {'actor':0,'judge':0,'evidence':0}",
        "self.active = item['run_id']\n            self.counts = copy.deepcopy(self.carryover['initial_transport_counts']) if self.index == 0 else {'actor':0,'judge':0,'evidence':0}")
    (OUT / 'protocol.py').write_text(protocol, encoding='utf8')
    transport = (OLD / 'gui_transport.py').read_text(encoding='utf8')
    transport = one(transport, "self.attempts={'actor':0,'judge':0,'evidence':0}",
        "carry=json.loads((Path(__file__).resolve().parent/'carryover/state.json').read_bytes())\n        self.attempts=copy.deepcopy(carry['initial_transport_counts']) if run_id==carry['original_track'] else {'actor':0,'judge':0,'evidence':0}")
    (OUT / 'gui_transport.py').write_text(transport, encoding='utf8')
    server = (OLD / 'gpu_server.py').read_text(encoding='utf8')
    server = one(server, 'budget=RunBudget(plan)', "budget=RunBudget(plan,json.loads((package/'carryover/state.json').read_bytes()))")
    server = one(server, "bounded_data=bounded_auxiliary.prepare(aux_processor,generation,root,package)",
        "bounded_data=bounded_auxiliary.prepare(aux_processor,generation,root,package)\n        from resident_schedule import ResidentSchedule\n        schedule=ResidentSchedule(runtime,root,journal,resource)")
    server = one(server, "if op=='evidence':\n                        raw_image", "if op=='evidence':\n                        schedule.to_auxiliary()\n                        raw_image")
    server = one(server, "envelope={'request_sha256'", "schedule.to_primary()\n                        envelope={'request_sha256'")
    server = server.replace('19138', '19139')
    (OUT / 'gpu_server.py').write_text(server, encoding='utf8')

    runner = (OLD / 'run_independent_gui.py').read_text(encoding='utf8')
    runner = one(runner, 'from complete_actor_history import CompleteAcceptedActorHistory',
        'from complete_actor_history import CompleteAcceptedActorHistory\nimport carryover_runtime as carryover')
    runner = one(runner, "for step in range(1,step_cap+1):", "package=Path(__file__).resolve().parent\n   linked=carryover.first_track(package,item['run_id'])\n   first_step=1\n   if linked:\n    recovered=carryover.hydrate_history(package,transcript,controller)\n    sequence=recovered['sequence'];previous=recovered['previous'];last_image=recovered['last_image'];execution_feedback=recovered['execution_feedback']\n    obs,info,trajectory=carryover.restore_native(package,env,png,attempt,log)\n    first_step=11;environment_actions=10\n   for step in range(first_step,step_cap+1):")
    runner = one(runner, 'result=controller.decide(initial,actor,parser,recapture)',
        "result=carryover.pending_decision(package,controller,initial,transcript,parser,log) if linked and step==11 else controller.decide(initial,actor,parser,recapture)")
    runner = one(runner, "result['auxiliary_calls']=actor_observer.calls", "result['technical_continuation_of_original23']=linked\n   result['original_prefix_actions_carried']=10 if linked else 0\n   result['original_prefix_actor_calls_carried']=11 if linked else 0\n   result['original_prefix_judge_calls_carried_including_OOM_and26']=34 if linked else 0\n   result['placement_and_infrastructure_disruption_requires_sensitivity_analysis']=linked\n   result['auxiliary_calls']=actor_observer.calls")
    (OUT / 'run_independent_gui.py').write_text(runner, encoding='utf8')
    launcher = (OLD / 'launch_gui_service_once.py').read_text(encoding='utf8')
    launcher = launcher.replace('full-history-gui-development-20261109-23', HERE.name)
    launcher = launcher.replace("'primary_physical_GPUs': [4, 5, 6]", "'primary_physical_GPUs': [4, 5, 6, 7]")
    (OUT / 'launch_gui_service_once.py').write_text(launcher, encoding='utf8')
    token = secrets.token_urlsafe(48).encode()
    with (OUT / 'private.token').open('xb') as stream:
        stream.write(token)
    environment = read(OLDROOT / 'environment-admission.json')
    assert environment['passed'] and environment['result']['status'] == 'passed'
    save(OUT / 'environment-preflight/receipt.json', environment['result'])
    save(OUT / 'admission.json', {'admit_new_GUI_development': True, 'formal_efficacy': False,
        'original_environment_preflight_reused_not_rerun': True,
        'new_live_original_state_identity_required_inside_GUI': True,
        'linked26_technical_audit_sha256': sha(collection / 'audit.json'),
        'all_original_call_step_recovery_caps_retained': True,
        'authorization': 'Existing sustained defense goal and authorized4-7; unfinished technical continuation plus original31unstarted tracks; no completed semantic controls rerun.'})
    for path in OUT.rglob('*.py'):
        compile(path.read_text(encoding='utf8'), str(path), 'exec')
    for name, expected in old_manifest['files'].items():
        if name.startswith('release/'):
            assert sha(OUT / name) == expected, name
    manifest = {key: copy.deepcopy(value) for key, value in old_manifest.items() if key not in ['files', 'worker_source_sha256', 'auth_token_sha256']}
    manifest.update({'schema': 'linked-original-budget-complete-history-GUI-memory-schedule-v1',
        'outputs': '/home/researcher/jev-defense-four-gpu-20261106/' + HERE.name,
        'GUI_output': '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name + '/batch',
        'model_url': 'http://192.0.2.11:19139', 'auth_token_sha256': hashlib.sha256(token).hexdigest(),
        'worker_source_sha256': sha(OUT / 'gpu_server.py'),
        'linked_original23_manifest_sha256': sha(OLD / 'manifest.json'),
        'linked26_capacity_manifest_sha256': sha(CAPACITY / 'runtime-package/manifest.json'),
        'linked26_capacity_audit_sha256': sha(collection / 'audit.json'),
        'carryover_state_sha256': sha(carry / 'state.json'),
        'previous_goal_turn_classification': 'no progress toward experimental outcome while answering prompt/output question; current29takes next safe unfinished-GUI action',
        'deployment_tradeoff': 'Same four-GPU18/18/15/13 BF16 SDPA main layout and idle-weight RAM schedule in both future arms. All forwards GPU only. Weight transfer time and all four reserved GPUs count. Device placement may change numerical outputs. First trajectory carries interrupted old placement and must be flagged, with technical/unknown sensitivity bounds. No efficacy claim.',
        'original_recovery_budgets': {'recaptures_per_decision': 2, 'regenerations_per_decision': 2, 'format_retry': 1},
        'restoration_capture_consumes_pending_recapture': 1,
        'files': {p.relative_to(OUT).as_posix(): sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name != 'private.token'}})
    save(OUT / 'manifest.json', manifest)
    save(HERE / 'preparation.json', {'time': time.time(), 'manifest_sha256': sha(OUT / 'manifest.json'),
        'files': len(manifest['files']), 'original32queue_and_order_unchanged': read(OUT / 'plan.json') == read(OLD / 'plan.json'),
        'original_release_unchanged': True, 'fresh_model_GUI_scorer_paid_calls': 0,
        'live_restore_unproven': True, 'launch_ready': False})
    print(json.dumps({'package': str(OUT), 'manifest_sha256': sha(OUT / 'manifest.json'),
        'files': len(manifest['files']), 'carried': state['initial_transport_counts'], 'new_experiment_calls': 0}))


if __name__ == '__main__':
    main()
