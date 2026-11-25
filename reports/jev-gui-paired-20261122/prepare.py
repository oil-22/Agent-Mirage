"""Freeze the independent study; the older preparation is read-only provenance."""
import ast
import hashlib
import json
import secrets
import time
from pathlib import Path
from urllib.parse import urlsplit

from paired_contract import SAMPLE_COUNT, STUDY, queue_for

HERE = Path(__file__).resolve().parent
OLD_ROOT = HERE.parents[1] / 'jev-defense-four-gpu-20261106'
OLD = OLD_ROOT / 'flash-four-mode-scale10-20261117-linked13'
SELECTION = OLD_ROOT / 'flash-four-mode-scale10-20261116-12'
SOURCE_SHA = '151c5bab54d631d9d8da2af898e270ee53d0f62dde5caf7c587d0f8647e400b8'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def edit(path, substitutions):
    source = path.read_bytes().decode('utf-8').replace('\r\n', '\n')
    for before, after in substitutions:
        assert source.count(before) == 1, (path, before)
        source = source.replace(before, after, 1)
    ast.parse(source)
    path.write_bytes(source.encode('utf-8'))


def unwrap(pointer, target):
    ptr = read(pointer)
    root = Path(ptr['root'])
    assert sha(root / 'seal.json') == ptr['seal_sha256']
    seal = read(root / 'seal.json')
    assert sha(root / target) == seal[target]
    return read(root / target), seal[target]


def main():
    assert not (HERE / 'frozen-current.json').exists(), 'No replacement cohort after freezing'
    parent = Path(read(OLD / 'preparation-current.json')['package'])
    assert sha(parent / 'manifest.json') == SOURCE_SHA
    source = read(parent / 'manifest.json')
    assert all(sha(parent / name) == h for name, h in source['files'].items())
    old_plan = read(parent / 'plan.json')
    catalog, catalog_record_hash = unwrap(SELECTION / 'task-selection-current.json', 'structural-bindings.json')
    selection, selection_hash = unwrap(SELECTION / 'task-selection-current.json', 'selection.json')
    catalog = catalog['result']
    all_rows = {row['task_id']: row for row in catalog['rows']}

    def eligible(task):
        row = all_rows[task]
        url = urlsplit(row['start_url'])
        return (row['eligible'] and row['require_reset'] is False and row['image'] is None
                and row['eval_types'] == ['url_match'] and row['sites'] == ['classifieds']
                and ' |AND| ' not in row['start_url'] and url.netloc == '192.0.2.10:19980')

    holdout = [i for i in selection['reserve_task_ids'] if eligible(i)]
    never_started = [i for i in sorted(all_rows) if eligible(i) and
                     sum(x['task_id'] == i for x in old_plan['queue']) == 5]
    ids = holdout + never_started[:SAMPLE_COUNT-len(holdout)]
    queue = queue_for(ids)
    assert set(row['run_id'] for row in queue).isdisjoint(row['run_id'] for row in old_plan['queue'])
    case = 'paper-paired-20261122-' + str(time.time_ns())
    root = HERE / case
    package = root / 'runtime'
    package.mkdir(parents=True, exist_ok=False)
    inherited = ['active-Flash-contract-binding.json', 'active-Flash-quality-readiness.json',
                 'actor-template.json', 'capacity_gate.py', 'capture_client.py', 'capture_source.py',
                 'evidence_store.py', 'expanded_guard.py', 'explicit-placement.json', 'four_gpu_contract.py',
                 'gui_experiment.py', 'gui_outer.py', 'historical_memory.py', 'injection.py', 'launch_group.py',
                 'memory_lifetime.py', 'mlp_lifetime.py', 'native_environment.py', 'native_fault.py',
                 'native_rpc.py', 'native-parser-source.py', 'native-sources.json', 'parent-capacity.json',
                 'preflight_support.py', 'primary_server.py', 'primary-reference.json', 'receipt_protocol.py',
                 'reference-original-Flash-contract.json', 'torch_chunk_lifetime.py']
    inherited.extend(name for name in source['files'] if name.startswith(('flash/', 'release/')))
    for name in inherited:
        dest = package / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((parent / name).read_bytes())
    (package / 'historical_admission.py').write_bytes((parent / 'continuation_guard.py').read_bytes())
    for name in ('continuation_guard.py', 'paired_contract.py', 'PROTOCOL.md'):
        (package / name).write_bytes((HERE / name).read_bytes())
    (package / 'private.token').write_bytes(secrets.token_hex(32).encode('ascii'))
    destinations = {
        'package3090': f'/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/{case}',
        'package4090': f'/data/researcher/jev-defense-four-gpu-20261106/{case}/runtime',
        'output3090': f'/data/researcher/jev-defense-four-gpu-20261106/{case}/model-attempt-01',
    }

    edit(package / 'gui_experiment.py', [
        ('"""29 unstarted linked native GUI trajectories, original full main history, one Flash."""',
         '"""Fixed full-GUI paired cohort; only the screenshot gate differs across arms."""'),
        ('import base64,copy,json,os,pickle,signal,sys,time,traceback,uuid',
         'import base64,copy,json,os,pickle,shutil,signal,sys,time,traceback,uuid'),
        ('from capture_client import CaptureClient', 'from capture_client import CaptureClient\nfrom paired_contract import load_plan,missing_image_request'),
        ("        folder=self.root/'capture-deliveries';folder.mkdir(exist_ok=True)",
         "        if shutil.disk_usage(self.root).free < 16 * 1024**3:raise RuntimeError('GUI evidence disk reserve reached')\n        folder=self.root/'capture-deliveries';folder.mkdir(exist_ok=True)"),
        ('self.main.text_blocks=blocks;return self.main(frame)',
         "self.main.text_blocks=blocks\n        self.log.emit('actor_submit_timing',{'step':self.step,'capture_id':frame.capture_id,'image_sha256':frame.sha256,'submit_monotonic_ns':time.monotonic_ns(),'current_image_present':frame.png is not None})\n        return missing_image_request(self.main,frame)"),
        ("plan=json.loads((P/'plan.json').read_bytes());tasks=", '_,plan=load_plan(P);tasks='),
        ("        transport.request('/begin',{'run_id':item['run_id']})\n        try:\n            env=CaptureClient(attempt)",
         "        began=False;run_started_ns=time.monotonic_ns()\n        try:\n            transport.request('/begin',{'run_id':item['run_id']});began=True\n            env=CaptureClient(attempt)"),
        ("                result=controller.step(adapter.initial_frame(),adapter.capture,adapter.actor,adapter.parse,adapter.execute,cancelled=cancelled)",
         "                started_ns=time.monotonic_ns();initial=adapter.initial_frame()\n                log.emit('observation_started_timing',{'step':step,'initial_capture_id':initial.capture_id,'started_monotonic_ns':started_ns,'initial_ready_monotonic_ns':time.monotonic_ns()})\n                result=controller.step(initial,adapter.capture,adapter.actor,adapter.parse,adapter.execute,cancelled=cancelled)\n                log.emit('observation_finished_timing',{'step':step,'ended_monotonic_ns':time.monotonic_ns(),'status':result['status']})"),
        ("                finally:env.close()", "                try:env.close()\n                except Exception:cleanup_error=(cleanup_error or '')+'\\n'+traceback.format_exc();infrastructure=True"),
        ("            terminal['cleanup_error']=cleanup_error;terminal['infrastructure_failure']=infrastructure",
         "            terminal['cleanup_error']=cleanup_error;terminal['infrastructure_failure']=infrastructure\n            terminal['elapsed_monotonic_ns']=time.monotonic_ns()-run_started_ns"),
        ("            try:transport.request('/end',{'run_id':item['run_id'],'terminal_sha256':sha(attempt/'terminal.json'),'infrastructure_failure':infrastructure})",
         "            try:\n                if began:transport.request('/end',{'run_id':item['run_id'],'terminal_sha256':sha(attempt/'terminal.json'),'infrastructure_failure':infrastructure,'manual_stop':outcome=='manually_stopped'})"),
    ])

    edit(package / 'primary_server.py', [
        ('json,os,signal,sys,threading', 'json,os,shutil,signal,sys,threading'),
        ('from wire_contract import decode_request', 'from wire_contract import decode_request\nfrom paired_contract import load_plan'),
        ("token=(P/'private.token').read_text().strip();journal=Journal(root/'journal');plan=json.loads((P/'plan.json').read_bytes());queue=[r['run_id']for r in plan['queue']]",
         "token=(P/'private.token').read_text().strip();journal=Journal(root/'journal');_,plan=load_plan(P);queue=[r['run_id']for r in plan['queue']];gate_enabled={r['run_id']:r['gate_enabled']for r in plan['queue']}"),
        ("                        if self.path=='/gate':\n                            request,png=decode_request(raw)\n                            if active is None:raise ValueError('No active GUI run')",
         "                        if self.path=='/abort':\n                            assert body=={'reason':'paired_GUI_controller_stopped'}\n                            journal.emit('GUI_abort',{'active':active,'no_automatic_retry':True});state('stopped');stop.set()\n                            return self.send(200,{'accepted':True})\n                        if self.path=='/gate':\n                            request,png=decode_request(raw)\n                            if active is None or not gate_enabled[active]:raise ValueError('No gate requests in the control arm')\n                            if shutil.disk_usage(root).free < 16 * 1024**3:raise RuntimeError('Flash evidence disk reserve reached')"),
        ("assert set(body)=={'run_id','terminal_sha256','infrastructure_failure'}and body['run_id']==active",
         "assert set(body)=={'run_id','terminal_sha256','infrastructure_failure','manual_stop'}and body['run_id']==active\n                            assert type(body['infrastructure_failure'])is bool and type(body['manual_stop'])is bool"),
        ("                            if body['infrastructure_failure']:stop.set()\n                            state('completed'if index==len(queue)else'stopped'if body['infrastructure_failure']else'ready_next')",
         "                            interrupted=body['infrastructure_failure'] or body['manual_stop']\n                            if interrupted:stop.set()\n                            state('stopped'if interrupted else'completed'if index==len(queue)else'ready_next')"),
        ("        while not stop.is_set():server.handle_request()\n        terminal_status='completed'if index==len(queue)else'stopped'",
         "        startup_deadline=time.monotonic()+1800\n        while not stop.is_set():\n            server.handle_request()\n            if index==0 and active is None and time.monotonic()>startup_deadline:\n                journal.emit('GUI_startup_window_expired',{'new_attempt_relaunch':False});state('stopped');stop.set()\n        terminal_status='completed'if index==len(queue)and json.loads((root/'status.json').read_bytes())['phase']=='completed'else'stopped'"),
    ])

    edit(package / 'gui_outer.py', [
        ('import fcntl,json,os,subprocess,sys,time,traceback', 'import fcntl,json,os,subprocess,sys,time,traceback,urllib.request'),
        ("  save(control/'exit.json',{'child_exit':None if child is None else code,'time':time.time(),'no_automatic_retry':True})",
         "  batch_status=json.loads((P/'batch/status.json').read_bytes()) if (P/'batch/status.json').exists() else {}\n  if batch_status.get('phase')!='completed':\n   try:\n    req=urllib.request.Request(m['main_url']+'/abort',data=b'{\"reason\":\"paired_GUI_controller_stopped\"}',headers={'Authorization':'Bearer '+(P/'private.token').read_text().strip(),'Content-Type':'application/json'})\n    with urllib.request.urlopen(req,timeout=20)as response:save(control/'model-abort-response.json',json.load(response))\n   except Exception:save(control/'model-abort-unavailable.json',{'error':traceback.format_exc()})\n  save(control/'exit.json',{'child_exit':None if child is None else code,'time':time.time(),'no_automatic_retry':True})"),
    ])
    edit(package / 'launch_group.py', [('jev-flash-four-mode-scale10-20261117-linked13.lock', case + '.lock')])

    task_rows = [all_rows[i] for i in ids]
    plan = {'version': STUDY, 'tasks': task_rows, 'queue': queue,
            'cohort_note': {'first_six_previous_reserve': holdout, 'old_not_started_only': ids[len(holdout):],
                            'selected_without_outcomes_or_private_references': True,
                            'structural_catalog_record_sha256': catalog_record_hash,
                            'historical_selection_record_sha256': selection_hash},
            'actor_budget': {'max_steps': 50, 'max_calls': 70, 'max_new_tokens': 2048, 'seed': 42},
            'browser_seed': 20261011, 'native_full_history': True, 'gate_recapture_wait_seconds': 0.5,
            'gate_manual_or_yes_only': True, 'old_paused_queue_resumed': False,
            'analysis_checkpoints_seconds_do_not_change_gate': [30, 120]}
    save(package / 'plan.json', plan)
    save(package / 'native-bindings-public.json', {'tasks': task_rows, 'plan_sha256': sha(package / 'plan.json')})
    files = {p.relative_to(package).as_posix(): sha(p) for p in sorted(package.rglob('*'))
             if p.is_file() and p.name != 'private.token'}
    for name in files:
        if name.endswith('.py'):
            ast.parse((package / name).read_bytes(), filename=name)
    for name in inherited:
        if name not in {'gui_experiment.py', 'gui_outer.py', 'primary_server.py', 'launch_group.py'}:
            assert files[name] == source['files'][name], name
    manifest = {'study': STUDY, 'trajectories': len(queue), 'plan_sha256': sha(package / 'plan.json'),
                'auth_token_sha256': sha(package / 'private.token'), 'main_url': source['main_url'], **destinations,
                'historical_manifest_sha256': SOURCE_SHA, 'historical_package3090': source['package3090'],
                'historical_package4090': source['package4090'], 'historical_output3090': source['output3090'],
                'files': files}
    save(package / 'manifest.json', manifest)
    frozen = {'root': str(root), 'runtime': str(package), 'manifest_sha256': sha(package / 'manifest.json'),
              'plan_sha256': manifest['plan_sha256'], 'tasks': ids, 'trajectories': len(queue),
              'first_pair': [row['run_id'] for row in queue[:2]]}
    save(HERE / 'frozen-current.json', frozen)
    print(json.dumps(frozen, ensure_ascii=False))


if __name__ == '__main__':
    main()
