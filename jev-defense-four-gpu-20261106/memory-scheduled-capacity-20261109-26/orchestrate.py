"""Once-only staging/admission/submission of the linked original-budget attempt."""
import argparse
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
PACKAGE = HERE / 'runtime-package'
sys.path.insert(0, str(BASE / 'full-history-gui-development-20261109-23'))
from remote_control import remote, save, sha

REMOTE_PACKAGE = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + HERE.name
OUTPUT = '/home/researcher/jev-defense-four-gpu-20261106/' + HERE.name
COMMON = r'''
from pathlib import Path
import hashlib,json,os,subprocess,time
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return {'pid':pid,'absent':True}
 t=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':t[19],'state':t[0]}
'''


def stage():
    assert not (HERE / 'staging.json').exists()
    m = json.loads((PACKAGE / 'manifest.json').read_bytes())
    for name, expected in m['files'].items():
        assert sha(PACKAGE / name) == expected
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in ['manifest.json'] + list(m['files']):
            z.writestr(name, (PACKAGE / name).read_bytes())
    code = 'ROOT=' + repr(REMOTE_PACKAGE) + '\nARCHIVE=' + repr(base64.b64encode(archive.getvalue()).decode()) + '\n' + COMMON + r'''
import base64,io,zipfile
r=Path(ROOT);assert os.getuid()==1033 and not r.exists();r.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(ARCHIVE)))as z:
 for item in z.infolist():
  q=r/item.filename;assert q.resolve().is_relative_to(r.resolve())
  q.parent.mkdir(parents=True,exist_ok=True)
  with q.open('xb')as f:f.write(z.read(item))
m=json.loads((r/'manifest.json').read_bytes())
for name,expected in m['files'].items():assert sha(r/name)==expected,name
print(json.dumps({'package':str(r),'manifest_sha256':sha(r/'manifest.json'),'files':len(m['files']),'new_experiment_calls':0}))
'''
    result, operation = remote('3090', code, 'stage-new-memory-scheduled26-once', timeout=55)
    save(HERE / 'staging.json', {'result': json.loads(result), 'operation': str(operation)})
    print(result)


def admit():
    assert not (HERE / 'CPU-admission.json').exists()
    code = 'PACKAGE=' + repr(REMOTE_PACKAGE) + '\n' + COMMON + r'''
import ast
p=Path(PACKAGE);m=json.loads((p/'manifest.json').read_bytes())
for name,h in m['files'].items():assert sha(p/name)==h,name
for q in p.rglob('*.py'):compile(q.read_text(),str(q),'exec')
assert m['original_budget']=={'actor_spent':11,'actor_cap':70,'judge_spent':33,'judge_cap':140,'pending_actor_candidate_index':11,'actions_executed':10,'step_cap':50}
assert m['one_linked_judge_attempt_index']==34 and m['remaining_judge_after_attempt']==106
old=p.parent/'full-history-gui-development-20261109-23'
oldm=json.loads((old/'manifest.json').read_bytes())
assert sha(old/'manifest.json')==m['original_manifest_sha256']
for name,h in oldm['files'].items():
 if name.startswith('release/'):assert sha(p/name)==h,name
tree=ast.parse((p/'model_runtime.py').read_text());oldtree=ast.parse((old/'model_runtime.py').read_text())
aud=lambda tree:next(n for n in ast.walk(tree)if isinstance(n,ast.FunctionDef)and n.name=='audited_generation')
assert ast.dump(aud(tree),include_attributes=False)==ast.dump(aud(oldtree),include_attributes=False)
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='load_runtime')
assignment=next(n for n in fn.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='device_map'for t in n.targets))
loop=next(n for n in fn.body if isinstance(n,ast.For)and any(isinstance(x,ast.Subscript)and isinstance(x.value,ast.Name)and x.value.id=='device_map'for x in ast.walk(n)))
space={};exec(compile(ast.Module(body=[assignment,loop],type_ignores=[]),'placement-only','exec'),space)
dm=space['device_map'];assert [sum(dm['model.language_model.layers.'+str(i)]==j for i in range(64))for j in range(4)]==[18,18,15,13]
ref=json.loads((p/'primary-reference.json').read_bytes());bound=Path(ref['primary_native_layout_receipt'])
assert sha(bound)==ref['primary_native_layout_receipt_sha256'];v=json.loads(bound.read_bytes())
state=Path(v['meta_root'])/'meta-state.json';seal=json.loads((state.parent/'seal.json').read_bytes());assert sha(state)==seal['meta-state.json']
totals={i:0 for i in range(4)}
for row in json.loads(state.read_bytes()):
 keys=[k for k in dm if row['name']==k or row['name'].startswith(k+'.')];assert keys,row['name']
 totals[dm[max(keys,key=len)]]+=row['bytes']
assert sum(totals.values())==54713457120 and max(totals.values())<15*1024**3
source=Path('/home/researcher/jev-defense-four-gpu-20261106/full-history-gui-development-20261109-23/worker/requests/0044')
for q in (p/'original0044').iterdir():assert sha(q)==sha(source/q.name),q.name
assert (source/'generated-token-progress.jsonl').stat().st_size==0
assert json.loads((source/'forward-count.json').read_bytes())['actual_forward_calls']==1
payload=json.loads((source/'payload.json').read_bytes());tensors=json.loads((source/'prepared.json').read_bytes())
assert len(payload['view']['images'])==11 and tensors['input_ids']['shape']==[1,22596]
assert tensors['input_ids']['sha256']==m['original_input_ids_sha256']
assert sha(source/'payload.json')==m['original_payload_sha256']
available=int(next(s.split()[1]for s in Path('/proc/meminfo').read_text().splitlines()if s.startswith('MemAvailable:')))*1024
assert available>=64*1024**3
print(json.dumps({'passed':True,'manifest_sha256':sha(p/'manifest.json'),'files':len(m['files']),
 'primary_parameter_bytes':totals,'primary_layer_counts':[18,18,15,13],'available_RAM_bytes':available,
 'old_full_release_and_native_generation_unchanged':True,'exact_original_failed_input_bound':True,
 'limits':m['limits'],'linked_judge_attempt':34,'original_judge_cap':140,
 'CPU_model_inference_allowed':False,'new_model_GPU_GUI_scorer_paid_calls':0,
 'actual_GPU_swap_and_input_capacity_still_unproven':True}))
'''
    output, operation = remote('3090', code, 'CPU-source-budget-and-placement26-admission', timeout=55)
    save(HERE / 'CPU-admission.json', {'result': json.loads(output), 'operation': str(operation)})
    print(output)


def submit():
    assert not (HERE / 'submission-intent.json').exists()
    admission = json.loads((HERE / 'CPU-admission.json').read_bytes())['result']
    assert admission['passed'] and admission['manifest_sha256'] == sha(PACKAGE / 'manifest.json')
    argv = ['/opt/whz/conda-envs/webmall-vlm/bin/python', REMOTE_PACKAGE + '/launch_capacity_once.py',
            '--manifest', REMOTE_PACKAGE + '/manifest.json', '--manifest-sha256', sha(PACKAGE / 'manifest.json'),
            '--output', OUTPUT]
    command = {'action': 'launch', 'argv': argv, 'script_sha256': sha(PACKAGE / 'launch_capacity_once.py')}
    save(HERE / 'submission-intent.json', {'time': time.time(), 'manifest_sha256': argv[5],
        'once_only': True, 'no_resubmit_after_ambiguous_observation': True,
        'limits': admission['limits'], 'original_judge_attempt_index': 34})
    code = 'PACKAGE=' + repr(REMOTE_PACKAGE) + '\nOUTPUT=' + repr(OUTPUT) + '\nCOMMAND=' + repr(command) + '\n' + COMMON + r'''
import fcntl
b=Path('/home/researcher/jev-defense-four-gpu-20261106');p=Path(PACKAGE);r=Path(OUTPUT)
assert os.getuid()==1033 and not r.exists()and not any((p/'claims').glob('*.json'))
m=json.loads((p/'manifest.json').read_bytes());assert sha(p/'manifest.json')==COMMAND['argv'][5]
for name,h in m['files'].items():assert sha(p/name)==h,name
closed=b/'full-history-gui-development-20261109-23'
assert (closed/'terminal-manifest.json').is_file()
for name in ['launcher-process.json','worker/process.json']:
 record=json.loads((closed/name).read_bytes());now=identity(record['pid']);assert now.get('absent')is True
state=json.loads((closed/'worker/status.json').read_bytes());assert state['counts']=={'actor':11,'evidence':0,'judge':33}
assert json.loads((closed/'exit.json').read_bytes())['worker_exit_code']==1
lease=json.loads((b/'resource-attempt-20261106-01/lease.json').read_bytes());holder=lease['holder'];actual=identity(holder['pid'])
assert sha(b/'resource-attempt-20261106-01/lease.json')==m['lease_sha256']
assert all(str(holder[k])==str(actual[k])for k in ['pid','uid','command','start_ticks'])and actual['state']not in ['Z','X']
for row in lease['lock_records']:
 proc=Path('/proc',str(holder['pid']));fd=proc/'fd'/str(row['fd']);info=(proc/'fdinfo'/str(row['fd'])).read_text()
 assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and'WRITE '+str(holder['pid'])in info
assert len(lease['lock_records'])==9 and {x['index']for x in lease['gpu']}=={4,5,6,7}
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
cards={int(s.split(',')[0]):(s.split(',')[1].strip(),int(s.split(',')[2]))for s in gpu.splitlines()}
for row in lease['gpu']:assert cards[row['index']][0]==row['uuid']and cards[row['index']][1]>=23000
targets={row['uuid']for row in lease['gpu']}
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
assert not any(s.split(',')[0].strip()in targets for s in compute.splitlines()if s.strip())
with Path(lease['inference_lock']).open('a')as mutex:fcntl.flock(mutex,fcntl.LOCK_EX|fcntl.LOCK_NB)
commands=b/'resource-attempt-20261106-01/commands';assert all(x.with_suffix('.claimed').exists()for x in commands.glob('*.json'))
dest=commands/'memory-scheduled-capacity-20261109-26.json';temporary=commands/('.memory26-'+str(os.getpid())+'.tmp')
with temporary.open('xb')as f:f.write(json.dumps(COMMAND,ensure_ascii=False,indent=2).encode());f.flush();os.fsync(f.fileno())
os.link(temporary,dest);temporary.unlink()
print(json.dumps({'submitted_once':True,'command':str(dest),'manifest_sha256':sha(p/'manifest.json'),
 'actual_holder_nine_locks_UUIDs_empty_authorized_GPUs_rechecked':True,'new_model_calls_from_submission':0}))
'''
    output, operation = remote('3090', code, 'submit-linked26-judge34-once-no-GUI', timeout=55)
    save(HERE / 'submission.json', {'result': json.loads(output), 'operation': str(operation)})
    print(output)


def inspect():
    code = 'ROOT=' + repr(OUTPUT) + '\n' + COMMON + r'''
r=Path(ROOT);out={'time':time.time(),'exists':r.exists(),'new_model_GPU_GUI_calls':0}
for name in ['launcher-process.json','worker/process.json','worker/status.json','worker/terminal.json','worker/failure.json','worker/summary.json','exit.json']:
 q=r/name
 if not q.is_file():continue
 v=json.loads(q.read_bytes());out[name]={'record':v,'actual':identity(v['pid'])}if name.endswith('process.json')else v
out['compute']=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
if (r/'worker.log').is_file():out['log_tail']=(r/'worker.log').read_bytes()[-1200:].decode(errors='replace')
out['residency_transitions']=[json.loads(q.read_bytes())for q in sorted((r/'worker').glob('residency-transition-*.json'))]
print(json.dumps(out,ensure_ascii=False))
'''
    output, operation = remote('3090', code, 'inspect-existing-linked26-actual-handle', timeout=55)
    snapshot = json.loads(output)
    print(json.dumps({'operation': str(operation), 'snapshot': snapshot}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['stage', 'admit', 'submit', 'inspect'])
    {'stage': stage, 'admit': admit, 'submit': submit, 'inspect': inspect}[parser.parse_args().action]()
