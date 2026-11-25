"""Deploy a frozen 100-task panel; the existing experiment remains running."""
from pathlib import Path
import json,subprocess,tarfile,hashlib
P=Path(__file__).resolve().parent
ROOT='/data/researcher/context-length-natural-20261117/scale100-resume01'
SSH=['D:/Git/usr/bin/ssh.exe','-o','BatchMode=yes','-o','ConnectTimeout=10']
def remote(host,code,timeout=60):
    r=subprocess.run(SSH+[host,'python3 -'],input='ROOT='+repr(ROOT)+'\n'+code,text=True,capture_output=True,timeout=timeout)
    if r.returncode:raise RuntimeError(host+': '+r.stderr[-3000:]+r.stdout[-1000:])
    return json.loads(r.stdout)
if __name__=='__main__':
    names=['config.json','model_service.py','run_scale100.py','actor-template.json','native_environment.py','native-parser-source.py','tasks.json','native-bindings-public.json','prospective-plan.json','reference-image-manifest.json','README.md','service.token']
    files=[P/n for n in names]+list((P/'reference-images').iterdir())+list((P/'PRIVATE-evaluator-configs').iterdir())
    manifest={str(f.relative_to(P)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in files if f.name!='service.token'}
    (P/'deployment-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    files.append(P/'deployment-manifest.json')
    package=P/'runtime-package.tar.gz'
    with tarfile.open(package,'w:gz') as t:
        for f in files:t.add(f,arcname=str(f.relative_to(P)).replace('\\','/'),recursive=False)
    for host in ['4090','3090']:
        remote(host,"from pathlib import Path\nimport json\np=Path(ROOT);p.mkdir(parents=True,exist_ok=False)\nprint(json.dumps({'created':str(p)}))")
        r=subprocess.run(['D:/Git/usr/bin/scp.exe','-q','-o','BatchMode=yes',str(package),host+':'+ROOT+'/runtime-package.tar.gz'],text=True,capture_output=True,timeout=100)
        assert r.returncode==0,r.stderr
        code=r'''
from pathlib import Path
import json,tarfile,hashlib,os
p=Path(ROOT)
with tarfile.open(p/'runtime-package.tar.gz') as t:
    for m in t.getmembers():
        target=(p/m.name).resolve();assert p.resolve() in target.parents and m.isfile(),m.name
    t.extractall(p)
manifest=json.loads((p/'deployment-manifest.json').read_text())
for name,digest in manifest.items():assert hashlib.sha256((p/name).read_bytes()).hexdigest()==digest,name
(p/'service.token').chmod(0o600)
(p/'PRIVATE-evaluator-configs').chmod(0o700)
for f in (p/'PRIVATE-evaluator-configs').iterdir():f.chmod(0o600)
print(json.dumps({'hashes_verified':len(manifest),'task_count':len(json.loads((p/'tasks.json').read_text()))}))
'''
        print(host,remote(host,code),flush=True)
    # Exercise reference preservation using the actual new input builder, without model generation or browser execution.
    code=r'''
import subprocess,json
test="""import run_scale100 as r
from types import SimpleNamespace
import json
tasks=json.loads((r.P/'tasks.json').read_text())
t=next(t for t in tasks if t['reference_image_paths'])
raw=(r.P/t['reference_image_paths'][0]).read_bytes()
env=SimpleNamespace(context=SimpleNamespace(pages=[1]))
b=r.body_for([],t,env,'',raw)
assert len(b['messages'][1]['content'])==1+len(t['reference_image_paths'])
drop=r.replace_current(b,None)
assert drop['messages'][1]==b['messages'][1]
assert not any(x['type']=='image_url' for x in drop['messages'][-1]['content'])
h=b['messages'][1:]+[dict(role='assistant',content='test-only, never generated or executed')]
n=r.body_for(h,t,env,'',raw)
assert n['messages'][1]==b['messages'][1]
assert len(n['messages'])==len(b['messages'])+2
assert r.sha(r.Path(r.native.__file__).read_bytes())==r.sha((r.P/'native-parser-source.py').read_bytes())
print('REFERENCE_AND_NATIVE_CHECK_OK')
"""
r=subprocess.run(['/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python','-c',test],cwd=ROOT,text=True,capture_output=True,timeout=70)
assert r.returncode==0,(r.stdout[-1000:],r.stderr[-2500:])
print(json.dumps({'reference_preservation_checked':True,'native_binding_checked':True,'actor_calls':0,'environment_actions':0}))
'''
    result=remote('4090',code,timeout=90)
    (P/'deployment-verification.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(result,flush=True)
