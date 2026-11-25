"""Preserve all exited retry01 GUI evidence remotely; export public terminals only."""
import base64,hashlib,json,subprocess,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
code=r'''import base64,hashlib,json,os,shutil,time
from pathlib import Path
base=Path('/data/researcher/jev-defense-four-gpu-20261106')
runtime=Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    with p.open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2)
for name in('gui-outer-background-retry01/actualprocess.json','gui-outer-control-retry01/runner-process.json'):
    old=json.loads((base/name).read_bytes());old=old.get('identity',old);proc=Path('/proc')/str(old['pid'])
    if proc.exists():
        stat=(proc/'stat').read_text().rsplit(')',1)[1].split()
        assert stat[0]in('Z','X')or stat[19]!=old['start_ticks']or proc.stat().st_uid!=old['uid'],'Original GUI process remains live'
batch=base/'gui-batch-image-observer-retry01';control=base/'gui-outer-control-retry01'
for manifest,root in((control/'postexit-sha256.json',control),(control/'batch-postexit-sha256.json',batch)):
    mapping=json.loads(manifest.read_bytes())
    for name,digest in mapping.items():
        path=(root/name).resolve();assert path.is_relative_to(root.resolve())and sha(path)==digest
    actual={p.relative_to(root).as_posix()for p in root.rglob('*')if p.is_file()and p.resolve()!=manifest.resolve()}
    assert actual==set(mapping)
assert json.loads((batch/'status.json').read_bytes())['phase']=='technical_failure'
folders=['gui-preparation-01','gui-once-wrapper-retry01','gui-final-readiness-retry01',
    'gui-batch-image-observer-retry01','gui-outer-control-retry01','gui-outer-background-retry01',
    'native-env-retry-preflight-01','ownership-transport-proof-1793979817792141700']
sources={name:base/name for name in folders}
sources['native-runtime-source']=runtime/'native'
sources['upstream-browser-env-source']=runtime/'upstream/browser_env'
sources['upstream-evaluator-source']=runtime/'upstream/evaluation_harness'
size=sum(p.stat().st_size for root in sources.values()for p in root.rglob('*')if p.is_file())
assert shutil.disk_usage(base).free>size+512*1024**2,'Insufficient space; preserve originals without retry'
dest=base/('gui-runtime-failure-preservation-'+str(time.time_ns()));dest.mkdir(mode=0o700)
maps={}
for name,source in sources.items():
    assert not any(p.is_symlink()for p in source.rglob('*')),'Do not follow source symlinks'
    before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*')if p.is_file()}
    shutil.copytree(source,dest/name)
    assert before=={p.relative_to(dest/name).as_posix():sha(p)for p in(dest/name).rglob('*')if p.is_file()}
    assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*')if p.is_file()}
    maps[name]=before
claim=base/'image-observer-four-run-01.once-only-retry01.json';shutil.copyfile(claim,dest/claim.name)
write(dest/'original-source-maps.json',maps)
write(dest/'preservation-seal.PRIVATE.json',{p.relative_to(dest).as_posix():sha(p)for p in dest.rglob('*')if p.is_file()})
attempts=list(batch.glob('runs/*/attempt-*'));assert len(attempts)==1
terminal=attempts[0]/'technical-failure.json';result=json.loads(terminal.read_bytes())
summary={'status':'preserved_complete_gui_technical_failure','time':time.time(),'preservation_root':str(dest),
    'original_batch_root':str(batch),'original_files_unchanged':True,'original_postexit_manifests_verified':True,
    'copied_files':sum(len(m)for m in maps.values())+1,'copied_bytes':size,
    'preservation_seal_sha256':sha(dest/'preservation-seal.PRIVATE.json'),
    'original_source_maps_sha256':sha(dest/'original-source-maps.json'),
    'terminal_sha256':sha(terminal),'terminal_kind':'technical-failure.json',
    'outcome':result['outcome'],'technical_status':result['technical_status'],
    'decisions':result['decisions'],'environment_actions':result['environment_actions'],
    'actor_calls':result['actor_calls'],'verifier_calls':result['verifier_calls'],'auxiliary_calls':result['auxiliary_calls'],
    'observer_technical_failures':result['observer_technical_failures'],
    'official_reward_is_not_semantic_label':True,'semantic_Mirage_labels_inferred':False,
    'images_fulllegalhistory_private_trace_config_auth_preserved_remote_only':True,
    'PRIVATE_task_auth_token_exported':False,'new_model_GUI_health_or_scorer_calls':0,
    'site_reset_or_run_restart':False}
write(dest/'preservation-public.json',summary)
selected={
    'preservation/preservation-public.json':dest/'preservation-public.json',
    'preservation/original-source-maps.json':dest/'original-source-maps.json',
    'terminal/technical-failure.json':terminal,
    'terminal/status.json':batch/'status.json'}
for name in('finalization.json','postexit-sha256.json','batch-postexit-sha256.json','runner.log',
    'fresh-health.json','native-environment.json','exact-command.json','runner-process.json','wrapper-process.json'):
    selected['control/'+name]=control/name
for name in('once-only-launch.json','actualprocess.json','wrapper.log'):
    selected['background/'+name]=base/'gui-outer-background-retry01'/name
public={}
for name,path in selected.items():
    assert 'PRIVATE'not in name and path.is_file()
    raw=path.read_bytes();public[name]={'data':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
print(json.dumps({'public_files':public,'summary':summary}))
'''
run=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','4090',
    '/data/researcher/venvs/qwen35-9b-full-20261019/bin/python -B -'],input=code,capture_output=True,text=True,timeout=240)
out=ROOT/('gui-runtime-failure-public-'+str(time.time_ns()));out.mkdir(exist_ok=False)
(out/'stderr.txt').write_text(run.stderr,encoding='utf8')
if run.returncode:
    (out/'failure.stdout.txt').write_text(run.stdout,encoding='utf8');raise SystemExit(run.returncode)
data=json.loads(run.stdout)
for name,item in data['public_files'].items():
    target=out/name;assert target.resolve().is_relative_to(out.resolve());target.parent.mkdir(parents=True,exist_ok=True)
    raw=base64.b64decode(item['data']);assert hashlib.sha256(raw).hexdigest()==item['sha256'];target.write_bytes(raw)
(out/'collection-receipt.json').write_text(json.dumps({'local':str(out),'remote':data['summary']['preservation_root'],
    'files_verified':len(data['public_files']),'sha256':{name:item['sha256']for name,item in data['public_files'].items()},
    'PRIVATE_task_auth_token_exported':False,'new_model_GUI_health_or_scorer_calls':0},indent=2),encoding='utf8')
(out/'seal.json').write_text(json.dumps({p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
    for p in out.rglob('*')if p.is_file()},indent=2),encoding='utf8')
print(json.dumps({'local':str(out),'files_verified':len(data['public_files']),'summary':data['summary']}))
