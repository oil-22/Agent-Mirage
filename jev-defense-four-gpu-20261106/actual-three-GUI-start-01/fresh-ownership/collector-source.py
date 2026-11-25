"""Collect one fresh read-only ownership/transport proof after root starts bridge.

Never starts a bridge/model/GUI. Tokens are read only by the fixed remote helper.
"""
import argparse
import ast
import base64
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parents[2]
REMOTE_BASE = '/home/researcher/jev-defense-four-gpu-20261106'
DEST_BASE = '/data/researcher/jev-defense-four-gpu-20261106'
MANAGER = BASE / 'transport-preparation/token-normalization-linked-1793975850202477300/bridge_manager.py'
SSH = r'D:\Git\usr\bin\ssh.exe'
SSH_CONFIG = r'C:\Users\researcher\.ssh\config'
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
ROLES = ('primary', 'pplx_flash')
FIELDS = ('role', 'stage', 'phase', 'state', 'exclusive_task_group', 'actual_allowed_pids', 'physical_gpu_uuids')

INSPECT_3090 = r'''import base64,hashlib,json,os,pathlib,subprocess,sys,time
B=pathlib.Path('/home/researcher/jev-defense-four-gpu-20261106')
group=pathlib.Path(sys.argv[1]); expected=json.loads(sys.argv[2])
assert str(group).startswith(str(B)+'/') and '..' not in group.parts
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,h in expected.items(): assert sha(B/name)==h,(name,'source_changed')
ready_path=pathlib.Path(sys.argv[3]); assert sha(ready_path)==sys.argv[4]
ready_binding={'path':str(ready_path),'sha256':sha(ready_path),'value':json.loads(ready_path.read_bytes())}
out=json.loads(subprocess.check_output([sys.executable,str(B/'inspect_model_group.py'),'--root',str(group)]).decode().splitlines()[-1])
inspection_path=pathlib.Path(out['receipt']); inspection=json.loads(inspection_path.read_bytes())
sys.path.insert(0,str(B)); from inspect_model_group import identity,locks_for
lease_path=B/'resource-attempt-20261106-01/lease.json'; lease=json.loads(lease_path.read_bytes())
holder=identity(lease['holder']['pid'])
assert all(str(holder[k])==str(lease['holder'][k]) for k in ('pid','uid','command','start_ticks'))
holder_locks=locks_for(holder['pid'],lease)
launcher_locks=locks_for(inspection['launcher']['pid'],lease)
config=json.loads((group/'runtime-config.json').read_bytes())
sources={str(B/n):h for n,h in expected.items()}
for argv in config['commands'].values():
 path=pathlib.Path(argv[2]); sources[str(path)]=sha(path)
for key in ('preflight_source_root',):
 if key in config:
  for name in ('preflight_service.py','four_gpu_contract.py'):
   path=pathlib.Path(config[key])/name; sources[str(path)]=sha(path)
lines=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits']).decode().splitlines()
cards={str(x['index']):x['uuid'] for x in lease['gpu']}; uuids=set(cards.values())
compute=[{'uuid':x.split(',')[0].strip(),'pid':int(x.split(',')[1])} for x in lines if x.strip() and x.split(',')[0].strip() in uuids]
launch_records={role:json.loads((group/(role+'-launch.json')).read_bytes()) for role in ('primary','pplx_flash')}
detail={'time':time.time(),'group':str(group),'inspection':inspection,'inspection_path':str(inspection_path),'inspection_sha256':sha(inspection_path),'lease_sha256':sha(lease_path),'holder':holder,'expected_holder':lease['holder'],'launch_records':launch_records,'holder_locks':holder_locks,'launcher_locks':launcher_locks,'expected_locks':lease['lock_records'],'physical_gpu_uuids':cards,'compute_on_leased_GPUs':compute,'source_sha256':sources,'reviewed_ready_evidence':ready_binding,'model_calls':0}
print(json.dumps(detail))
'''

HEALTH_4090 = r'''import ast,hashlib,json,os,pathlib,stat,subprocess,sys,time,urllib.request,urllib.error
token_path=pathlib.Path('/data/researcher/jev-defense-four-gpu-20261106/transport-online-three-01/private.token')
fd=os.open(str(token_path),os.O_RDONLY|os.O_NOFOLLOW); fs=os.fstat(fd)
assert stat.S_ISREG(fs.st_mode) and fs.st_uid==os.getuid() and stat.S_IMODE(fs.st_mode)==0o600
with os.fdopen(fd,'rb') as f: token=f.read(8193)
assert len(token)<=8192; token=token.strip(b' \t\r\n\v\f'); assert 32<=len(token)<=8192 and all(33<=x<=126 for x in token)
wrapper=pathlib.Path(sys.argv[1]); expected=sys.argv[2]
assert wrapper.is_file() and not wrapper.is_symlink(); wrapper_sha=hashlib.sha256(wrapper.read_bytes()).hexdigest(); assert wrapper_sha==expected
fields=('role','stage','phase','state','exclusive_task_group','actual_allowed_pids','physical_gpu_uuids')
results=[]
for port in (28427,28423):
 url='http://127.0.0.1:'+str(port)+'/health'
 try:
  with urllib.request.urlopen(url,timeout=10): raise SystemExit(31)
 except urllib.error.HTTPError as error: assert error.code in (401,403)
 req=urllib.request.Request(url,headers={'Authorization':'Bearer '+token.decode('ascii')})
 with urllib.request.urlopen(req,timeout=10) as response:
  assert response.status==200; value=json.load(response)
 value={k:value[k] for k in fields}
 assert token.decode('ascii') not in json.dumps(value)
 results.append(value)
rows=subprocess.check_output(['ss','-H','-ltn']).decode().splitlines()
listeners=[x.split()[3] for x in rows if len(x.split())>3 and x.split()[3].rsplit(':',1)[-1] in ('28427','28423')]
assert sorted(listeners)==['127.0.0.1:28423','127.0.0.1:28427']
print(json.dumps({'time':time.time(),'primary':results[0],'observer':results[1],'unauthenticated_rejected':True,'actual_reverse_loopback_listeners':listeners,'wrapper_path':str(wrapper),'wrapper_sha256':wrapper_sha,'model_calls':0}))
'''

COPY_PROOF_4090 = r'''import base64,hashlib,json,os,pathlib,sys
root=pathlib.Path(sys.argv[1]); base=pathlib.Path('/data/researcher/jev-defense-four-gpu-20261106')
assert str(root).startswith(str(base)+'/ownership-transport-proof-') and '..' not in root.parts
root.mkdir(mode=0o700,parents=True,exist_ok=False)
value=json.load(sys.stdin)
for name,item in value.items():
 assert pathlib.Path(name).name==name and name.endswith('.json')
 data=base64.b64decode(item['base64'],validate=True); assert hashlib.sha256(data).hexdigest()==item['sha256']
 fd=os.open(str(root/name),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
print(json.dumps({'root':str(root),'files':{n:v['sha256'] for n,v in value.items()},'token_copied':False,'model_calls':0}))
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def ssh(host, code, args, remote_python='/usr/bin/python3', stdin=None):
    command = [SSH, '-F', SSH_CONFIG, '-o', 'BatchMode=yes', '-T', host,
               shlex.join([remote_python, '-c', code, *map(str, args)])]
    result = subprocess.run(command, input=stdin, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            creationflags=NO_WINDOW, timeout=80, check=True)
    return json.loads(result.stdout)


def fresh_state(value):
    state = value.get('state', {})
    assert state.get('phase') == 'ready' and state.get('active') is None and state.get('next_run_index') == 0
    assert isinstance(state.get('runs'), dict) and list(state['runs']) == ['image-observer-v1--classifieds_112--clean--joint--observer', 'image-observer-v1--classifieds_112--stale_replace--joint--no-observer', 'image-observer-v1--classifieds_112--stale_replace--joint--observer']
    for run in state['runs'].values():
        assert run.get('status') == 'not_started' and run.get('last_decision_index') == 0
        assert run.get('calls') == {'actor': 0, 'judge': 0, 'observe': 0}
    return list(state['runs'])


def match_locks(actual, expected):
    assert len(actual) == len(expected) == 9
    fields = ('fd', 'path', 'inode')
    assert sorted(tuple(x[k] for k in fields) for x in actual) == sorted(tuple(x[k] for k in fields) for x in expected)


def conservative_4090_time(remote_epoch, collection_elapsed):
    assert isinstance(remote_epoch, (int, float)) and 0 <= collection_elapsed < 100
    return remote_epoch - collection_elapsed


def validate_sources(detail, health, bridge, now):
    assert 0 <= now - detail['time'] <= 120 and 0 <= now - health['time'] <= 120
    inspection = detail['inspection']; resources = inspection['resources']
    assert resources['exclusive_task_group'] is True
    cards = {str(k): v for k, v in resources['physical_gpu_uuids'].items()}
    assert set(cards) == {'4', '5', '6', '7'} and len(set(cards.values())) == 4
    assert cards == detail['physical_gpu_uuids']
    workers = {x['role']: x for x in inspection['workers']}
    assert set(workers) == set(ROLES)
    pids = sorted(x['identity']['pid'] for x in workers.values())
    assert len(set(pids)) == 2 and pids == sorted(resources['actual_allowed_pids'])
    assert detail['holder']['uid'] == inspection['launcher']['uid'] == 1033
    assert all(str(detail['holder'][key]) == str(detail['expected_holder'][key]) for key in ('pid', 'uid', 'command', 'start_ticks'))
    match_locks(detail['holder_locks'], detail['expected_locks'])
    match_locks(detail['launcher_locks'], detail['expected_locks'])
    expected_runs = None
    for role, remote_health in zip(ROLES, (health['primary'], health['observer'])):
        worker = workers[role]
        assert worker['identity']['uid'] == 1033 and worker['identity']['command'] and worker['identity']['start_ticks']
        assert worker['identity'] == detail['launch_records'][role]['identity']
        assert worker['identity']['command'] == ' '.join(detail['launch_records'][role]['argv'])
        assert worker['requests'] == []
        match_locks(worker['held_locks'], detail['expected_locks'])
        for value in (worker['health'], remote_health):
            assert value['role'] == role and value['stage'] == 'online_ready' and value['phase'] == 'ready_gui'
            assert value['exclusive_task_group'] is True and sorted(value['actual_allowed_pids']) == pids
            assert {str(k): v for k, v in value['physical_gpu_uuids'].items()} == cards
            runs = fresh_state(value)
            if expected_runs is None:
                expected_runs = runs
            assert runs == expected_runs
    compute = detail['compute_on_leased_GPUs']
    assert all(row['pid'] in pids and row['uuid'] in cards.values() for row in compute)
    assert {row['uuid'] for row in compute if row['pid'] == workers['primary']['identity']['pid']} == set(cards.values())
    assert {row['uuid'] for row in compute if row['pid'] == workers['pplx_flash']['identity']['pid']} == {cards['7']}
    assert health['unauthenticated_rejected'] is True
    assert sorted(health['actual_reverse_loopback_listeners']) == ['127.0.0.1:28423', '127.0.0.1:28427']
    assert bridge['status'] == 'authenticated_transport_online_stage_only'
    assert bridge['inference_verified'] is False and bridge['GUI_run_ready'] is False
    for host in ('3090', '4090'):
        assert [x['role'] for x in bridge['authenticated_health'][host]] == list(ROLES)
        assert all(x['stage'] == 'online_ready' and x['phase'] == 'ready_gui' and x['bearer_required'] for x in bridge['authenticated_health'][host])
    return cards, pids, expected_runs


def validate_wrapper_fresh_guards(path, expected_sha):
    assert sha(path) == expected_sha
    tree = ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    constants = {node.targets[0].id: node.value.value for node in tree.body if isinstance(node, ast.Assign)
                 and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                 and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)}
    run = functions['run']
    names = {name: [x for x in ast.walk(run) if isinstance(x, ast.Call) and
                     isinstance(x.func, ast.Name) and x.func.id == name]
             for name in ('ownership', 'fetch_health', 'validate_health')}
    assert len(names['ownership']) == 1 and names['ownership'][0].args[1].func.attr == 'time'
    endpoints = {x.args[0].value if isinstance(x.args[0], ast.Constant) else constants[x.args[0].id]
                 for x in names['fetch_health']}
    assert len(names['fetch_health']) == 2 and endpoints == {
        'http://127.0.0.1:28427', 'http://127.0.0.1:28423'}
    assert len(names['validate_health']) == 1
    popen = [x.lineno for x in ast.walk(run) if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and x.func.attr == 'Popen']
    assert len(popen) == 1 and all(x.lineno < popen[0] for values in names.values() for x in values)
    owner = ast.get_source_segment(Path(path).read_text(encoding='utf-8-sig'), functions['ownership'])
    assert '120' in owner and 'bound(' in owner
    return {'wrapper_source_sha256': expected_sha, 'fresh_ownership_max_age_seconds': 120,
            'both_health_endpoints_rechecked_before_child_spawn': True,
            'source_evidence_hashes_rechecked_before_child_spawn': True}


def main(a):
    started = time.time()
    monotonic_started = time.monotonic()
    group = PurePosixPath(a.group)
    assert str(group).startswith(REMOTE_BASE + '/') and '..' not in group.parts
    a.output.mkdir(parents=True, exist_ok=False)
    (a.output / 'collector-source.py').write_bytes(Path(__file__).read_bytes())
    try:
        wrapper_check = validate_wrapper_fresh_guards(a.wrapper_local, a.wrapper_sha256)
        save(a.output / 'wrapper-source-binding.json', {**wrapper_check, 'remote_wrapper_path': a.wrapper_remote})
        for name, expected in json.loads((MANAGER.parent / 'seal.json').read_bytes()).items():
            assert sha(MANAGER.parent / name) == expected
        command = [sys.executable, '-B', str(MANAGER), 'inspect', '--session', str(a.bridge_session)]
        completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   creationflags=NO_WINDOW, timeout=90, check=True)
        bridge_operation = Path(json.loads(completed.stdout)['session'])
        bridge = json.loads((bridge_operation / 'receipt.json').read_bytes())
        save(a.output / 'bridge-inspect.json', bridge)
        bridge_state = json.loads((a.bridge_session / 'state.json').read_bytes())
        save(a.output / 'bridge-process-identity.json', {
            'recorded_process_identities_revalidated_by_manager_inspect': bridge_state['processes'],
            'manager_source_sha256': sha(MANAGER), 'initial_session_state_sha256': sha(a.bridge_session / 'state.json'),
            'fresh_inspect_path': str(bridge_operation), 'fresh_receipt_sha256': sha(bridge_operation / 'receipt.json'),
            'checked_time': time.time(), 'model_calls': 0})
        sources = {name: sha(BASE / name) for name in ('inspect_model_group.py', 'resource_control.py')}
        detail = ssh('3090', INSPECT_3090, [str(group), json.dumps(sources), a.ready_evidence, a.ready_evidence_sha256],
                     remote_python='/opt/whz/conda-envs/webmall-vlm/bin/python')
        save(a.output / '3090-ownership-inspection.json', detail)
        health = ssh('4090', HEALTH_4090, [a.wrapper_remote, a.wrapper_sha256])
        save(a.output / '4090-authenticated-health.json', health)
        # Wrapper runs on4090; Windows can lag its wall clock by subsecond.
        # Keep120seconds and subtract the full monotonic collection cost.
        cards, pids, runs = validate_sources(detail, health, bridge, health['time'])
        collection_elapsed = time.monotonic() - monotonic_started
        collected_time = conservative_4090_time(health['time'], collection_elapsed)
        remote_root = DEST_BASE + '/ownership-transport-proof-' + str(time.time_ns())
        evidence_names = ('3090-ownership-inspection.json', 'bridge-inspect.json', 'bridge-process-identity.json',
                          '4090-authenticated-health.json', 'wrapper-source-binding.json')
        proof = {'actual_uid_full_command_verified': True, 'all_inherited_locks_held': True,
                 'no_foreign_compute_on_leased_GPUs': True, 'transport_ready': True,
                 'outer_launcher_rechecks_fresh': True, 'collected_time': collected_time,
                 'timestamp_authority': '4090 helper epoch minus full local monotonic collection duration',
                 'Windows_started_time_diagnostic_only': started, 'collection_monotonic_seconds': collection_elapsed,
                 'physical_gpu_uuids': cards, 'actual_allowed_pids': pids,
                 'source_evidence': [{'path': remote_root + '/' + name, 'sha256': sha(a.output / name)} for name in evidence_names],
                 'wrapper': {'path': a.wrapper_remote, 'sha256': a.wrapper_sha256},
                 'new_online_group': str(group), 'three_unstarted_run_ids': runs,
                 'model_calls': 0, 'GUI_actions': 0, 'token_returned_or_logged': False,
                 'collector_source_sha256': sha(Path(__file__)),
                 'bridge_operation': {'path': str(bridge_operation), 'receipt_sha256': sha(bridge_operation / 'receipt.json')}}
        save(a.output / 'ownership-transport-proof.json', proof)
        payload = {name: {'base64': base64.b64encode((a.output / name).read_bytes()).decode(),
                          'sha256': sha(a.output / name)} for name in (*evidence_names, 'ownership-transport-proof.json')}
        delivery = ssh('4090', COPY_PROOF_4090, [remote_root], stdin=json.dumps(payload).encode())
        assert delivery['files'] == {name: item['sha256'] for name, item in payload.items()}
        save(a.output / 'delivery.json', delivery)
        print(json.dumps({'proof': remote_root + '/ownership-transport-proof.json',
                          'sha256': sha(a.output / 'ownership-transport-proof.json'),
                          'collected_time': collected_time,
                          'collection_and_delivery_monotonic_seconds': time.monotonic() - monotonic_started, 'model_calls': 0}))
    except BaseException as error:
        save(a.output / 'failure.json', {'status': 'read_only_collector_failure',
                                       'error_type': type(error).__name__, 'model_calls': 0, 'GUI_actions': 0})
        raise
    finally:
        save(a.output / 'seal.json', {p.name: sha(p) for p in a.output.iterdir() if p.is_file()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', required=True)
    parser.add_argument('--bridge-session', type=Path, required=True)
    parser.add_argument('--wrapper-local', type=Path, required=True)
    parser.add_argument('--wrapper-remote', required=True)
    parser.add_argument('--wrapper-sha256', required=True)
    parser.add_argument('--ready-evidence', required=True)
    parser.add_argument('--ready-evidence-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args())
