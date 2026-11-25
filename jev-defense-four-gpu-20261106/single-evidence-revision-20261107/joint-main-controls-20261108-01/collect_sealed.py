"""Read-only collection of completed call seals; raw tensor bytes stay sealed remote."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import time
import zipfile

HERE = Path(__file__).resolve().parent
CODE = r'''
from pathlib import Path
import hashlib,io,json,sys,time,zipfile
import numpy as np
r=Path('/home/researcher/jev-defense-four-gpu-20261106/single-evidence-revision-20261107/joint-main-controls-20261108-02')
w=r/'worker'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
calls=sorted((w/'auxiliary').glob('*/seal.json'))+sorted((w/'judges').glob('*/seal.json'))
audit={'root':str(r),'time_unix':time.time(),'remote_read_only':True,'new_model_GUI_calls':0,
       'raw_tensor_bytes_mirrored':False,'calls':[],'errors':[]}
files={}
for seal in calls:
 d=seal.parent;inv=json.loads(seal.read_bytes());errors=[]
 for n,h in inv.items():
  p=d/n
  if not p.is_file() or sha(p)!=h:errors.append(n)
 row={'directory':str(d.relative_to(r)),'seal_sha256':sha(seal),'all_sealed_files_SHA_verified':not errors,
      'files':len(inv),'errors':errors,'CPU_to_first_forward':{}}
 prepared=json.loads((d/'prepared.json').read_bytes())
 first=json.loads((d/'first-forward.json').read_bytes())
 if set(prepared)!=set(first):errors.append('CPU/forward tensor names')
 for n,v in prepared.items():
  f=first[n]
  matches=all(v[k]==f[k] for k in ['shape','dtype','bytes','sha256'])
  matches=matches and sha(d/v['file'])==v['sha256'] and sha(d/f['file'])==f['sha256']
  row['CPU_to_first_forward'][n]=matches
  if not matches:errors.append(n+' prepared/forward binding')
 actual=json.loads((d/'actual-generation.json').read_bytes())
 cfg=json.loads((d/'effective-generation.json').read_bytes())
 ids=np.fromfile(d/prepared['input_ids']['file'],dtype='<i8').reshape(prepared['input_ids']['shape'])
 seq=np.asarray(json.loads((d/'sequence_ids.json').read_bytes()),dtype='<i8')
 raw_seq=(d/'sequence_ids.tensor').read_bytes()
 row['sequence_raw_JSON_equal']=seq.tobytes()==raw_seq
 row['complete_input_prefix_equal']=bool(np.array_equal(seq[:,:ids.shape[1]],ids))
 out=seq[0,ids.shape[1]:].tolist()
 row['output_ids_equal']=out==actual['output_ids']
 eos=cfg['eos_token_id'];eos=[eos] if isinstance(eos,int) else eos
 row['EOS_recomputed']=bool(out and out[-1] in eos)
 row['EOS_record_equal']=row['EOS_recomputed']==actual['natural_EOS']
 row['input_tokens']=ids.shape[1];row['output_tokens']=len(out)
 row['max_new_tokens']=cfg['max_new_tokens']
 row['output_cap_respected']=len(out)<=cfg['max_new_tokens']
 for n in ['sequence_raw_JSON_equal','complete_input_prefix_equal','output_ids_equal','EOS_record_equal','output_cap_respected']:
  if not row[n]:errors.append(n)
 audit['calls'].append(row)
 audit['errors'].extend(str(d.relative_to(r))+'/'+x for x in errors)
 for p in sorted(d.iterdir()):
  if p.is_file() and p.suffix!='.tensor':files[str(p.relative_to(r))]=p
for n in ['manifest.json','launcher-process.json','worker-launch.json','exit.json','terminal-manifest.json',
 'launcher-failure.json','worker.log','before-resources.json','after-resources.json',
 'worker/process.json','worker/loaded.json','worker/summary.json','worker/terminal.json','worker/failure.json',
 'worker/worker-manifest.json','worker/journal/events.jsonl']:
 p=r/n
 if p.is_file():files[n]=p
for p in w.glob('C*-result.json'):files[str(p.relative_to(r))]=p
for p in w.glob('*.json'):
 if p.is_file():files[str(p.relative_to(r))]=p
audit['unfinished_call_directories']=[]
if (r/'terminal-manifest.json').exists():
 for d in sorted((w/'judges').glob('*')):
  if not d.is_dir() or (d/'seal.json').exists():continue
  entry={'directory':str(d.relative_to(r)),'no_complete_reply_seal':True,'files':{}}
  for p in sorted(d.iterdir()):
   if p.is_file():
    entry['files'][p.name]={'bytes':p.stat().st_size,'sha256':sha(p)}
    if p.suffix!='.tensor':files[str(p.relative_to(r))]=p
  if (d/'prepared.json').exists() and (d/'first-forward.json').exists():
   prepared=json.loads((d/'prepared.json').read_bytes());first=json.loads((d/'first-forward.json').read_bytes())
   entry['CPU_to_failed_first_forward']={n:all(v[k]==first[n][k] for k in ['shape','dtype','bytes','sha256'])
     and sha(d/v['file'])==v['sha256'] and sha(d/first[n]['file'])==first[n]['sha256'] for n,v in prepared.items()}
   if not all(entry['CPU_to_failed_first_forward'].values()):audit['errors'].append('failed call input/forward mismatch')
  audit['unfinished_call_directories'].append(entry)
for folder in ['primary-native-state','auxiliary-identity']:
 for p in (w/folder).rglob('*'):
  if p.is_file() and p.suffix!='.tensor':files[str(p.relative_to(r))]=p
t=r/'terminal-manifest.json'
if t.exists():
 inv=json.loads(t.read_bytes())
 errors=[n for n,h in inv.items() if not(r/n).is_file() or sha(r/n)!=h]
 audit['terminal']={'manifest_sha256':sha(t),'files':len(inv),'errors':errors,'all_SHA_verified':not errors}
 audit['errors'].extend('terminal/'+n for n in errors)
audit['mirrored_files']={n:sha(p) for n,p in files.items()}
z=io.BytesIO()
with zipfile.ZipFile(z,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as o:
 for n,p in files.items():o.writestr('original/'+n,p.read_bytes())
 o.writestr('collection-audit.json',json.dumps(audit,ensure_ascii=False,indent=2))
sys.stdout.buffer.write(z.getvalue())
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--terminal', action='store_true')
    parser.add_argument('--attempt', choices=['02','03'], default='02')
    a = parser.parse_args()
    target = HERE / (('terminal-collection-' if a.terminal else 'sealed-call-collection-') + a.attempt) / str(time.time_ns())
    target.mkdir(parents=True, exist_ok=False)
    source = CODE.replace('joint-main-controls-20261108-02','joint-main-controls-20261108-' + a.attempt)
    (target / 'source.py').write_text(source, encoding='utf8')
    res = subprocess.run(['D:/Git/usr/bin/ssh.exe', '-F', 'C:/Users/researcher/.ssh/config', '-o', 'BatchMode=yes',
        '-o', 'ConnectTimeout=15', '3090', '/opt/whz/conda-envs/webmall-vlm/bin/python', '-'],
        input=source.encode(), capture_output=True, timeout=60)
    (target / 'stderr.txt').write_bytes(res.stderr)
    if res.returncode:
        (target / 'stdout-failure.bin').write_bytes(res.stdout)
        raise RuntimeError(res.stderr.decode(errors='replace'))
    (target / 'public-evidence.zip').write_bytes(res.stdout)
    with zipfile.ZipFile(io.BytesIO(res.stdout)) as archive:
        for name in archive.namelist():
            dest = (target / name).resolve()
            assert dest.is_relative_to(target.resolve()) and not dest.exists()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(archive.read(name))
    audit = json.loads((target / 'collection-audit.json').read_bytes())
    for name, h in audit['mirrored_files'].items():
        assert hashlib.sha256((target / 'original' / name).read_bytes()).hexdigest() == h, name
    (target / 'seal.json').write_text(json.dumps({str(p.relative_to(target)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(target.rglob('*')) if p.is_file()}, indent=2), encoding='utf8')
    print(json.dumps({'directory': str(target), 'calls_sealed_and_audited': len(audit['calls']),
        'audit_errors': audit['errors'], 'mirrored_files': len(audit['mirrored_files']),
        'raw_tensor_bytes_remain_remote': True, 'terminal': audit.get('terminal')}, ensure_ascii=False))
    assert not audit['errors'], 'Preserved audit failure'
    if a.terminal:
        assert audit.get('terminal', {}).get('all_SHA_verified'), 'Not a terminal yet'
