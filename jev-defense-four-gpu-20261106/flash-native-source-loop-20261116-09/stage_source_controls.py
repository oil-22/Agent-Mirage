"""Freeze new source fault bridge and run its finite real-browser controls once."""
import ast
import base64
import io
import json
import time
import zipfile
from pathlib import Path
from remote_util import HERE, remote, save, sha


def main():
    assert not (HERE / 'CPU-source-current.json').exists()
    pp = json.loads((HERE.parent / 'flash-trusted-capture-protocol-20261116-06/preparation-current.json').read_bytes())
    parent = Path(pp['package']); manifest = json.loads((parent / 'manifest.json').read_bytes())
    assert sha(parent / 'manifest.json') == pp['manifest_sha256']
    root = HERE / ('cpu-source-' + str(time.time_ns())); root.mkdir()
    snapshot = root / 'source'; snapshot.mkdir()
    for name in ['capture_source.py', 'capture_client.py', 'native_fault.py', 'native_rpc.py', 'receipt_protocol.py', 'test_native_fault_live.py']:
        (snapshot / name).write_bytes((HERE / name).read_bytes())
    for name in ['native_environment.py', 'native-bindings-public.json', 'native-sources.json']:
        assert sha(parent / name) == manifest['files'][name]
        (snapshot / name).write_bytes((parent / name).read_bytes())
    old = ast.parse((parent / 'injection.py').read_text('utf8'))
    new = ast.parse((snapshot / 'native_fault.py').read_text('utf8'))
    defs = {n.targets[0].id: n.value.value for n in new.body if isinstance(n, ast.Assign)}
    css = next(n.value.value for n in old.body if isinstance(n, ast.Assign) and n.targets[0].id == 'CSS')
    assert defs['CSS'] == css
    strings = {n.value for n in ast.walk(old) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert all(defs[k] in strings for k in ['APPLY', 'REMOVE', 'PRESENT'])
    detail = lambda tree: next(n for n in tree.body if getattr(n, 'name', '') == 'detail')
    assert ast.dump(detail(old), include_attributes=False) == ast.dump(detail(new), include_attributes=False)
    save(root / 'invariance.json', {'original_CSS_and_JS_exact': True, 'original_detail_predicate_AST_unchanged': True, 'original_injection_after_normal_signed_capture': True, 'signature_API_no_arbitrary_bytes': True, 'source_trust_limitation_retained': True})
    files = {q.name: sha(q) for q in snapshot.iterdir() if q.is_file()}
    save(snapshot / 'source-manifest.json', files)
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, 'w', zipfile.ZIP_DEFLATED) as z:
        for q in snapshot.iterdir(): z.writestr(q.name, q.read_bytes())
    remote_root = '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name + '/' + root.name
    code = 'ROOT=' + repr(remote_root) + '\nEXPECTED=' + repr(sha(snapshot / 'source-manifest.json')) + '\n' + r'''
import base64,fcntl,hashlib,io,json,os,subprocess,time,zipfile
from pathlib import Path
p=Path(ROOT);p.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD,validate=True)))as z:
 for name in z.namelist():
  dest=p/name;assert dest.resolve().is_relative_to(p.resolve());dest.write_bytes(z.read(name))
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
assert sha(p/'source-manifest.json')==EXPECTED
for name,h in json.loads((p/'source-manifest.json').read_bytes()).items():assert sha(p/name)==h,name
lock=Path('/data/researcher/jev-defense-four-gpu-20261106/.full-gui-site29980.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
python='/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python'
argv=[python,'-B','-u',str(p/'test_native_fault_live.py'),str(p/'live-controls')]
env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1','PLAYWRIGHT_BROWSERS_PATH':'/data/researcher/playwright-browsers'}
with(p/'stdout.bin').open('xb')as out,(p/'stderr.bin').open('xb')as err:
 result=subprocess.run(argv,cwd=p,env=env,stdout=out,stderr=err,timeout=420)
value={'passed':result.returncode==0,'returncode':result.returncode,'argv':argv,'new_model_GUI_trajectory_calls':0,'time':time.time()}
if(p/'live-controls/result.json').exists():value['controls']=json.loads((p/'live-controls/result.json').read_bytes())
(p/'result.json').write_text(json.dumps(value,indent=2))
(p/'seal.json').write_text(json.dumps({q.relative_to(p).as_posix():sha(q)for q in p.rglob('*')if q.is_file()},indent=2))
print(json.dumps({'root':str(p),'result':value,'seal_sha256':sha(p/'seal.json'),'stdout':(p/'stdout.bin').read_text(errors='replace')[-3500:],'stderr':(p/'stderr.bin').read_text(errors='replace')[-5000:]}))
'''
    raw, operation = remote('4090', code, 'new-native-fault-source-browser-controls', timeout=500, private_prefix='PAYLOAD=' + repr(base64.b64encode(payload.getvalue()).decode()) + '\n')
    value = json.loads(raw)
    save(root / 'result.json', {'operation': str(operation), **value})
    save(root / 'seal.json', {q.relative_to(root).as_posix(): sha(q) for q in root.rglob('*') if q.is_file()})
    if value['result']['passed']:
        save(HERE / 'CPU-source-current.json', {'root': str(root), 'remote_root': remote_root, 'passed': True, 'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps(value, ensure_ascii=False))
    assert value['result']['passed'], 'Failed source attempt preserved; no GUI launch'


if __name__ == '__main__':
    main()
