"""Local, evidence-preserving transport for the separately requested model comparison."""
import base64, hashlib, io, json, subprocess, sys, time, zipfile
from pathlib import Path
sys.stdout.reconfigure(encoding='utf8')
sys.stderr.reconfigure(encoding='utf8')

HERE = Path(__file__).resolve().parent
REMOTE = '/home/researcher/jev-defense-four-gpu-20261106/binary-gate-comparison-20261112'
SSH = ['D:/Git/usr/bin/ssh.exe', '-F', 'C:/Users/researcher/.ssh/config', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '3090']
PY = '/opt/whz/conda-envs/webmall-vlm/bin/python'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, v):
    with Path(p).open('x', encoding='utf8') as f: json.dump(v, f, ensure_ascii=False, indent=2)
def remote(code, label, timeout=55):
    d = HERE/'operations'/(str(time.time_ns())+'-'+label)
    d.mkdir(parents=True)
    (d/'source.py').write_text(code, encoding='utf8')
    try:
        r = subprocess.run(SSH+[PY+' -B -'], input=code, text=True, encoding='utf8', capture_output=True, timeout=timeout)
        (d/'stdout.txt').write_text(r.stdout, encoding='utf8')
        (d/'stderr.txt').write_text(r.stderr, encoding='utf8')
        save(d/'receipt.json', {'returncode':r.returncode, 'source_sha256':sha(d/'source.py'), 'time':time.time()})
    except BaseException as e:
        save(d/'failure.json', {'type':type(e).__name__, 'message':str(e)})
        raise
    if r.returncode: raise RuntimeError(str(d)+'\n'+r.stderr[-3000:]+'\n'+r.stdout[-3000:])
    return r.stdout, d

def stage():
    import ast
    ast.parse((HERE/'run_comparison.py').read_text(encoding='utf8'))
    commitment={'protocol_sha256':sha(HERE/'protocol.json'),'private_labels_sha256':sha(HERE/'PRIVATE-labels-pre-output.json'),'pre_output_seal_sha256':sha(HERE/'pre-output-seal.json'),'labels_sent_to_workers':False,'time':time.time()}
    save(HERE/'pre-output-commitment.json',commitment)
    files=['protocol.json','flash-identity.json','run_comparison.py','pre-output-commitment.json']+['inputs/'+p.name for p in sorted((HERE/'inputs').glob('*.png'))]
    manifest={'files':{n:sha(HERE/n) for n in files},'created':time.time(),'private_labels_excluded':True}
    save(HERE/'package-manifest.json',manifest);files.append('package-manifest.json')
    blob=io.BytesIO()
    with zipfile.ZipFile(blob,'w',zipfile.ZIP_DEFLATED) as z:
        for n in files:z.write(HERE/n,n)
    code="""from pathlib import Path
import base64,hashlib,io,json,zipfile
root=Path(REMOTE_ROOT);root.mkdir(parents=True,exist_ok=False)
data=base64.b64decode(DATA)
with zipfile.ZipFile(io.BytesIO(data)) as z:
 for n in z.namelist():
  p=root/n
  assert p.resolve().is_relative_to(root.resolve())
  p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(z.read(n))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((root/'package-manifest.json').read_bytes())
assert all(sha(root/n)==h for n,h in manifest['files'].items())
script=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/binary_gate_compare_20261112.py')
with script.open('xb') as f:f.write((root/'run_comparison.py').read_bytes())
assert sha(script)==manifest['files']['run_comparison.py']
print(json.dumps({'root':str(root),'script':str(script),'script_sha256':sha(script),'manifest_sha256':sha(root/'package-manifest.json'),'files':len(manifest['files']),'model_calls':0,'GPU_allocations':0}))
""".replace('REMOTE_ROOT',repr(REMOTE)).replace('DATA',repr(base64.b64encode(blob.getvalue()).decode()))
    out,d=remote(code,'stage',timeout=55);save(HERE/'staging-receipt.json',{'value':json.loads(out),'evidence':str(d)});print(out)

def submit():
    staged=json.loads((HERE/'staging-receipt.json').read_bytes())['value']
    code=(HERE/'inspect_remote.py').read_text(encoding='utf8').replace('print(json.dumps(out,ensure_ascii=False))','')
    code+='\n'+"""
assert out['uid']==1033 and not out['compute'].strip()
root=B/'binary-gate-comparison-20261112'
assert root.is_dir() and not (root/'launch.json').exists() and not (root/'terminal.json').exists()
script=Path(SCRIPT);assert sha(script)==SCRIPT_SHA
command=B/'resource-attempt-20261106-01/commands/binary-gate-comparison-20261112.json'
with command.open('x',encoding='utf8') as f:json.dump({'action':'launch','argv':['/opt/whz/conda-envs/webmall-vlm/bin/python',str(script)],'script_sha256':SCRIPT_SHA,'max_calls':54,'old_queues':False,'time':time.time()},f,indent=2)
print(json.dumps({'command':str(command),'command_sha256':sha(command),'submitted_once':True,'time':time.time()}))
""".replace('SCRIPT_SHA',repr(staged['script_sha256'])).replace('SCRIPT',repr(staged['script']))
    out,d=remote(code,'submit');save(HERE/'submission-receipt.json',{'value':json.loads(out),'evidence':str(d)});print(out)

def audit():
    source=(HERE/'audit_remote.py').read_text(encoding='utf8')
    code="""import base64,json,os,subprocess
from pathlib import Path
root=Path(REMOTE_ROOT)
assert json.loads((root/'terminal.json').read_bytes())['status']=='completed'
launch=json.loads((root/'launch.json').read_bytes())
exitfile=Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01')/('child-'+str(launch['pid'])+'-exit.json')
assert exitfile.is_file() and json.loads(exitfile.read_bytes())['exit_code']==0, 'Wait for verified launcher exit before postexit audit'
assert (root/'terminal-seal.json').is_file()
assert not list(root.glob('independent-audit-*/audit.json')), 'Completed audit already exists; collect it instead of rerunning'
source=base64.b64decode(SOURCE).decode()
env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}
r=subprocess.run(['/home/researcher/jev-defense-local-20261102/env-neohorse/bin/python','-B','-'],input=source,text=True,encoding='utf8',capture_output=True,env=env)
print(r.stdout,end='')
if r.returncode:
 import sys
 print(r.stderr,file=sys.stderr,end='');raise SystemExit(r.returncode)
""".replace('REMOTE_ROOT',repr(REMOTE)).replace('SOURCE',repr(base64.b64encode(source.encode()).decode()))
    out,d=remote(code,'independent-audit',timeout=55)
    save(HERE/'audit-receipt.json',{'value':json.loads(out),'evidence':str(d)});print(out)

def collect():
    code="""from pathlib import Path
import base64,hashlib,io,json,zipfile
root=Path(REMOTE_ROOT)
assert (root/'terminal.json').exists() and list(root.glob('independent-audit-*/audit.json'))
files=[p for p in root.rglob('*') if p.is_file() and p.suffix!='.pt' and not p.is_relative_to(root/'inputs')]
blob=io.BytesIO()
with zipfile.ZipFile(blob,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,str(p.relative_to(root)))
print(json.dumps({'zip_base64':base64.b64encode(blob.getvalue()).decode(),'zip_sha256':hashlib.sha256(blob.getvalue()).hexdigest(),'files':len(files)}))
""".replace('REMOTE_ROOT',repr(REMOTE))
    out,d=remote(code,'collect',timeout=55);v=json.loads(out);data=base64.b64decode(v['zip_base64']);assert hashlib.sha256(data).hexdigest()==v['zip_sha256']
    dest=HERE/('collected-'+str(time.time_ns()));dest.mkdir()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for n in z.namelist():
            p=dest/n;assert p.resolve().is_relative_to(dest.resolve());p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('xb') as f:f.write(z.read(n))
    full=json.loads((dest/'terminal-seal.json').read_bytes());verified=0
    for n,h in full.items():
        p=dest/n
        if p.is_file():assert sha(p)==h;verified+=1
    save(dest/'local-collection-audit.json',{'collected_files':v['files'],'verified_original_terminal_file_hashes':verified,'actual_forward_tensor_files_kept_remote':54,'zip_sha256':v['zip_sha256'],'independent_runtime_tensor_audit':'see independent-audit audit.json; full tensor bytes reloaded on CPU remotely','time':time.time()})
    save(HERE/'collection-receipt.json',{'path':str(dest),'remote_evidence':str(d),'files':v['files'],'verified_original_terminal_file_hashes':verified});print(json.dumps({'path':str(dest),'files':v['files'],'verified_original_terminal_file_hashes':verified}))

if __name__=='__main__':
    action = sys.argv[1]
    if action=='inspect':
        out,d=remote((HERE/'inspect_remote.py').read_text(encoding='utf8'), 'inspect')
        print(out); print('Evidence: '+str(d))
    elif action=='stage':stage()
    elif action=='submit':submit()
    elif action=='progress':
        out,d=remote((HERE/'progress_remote.py').read_text(encoding='utf8'),'progress')
        v=json.loads(out)
        print(json.dumps({'time':v['time'],'models':{n:{'started':x['started'],'complete':x['completed_requests'],'terminal_status':x.get('terminal.json',{}).get('status'),'actual':x.get('actual_process'),'loaded':bool(x.get('loaded.json')),'failure_count':len(x['failures'])} for n,x in v['models'].items()},'compute':v['compute'],'terminal_status':v.get('terminal.json',{}).get('status'),'launcher_failure':v.get('launcher-failure.json'),'evidence':str(d)},ensure_ascii=False))
    elif action=='audit':audit()
    elif action=='collect':collect()
    else: raise ValueError(action)
