"""Inspect the existing CPU handle, preserving a post-exit original snapshot."""
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


def main(attempt):
    code = 'ATTEMPT='+repr(attempt)+'\n'+r'''
from pathlib import Path
import base64,hashlib,io,json,os,time,zipfile
r=Path('/home/researcher/jev-defense-four-gpu-20261106/unicode-length-guard-20261109-17')
assert os.getuid()==1033
launch_name='launch.json' if ATTEMPT=='01' else 'launch-linked02.json'
seal_name='source-seal.json' if ATTEMPT=='01' else 'source-seal-linked02.json'
package_name='CPU-package' if ATTEMPT=='01' else 'CPU-package-linked02'
attempt='attempt-'+ATTEMPT
launch=json.loads((r/launch_name).read_bytes())
p=Path('/proc',str(launch['pid']))
if p.exists():
 tail=(p/'stat').read_text().rsplit(')',1)[1].split()
 actual={'pid':launch['pid'],'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':tail[19],'state':tail[0]}
 assert actual['uid']==launch['uid'] and actual['start_ticks']==launch['start_ticks']
 assert actual['command']==' '.join(launch['command'])
else:actual={'pid':launch['pid'],'absent':True}
values={}
for name in [attempt+'/'+suffix for suffix in ['status.json','terminal.json','receipt.json','failure.json']]:
 q=r/name
 if q.is_file():values[name]=json.loads(q.read_bytes())
log=(r/(attempt+'.log')).read_bytes()
sealed=False;files={};archive=None
if actual.get('absent') and (r/attempt/'seal.json').is_file():
 def h(q):return hashlib.sha256(q.read_bytes()).hexdigest()
 for name,expected in json.loads((r/seal_name).read_bytes()).items():assert h(r/package_name/name)==expected,name
 for name,expected in json.loads((r/attempt/'seal.json').read_bytes()).items():assert h(r/attempt/name)==expected,name
 stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
  for q in sorted(r.rglob('*')):
   if not q.is_file() or '__pycache__' in q.parts:continue
   name=q.relative_to(r).as_posix();before=q.stat();raw=q.read_bytes();after=q.stat()
   assert (before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino),name
   files[name]=hashlib.sha256(raw).hexdigest();z.writestr(name,raw)
 archive=base64.b64encode(stream.getvalue()).decode();sealed=True
receipt={'time':time.time(),'actual_process':actual,'original_launch':launch,'values':values,'terminal_sources_and_outputs_sealed':sealed,
 'files':files,'log_sha256':hashlib.sha256(log).hexdigest(),'log_tail':log[-3500:].decode(errors='replace'),
 'read_only':True,'new_model_GPU_GUI_calls':0,'original_files_modified':False}
print(json.dumps({'receipt':receipt,'archive_base64':archive}))
'''
    output, operation = remote('3090', code, 'inspect-length17-original-native-CPU-handle', timeout=55)
    value = json.loads(output)
    target = HERE / ('native-CPU-inspection-' + str(time.time_ns()))
    target.mkdir()
    receipt = value['receipt']
    receipt['operation'] = str(operation)
    if value['archive_base64']:
        raw = base64.b64decode(value['archive_base64'])
        (target / 'originals.zip').write_bytes(raw)
        originals = target / 'original'
        originals.mkdir()
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for item in z.infolist():
                dest = originals / item.filename
                assert dest.resolve().is_relative_to(originals.resolve())
                data = z.read(item)
                assert hashlib.sha256(data).hexdigest() == receipt['files'][item.filename]
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open('xb') as stream:
                    stream.write(data)
    save(target / 'receipt.json', receipt)
    save(target / 'seal.json', {p.relative_to(target).as_posix(): sha(p) for p in target.rglob('*') if p.is_file()})
    print(json.dumps({'evidence': str(target), 'receipt_sha256': sha(target/'receipt.json'),
                     'actual_process': receipt['actual_process'],
                     'terminal': receipt['values'].get('attempt-'+attempt+'/terminal.json'),
                     'status': receipt['values'].get('attempt-'+attempt+'/status.json'),
                     'sealed': receipt['terminal_sources_and_outputs_sealed'],
                     'failure': receipt['values'].get('attempt-'+attempt+'/failure.json')}, ensure_ascii=False))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--attempt',choices=['01','02'],default='01')
    main(parser.parse_args().attempt)
