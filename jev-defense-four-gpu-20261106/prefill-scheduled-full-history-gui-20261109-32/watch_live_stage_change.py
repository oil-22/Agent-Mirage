"""Bounded read-only watch of the same actual worker; never restarts a job."""
import argparse
import json
from pathlib import Path
import time

from orchestrate import HERE, OUTPUT, COMMON, remote, save, sha


def main(seconds, previous_authority):
    assert 1 <= seconds <= 3600
    previous = HERE / previous_authority
    assert previous.parent == HERE and previous.is_file()
    root = HERE / ('live-stage-watch-' + str(time.time_ns()))
    root.mkdir()
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(root / 'intent.json', dict(time=time.time(), previous_goal_turn_classification='progress',
        previous_turn_evidence=previous_authority, previous_turn_evidence_sha256=sha(previous),
        expected_original_active_run='fullhistory23-T000-clean-noaux', actor_count=38,
        read_only=True, inference_GUI_scorer_calls=0, no_restart_or_model_retry=True))
    started, observations, failures = time.monotonic(), [], []
    while True:
        code = 'ROOT=' + repr(OUTPUT) + '\n' + COMMON + r'''
r=Path(ROOT);record=json.loads((r/'worker/process.json').read_bytes());actual=identity(record['pid'])
live=not actual.get('absent')and actual['state']not in ['Z','X']
matches=live and all(str(actual[k])==str(record[k])for k in ['pid','uid','command','start_ticks'])
state=json.loads((r/'worker/status.json').read_bytes())
terminal={}
for path in [r/'worker/terminal.json',r/'exit.json',r/'terminal-manifest.json']:
 if path.exists():terminal[str(path)]= {'sha256':sha(path),'value':json.loads(path.read_bytes())}
print(json.dumps({'time':time.time(),'actual':actual,'record':record,'same_verified_live_worker':matches,
 'state':state,'terminal':terminal,'no_new_model_GUI_scorer_calls':True}))
'''
        index = len(observations) + len(failures)
        try:
            output, operation = remote('3090', code, 'read-only-same-live-stage-watch-' + root.name + '-' + str(index), timeout=55)
            value = json.loads(output)
            save(root / ('observation-' + str(index).zfill(3) + '.json'), dict(observation=value, operation=str(operation)))
            observations.append(value)
            state = value['state']
            changed = (not value['same_verified_live_worker'] or bool(value['terminal'])
                       or state.get('active') != 'fullhistory23-T000-clean-noaux'
                       or state.get('counts', {}).get('actor') != 38
                       or state.get('phase') in ['technical_failure','terminal_failure','stopped','completed'])
            if changed:
                outcome = 'observed_stage_or_handle_change_requires_full_inspection'
                break
            if time.monotonic() - started >= seconds:
                outcome = 'verified_wait_timeout_same_actual_worker_alive_not_terminal'
                break
            if len(observations) == 1 or len(observations) % 4 == 0:
                print(json.dumps(dict(watch=str(root), actual_pid=value['actual']['pid'],
                    phase=state.get('phase'), request=state.get('request'), counts=state.get('counts'),
                    no_new_model_GUI_calls=True)), flush=True)
        except BaseException as error:
            failure = dict(time=time.time(), error_type=type(error).__name__, error=str(error),
                           observation_failure_not_model_terminal=True, no_restart_performed=True)
            save(root / ('observation-failure-' + str(index).zfill(3) + '.json'), failure)
            failures.append(failure)
            print(json.dumps(dict(watch=str(root), observation_error=failure)), flush=True)
            # A failed observation never proves the model stopped. Three
            # consecutive observation errors return for independent inspection.
            if len(failures) >= 3 and not (root / ('observation-' + str(index - 1).zfill(3) + '.json')).exists() and not (
                    root / ('observation-' + str(index - 2).zfill(3) + '.json')).exists():
                outcome = 'observation_errors_require_independent_repoll_not_restart'
                break
        time.sleep(min(50, max(1, seconds - (time.monotonic() - started))))
    receipt = dict(time=time.time(), outcome=outcome, observations=len(observations), observation_errors=len(failures),
        last_actual_observation=observations[-1] if observations else None,
        current_goal_turn_classification='verified wait' if outcome.startswith('verified_wait') else 'new observation requires follow-up',
        runtime_modified=False, original_files_deleted_moved_compressed=False,
        new_model_GUI_scorer_paid_calls=0, semantic_correctness_or_defense_efficacy_established=False)
    save(root / 'receipt.json', receipt)
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    result = dict(root=str(root), outcome=outcome, receipt_sha256=sha(root/'receipt.json'), seal_sha256=sha(root/'seal.json'))
    save(HERE / ('live-stage-watch-created-' + root.name.split('-')[-1] + '.json'), result)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=1800)
    p.add_argument('--previous-authority',default='matched-analysis-preparation-publication-created.json')
    args=p.parse_args()
    main(args.seconds,args.previous_authority)
