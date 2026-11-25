"""Collect sealed actual calls and complete postexit SHA/stat provenance."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import zipfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'full-gui-bounded-evidence-20261109-03'))
from remote_control import remote,save,sha


def collect(terminal):
    manifest_sha=sha(HERE/'runtime-package/manifest.json')
    code='TERMINAL='+repr(terminal)+'\nEXPECTED='+repr(manifest_sha)+'\n'+r'''
from pathlib import Path
import base64,hashlib,io,json,os,time,zipfile
r=Path('/home/researcher/jev-defense-four-gpu-20261106/unicode-guard-real-preflight-20261109-18')
p=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/unicode-guard-real-preflight-20261109-18')
cache={};stats={}
def sha(q):
 q=Path(q);before=q.stat();key=(str(q),before.st_size,before.st_mtime_ns,before.st_ino)
 if key in cache:return cache[key]
 h=hashlib.sha256()
 with q.open('rb')as f:
  for part in iter(lambda:f.read(1048576),b''):h.update(part)
 after=q.stat();assert (before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino),str(q)
 cache[key]=h.hexdigest();return cache[key]
def identity(pid):
 q=Path('/proc',str(pid))
 if not q.exists():return {'pid':pid,'absent':True}
 tail=(q/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':q.stat().st_uid,'command':(q/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':tail[19],'state':tail[0]}
assert os.getuid()==1033 and sha(p/'manifest.json')==EXPECTED
manifest=json.loads((p/'manifest.json').read_bytes())
for n,h in manifest['files'].items():assert sha(p/n)==h,n
identities={}
for name in ['launcher-process.json','worker/process.json']:
 record=json.loads((r/name).read_bytes());actual=identity(record['pid'])
 if TERMINAL:assert actual.get('absent')is True
 else:
  if not actual.get('absent'):assert all(str(record[k])==str(actual[k])for k in ['pid','uid','command','start_ticks'])
 identities[name]={'record':record,'actual':actual}
if TERMINAL:assert(r/'exit.json').is_file()and(r/'worker/terminal.json').is_file()
selected=set();sealed=[]
groups=['auxiliary','actors','judges']
for group in groups:
 for q in sorted((r/'worker'/group).glob('*/seal.json')):
  original=json.loads(q.read_bytes())
  for name,h in original.items():assert sha(q.parent/name)==h,str(q.parent/name)
  sealed.append({'directory':q.parent.relative_to(r).as_posix(),'seal_sha256':sha(q),'files_verified':len(original)})
  selected.update(t for t in q.parent.iterdir()if t.is_file()and t.suffix not in ['.bin','.tensor','.pt','.safetensors'])
for q in r.rglob('*'):
 if not q.is_file()or q.suffix in ['.bin','.tensor','.pt','.safetensors']:continue
 if TERMINAL or not any(x in q.relative_to(r).parts for x in groups):selected.add(q)
indices={}
if TERMINAL:
 for q in sorted(r.rglob('*')):
  if not q.is_file():continue
  name=q.relative_to(r).as_posix();indices[name]=sha(q);st=q.stat()
  stats[name]={'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'inode':st.st_ino}
 for name in ['terminal-manifest.json','worker/worker-manifest.json']:
  q=r/name
  for rel,h in json.loads(q.read_bytes()).items():assert sha(q.parent/rel)==h,str(q.parent/rel)
chains=[]
for q in sorted(r.rglob('events.jsonl')):
 previous='0'*64;n=0;kinds={};raw=q.read_bytes()
 assert not raw or raw.endswith(b'\n')
 for line in raw.splitlines():
  v=json.loads(line);signature=v.pop('sha256')
  assert v['seq']==n and v['previous']==previous
  assert hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==signature
  previous=signature;n+=1;kinds[v['kind']]=kinds.get(v['kind'],0)+1
 chains.append({'path':q.relative_to(r).as_posix(),'events':n,'head':previous,'counts':kinds})
exported={};archive=io.BytesIO()
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
 for q in sorted(selected):
  name=q.relative_to(r).as_posix();raw=q.read_bytes();exported[name]=hashlib.sha256(raw).hexdigest()
  if TERMINAL:assert exported[name]==indices[name],name
  z.writestr(name,raw)
receipt={'time':time.time(),'remote_read_only':True,'terminal_collection':TERMINAL,
 'new_model_GPU_GUI_scorer_paid_calls':0,'original_sources_modified':False,
 'root':str(r),'manifest_sha256':EXPECTED,'source_files_verified':len(manifest['files']),
 'actual_processes':identities,'sealed_calls_verified':sealed,'chains':chains,'exported_files':exported,
 'all_terminal_original_files':indices,'all_terminal_original_stats':stats,
 'raw_tensors_preserved_at_original_remote_paths_not_deleted':True,'archive_sha256':hashlib.sha256(archive.getvalue()).hexdigest()}
print(json.dumps({'receipt':receipt,'archive_base64':base64.b64encode(archive.getvalue()).decode()},ensure_ascii=False))
'''
    output,op=remote('3090',code,'unicode18-collect-'+('terminal'if terminal else'sealed-live'),timeout=55)
    v=json.loads(output)
    target=HERE/(('terminal-collection-'if terminal else'sealed-live-collection-')+str(time.time_ns()))
    target.mkdir()
    raw=base64.b64decode(v['archive_base64'])
    assert hashlib.sha256(raw).hexdigest()==v['receipt']['archive_sha256']
    (target/'originals.zip').write_bytes(raw)
    root=target/'original';root.mkdir()
    with zipfile.ZipFile(io.BytesIO(raw))as z:
        for item in z.infolist():
            q=root/item.filename
            assert q.resolve().is_relative_to(root.resolve())
            raw=z.read(item)
            assert hashlib.sha256(raw).hexdigest()==v['receipt']['exported_files'][item.filename]
            q.parent.mkdir(parents=True,exist_ok=True)
            with q.open('xb')as f:f.write(raw)
    v['receipt']['operation']=str(op)
    save(target/'receipt.json',v['receipt'])
    save(target/'seal.json',{q.relative_to(target).as_posix():sha(q)for q in target.rglob('*')if q.is_file()})
    print(json.dumps({'collection':str(target),'receipt_sha256':sha(target/'receipt.json'),
                      'sealed_calls':len(v['receipt']['sealed_calls_verified']),'terminal':terminal,'chains':v['receipt']['chains']},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--terminal',action='store_true')
    collect(parser.parse_args().terminal)
