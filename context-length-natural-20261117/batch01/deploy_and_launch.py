"""Launch the frozen natural-history batch on the same four owned GPUs."""
from pathlib import Path
import json,subprocess,hashlib

P=Path(__file__).resolve().parent
ROOT='/data/researcher/context-length-natural-20261117/batch01'
SSH=['D:/Git/usr/bin/ssh.exe','-o','BatchMode=yes','-o','ConnectTimeout=10']
MODEL_PY='/opt/whz/conda-envs/webmall-vlm/bin/python'
GUI_PY='/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python'

def remote(host,code,timeout=45):
    r=subprocess.run(SSH+[host,'python3 -'],input='ROOT='+repr(ROOT)+'\n'+code,text=True,capture_output=True,timeout=timeout)
    if r.returncode:raise RuntimeError(host+': '+r.stderr[-5000:]+'\n'+r.stdout[-1500:])
    return json.loads(r.stdout)

preflight=r'''
from pathlib import Path
import json,os,socket,subprocess,fcntl,hashlib
p=Path(ROOT);assert not p.exists(), 'Destination already exists; do not overwrite a run'
out={'uid':os.getuid(),'destination_absent':True}
if HOST=='3090':
    assert Path('/data/llms/Qwen3.8-27B/config.json').is_file()
    assert Path('/opt/whz/conda-envs/webmall-vlm/bin/python').is_file()
    rows=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
    selected=[dict(index=int(a),uuid=b.strip(),free_mib=int(c)) for a,b,c in [line.split(',') for line in rows.splitlines()] if int(a) in [4,5,6,7]]
    assert len(selected)==4 and min(r['free_mib'] for r in selected)>23000
    compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True)
    assert not any(r['uuid'] in compute for r in selected)
    sock=socket.socket();sock.bind(('192.0.2.11',19318));sock.close()
    out.update(gpus=selected,port_free=19318)
else:
    assert Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python').is_file()
    lease=Path('/data/researcher/jev-defense-four-gpu-20261106/.full-gui-site29980.lock').open('a')
    fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
    import urllib.request
    with urllib.request.urlopen('http://192.0.2.10:29980',timeout=20) as r:out['site_status']=r.status
    out['site_lease_available']=True
print(json.dumps(out))
'''

if __name__=='__main__':
    receipts={}
    for host in ['3090','4090']:
        receipts[host]=remote(host,'HOST='+repr(host)+'\n'+preflight)
    (P/'preflight.json').write_text(json.dumps(receipts,indent=2),encoding='utf8')
    files=['config.json','model_service.py','run_natural.py','actor-template.json','native_environment.py','native-bindings-public.json','native-parser-source.py','tasks.json','service.token','prospective-plan.json','source-manifest.json','README.md']
    for host in ['3090','4090']:
        remote(host,"from pathlib import Path\nimport json\np=Path(ROOT);p.mkdir(parents=True,exist_ok=False)\nprint(json.dumps({'created':str(p)}))")
        r=subprocess.run(['D:/Git/usr/bin/scp.exe','-q','-o','BatchMode=yes']+[str(P/name) for name in files]+[host+':'+ROOT+'/'],text=True,capture_output=True,timeout=90)
        if r.returncode:raise RuntimeError(r.stderr[-3000:])
        check=r'''
from pathlib import Path
import json,hashlib,ast
p=Path(ROOT);(p/'service.token').chmod(0o600)
manifest=json.loads((p/'source-manifest.json').read_text())
for name,digest in manifest.items():assert hashlib.sha256((p/name).read_bytes()).hexdigest()==digest,name
for name in ['run_natural.py','model_service.py']:ast.parse((p/name).read_text(),filename=name)
print(json.dumps({'source_hashes_verified':True,'syntax_checked':True}))
'''
        receipts[host]['deployment']=remote(host,check)
    # Importing the GUI module checks the actual native parser binding without creating a browser.
    verify_gui=r'''
import subprocess,json
r=subprocess.run([PY,'-c',"import run_natural as r; assert r.sha(r.Path(r.native.__file__).read_bytes())==r.sha((r.P/'native-parser-source.py').read_bytes()); print('NATIVE_IMPORT_OK')"],cwd=ROOT,text=True,capture_output=True,timeout=75)
assert r.returncode==0,(r.stdout[-1000:],r.stderr[-4000:])
assert 'NATIVE_IMPORT_OK' in r.stdout
print(json.dumps({'native_import_verified':True}))
'''
    receipts['4090']['native_import']=remote('4090','PY='+repr(GUI_PY)+'\n'+verify_gui,timeout=90)
    launch=r'''
from pathlib import Path
import subprocess,os,json,time
p=Path(ROOT);env=os.environ.copy();env.update(PYTHONUNBUFFERED='1',TOKENIZERS_PARALLELISM='false')
if KIND=='model':
    env.update(CUDA_VISIBLE_DEVICES='4,5,6,7',PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
    script='model_service.py'
else:script='run_natural.py'
with (p/(KIND+'.log')).open('ab',buffering=0) as log:
    child=subprocess.Popen([PY,'-u',str(p/script)],cwd=p,env=env,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
d={'pid':child.pid,'time':time.time(),'kind':KIND,'script':script,'task_ids':[3,58,94,112,131],'physical_gpus':[4,5,6,7] if KIND=='model' else [],'batch':ROOT}
(p/(KIND+'-launch-receipt.json')).write_text(json.dumps(d))
print(json.dumps(d))
'''
    for host,kind,py in [('3090','model',MODEL_PY),('4090','gui',GUI_PY)]:
        rec=remote(host,'KIND='+repr(kind)+'\nPY='+repr(py)+'\n'+launch)
        (P/(kind+'-launch-receipt.json')).write_text(json.dumps(rec,indent=2),encoding='utf8')
        print(json.dumps(rec),flush=True)
    (P/'deployment-verification.json').write_text(json.dumps(receipts,indent=2),encoding='utf8')
