"""Collect sealed controls without sending inference requests or changing sources."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'full-gui-bounded-evidence-20261109-03'))
from remote_control import remote, save, sha


def collect(terminal=False):
    code = 'TERMINAL=' + repr(terminal) + '\n' + r'''
from pathlib import Path
import base64,hashlib,io,json,os,time,zipfile
r=Path('/home/researcher/jev-defense-four-gpu-20261106/source-bound-controls-20261109-08')
p=Path('/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/source-bound-controls-20261109-08')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as stream:
  for part in iter(lambda:stream.read(1048576),b''):h.update(part)
 return h.hexdigest()
def identity(pid):
 q=Path('/proc',str(pid))
 if not q.exists():return {'pid':pid,'absent':True}
 t=(q/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':q.stat().st_uid,'command':(q/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':t[19],'state':t[0]}
assert os.getuid()==1033
identities={}
for name in ['launcher-process.json','worker/process.json']:
 record=json.loads((r/name).read_bytes())
 identities[name]={'record':record,'actual':identity(record['pid'])}
 if TERMINAL:assert identities[name]['actual'].get('absent')is True
if TERMINAL:assert (r/'exit.json').is_file()and(r/'worker/terminal.json').is_file()
manifest=json.loads((p/'manifest.json').read_bytes())
assert sha(p/'manifest.json')=='6411eb8a8d3592cb0e13b8630ae7c5a77261ce3b4ef0c1bb140f91e55bc7ccd9'
for name,expected in manifest['files'].items():assert sha(p/name)==expected,name
selected=[];checks=[]
for directory in [r/'worker/auxiliary',r/'worker/judges']:
 for target in sorted(directory.glob('*')):
  seal=target/'seal.json'
  if not seal.is_file():continue
  value=json.loads(seal.read_bytes())
  for name,expected in value.items():assert sha(target/name)==expected,str(target/name)
  checks.append({'directory':target.relative_to(r).as_posix(),'seal_sha256':sha(seal),'files_verified':len(value)})
  selected.extend(q for q in target.iterdir()if q.is_file()and q.suffix not in ['.tensor','.bin','.pt','.safetensors'])
for q in r.rglob('*'):
 if q.is_file()and not any(x in q.relative_to(r).parts for x in ['auxiliary','judges'])and q.suffix not in ['.tensor','.bin','.pt','.safetensors']:
  selected.append(q)
indices={};stats={}
if TERMINAL:
 for q in sorted(r.rglob('*')):
  if not q.is_file():continue
  before=q.stat();name=q.relative_to(r).as_posix();indices[name]=sha(q);after=q.stat()
  assert (before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino),name
  stats[name]={'bytes':after.st_size,'mtime_ns':after.st_mtime_ns,'inode':after.st_ino}
 for name in ['terminal-manifest.json','worker/worker-manifest.json']:
  q=r/name;value=json.loads(q.read_bytes())
  for rel,expected in value.items():assert sha(q.parent/rel)==expected,str(q.parent/rel)
chains=[]
for q in sorted(r.rglob('events.jsonl')):
 previous='0'*64;n=0;kinds={};raw=q.read_bytes()
 assert not raw or raw.endswith(b'\n')
 for line in raw.splitlines():
  v=json.loads(line);sig=v.pop('sha256')
  assert v['seq']==n and v['previous']==previous
  assert hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==sig
  previous=sig;n+=1;kinds[v['kind']]=kinds.get(v['kind'],0)+1
 chains.append({'path':q.relative_to(r).as_posix(),'events':n,'head':previous,'counts':kinds})
archive=io.BytesIO();exported={}
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
 for q in sorted(set(selected)):
  name=q.relative_to(r).as_posix();raw=q.read_bytes();exported[name]=hashlib.sha256(raw).hexdigest()
  if TERMINAL:assert exported[name]==indices[name],name
  z.writestr(name,raw)
receipt={'time':time.time(),'remote_read_only':True,'terminal_collection':TERMINAL,
 'new_model_GPU_GUI_scorer_paid_calls':0,'original_sources_modified':False,
 'root':str(r),'manifest_sha256':sha(p/'manifest.json'),'source_files_verified':len(manifest['files']),
 'actual_processes':identities,'sealed_calls_verified':checks,'chains':chains,
 'exported_files':exported,'all_terminal_original_files':indices,'all_terminal_original_stats':stats,
 'raw_tensors_preserved_at_original_remote_paths_not_deleted':True}
raw=archive.getvalue();receipt['archive_sha256']=hashlib.sha256(raw).hexdigest()
print(json.dumps({'receipt':receipt,'archive_base64':base64.b64encode(raw).decode()},ensure_ascii=False))
'''
    output, operation = remote('3090', code, 'collect-controls08-' + ('terminal' if terminal else 'sealed-live'), timeout=55)
    value = json.loads(output)
    target = HERE / (('terminal-collection-' if terminal else 'sealed-live-collection-') + str(time.time_ns()))
    target.mkdir()
    archive = base64.b64decode(value['archive_base64'])
    assert hashlib.sha256(archive).hexdigest() == value['receipt']['archive_sha256']
    (target / 'originals.zip').write_bytes(archive)
    root = target / 'original'; root.mkdir()
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for item in z.infolist():
            path = root / item.filename
            assert path.resolve().is_relative_to(root.resolve())
            raw = z.read(item)
            assert hashlib.sha256(raw).hexdigest() == value['receipt']['exported_files'][item.filename]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    value['receipt']['operation'] = str(operation)
    save(target / 'receipt.json', value['receipt'])
    save(target / 'seal.json', {p.relative_to(target).as_posix(): sha(p) for p in target.rglob('*') if p.is_file()})
    print(json.dumps({'collection': str(target), 'receipt_sha256': sha(target / 'receipt.json'),
                      'sealed_calls': len(value['receipt']['sealed_calls_verified']),
                      'terminal': terminal, 'chains': value['receipt']['chains']}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--terminal', action='store_true')
    collect(parser.parse_args().terminal)
