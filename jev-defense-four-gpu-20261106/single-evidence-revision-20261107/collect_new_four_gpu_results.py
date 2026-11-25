"""Postexit read-only full collection/audit of the new four-image GPU terminal."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'gpu-four-terminal-collection-01'
REMOTE='/home/researcher/jev-defense-four-gpu-20261106/single-evidence-revision-20261107/gpu-four-first-attempts-01'
SSH=['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','-o','BatchMode=yes','-o','ConnectTimeout=15','3090']

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        while True:
            raw=stream.read(16*1024*1024)
            if not raw:break
            h.update(raw)
    return h.hexdigest()

def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')
def write(path,value):
    with path.open('x',encoding='utf-8')as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')

OUT.mkdir(exist_ok=False)
code='''import hashlib,json,pathlib,time
root=pathlib.Path('''+repr(REMOTE)+''')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as stream:
  while True:
   raw=stream.read(16*1024*1024)
   if not raw:break
   h.update(raw)
 return h.hexdigest()
manifest=json.loads((root/'terminal-manifest.json').read_bytes())
assert all(sha(root/name)==h for name,h in manifest.items())
exit_record=json.loads((root/'exit.json').read_bytes())
actual_processes={}
for role in ['launcher_identity','worker_identity']:
 expected=exit_record.get(role)
 if expected is None:continue
 p=pathlib.Path('/proc')/str(expected['pid'])
 if p.exists():
  tail=(p/'stat').read_text().rsplit(')',1)[1].split()
  actual={'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(b'\\0',b' ').decode().strip(),'start_ticks':tail[19],'state':tail[0]}
  actual_processes[role]=actual
  assert not(all(str(actual[k])==str(expected[k])for k in ['uid','command','start_ticks'])and actual['state']not in ['Z','X'])
 else:actual_processes[role]=None
print(json.dumps({'status':'postexit_remote_terminal_manifest_all_files_verified','files':len(manifest),
 'terminal_manifest_sha256':sha(root/'terminal-manifest.json'),'exit':exit_record,
 'actual_original_processes':actual_processes,'read_only':True,'new_model_GUI_calls':0,'time_unix':time.time()}))
'''
(OUT/'remote-postexit-audit.py').write_text(code,encoding='utf-8')
audit=subprocess.run(SSH+['python3','-'],input=code.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
(OUT/'audit.stdout').write_bytes(audit.stdout);(OUT/'audit.stderr').write_bytes(audit.stderr)
if audit.returncode:
    write(OUT/'failure.json',{'stage':'read_only_postexit_audit','returncode':audit.returncode,'new_model_calls':0})
    raise SystemExit(audit.returncode)
report=json.loads(audit.stdout);write(OUT/'remote-audit.json',report)
archive_path=OUT/'original-terminal.tar'
with archive_path.open('xb')as stream:
    result=subprocess.run(SSH+['tar','-C',REMOTE,'-cf','-','.'],stdout=stream,stderr=subprocess.PIPE,timeout=300)
(OUT/'collection.stderr').write_bytes(result.stderr)
if result.returncode:
    write(OUT/'failure.json',{'stage':'read_only_full_collection','returncode':result.returncode,'new_model_calls':0})
    raise SystemExit(result.returncode)
local=OUT/'original';local.mkdir()
with tarfile.open(archive_path,'r:')as archive:
    for member in archive:
        path=local/member.name
        if not path.resolve().is_relative_to(local.resolve()):raise ValueError('Archive path escaped dedicated collection')
        if member.isdir():path.mkdir(parents=True,exist_ok=True)
        elif member.isfile():
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb')as stream:stream.write(archive.extractfile(member).read())
        else:raise ValueError('Unexpected symlink or non-file in immutable experiment terminal')
manifest=json.loads((local/'terminal-manifest.json').read_bytes())
assert sha(local/'terminal-manifest.json')==report['terminal_manifest_sha256']
assert all(sha(local/name)==h for name,h in manifest.items())
chains={}
for name in ['journal.jsonl','worker/journal.jsonl']:
    previous='0'*64;count=0
    for raw in(local/name).read_bytes().splitlines():
        event=json.loads(raw);supplied=event.pop('sha256')
        assert event.get('seq',event.get('index'))==count
        assert event.get('previous',event.get('previous_sha256'))==previous
        assert hashlib.sha256(canonical(event)).hexdigest()==supplied
        previous=supplied;count+=1
    chains[name]={'events':count,'head':previous,'raw_sha256':sha(local/name)}
terminal=json.loads((local/'worker/terminal.json').read_bytes())
write(OUT/'receipt.json',{'status':'full_original_terminal_collected_and_verified',
    'original_files_verified':len(manifest),'original_terminal_manifest_sha256':report['terminal_manifest_sha256'],
    'archive_sha256':sha(archive_path),'chains':chains,'worker_terminal':terminal,
    'original_exit':report['exit'],'all_original_tensor_bytes_mirrored':True,
    'collection_new_model_GUI_scorer_calls':0,'semantic_review_complete':False})
write(OUT/'seal.json',{str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()})
print(json.dumps({'status':'collected_verified','original_files':len(manifest),
    'terminal':terminal,'receipt_sha256':sha(OUT/'receipt.json'),'seal_sha256':sha(OUT/'seal.json')},ensure_ascii=False))
