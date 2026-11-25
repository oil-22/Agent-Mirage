"""Stage and admit only the new two-call capacity attempt, once, on GPUs4-7."""
import argparse
import base64
import io
import json
from pathlib import Path
import sys
import time
import zipfile

HERE = Path(__file__).resolve().parent
PACKAGE = HERE / 'runtime-package'
sys.path.insert(0, str(HERE.parent / 'full-gui-bounded-evidence-20261109-03'))
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
    manifest = json.loads((PACKAGE / 'manifest.json').read_bytes())
    for name, expected in manifest['files'].items():
        assert sha(PACKAGE / name) == expected
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in ['manifest.json'] + list(manifest['files']):
            z.writestr(name, (PACKAGE / name).read_bytes())
    code = 'ROOT=' + repr(REMOTE_PACKAGE) + '\nARCHIVE=' + repr(base64.b64encode(archive.getvalue()).decode()) + '\n' + COMMON + r'''
import base64,io,zipfile
r=Path(ROOT);assert os.getuid()==1033 and not r.exists()
r.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(ARCHIVE)))as z:
 for item in z.infolist():
  q=r/item.filename;assert q.resolve().is_relative_to(r.resolve())
  q.parent.mkdir(parents=True,exist_ok=True)
  with q.open('xb')as stream:stream.write(z.read(item))
m=json.loads((r/'manifest.json').read_bytes())
for n,h in m['files'].items():assert sha(r/n)==h,n
print(json.dumps({'staged':str(r),'manifest_sha256':sha(r/'manifest.json'),'files_verified':len(m['files']),'new_model_GPU_GUI_calls':0}))
'''
    output, operation = remote('3090', code, 'stage-new-exact-capacity13', timeout=55)
    save(HERE / 'staging.json', {'result': json.loads(output), 'operation': str(operation)})
    print(output)


def admit_cpu():
    assert not (HERE / 'CPU-admission.json').exists()
    code = 'PACKAGE=' + repr(REMOTE_PACKAGE) + '\n' + COMMON + r'''
import ast
p=Path(PACKAGE);m=json.loads((p/'manifest.json').read_bytes())
for n,h in m['files'].items():assert sha(p/n)==h,n
for q in p.rglob('*.py'):compile(q.read_text(),str(q),'exec')
tree=ast.parse((p/'model_runtime.py').read_text())
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='load_runtime')
assignment=next(n for n in fn.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='device_map'for t in n.targets))
loop=next(n for n in fn.body if isinstance(n,ast.For)and any(isinstance(x,ast.Subscript)and isinstance(x.value,ast.Name)and x.value.id=='device_map'for x in ast.walk(n)))
namespace={};exec(compile(ast.Module(body=[assignment,loop],type_ignores=[]),'placement-only','exec'),namespace)
dm=namespace['device_map'];assert len([k for k in dm if '.layers.'in k])==64
assert [sum(dm['model.language_model.layers.'+str(i)]==j for i in range(64))for j in range(3)]==[22,23,19]
assert dm['model.visual']==dm['model.language_model.embed_tokens']==3
assert all(v in [0,1,2,3]for v in dm.values())
ref=json.loads((p/'primary-reference.json').read_bytes());bound=json.loads(Path(ref['primary_native_layout_receipt']).read_bytes())
assert sha(Path(ref['primary_native_layout_receipt']))==ref['primary_native_layout_receipt_sha256']
state=json.loads((Path(bound['meta_root'])/'meta-state.json').read_bytes())
totals={i:0 for i in range(4)}
for row in state:
 keys=[k for k in dm if row['name']==k or row['name'].startswith(k+'.')];assert keys,row['name']
 totals[dm[max(keys,key=len)]]+=row['bytes']
assert sum(totals.values())==54713457120
old=Path('/home/researcher/jev-defense-four-gpu-20261106/source-bound-controls-20261109-08')
loaded=json.loads((old/'worker/loaded.json').read_bytes())
aux=loaded['auxiliary_CUDA']['tensor_bytes_by_device']['cuda:3']
combined=dict(totals);combined[3]+=aux
failed=p/'original0178';payload=json.loads((failed/'payload.json').read_bytes())
prepared=json.loads((failed/'prepared.json').read_bytes())
assert sha(failed/'payload.json')==m['original_payload_sha256']
assert prepared['input_ids']['shape']==[1,20382]and prepared['input_ids']['sha256']==m['original_input_ids_sha256']
assert len(payload['view']['images'])==4 and len(payload['view']['messages'])==46
assert (failed/'generated-token-progress.jsonl').stat().st_size==0
assert json.loads((failed/'forward-count.json').read_bytes())['actual_forward_calls']==1
assert sha(p/'release/defense/qwen_backend.py')==ref['primary_backend_sha256']
print(json.dumps({'passed':True,'manifest_sha256':sha(p/'manifest.json'),'primary_layer_counts':[22,23,19],
 'primary_parameter_bytes':totals,'auxiliary_tensor_bytes_from_actual_closed_load':aux,'combined_parameter_bytes':combined,
 'complete_original_input_tokens':20382,'complete_original_images':4,'complete_legal_messages':46,
 'native_backend_unchanged':True,'no_CPU_inference_or_weight_loading':True,
 'parameter_inventory_only_not_activation_KV_or_real_joint_fit':True,'new_model_GPU_GUI_calls':0}))
'''
    output, operation = remote('3090', code, 'capacity13-CPU-placement-and-source-admission', timeout=55)
    save(HERE / 'CPU-admission.json', {'result': json.loads(output), 'operation': str(operation)})
    print(output)


def submit():
    assert not (HERE / 'submission-intent.json').exists()
    admission = json.loads((HERE / 'CPU-admission.json').read_bytes())['result']
    assert admission['passed'] and admission['manifest_sha256'] == sha(PACKAGE / 'manifest.json')
    audit = HERE.parent / 'source-bound-controls-20261109-08/terminal-audit-1794212587130988100/receipt.json'
    v = json.loads(audit.read_bytes())
    assert v['passed'] and v['worker_and_launcher_actually_absent']
    assert v['actual_attempts'] == v['natural_EOS_replies'] == 26
    assert v['actual_judge_calls'] == 23 and v['actual_auxiliary_calls'] == 3
    assert v['terminal_and_exit_codes_verified']
    argv = ['/opt/whz/conda-envs/webmall-vlm/bin/python', REMOTE_PACKAGE + '/launch_capacity_once.py',
            '--manifest', REMOTE_PACKAGE + '/manifest.json', '--manifest-sha256', sha(PACKAGE / 'manifest.json'), '--output', OUTPUT]
    command = {'action': 'launch', 'argv': argv, 'script_sha256': sha(PACKAGE / 'launch_capacity_once.py')}
    save(HERE / 'submission-intent.json', {'time': time.time(), 'once_only': True,
          'manifest_sha256': argv[5], 'controls08_closed_audit_sha256': sha(audit),
          'ambiguous_result_requires_inspection_not_resubmission': True})
    code = 'PACKAGE=' + repr(REMOTE_PACKAGE) + '\nOUTPUT=' + repr(OUTPUT) + '\nCOMMAND=' + repr(command) + '\n' + COMMON + r'''
import fcntl
b=Path('/home/researcher/jev-defense-four-gpu-20261106');p=Path(PACKAGE);r=Path(OUTPUT)
assert os.getuid()==1033 and not r.exists()and not any((p/'claims').glob('*.json'))
closed=b/'source-bound-controls-20261109-08'
assert (closed/'exit.json').is_file()and(closed/'terminal-manifest.json').is_file()
for name in ['launcher-process.json','worker/process.json']:
 record=json.loads((closed/name).read_bytes());assert identity(record['pid']).get('absent')is True
exit_record=json.loads((closed/'exit.json').read_bytes());assert exit_record['worker_exit_code']==exit_record['launcher_exit_code']==0
assert sha(p/'manifest.json')==COMMAND['argv'][5]
m=json.loads((p/'manifest.json').read_bytes())
for n,h in m['files'].items():assert sha(p/n)==h,n
lease=json.loads((b/'resource-attempt-20261106-01/lease.json').read_bytes());holder=lease['holder'];actual=identity(holder['pid'])
assert all(str(actual[k])==str(holder[k])for k in ['pid','uid','command','start_ticks'])and actual['state']not in ['Z','X']
for row in lease['lock_records']:
 proc=Path('/proc',str(holder['pid']));fd=proc/'fd'/str(row['fd']);info=(proc/'fdinfo'/str(row['fd'])).read_text()
 assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']and 'WRITE '+str(holder['pid'])in info
assert len(lease['lock_records'])==9 and {x['index']for x in lease['gpu']}=={4,5,6,7}
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
cards={int(s.split(',')[0]):(s.split(',')[1].strip(),int(s.split(',')[2]))for s in gpu.splitlines()}
for row in lease['gpu']:assert cards[row['index']][0]==row['uuid']and cards[row['index']][1]>=23000
target={x['uuid']for x in lease['gpu']}
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
assert not any(s.split(',')[0].strip()in target for s in compute.splitlines()if s.strip())
with Path(lease['inference_lock']).open('a')as mutex:fcntl.flock(mutex,fcntl.LOCK_EX|fcntl.LOCK_NB)
commands=b/'resource-attempt-20261106-01/commands'
assert all(x.with_suffix('.claimed').exists()for x in commands.glob('*.json'))
dest=commands/'capacity-preflight-20261109-13.json';temporary=commands/('.capacity13-'+str(os.getpid())+'.tmp')
with temporary.open('xb')as f:f.write(json.dumps(COMMAND,ensure_ascii=False,indent=2).encode());f.flush();os.fsync(f.fileno())
os.link(temporary,dest);temporary.unlink()
print(json.dumps({'submitted_once':True,'command_file':str(dest),'time':time.time(),'manifest_sha256':COMMAND['argv'][5],'actual_holder_and_nine_locks_and_empty_authorized_GPUs_rechecked':True}))
'''
    output, operation = remote('3090', code, 'submit-capacity13-exact-two-calls-once', timeout=55)
    save(HERE / 'submission.json', {'result': json.loads(output), 'operation': str(operation)})
    print(output)


def inspect():
    code = 'ROOT=' + repr(OUTPUT) + '\n' + COMMON + r'''
r=Path(ROOT);out={'time':time.time(),'exists':r.exists(),'new_model_GPU_GUI_calls':0}
for name in ['launcher-process.json','worker/process.json','worker/status.json','worker/terminal.json','worker/failure.json','exit.json']:
 q=r/name
 if not q.is_file():continue
 v=json.loads(q.read_bytes());out[name]={'record':v,'actual':identity(v['pid'])}if name.endswith('process.json')else v
out['compute']=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
if (r/'worker.log').is_file():out['log_tail']=(r/'worker.log').read_bytes()[-900:].decode(errors='replace')
print(json.dumps(out,ensure_ascii=False))
'''
    output, operation = remote('3090', code, 'inspect-new-capacity13-only', timeout=55)
    print(json.dumps({'operation': str(operation), 'snapshot': json.loads(output)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['stage', 'admit-cpu', 'submit', 'inspect'])
    action = parser.parse_args().action
    {'stage': stage, 'admit-cpu': admit_cpu, 'submit': submit, 'inspect': inspect}[action]()
