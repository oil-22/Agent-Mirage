"""Seal a naturally exited failed batch before diagnosis or technical changes."""
from pathlib import Path
import ast
import base64
import hashlib
import io
import json
import sys
import time
import zipfile

HERE = Path(__file__).resolve().parent
GUI = HERE.parent / 'full-gui-bounded-evidence-20261109-03'
sys.path.insert(0, str(GUI))
from remote_control import remote, save, sha

STAMP = str(time.time_ns())
ROOTS = {'3090': '/home/researcher/jev-defense-four-gpu-20261106',
         '4090': '/data/researcher/jev-defense-four-gpu-20261106'}

def preserve(host):
    code = 'HOST=' + repr(host) + '\nBASE=' + repr(ROOTS[host]) + '\nSTAMP=' + repr(STAMP) + '\n' + r'''
from pathlib import Path
import base64,hashlib,io,json,os,shutil,subprocess,time,zipfile
b=Path(BASE);r=b/'full-gui-bounded-evidence-20261109-03'
target=b/'full-gui-OOM-preservation-20261109-11'/STAMP
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for part in iter(lambda:f.read(1048576),b''):h.update(part)
 return h.hexdigest()
def save(p,v):
 with p.open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def actual(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return {'pid':pid,'absent':True}
 t=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':t[19],'state':t[0]}
assert os.getuid()==(1033 if HOST=='3090' else 1015)
assert (r/('exit.json' if HOST=='3090' else 'control/exit.json')).is_file()
identities={}
for name in (['launcher-process.json','worker/process.json'] if HOST=='3090' else ['control/process.json','control/runner-process.json']):
 record=json.loads((r/name).read_bytes());identities[name]={'record':record,'actual':actual(record['pid'])}
 assert identities[name]['actual'].get('absent') is True
target.mkdir(parents=True,exist_ok=False)
copy=target/'originals';copy.mkdir()
manifest_checks=[]
for p in sorted(r.rglob('*')):
 if p.name not in ['terminal-manifest.json','worker-manifest.json','seal.json','manifest.json'] or not p.is_file():continue
 try:value=json.loads(p.read_bytes())
 except (ValueError,OSError):continue
 if not isinstance(value,dict) or not value or not all(isinstance(v,str)and len(v)==64 for v in value.values()):continue
 differences=[]
 for name,expected in value.items():
  q=p.parent/name
  if not q.is_file():differences.append({'file':name,'missing':True,'expected':expected})
  else:
   got=sha(q)
   if got!=expected:differences.append({'file':name,'expected':expected,'actual':got})
 manifest_checks.append({'manifest':str(p.relative_to(r)),'sha256':sha(p),'entries':len(value),'differences':differences})
files={};stats={}
for p in sorted(r.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(r).as_posix();before=p.stat();h=sha(p);after=p.stat()
 assert(before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino),rel
 files[rel]=h;stats[rel]={'bytes':after.st_size,'mtime_ns':after.st_mtime_ns,'inode':after.st_ino}
selected=[]
if HOST=='3090':
 failed=r/'worker/requests/0178';assert (failed/'failure.json').is_file()
 selected.extend(p for p in failed.rglob('*')if p.is_file())
 selected.extend(p for name in ['worker.log','manifest.json','terminal-manifest.json','exit.json','worker/terminal.json','worker/worker-manifest.json','worker/journal/events.jsonl','worker/loaded.json'] if(p:=r/name).is_file())
 package=b/'runtime-preparation/full-gui-bounded-evidence-20261109-03'
 for p in package.rglob('*'):
  if p.is_file()and p.name!='private.token'and '__pycache__'not in p.parts:
   dest=target/'runtime-source'/p.relative_to(package);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
else:
 selected.extend(p for p in r.rglob('*')if p.is_file()and(p.suffix in ['.png','.log','.jsonl']or p.name in ['technical-failure.json','uncaught-failure.json','batch-failure.json','complete.json','exit.json','terminal-manifest.json','plan.json','manifest.json']))
for p in selected:
 rel=p.relative_to(r);dest=copy/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 assert sha(dest)==files[rel.as_posix()]
chains=[]
for p in sorted(r.rglob('events.jsonl')):
 previous='0'*64;n=0;kinds={}
 raw=p.read_bytes();assert not raw or raw.endswith(b'\n')
 for line in raw.splitlines():
  v=json.loads(line);sig=v.pop('sha256');assert v['seq']==n and v['previous']==previous
  assert hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==sig
  previous=sig;n+=1;kinds[v['kind']]=kinds.get(v['kind'],0)+1
 chains.append({'file':p.relative_to(r).as_posix(),'events':n,'head':previous,'kinds':kinds})
gpu=None
if HOST=='3090':
 gpu={'cards':subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True),'compute':subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)}
save(target/'original-file-SHA256.json',files);save(target/'original-file-stat.json',stats)
save(target/'original-manifest-checks.json',manifest_checks)
receipt={'host':HOST,'time':time.time(),'source':str(r),'snapshot':str(target),'actual_processes_absent':identities,
 'original_file_count':len(files),'copied_original_files':len(selected),'all_original_files_SHA_recorded':True,
 'all_event_chains_verified':chains,'old_manifests_preserved_and_mismatches_reported':manifest_checks,
 'no_original_file_modified':True,'new_model_GUI_scorer_paid_calls':0,'actual_GPU':gpu,
 'PRIVATE_native_scorer_data_not_sent_to_checker':True,'technical_failure_is_not_model_zero':True,
 'two_unstarted_stale_tracks_not_completed':True}
save(target/'receipt.json',receipt)
seal={p.relative_to(target).as_posix():sha(p)for p in target.rglob('*')if p.is_file()}
save(target/'snapshot-seal.json',seal)
archive=io.BytesIO()
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
 for p in target.rglob('*'):
  if p.is_file()and p.name!='private.token'and p.suffix not in ['.bin','.pt','.safetensors']:
   z.write(p,p.relative_to(target).as_posix())
print(json.dumps({'receipt':receipt,'seal_sha256':sha(target/'snapshot-seal.json'),
 'compact_archive_base64':base64.b64encode(archive.getvalue()).decode(),
 'archive_sha256':hashlib.sha256(archive.getvalue()).hexdigest(),'all_raw_tensors_preserved_remote':True}))
'''
    ast.parse(code)
    output, operation = remote(host, code, 'preserve-closed-OOM-batch-' + host, timeout=240)
    value = json.loads(output)
    # Short extraction root avoids the earlier Windows long-path failure.
    target = Path(r'D:\MultiModel\jev-oom-evidence') / STAMP / host
    target.mkdir(parents=True, exist_ok=False)
    archive = base64.b64decode(value.pop('compact_archive_base64'))
    assert hashlib.sha256(archive).hexdigest() == value['archive_sha256']
    (target / 'originals.zip').write_bytes(archive)
    original = target / 'original';original.mkdir()
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for name in z.namelist():
            assert (original / name).resolve().is_relative_to(original.resolve())
        z.extractall(original)
    seal = json.loads((original / 'snapshot-seal.json').read_bytes())
    assert sha(original / 'snapshot-seal.json') == value['seal_sha256']
    for name, expected in seal.items():
        path = original / name
        if path.is_file():assert sha(path) == expected, name
    save(target / 'collection.json', {'operation': str(operation), **value,
        'large_raw_tensors_preserved_and_sealed_remote_not_reinterpreted': True})
    save(HERE / (STAMP + '-' + host + '-collection.json'), {'collection':str(target/'collection.json'),
        'collection_sha256':sha(target/'collection.json'),'operation':str(operation)})
    print(json.dumps({'host': host, 'collection': str(target / 'collection.json'),
        'original_files': value['receipt']['original_file_count'],
        'original_manifest_mismatches': [r for r in value['receipt']['old_manifests_preserved_and_mismatches_reported']if r['differences']],
        'chains': [{'events':c['events'],'head':c['head']}for c in value['receipt']['all_event_chains_verified']],
        'model_GUI_calls':0}), flush=True)
    return target

if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('host',choices=['3090','4090'])
    preserve(parser.parse_args().host)
