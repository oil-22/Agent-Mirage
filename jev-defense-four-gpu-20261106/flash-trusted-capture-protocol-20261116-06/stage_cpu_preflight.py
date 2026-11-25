"""Freeze new source bytes, then run new CPU/live controls once in isolation."""
import base64
import io
import json
import sys
import time
import zipfile
from pathlib import Path
from remote_util import HERE, remote, save, sha


def main():
    assert not (HERE / 'CPU-source-current.json').exists()
    root = HERE / ('cpu-preflight-' + str(time.time_ns()))
    root.mkdir()
    (root / 'stage-source.py').write_bytes(Path(__file__).read_bytes())
    snapshot = root / 'source'
    snapshot.mkdir()
    prior = json.loads((HERE.parent / 'flash-four-injection-defense-20261115-04/preparation-current.json').read_bytes())
    package = Path(prior['package'])
    names = ['receipt_protocol.py', 'native_rpc.py', 'capture_source.py', 'capture_client.py',
             'test_receipt_protocol.py', 'test_capture_source_live.py', 'audit_completed_fixture.py', 'user-authorization.json']
    for name in names:
        (snapshot / name).write_bytes((HERE / name).read_bytes())
    for name in ['native_environment.py', 'native-bindings-public.json']:
        (snapshot / name).write_bytes((package / name).read_bytes())
    inspected = sorted(HERE.glob('resource-4090-*.json'))[-1]
    sources = json.loads(inspected.read_bytes())['result']['native_sources']
    save(snapshot / 'native-sources.json', {name: row['sha256'] for name, row in sources.items()})
    files = {p.name: sha(p) for p in snapshot.iterdir() if p.is_file()}
    save(snapshot / 'source-manifest.json', files)
    remote_root = '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name + '/cpu-preflight-' + root.name.split('-')[-1]
    save(root / 'staging.json', {'remote_root': remote_root, 'files': files, 'preparation_only': True})
    reuse = Path(sys.argv[1]) if len(sys.argv) == 2 else None
    reused_remote = None
    if reuse is not None:
        old = json.loads((reuse / 'result.json').read_bytes())
        assert old['result']['steps'][0]['name'] == 'unit' and old['result']['steps'][0]['returncode'] == 0
        for name in ['receipt_protocol.py', 'test_receipt_protocol.py']:
            assert sha(reuse / 'source' / name) == sha(snapshot / name), name
        reused_remote = old['result']['steps'][0].get('reused_from', old['root'])
        save(root / 'linked-prior-attempt.json', {'root': str(reuse), 'remote_root': reused_remote,
                                                 'original_seal_sha256': sha(reuse / 'seal.json'),
                                                 'completed_unit_controls_reused_not_reexecuted': True,
                                                 'repair': 'inherit original native browser environment before fixture load; await source exit before log seal',
                                                 'original_sealed_files_unchanged': True})
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in snapshot.iterdir():
            z.writestr(p.name, p.read_bytes())
    fixture_remote = old['root'] if reuse is not None and 'DetachedPage' in old.get('logs', {}).get('live-stderr.bin', '') else None
    code = 'ROOT=' + repr(remote_root) + '\nEXPECTED=' + repr(sha(snapshot / 'source-manifest.json')) + '\nREUSE_UNIT=' + repr(reused_remote) + '\nREUSE_FIXTURE=' + repr(fixture_remote) + '\n' + r'''
import base64,fcntl,hashlib,io,json,os,subprocess,sys,time,zipfile
from pathlib import Path
p=Path(ROOT);p.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD,validate=True)))as z:
 for name in z.namelist():
  target=p/name;assert target.resolve().is_relative_to(p.resolve())
  with target.open('xb')as f:f.write(z.read(name))
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
assert sha(p/'source-manifest.json')==EXPECTED
for name,h in json.loads((p/'source-manifest.json').read_bytes()).items():assert sha(p/name)==h,name
python='/data/researcher/jev-defense-validation-20261103/runtime-stage-01/env/bin/python'
env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1'}
steps=[]
fixture_args=[]
if REUSE_FIXTURE:
 sys.path.insert(0,str(p))
 from audit_completed_fixture import audit
 fixture_proof=p/'fixture-reuse-proof.json';audit(Path(REUSE_FIXTURE),fixture_proof)
 fixture_args=['--fixture-proof',str(fixture_proof)]
if REUSE_UNIT:
 old=Path(REUSE_UNIT);seals=json.loads((old/'seal.json').read_bytes())
 for name in ['result.json','unit-stderr.bin','receipt_protocol.py','native_rpc.py','test_receipt_protocol.py']:
  assert sha(old/name)==seals[name],name
 assert json.loads((old/'result.json').read_bytes())['steps'][0]['returncode']==0
 assert 'Ran 20 tests' in(old/'unit-stderr.bin').read_text()and'OK'in(old/'unit-stderr.bin').read_text()
 ready=json.loads((old/'live-controls/fixture/trusted-source/ready.json').read_bytes());proc=Path('/proc',str(ready['identity']['pid']))
 if proc.exists():
  s=(proc/'stat').read_text().rsplit(')',1)[1].split();assert s[19]!=ready['identity']['start_ticks']or s[0]in['Z','X']
 steps.append({'name':'unit','returncode':0,'reused_from':str(old),'original_seal_sha256':sha(old/'seal.json'),'not_reexecuted':True})
lock=Path('/data/researcher/jev-defense-four-gpu-20261106/.full-gui-site29980.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
for name,argv in [('unit',[python,'-B','test_receipt_protocol.py']),('live',[python,'-B','test_capture_source_live.py',str(p/'live-controls')]+fixture_args)]:
 if name=='unit'and REUSE_UNIT:continue
 with(p/(name+'-stdout.bin')).open('xb')as out,(p/(name+'-stderr.bin')).open('xb')as err:
  result=subprocess.run(argv,cwd=p,env=env,stdout=out,stderr=err,timeout=420)
 steps.append({'name':name,'argv':argv,'returncode':result.returncode})
 if result.returncode:break
summary={'time':time.time(),'steps':steps,'passed':len(steps)==2 and all(s['returncode']==0 for s in steps),'new_model_calls':0}
if(p/'live-controls/result.json').exists():summary['live_result']=json.loads((p/'live-controls/result.json').read_bytes())
(p/'result.json').write_text(json.dumps(summary,indent=2))
(p/'seal.json').write_text(json.dumps({str(q.relative_to(p)):sha(q)for q in p.rglob('*')if q.is_file()},indent=2))
print(json.dumps({'root':str(p),'result':summary,'seal_sha256':sha(p/'seal.json'),'logs':{name:(p/name).read_text(errors='replace')[-5000:]for name in ['unit-stderr.bin','live-stderr.bin']if(p/name).exists()}}))
'''
    raw, operation = remote('4090', code, 'new-trusted-capture-CPU-and-live-controls', timeout=600,
                            private_prefix='PAYLOAD=' + repr(base64.b64encode(data.getvalue()).decode()) + '\n')
    result = json.loads(raw)
    save(root / 'result.json', {'operation': str(operation), **result})
    save(root / 'seal.json', {str(p.relative_to(root)): sha(p) for p in root.rglob('*') if p.is_file()})
    pointer = {'root': str(root), 'remote_root': remote_root, 'seal_sha256': sha(root / 'seal.json'),
               'passed': result['result']['passed']}
    if pointer['passed']:
        save(HERE / 'CPU-source-current.json', pointer)
    print(json.dumps({**pointer, 'result': result['result'], 'logs': result['logs']}, ensure_ascii=False))
    if not pointer['passed']:
        raise RuntimeError('CPU/live attempt preserved; linked source repair required, no model launch')


if __name__ == '__main__':
    main()
