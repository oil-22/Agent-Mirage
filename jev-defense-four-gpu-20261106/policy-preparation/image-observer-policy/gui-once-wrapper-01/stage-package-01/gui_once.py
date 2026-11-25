"""Once-only outer execution and linked readiness preparation; no legacy queues.

The preparation command never calls a model/browser. The run command starts only
the source-sealed release04 runner, once, with the original four-run plan.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback
from types import SimpleNamespace
import urllib.request

PACKAGE_SHA = 'f16dcef1024320e38daa8412f2e774eb5d834b7aaa34e375a7d95e9a145a69ee'
POLICY_SEAL_SHA = '3257dae74775d13adff6d8856785159608cf6570130b078339887664e3193c61'
PLAN_SHA = 'a6e248f730408ab9c5bbaeb72bfa0d392ecf99f247159495273d2b3f5616ef8e'
CAPACITY_SHA = '5a89138010f8cf005cbcd03bc2a4b249af0e253178666388fb17652bb0571fb8'
CAPACITY_FIELDS = ('capacity_passed', 'full_input_preserved',
    'actual_input_forward_audited', 'output_budget_4096_preserved')
OWNERSHIP_FIELDS = ('actual_uid_full_command_verified', 'all_inherited_locks_held',
    'no_foreign_compute_on_leased_GPUs', 'transport_ready', 'outer_launcher_rechecks_fresh')
PYTHON = '/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python'
RUNTIME = '/data/researcher/jev-defense-validation-20261103/runtime-stage-01'
TASK = '/data/researcher/jev-defense-validation-20261103/task-restore-1793683370167273452/classifieds_112.PRIVATE.json'
TEMPLATE = '/data/researcher/jev-defense-validation-20261103/native-vwa-request.recovered.json'
TOKEN = '/data/researcher/jev-defense-four-gpu-20261106/transport-online-01/private.token'
PRIMARY_URL = 'http://127.0.0.1:28427'


def require(value, message):
    if not value: raise RuntimeError(message)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_bytes())


def write(path, value):
    with Path(path).open('x', encoding='utf8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.flush(); os.fsync(handle.fileno())


def bound(path, expected):
    path = Path(path)
    require(not path.is_symlink() and sha(path) == expected, 'Bound evidence changed: ' + str(path))
    return read(path)


def validate_package(package):
    package = Path(package).resolve()
    seal = bound(package / 'package-seal.json', PACKAGE_SHA)
    for name, expected in seal['files'].items():
        path = (package / name).resolve()
        require(path.is_relative_to(package), 'Package path escaped')
        require(not (package / name).is_symlink() and sha(path) == expected, 'Frozen package file changed: ' + name)
    require(sha(package / 'policy-source-seal.json') == POLICY_SEAL_SHA and
            sha(package / 'plan.json') == PLAN_SHA, 'Wrong release/plan')
    return seal


def ownership(value, now=None):
    require(all(value.get(k) is True for k in OWNERSHIP_FIELDS), 'Ownership/transport gate is incomplete')
    require(type(value.get('collected_time')) in (int, float), 'Ownership collection time missing')
    if now is not None:
        age = now - value['collected_time']
        require(0 <= age <= 120, 'Ownership evidence is not fresh within120seconds')
    cards = value.get('physical_gpu_uuids', {})
    require(set(str(k) for k in cards) == {'4', '5', '6', '7'} and len(set(cards.values())) == 4,
            'Ownership must bind exactly four physical GPUs4-7/UUIDs')
    pids = value.get('actual_allowed_pids')
    require(isinstance(pids, list) and len(pids) == 2 and len(set(pids)) == 2 and
            all(type(pid) is int and pid > 0 for pid in pids), 'Exactly two real model peers required')
    sources = value.get('source_evidence')
    require(isinstance(sources, list) and bool(sources), 'Actual ownership inspection source missing')
    for item in sources: bound(item['path'], item['sha256'])


def runner_args(package, linked, batch):
    return SimpleNamespace(root=Path(batch), plan=package/'plan.json', token_file=Path(TOKEN),
        runtime=Path(RUNTIME), native_task=Path(TASK), actor_template=Path(TEMPLATE),
        auxiliary_config=linked/'auxiliary-config.json', readiness=linked/'readiness.json',
        model_url=PRIMARY_URL)


def argv_for(package, linked, batch):
    a = runner_args(package, linked, batch)
    values = [PYTHON, '-u', str(package/'release/run_image_observer_vwa_validation.py')]
    for name in ('root', 'plan', 'token_file', 'runtime', 'native_task', 'actor_template',
                 'auxiliary_config', 'readiness', 'model_url'):
        values += ['--'+name.replace('_', '-'), str(getattr(a, name))]
    return values


def native_validate(package, args):
    sys.path.insert(0, str(package/'release'))
    from observer_launch_contract import validate_launch_inputs
    validate_launch_inputs(args)


def prepare(a):
    package = a.package.resolve(); output = a.output.resolve(); batch = a.batch_root.resolve()
    validate_package(package)
    require(not output.exists() and not batch.exists(), 'Linked evidence or experiment root already exists')
    cap = bound(a.capacity_evidence, a.capacity_sha256)
    require(a.capacity_sha256 == CAPACITY_SHA and all(cap.get(k) is True for k in CAPACITY_FIELDS),
            'Only the actual completed full-input capacity proof is allowed')
    owner = bound(a.ownership_evidence, a.ownership_sha256); ownership(owner, time.time())
    require(Path(TOKEN).is_file() and len(Path(TOKEN).read_bytes().strip()) >= 32,
            'Parent must create the independent private transport token first')
    output.mkdir(parents=True, exist_ok=False)
    try:
        ready = copy.deepcopy(read(package/'readiness.template.json'))
        require(ready['launch_ready'] is False and ready['deployment_applied'] is False, 'Template changed')
        ready['evidence']['primary_full_input_capacity'] = {'path': str(a.capacity_evidence.resolve()), 'sha256': a.capacity_sha256}
        ready['evidence']['ownership_transport'] = {'path': str(a.ownership_evidence.resolve()), 'sha256': a.ownership_sha256}
        ready.update(launch_ready=True, deployment_applied=True,
            unverified_required_evidence={}, parent_template={'path': str(package/'readiness.template.json'),
                'sha256': sha(package/'readiness.template.json')},
            linked_final_preparation_only=True, model_calls_during_finalization=0,
            formal_defense_efficacy_ready=False)
        config = read(package/'auxiliary-config.proposed.json')
        require(config['deployment_applied'] is False and config['token_file'] == TOKEN, 'Wrong proposed transport')
        config.update(deployment_applied=True, ownership_transport=ready['evidence']['ownership_transport'],
            parent_proposed_config_sha256=sha(package/'auxiliary-config.proposed.json'))
        write(output/'auxiliary-config.json', config); write(output/'readiness.json', ready)
        native_validate(package, runner_args(package, output, batch))
        spec = {'package': str(package), 'package_sha256': PACKAGE_SHA, 'batch_root': str(batch),
            'linked_root': str(output), 'runner_argv': argv_for(package, output, batch),
            'readiness_sha256': sha(output/'readiness.json'),
            'config_sha256': sha(output/'auxiliary-config.json'),
            'ownership_evidence': ready['evidence']['ownership_transport'],
            'capacity_evidence': ready['evidence']['primary_full_input_capacity'],
            'claim_file': str(package.parent/'image-observer-four-run-01.once-only.json'),
            'automatic_retries': False, 'legacy_queues_allowed': False,
            'wrapper_source_sha256': sha(Path(__file__)), 'prepared_time': time.time()}
        spec['transport_linked_correction'] = {'proposed_primary_url':'http://127.0.0.1:28422',
            'actual_primary_url':PRIMARY_URL,'reason':'New independent online bridge local port; original proposal preserved',
            'native_model_payload_or_experimental_condition_changed':False}
        write(output/'launch-spec.json', spec)
        write(output/'preparation.json', {'status': 'prepared', 'actual_original_gate_validated': True,
            'model_GUI_calls': 0, 'launch_spec_sha256': sha(output/'launch-spec.json'),
            'known_capacity_scope': '15720 input tokens/1102 natural EOS; not all future histories fit',
            'formal_defense_success_claim': False})
    except BaseException:
        write(output/'preparation-failure.json', {'traceback': traceback.format_exc(), 'model_GUI_calls': 0})
        raise
    finally:
        write(output/'seal.json', {p.name: sha(p) for p in output.iterdir() if p.is_file()})
    return {'linked_root': str(output), 'launch_spec_sha256': sha(output/'launch-spec.json'),
            'wrapper_source_sha256': sha(Path(__file__)), 'model_GUI_calls': 0}


def validate_health(primary, observer, owner, plan):
    expected = [q['run_id'] for q in plan['queue']]
    for value, role in ((primary, 'primary'), (observer, 'pplx_flash')):
        require(value.get('role') == role and value.get('stage') == 'online_ready' and
                value.get('phase') == 'ready_gui' and value.get('exclusive_task_group') is True,
                'Both actual owned models must be ready with full resource admission')
        require(sorted(value.get('actual_allowed_pids', [])) == sorted(owner['actual_allowed_pids']) and
                {str(k):v for k,v in value.get('physical_gpu_uuids', {}).items()} ==
                {str(k):v for k,v in owner['physical_gpu_uuids'].items()}, 'Fresh model resources differ from ownership proof')
        state = value.get('state', {})
        require(state.get('phase') == 'ready' and state.get('active') is None and
                state.get('next_run_index') == 0 and list(state.get('runs', {})) == expected,
                'An active/previous terminal service group cannot be reused')
        for run in state['runs'].values():
            require(run.get('status') == 'not_started' and run.get('last_decision_index') == 0 and
                    run.get('calls') == {'actor':0, 'judge':0, 'observe':0}, 'Model group already spent run budget')


def fetch_health(url):
    token = Path(TOKEN).read_text().strip()
    request = urllib.request.Request(url+'/health', headers={'Authorization': 'Bearer '+token})
    with urllib.request.urlopen(request, timeout=15) as response:
        require(response.status == 200, 'Model health HTTP failed')
        value = json.loads(response.read())
    # Never persist headers, token or arbitrary remote exception bodies.
    fields = ('role','stage','phase','state','exclusive_task_group','actual_allowed_pids','physical_gpu_uuids')
    return {key:value[key] for key in fields if key in value}


def identity(pid):
    root = Path('/proc')/str(pid)
    stat = (root/'stat').read_text().rsplit(')',1)[1].split()
    return {'pid':pid, 'uid':root.stat().st_uid, 'start_ticks':stat[19],
            'command':(root/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip()}


class ObserverFailureMonitor:
    """Incrementally inspect complete SHA-chain event lines, never private task files."""
    def __init__(self): self.states = {}

    def scan(self, batch):
        for path in sorted(Path(batch).glob('runs/*/attempt-*/events.jsonl')):
            offset, pending, seq, previous = self.states.get(path, (0,b'',0,'0'*64))
            require(path.stat().st_size >= offset, 'Running event journal was truncated')
            with path.open('rb') as handle: handle.seek(offset); fresh = handle.read()
            offset += len(fresh); lines = (pending+fresh).split(b'\n'); pending = lines.pop()
            for line in lines:
                event = json.loads(line); expected = event.pop('sha256')
                raw = json.dumps(event,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
                require(event.get('seq') == seq and event.get('previous') == previous and
                        hashlib.sha256(raw).hexdigest() == expected, 'Running event SHA chain changed')
                seq += 1; previous = expected
                if event.get('kind') == 'actor_observer_packet' and event['data'].get('status') in {
                        'technical_failure','preserved_failure_no_retry'}:
                    return {'event_path':str(path),'seq':event['seq'],'event_sha256':expected,
                        'status':event['data']['status'],'request_safe_decision_boundary_stop':True,
                        'no_automatic_retry':True,'error_text_not_a_semantic_label':True}
            self.states[path] = (offset,pending,seq,previous)
        return None


def terminal_summary(batch, plan):
    status = read(batch/'status.json') if (batch/'status.json').exists() else {}
    rows = []; any_gap = False
    for item in plan['queue']:
        run = batch/'runs'/item['run_id']; attempts = list(run.glob('attempt-*'))
        require(len(attempts) <= 1, 'Unexpected repeated run attempts')
        pointer = run/'complete.json'
        if pointer.exists():
            require(not any_gap and len(attempts) == 1, 'Four-run order has a gap or missing attempt')
            target = read(pointer); attempt = attempts[0]
            require(Path(target['attempt']).resolve() == attempt.resolve() and
                    target['sha256'] == sha(attempt/'complete.json'), 'Completion pointer identity differs')
            result = read(attempt/'complete.json')
            require(result['run'] == item and result['semantic_mirage'] is None,
                    'Terminal condition differs or semantic label substituted')
            require(result['actor_calls'] <= 70 and result['verifier_calls'] <= 140 and
                    result['auxiliary_calls'] <= (60 if item['observer_enabled'] else 0), 'Terminal caps exceeded')
            rows.append({'run_id':item['run_id'],'complete':True,'result':result})
        else:
            any_gap = True
            rows.append({'run_id':item['run_id'],'complete':False,
                'status':'attempted_not_complete' if attempts else 'not_attempted'})
    complete = status.get('phase') == 'completed' and status.get('completed') == 4 and all(r['complete'] for r in rows)
    observer_failures = sum(r.get('result',{}).get('observer_technical_failures',0) for r in rows)
    return {'all_four_complete':complete, 'phase':status.get('phase'), 'runs':rows,
            'semantic_Mirage_review_pending':True, 'service_wire_EOS_audit_pending':True,
            'observer_technical_failure_count':observer_failures,
            'all_four_without_reported_observer_technical_failure':complete and observer_failures == 0,
            'sealed04_missing_observer_packet_fallback_preserved':True,
            'defense_success_claim':False, 'no_automatic_retry':True}


def run(a):
    spec = bound(a.spec, a.spec_sha256); package = Path(spec['package']); linked = Path(spec['linked_root'])
    validate_package(package)
    require(sha(Path(__file__)) == spec['wrapper_source_sha256'], 'Wrapper source changed')
    require(sha(linked/'readiness.json') == spec['readiness_sha256'] and
            sha(linked/'auxiliary-config.json') == spec['config_sha256'], 'Linked gate/config changed')
    for name, expected in read(linked/'seal.json').items(): require(sha(linked/name) == expected, 'Linked finalization changed')
    batch = Path(spec['batch_root']); control = a.control_root.resolve()
    require(spec['runner_argv'] == argv_for(package, linked, batch) and
            spec['claim_file'] == str(package.parent/'image-observer-four-run-01.once-only.json') and
            spec['automatic_retries'] is False and spec['legacy_queues_allowed'] is False,
            'Only sealed04 exact once-only CLI is allowed')
    require(not batch.exists() and not control.exists(), 'Experiment/control root already exists')
    owner = bound(**{'path':spec['ownership_evidence']['path'], 'expected':spec['ownership_evidence']['sha256']})
    ownership(owner, time.time()); native_validate(package, runner_args(package, linked, batch))
    primary = fetch_health(PRIMARY_URL); observer = fetch_health('http://127.0.0.1:28423')
    validate_health(primary, observer, owner, read(package/'plan.json'))
    # Persistent O_EXCL claim is intentionally retained on technical failure.
    write(Path(spec['claim_file']), {'spec_sha256':a.spec_sha256, 'batch_root':str(batch),
        'control_root':str(control), 'time':time.time(), 'no_automatic_retry':True})
    control.mkdir(parents=True, exist_ok=False)
    process = None; code = None
    try:
        write(control/'fresh-health.json', {'time':time.time(),'primary':primary,'observer':observer,
            'ownership_receipt_sha256':spec['ownership_evidence']['sha256'],'new_model_calls':0})
        write(control/'wrapper-process.json', identity(os.getpid()))
        write(control/'exact-command.json', {'argv':spec['runner_argv'],'spec_sha256':a.spec_sha256})
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE':'1'}
        monitor = ObserverFailureMonitor(); stop_sent = False
        with (control/'runner.log').open('xb') as handle:
            process = subprocess.Popen(spec['runner_argv'], stdout=handle, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, cwd=str(package), env=env, start_new_session=True)
            child_identity = identity(process.pid); write(control/'runner-process.json', child_identity)
            while process.poll() is None:
                if not stop_sent:
                    try: failure = monitor.scan(batch)
                    except Exception:
                        failure = {'event_chain_monitor_error':traceback.format_exc(),
                            'request_safe_decision_boundary_stop':True,'no_automatic_retry':True}
                    if failure is not None:
                        write(control/'safe-boundary-stop-request.json',failure)
                        if process.poll() is None:
                            require(identity(process.pid) == child_identity, 'Child process identity changed; refuse signal')
                            try: os.kill(process.pid,signal.SIGUSR1)
                            except ProcessLookupError: require(process.poll() is not None,'Child disappeared without exit')
                        stop_sent = True
                time.sleep(0.5)
            code = process.wait()
        result = terminal_summary(batch, read(package/'plan.json'))
        result.update(exit_code=code, execution_completed=code == 0 and
            result['all_four_without_reported_observer_technical_failure'])
        write(control/'finalization.json', result)
    except BaseException:
        # Never restart, terminate foreign jobs or touch preserved failed terminals.
        write(control/'wrapper-failure.json', {'traceback':traceback.format_exc(), 'exit_code':code,
            'child_may_still_be_running':process is not None and process.poll() is None,
            'no_automatic_retry':True,'semantic_mirage':None})
        raise
    finally:
        if process is None or process.poll() is not None:
            if batch.exists():
                write(control/'batch-postexit-sha256.json', {p.relative_to(batch).as_posix():sha(p)
                    for p in batch.rglob('*') if p.is_file()})
            write(control/'postexit-sha256.json', {p.relative_to(control).as_posix():sha(p)
                for p in control.rglob('*') if p.is_file()})
    return {'control_root':str(control),'exit_code':code,'execution_completed':result['execution_completed'],
            'service_wire_EOS_and_semantic_audits_pending':True,'automatic_retry':False}


def flat_manifest(root, manifest, expected):
    root = Path(root).resolve(); values = bound(manifest,expected)
    require(bool(values) and isinstance(values,dict),'Empty postexit manifest')
    for name, digest in values.items():
        target = (root/name).resolve(); require(target.is_relative_to(root),'Manifest escaped root')
        require(sha(target) == digest,'Postexit terminal file changed: '+name)
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*')
        if p.is_file() and p.resolve() != Path(manifest).resolve()}
    require(actual == set(values),'Terminal manifest omits/adds files')
    return values


def audit_spec(a):
    """Prepare actual terminal auditor input after service shutdown/copy; no calls."""
    spec = bound(a.launch_spec,a.launch_spec_sha256)
    package = Path(spec['package']); validate_package(package)
    control = a.control_root.resolve(); batch = Path(spec['batch_root'])
    manifest = control/'batch-postexit-sha256.json'
    require((control/'postexit-sha256.json').exists(),'GUI outer process lacks its postexit seal')
    flat_manifest(control,control/'postexit-sha256.json',sha(control/'postexit-sha256.json'))
    flat_manifest(batch,manifest,sha(manifest))
    service = a.service_root.resolve(); sm = service/'terminal-sha256.json'
    flat_manifest(service,sm,a.service_manifest_sha256)
    admission = service/'online-admission.json'; requests = []
    for role in ('primary','pplx_flash'):
        for request in sorted((service/role/'requests').iterdir()):
            if request.is_dir(): requests.append({'path':str(request),'seal_sha256':sha(request/'seal.json'),'role':role})
    for request in sorted((service/'transitions').iterdir()):
        if request.is_dir(): requests.append({'path':str(request),'seal_sha256':sha(request/'seal.json'),'role':'primary'})
    obj = {'batch_root':str(batch), 'plan':{'path':str(package/'plan.json'),'sha256':PLAN_SHA},
        'policy_source_seal':{'path':str(package/'policy-source-seal.json'),'sha256':POLICY_SEAL_SHA},
        'release_root':str(package/'release'),
        'runtime_admission':{'path':str(admission),'sha256':sha(admission)},
        'terminal_manifests':[{'root':str(batch),'path':str(manifest),'sha256':sha(manifest),'exhaustive':True},
            {'root':str(service),'path':str(sm),'sha256':a.service_manifest_sha256,'exhaustive':True}],
        'service_requests':requests, 'service_journals':[{'path':str(service/'journal.jsonl'),
            'sha256':sha(service/'journal.jsonl')}]}
    a.output.mkdir(parents=True,exist_ok=False); write(a.output/'audit-spec.json',obj)
    write(a.output/'receipt.json',{'audit_spec_prepared':True,'actual_integrity_audit_not_yet_run':True,
        'service_actual_request_directories':len(requests),'model_GUI_calls':0,
        'service_terminal_manifest_sha256':a.service_manifest_sha256,
        'launch_spec_sha256':a.launch_spec_sha256,'semantic_labels_inferred':False})
    write(a.output/'seal.json',{p.name:sha(p) for p in a.output.iterdir() if p.is_file()})
    return {'spec':str(a.output/'audit-spec.json'),'audit_spec_sha256':sha(a.output/'audit-spec.json'),
        'actual_audit_still_required':True,'model_GUI_calls':0}


def main():
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest='mode', required=True)
    prep = sub.add_parser('prepare')
    for name in ('package','capacity-evidence','ownership-evidence','output','batch-root'):
        prep.add_argument('--'+name, type=Path, required=True)
    for name in ('capacity-sha256','ownership-sha256'): prep.add_argument('--'+name, required=True)
    execute = sub.add_parser('run')
    execute.add_argument('--spec', type=Path, required=True); execute.add_argument('--spec-sha256', required=True)
    execute.add_argument('--control-root', type=Path, required=True)
    audit = sub.add_parser('audit-spec')
    for name in ('launch-spec','control-root','service-root','output'):
        audit.add_argument('--'+name,type=Path,required=True)
    audit.add_argument('--launch-spec-sha256',required=True); audit.add_argument('--service-manifest-sha256',required=True)
    args = parser.parse_args()
    result = {'prepare':prepare,'run':run,'audit-spec':audit_spec}[args.mode](args)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__': main()
