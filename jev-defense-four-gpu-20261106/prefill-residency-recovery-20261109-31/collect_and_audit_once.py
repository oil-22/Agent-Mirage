"""Collect and audit the completed exact request, retaining original GPU tensors."""
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import zipfile

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE / 'full-history-gui-development-20261109-23'))
from remote_control import remote, save, sha


def main():
    assert not (HERE / 'terminal-collection-created.json').exists()
    target = HERE / ('terminal-collection-' + str(time.time_ns())); target.mkdir()
    remote_root = '/home/researcher/jev-defense-four-gpu-20261106/' + HERE.name
    code = 'ROOT=' + repr(remote_root) + '\nEXPECTED=' + repr(sha(HERE / 'runtime-package/manifest.json')) + '\n' + r'''
from pathlib import Path
import base64,hashlib,io,json,os,subprocess,time,zipfile
r=Path(ROOT);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return {'pid':pid,'absent':True}
 t=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':t[19],'state':t[0]}
assert os.getuid()==1033 and sha(r/'manifest.json')==EXPECTED
actual=[]
for name in ['launcher-process.json','worker/process.json']:
 row=json.loads((r/name).read_bytes());now=identity(row['pid']);assert now.get('absent')is True
 actual.append({'record':row,'actual':now})
exit_record=json.loads((r/'exit.json').read_bytes());assert exit_record['worker_exit_code']==exit_record['launcher_exit_code']==0
manifest=json.loads((r/'terminal-manifest.json').read_bytes())
for name,h in manifest.items():assert sha(r/name)==h,name
original={p.relative_to(r).as_posix():sha(p)for p in sorted(r.rglob('*'))if p.is_file()}
stats={p.relative_to(r).as_posix():{'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns,'inode':p.stat().st_ino,'uid':p.stat().st_uid}for p in sorted(r.rglob('*'))if p.is_file()}
bindings=json.loads((r/'worker/judge/J01/seal.json').read_bytes())
for name,h in bindings.items():assert sha(r/'worker/judge/J01'/name)==h,name
previous='0'*64;count=0
for line in (r/'worker/journal/events.jsonl').read_bytes().splitlines():
 row=json.loads(line);signature=row.pop('sha256');assert row['seq']==count and row['previous']==previous
 assert hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==signature
 previous=signature;count+=1
b=r.parent;lease=json.loads((b/'resource-attempt-20261106-01/lease.json').read_bytes());holder=lease['holder'];now=identity(holder['pid'])
assert all(str(holder[k])==str(now[k])for k in ['pid','uid','command','start_ticks'])
for row in lease['lock_records']:
 p=Path('/proc',str(holder['pid']));fd=p/'fd'/str(row['fd']);info=(p/'fdinfo'/str(row['fd'])).read_text()
 assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and'WRITE '+str(holder['pid'])in info
assert len(lease['lock_records'])==9
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
targets={row['uuid']for row in lease['gpu']}
assert not any(s.split(',')[0].strip()in targets for s in compute.splitlines()if s.strip())
public={};archive=io.BytesIO()
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
 for name,h in original.items():
  p=r/name
  if p.suffix in ['.json','.jsonl','.log','.txt','.png']:
   raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==h
   z.writestr(name,raw);public[name]=h
for name,st in stats.items():
 p=r/name;assert p.stat().st_size==st['bytes']and p.stat().st_mtime_ns==st['mtime_ns']and p.stat().st_ino==st['inode']
receipt={'time':time.time(),'original_root':str(r),'all_original_files':original,'original_file_stats':stats,
 'public_exported_files':public,'archive_sha256':hashlib.sha256(archive.getvalue()).hexdigest(),
 'all_terminal_and_request_seals_verified':True,'all_original_files_retained_in_place':True,
 'actual_worker_and_launcher':actual,'actual_holder':now,'nine_locks_still_held':True,
 'no_authorized_GPU_compute_after_exit':True,'chain':{'events':count,'head':previous},
 'new_model_GUI_scorer_paid_calls':0,'remote_read_only':True}
print(json.dumps({'receipt':receipt,'archive_base64':base64.b64encode(archive.getvalue()).decode()}))
'''
    output, operation = remote('3090', code, 'collect-completed31-all-original-SHA-and-native-tensors-once', timeout=90)
    result = json.loads(output); proof = result['receipt']
    raw = base64.b64decode(result['archive_base64'])
    assert hashlib.sha256(raw).hexdigest() == proof['archive_sha256']
    (target / 'public-originals.zip').write_bytes(raw)
    original = target / 'original'; original.mkdir()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for entry in z.infolist():
            path = original / entry.filename
            assert path.resolve().is_relative_to(original.resolve())
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(z.read(entry))
    for name, expected in proof['public_exported_files'].items():
        assert sha(original / name) == expected
    save(target / 'remote-preservation.json', dict(proof, operation=str(operation)))
    folder = original / 'worker/judge/J01'
    prepared = json.loads((folder / 'prepared.json').read_bytes())
    first = json.loads((folder / 'first-forward.json').read_bytes())
    old = json.loads((HERE / 'runtime-package/original0021/prepared.json').read_bytes())
    for key in old:
        assert all(old[key][field] == prepared[key][field] == first[key][field]
                   for field in ['shape', 'dtype', 'bytes', 'sha256']), key
    generation = json.loads((folder / 'actual-generation.json').read_bytes())
    native = json.loads((folder / 'generation.json').read_bytes())
    reply = json.loads((folder / 'response.json').read_bytes())
    assert native['generated_ids'] == generation['output_ids']
    assert native['text'] == reply['text'] == (folder / 'raw-output.txt').read_text(encoding='utf8')
    assert generation['natural_EOS'] and not native['hit_output_cap']
    assert generation['input_tokens'] == 32184
    assert (folder / 'payload.json').read_bytes() == (HERE / 'runtime-package/original0021/payload.json').read_bytes()
    assert json.loads((folder / 'effective-generation.json').read_bytes()) == json.loads((HERE / 'runtime-package/original0021/effective-generation.json').read_bytes())
    assert native['generation_config'] == json.loads((folder / 'effective-generation.json').read_bytes())
    prefills = [json.loads(p.read_bytes()) for p in sorted((original / 'worker').glob('prefill-residency-*.json'))]
    assert len(prefills) == 1
    prefill = prefills[0]
    assert prefill['input_tokens'] == 32184 and prefill['success']
    assert prefill['all_group_forward_parameters_BF16_on_original_GPU']
    assert prefill['full_GPU_resident_before_decode']
    assert prefill['native_attention_generation_inputs_outputs_and_cache_unmodified']
    assert len(prefill['same_native_execution_device_map']) == 69
    assert set(prefill['visited_groups']) == set(prefill['same_native_execution_device_map'])
    assert len(prefill['visited_groups']) == 69
    original_view = json.loads((folder / 'payload.json').read_bytes())['view']
    assert len(original_view['images']) == 17
    summary = json.loads((original / 'worker/summary.json').read_bytes())
    assert summary['actual_calls'] == summary['actual_judge_calls'] == 1
    assert summary['linked_judge_spent'] == 50 and summary['original_actor_spent'] == 17
    assert summary['auxiliary_generation_calls'] == summary['GUI_actions_or_scorer_paid_calls'] == 0
    exit_record = json.loads((original / 'exit.json').read_bytes())
    audit = {'schema': 'exact-original-GUI29-0021-prefill-residency-technical-audit-v1',
        'time': time.time(), 'passed': True, 'terminal': 'completed', 'must_not_rerun': True,
        'original_manifest_sha256': sha(HERE / 'runtime-package/manifest.json'),
        'remote_preservation_sha256': sha(target / 'remote-preservation.json'),
        'all_original_terminal_request_and_chain_SHA_verified': True,
        'original_CPU_prepared_and_actual_first_forward_all_equal': True,
        'input_tokens': generation['input_tokens'], 'complete_original_images': 17,
        'original_input_ids_sha256': prepared['input_ids']['sha256'],
        'actual_judge_attempts': 1, 'natural_EOS': True, 'output_tokens': generation['output_tokens'],
        'native_generation_seconds': native['seconds'],
        'instrumented_seconds': reply['seconds_including_instrumentation'],
        'four_GPU_reserved_seconds_inside_launcher': exit_record['four_GPU_reserved_seconds_in_launcher'],
        'prefill_weight_transfer_seconds': prefill['all_transfer_seconds'],
        'prefill_seconds_including_restore': prefill['seconds_including_restore'],
        'native_execution_device_map_unchanged': True,
        'no_claim_of_future_longest_input_fit_or_bitwise_output_identity': True,
        'per_device_generation_peak_memory': generation['memory'],
        'all_actual_forwards_GPU_only': True, 'CPU_only_stores_idle_weights': True,
        'no_auxiliary_forward_or_new_weight_cycle_control': True,
        'original_judge_attempts_spent_after_this_reply': 50, 'original_judge_cap': 140,
        'remaining_original_judge_attempts': 90, 'original_actor_attempts_spent': 17,
        'original_executed_actions': 16,
        'new_auxiliary_actor_GUI_scorer_paid_calls': 0,
        'GUI_trajectory_or_all_future_history_capacity_recovered': False,
        'semantic_pass_or_Mirage_reduction_established': False,
        'worker_and_launcher_actually_absent': True, 'nine_owned_locks_remain': True,
        'no_currency_energy_walltime_or_end_to_end_savings_claim': True}
    save(target / 'audit.json', audit)
    save(target / 'receipt.json', {'audit_sha256': sha(target / 'audit.json'),
        'remote_preservation_sha256': sha(target / 'remote-preservation.json'),
        'public_files_verified': len(proof['public_exported_files']), 'original_files_verified': len(proof['all_original_files']),
        'no_new_experiment_calls': True, 'goal': 'active'})
    save(target / 'seal.json', {p.relative_to(target).as_posix(): sha(p) for p in target.rglob('*') if p.is_file()})
    save(HERE / 'terminal-collection-created.json', {'collection': str(target), 'audit_sha256': sha(target / 'audit.json'),
                                                 'receipt_sha256': sha(target / 'receipt.json'), 'seal_sha256': sha(target / 'seal.json')})
    print(json.dumps({'collection': str(target), 'audit': audit, 'receipt_sha256': sha(target / 'receipt.json')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
