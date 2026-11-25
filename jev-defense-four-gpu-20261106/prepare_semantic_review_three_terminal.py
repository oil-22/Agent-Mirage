"""Export only public candidate inputs and bring a review-only view locally."""
import base64
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import time

BASE=Path(__file__).resolve().parent
EXPORTER=BASE/'semantic-packet-preparation-01/export_semantic_packets.py'
RELEASE=BASE/'policy-preparation/image-observer-policy/gui-migration-three-linked02/release'
NAMES=['run_image_observer_vwa_validation.py','image_observer.py','observer_launch_contract.py','online_transport.py','defense/core.py','defense/prompts.py']
SSH=[r'D:\Git\usr\bin\ssh.exe','-F',r'C:\Users\researcher\.ssh\config','-o','BatchMode=yes','-o','ConnectTimeout=15','4090','python3','-']

if __name__=='__main__':
    sha=lambda raw:hashlib.sha256(raw).hexdigest()
    assert sha(EXPORTER.read_bytes())=='4961723b6a1dcf2a0ead4948abc3181dff8b9f0c8985d1395707ba8eda2ae283'
    bindings={name:sha((RELEASE/name).read_bytes()) for name in NAMES}
    stamp=str(time.time_ns())
    local=BASE/'semantic-three-terminal-review'/stamp
    local.mkdir(parents=True,exist_ok=False)
    remote='/data/researcher/jev-defense-four-gpu-20261106/semantic-three-terminal-export-'+stamp
    cfg={'root':remote,'exporter':base64.b64encode(EXPORTER.read_bytes()).decode(),'bindings':bindings}
    code=r'''
import base64,hashlib,importlib.util,json,os,pathlib,sys
C=CFG
root=pathlib.Path(C['root']);root.mkdir(mode=0o700,exist_ok=False)
raw=base64.b64decode(C['exporter']);assert hashlib.sha256(raw).hexdigest()=='4961723b6a1dcf2a0ead4948abc3181dff8b9f0c8985d1395707ba8eda2ae283'
(root/'exporter.py').write_bytes(raw)
release=pathlib.Path('/data/researcher/jev-defense-four-gpu-20261106/gui-migration-three-linked02/release')
for name,h in C['bindings'].items():assert hashlib.sha256((release/name).read_bytes()).hexdigest()==h
(root/'release-code-bindings.json').write_text(json.dumps(C['bindings'],indent=2))
spec=importlib.util.spec_from_file_location('new_semantic_exporter',root/'exporter.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
attempt=pathlib.Path('/data/researcher/jev-defense-four-gpu-20261106/gui-batch-image-observer-three-01/runs/image-observer-v1--classifieds_112--clean--joint--observer/attempt-1793987248242098761')
terminal=attempt/'technical-failure.json';assert hashlib.sha256(terminal.read_bytes()).hexdigest()=='66d18d91d05e635d58363a54b9a26aa78bcfde06bcd6edeb66f4c86b1e52f01a'
result=module.export_attempt(attempt,root/'packets',C['bindings'])
assert result['complete_candidates']==24
review=root/'packets/review'
mapping={str(p.relative_to(review)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(review.rglob('*'))if p.is_file()}
(root/'review-only-seal.json').write_text(json.dumps(mapping,indent=2))
print(json.dumps({'remote':str(root),'complete_candidates':result['complete_candidates'],'review_only_files':len(mapping),'review_only_seal_sha256':hashlib.sha256((root/'review-only-seal.json').read_bytes()).hexdigest(),'model_GUI_calls':0}))
'''
    code='CFG='+repr(cfg)+'\n'+code
    (local/'export-invocation.py').write_text(code,encoding='utf8')
    r=subprocess.run(SSH,input=code.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180)
    (local/'export.stdout.txt').write_bytes(r.stdout);(local/'export.stderr.txt').write_bytes(r.stderr)
    if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
    result=json.loads(r.stdout.decode().splitlines()[-1]);print(json.dumps(result),flush=True)
    # The reviewer gets only review/ and its manifest; provenance stays remote.
    code2=r'''
import io,pathlib,sys,tarfile
root=pathlib.Path(REMOTE)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz')as archive:
 archive.add(root/'packets/review',arcname='review')
 archive.add(root/'review-only-seal.json',arcname='review-only-seal.json')
'''
    r=subprocess.run(SSH,input=('REMOTE='+repr(remote)+'\n'+code2).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180)
    (local/'download.stderr.txt').write_bytes(r.stderr)
    if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
    with tarfile.open(fileobj=io.BytesIO(r.stdout),mode='r:gz')as archive:
        for item in archive.getmembers():
            path=local/item.name
            assert path.resolve().is_relative_to(local.resolve()) and not item.issym() and not item.islnk()
        archive.extractall(local,filter='data')
    mapping=json.loads((local/'review-only-seal.json').read_bytes())
    for name,h in mapping.items():assert sha((local/'review'/name).read_bytes())==h,name
    summary={'remote_export':remote,'local_review':str(local/'review'),'candidate_count':24,
        'review_only_SHA_verified':True,'private_or_provenance_downloaded':False,'execution_join_performed':False,
        'model_GUI_calls':0,'review_only_seal_sha256':sha((local/'review-only-seal.json').read_bytes())}
    (local/'transfer.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
    print(json.dumps(summary))
