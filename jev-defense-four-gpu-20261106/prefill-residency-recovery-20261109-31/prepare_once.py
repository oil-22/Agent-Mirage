"""Freeze one original-budget linked prefill repair; never load or invoke models."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OLD = BASE / 'memory-scheduled-full-history-gui-20261109-29/runtime-package-linked02'
FAILED = BASE.parent / 'j29evidence/1794228241952080200/3090/output/worker/requests/0021'
PRESERVATION = BASE / 'memory-scheduled-full-history-gui-20261109-29/failure-preservation-1794228241952080200/receipt.json'
OUT = HERE / 'runtime-package'
sha = lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, v):
    with p.open('x', encoding='utf8') as stream:
        json.dump(v, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    assert not OUT.exists()
    assert sha(PRESERVATION) == '6b6881fb9c650dd9d689438d4534d8698c347b09158c1619166817e3841409a8'
    original = json.loads((OLD / 'manifest.json').read_bytes())
    assert sha(OLD / 'manifest.json') == 'bced549e679b03e286e2663a34f17b2319b2b35f0ef09397a8f39404073ee8a0'
    for name, expected in original['files'].items():
        assert sha(OLD / name) == expected, name
    OUT.mkdir()
    for name in original['files']:
        if name.startswith('carryover/') or name in ['gpu_server.py','launch_gui_service_once.py','private.token']:
            continue
        destination = OUT / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OLD / name, destination)
    shutil.copyfile(HERE / 'prefill_residency.py', OUT / 'prefill_residency.py')
    worker = (BASE / 'memory-scheduled-capacity-20261109-26/capacity_worker.py').read_text(encoding='utf8')
    start = worker.index('        # Exercise actual full-weight transfer only.')
    end = worker.index("        original = package / 'original0044'", start)
    worker = worker[:start] + '        prefill = PrefillResidency(runtime, scheduler, root, journal, resource)\n' + worker[end:]
    worker = worker.replace('from resident_schedule import ResidentSchedule',
                            'from resident_schedule import ResidentSchedule\nfrom prefill_residency import PrefillResidency')
    worker = worker.replace('GUI23', 'GUI29').replace('original0044','original0021')
    worker = worker.replace("'original_judge_attempts_spent': 33", "'original_judge_attempts_spent': 49")
    worker = worker.replace("'total_linked_judge_attempts_spent': 33 + attempted", "'total_linked_judge_attempts_spent': 49 + attempted")
    worker = worker.replace('len(view.images) == 11', 'len(view.images) == 17').replace('[1, 22596]', '[1, 32184]')
    worker = worker.replace("'complete_images': 11, 'complete_tokens': 22596", "'complete_images': 17, 'complete_tokens': 32184")
    worker = worker.replace("'prior_judge_attempts_spent': 33, 'this_attempt_index': 34", "'prior_judge_attempts_spent': 49, 'this_attempt_index': 50")
    worker = worker.replace("'original_judge_spent': 33, 'linked_judge_spent': 34", "'original_judge_spent': 49, 'linked_judge_spent': 50")
    worker = worker.replace("'original_actor_spent': 11", "'original_actor_spent': 17")
    worker = worker.replace("'original_executed_actions': 10", "'original_executed_actions': 16")
    assert '22596' not in worker and 'original0044' not in worker
    (OUT / 'capacity_worker.py').write_bytes(worker.encode('utf8'))
    launch = (BASE / 'memory-scheduled-capacity-20261109-26/runtime-package/launch_capacity_once.py').read_bytes()
    launch = launch.replace(b'memory-scheduled-capacity-20261109-26', HERE.name.encode())
    (OUT / 'launch_capacity_once.py').write_bytes(launch)
    bindings = json.loads((FAILED / 'seal.json').read_bytes())
    target = OUT / 'original0021'
    target.mkdir()
    for name in ['payload.json','prepared.json','first-forward.json','effective-generation.json',
                 'failure.json','forward-count.json','generated-token-progress.jsonl','external-wire.json','seal.json']:
        if name != 'seal.json':
            assert sha(FAILED / name) == bindings[name], name
        shutil.copyfile(FAILED / name, target / name)
    assert (target / 'generated-token-progress.jsonl').stat().st_size == 0
    payload = json.loads((target / 'payload.json').read_bytes())
    prepared = json.loads((target / 'prepared.json').read_bytes())
    assert payload['operation'] == 'judge' and len(payload['view']['images']) == 17
    assert prepared['input_ids']['shape'] == [1,32184]
    for p in OUT.rglob('*.py'):
        compile(p.read_bytes(), str(p), 'exec')
    assert sha(OUT / 'model_runtime.py') == sha(OLD / 'model_runtime.py')
    limits = {'auxiliary':0,'judge':1,'actor':0,'GUI':0,'scorer':0,'paid_API':0,'format_retries':0}
    manifest = {
        'schema':'GUI29-exact-original-budget-prefill-idle-weight-scheduling-v1',
        'authorized_finite_joint_development':True, 'expected_holder':original['expected_holder'],
        'lease_sha256':original['lease_sha256'], 'limits':limits,
        'original_manifest_sha256':sha(OLD / 'manifest.json'),
        'failure_preservation_receipt_sha256':sha(PRESERVATION),
        'original_track':'fullhistory23-T000-clean-noaux','original_failed_request':'0021',
        'original_budget':{'actor_spent':17,'actor_cap':70,'judge_spent':49,'judge_cap':140,
                           'pending_actor_candidate_index':17,'actions_executed':16,'step_cap':50},
        'one_linked_judge_attempt_index':50,'remaining_judge_after_attempt':90,
        'original_failed_full_input_tokens':32184,'original_complete_images':17,
        'original_input_ids_sha256':prepared['input_ids']['sha256'],
        'original_payload_sha256':sha(FAILED / 'payload.json'),
        'authorized_physical_GPUs':[4,5,6,7],'CPU_inference_allowed':False,
        'idle_weight_RAM_staging':True,'primary_layer_counts':[18,18,15,13],
        'same_native_execution_device_map':True,'native_model_runtime_source_unchanged':True,
        'auxiliary_model':'Qwen/Qwen3.5-9B','decision_adapter_loaded':False,
        'exact_tradeoff':'During the complete native prefill, idle groups are stored in RAM and '
                         'each original group runs on exactly its original GPU, BF16 and SDPA. '
                         'All weights return to their original GPUs before native token decoding. '
                         'No input/cache/output/algorithm/validator/budget edit. Transfers and four '
                         'reserved GPUs count as cost. Numerical invariance, future capacity and '
                         'GUI recovery/effect are not established by preparation.',
        'no_completed_call_or_GUI_action_reexecution':True,
        'files':{p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()},
    }
    save(OUT / 'manifest.json', manifest)
    save(HERE / 'preparation.json', {'manifest_sha256':sha(OUT / 'manifest.json'), 'time':time.time(),
        'limits':limits, 'source_request_bound':True, 'all_release_and_native_generation_unchanged':True,
        'new_model_GUI_scorer_calls':0,'launch_ready':False})
    print(json.dumps({'manifest_sha256':sha(OUT / 'manifest.json'),'files':len(manifest['files']),
                      'limits':limits,'linked_original_judge_index':50,'new_experiment_calls':0}))


if __name__ == '__main__':
    main()
