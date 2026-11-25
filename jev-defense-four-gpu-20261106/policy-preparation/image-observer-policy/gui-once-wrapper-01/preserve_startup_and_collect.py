"""Preserve exited startup failure remotely; collect only explicit public evidence."""
import base64,hashlib,json,subprocess,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
code=r'''import base64,hashlib,json,os,shutil,time
from pathlib import Path
base=Path('/data/researcher/jev-defense-four-gpu-20261106')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    with p.open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2)
for name in ('gui-outer-background-01/actualprocess.json','gui-outer-control-01/runner-process.json'):
    old=json.loads((base/name).read_bytes());old=old.get('identity',old);proc=Path('/proc')/str(old['pid'])
    if proc.exists():
        stat=(proc/'stat').read_text().rsplit(')',1)[1].split()
        assert stat[19]!=old['start_ticks']or proc.stat().st_uid!=old['uid'],'Original process still alive; refuse postexit preservation'
dest=base/'gui-startup-failure-preservation-01';dest.mkdir(exist_ok=False)
folders=['gui-preparation-01','gui-once-wrapper-01','gui-background-helper-01',
    'gui-final-readiness-01','gui-batch-image-observer-01','gui-outer-control-01','gui-outer-background-01']
before={}
for name in folders:
    source=base/name
    before[name]={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*')if p.is_file()}
    shutil.copytree(source,dest/name)
    assert before[name]=={p.relative_to(dest/name).as_posix():sha(p)for p in(dest/name).rglob('*')if p.is_file()}
    assert before[name]=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*')if p.is_file()}
claim=base/'image-observer-four-run-01.once-only.json';shutil.copyfile(claim,dest/claim.name)
write(dest/'original-source-maps.json',before)
write(dest/'preservation-seal.PRIVATE.json',{p.relative_to(dest).as_posix():sha(p)for p in dest.rglob('*')if p.is_file()})
summary={'status':'preserved','time':time.time(),'root':str(dest),'old_files_not_modified':True,
    'all_original_sources_batch_control_background_copied':True,
    'remote_only_private_config_auth_preserved':True,'private_task_auth_token_exported':False,
    'source_maps_sha256':sha(dest/'original-source-maps.json'),
    'preservation_seal_sha256':sha(dest/'preservation-seal.PRIVATE.json'),
    'new_model_GUI_or_scorer_calls':0}
write(dest/'preservation-public.json',summary)
public={}
selected={
'gui-final-readiness-01':[p.name for p in(base/'gui-final-readiness-01').iterdir()if p.is_file()],
'ownership-transport-proof-1793979127450599500':[p.name for p in(base/'ownership-transport-proof-1793979127450599500').iterdir()if p.is_file()],
'gui-outer-background-01':['once-only-launch.json','actualprocess.json','wrapper.log'],
'gui-outer-control-01':['fresh-health.json','runner-process.json','wrapper-process.json','exact-command.json',
    'finalization.json','postexit-sha256.json','batch-postexit-sha256.json','runner.log'],
'gui-batch-image-observer-01':['uncaught-failure.json','status.json'],
'gui-startup-failure-preservation-01':['preservation-public.json','original-source-maps.json']}
for folder,names in selected.items():
    for name in names:
        path=base/folder/name
        assert 'PRIVATE'not in name and'token'not in name.lower()and name not in('.auth','official_config.json')
        assert path.is_file()and not path.is_symlink()
        raw=path.read_bytes();public[folder+'/'+name]={'sha256':sha(path),'data':base64.b64encode(raw).decode()}
print(json.dumps({'public_files':public,'summary':summary}))
'''
r=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','4090',
    '/data/researcher/venvs/qwen35-9b-full-20261019/bin/python -B -'],input=code,capture_output=True,text=True,timeout=120)
out=ROOT/('gui-startup-public-preservation-'+str(time.time_ns()));out.mkdir(exist_ok=False)
(out/'stderr.txt').write_text(r.stderr,encoding='utf8')
if r.returncode:
    (out/'failure.stdout.txt').write_text(r.stdout,encoding='utf8');raise SystemExit(r.returncode)
data=json.loads(r.stdout)
for name,item in data['public_files'].items():
    target=out/name;assert target.resolve().is_relative_to(out.resolve());target.parent.mkdir(parents=True,exist_ok=True)
    raw=base64.b64decode(item['data']);assert hashlib.sha256(raw).hexdigest()==item['sha256'];target.write_bytes(raw)
summary={**data['summary'],'local_root':str(out),'files_verified':len(data['public_files']),
    'local_sha256':{name:item['sha256']for name,item in data['public_files'].items()},'originals_preserved_verbatim':True}
(out/'collection-receipt.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
(out/'seal.json').write_text(json.dumps({p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
    for p in out.rglob('*')if p.is_file()},indent=2),encoding='utf8')
print(json.dumps({'local':str(out),'remote_preservation':data['summary']['root'],
    'files_verified':len(data['public_files']),'private_task_auth_token_exported':False,'model_GUI_calls':0}))
