"""Read-only identity/seal inspection; export only public initialization evidence."""
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


def main(collect):
    code = 'COLLECT=' + repr(collect) + '\n' + r'''
from pathlib import Path
import base64,hashlib,io,json,os,time,zipfile
r=Path('/data/researcher/jev-defense-four-gpu-20261106/independent-native-bindings-20261109-19')
a=r/'attempt-01'
def sha(q):
 q=Path(q);s=q.stat();h=hashlib.sha256(q.read_bytes()).hexdigest();t=q.stat()
 assert(s.st_size,s.st_mtime_ns,s.st_ino)==(t.st_size,t.st_mtime_ns,t.st_ino),str(q)
 return h
def identity(pid):
 p=Path('/proc',str(pid))
 if not p.exists():return {'pid':pid,'absent':True}
 s=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'uid':p.stat().st_uid,'command':(p/'cmdline').read_bytes().replace(bytes([0]),b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
assert os.getuid()==1015
record=json.loads((r/'launch.json').read_bytes());actual=identity(record['pid'])
if not actual.get('absent'):
 assert all(str(record[k])==str(actual[k])for k in ['pid','uid','command','start_ticks'])
out={'time':time.time(),'read_only':True,'new_model_GPU_agent_scorer_paid_calls':0,
     'actual_process':actual,'launch_sha256':sha(r/'launch.json'),'public_task_receipts':[]}
for q in sorted(a.glob('task-*/receipt.json')):
 out['public_task_receipts'].append({'path':q.relative_to(a).as_posix(),'sha256':sha(q),'value':json.loads(q.read_bytes())})
if(a/'terminal.json').is_file():
 terminal=json.loads((a/'terminal.json').read_bytes())
 out['terminal']={k:terminal[k]for k in ['time','started','status','completed_tasks','no_automatic_retry']}
 out['terminal_sha256']=sha(a/'terminal.json')
if(a/'failure.json').is_file():
 failure=json.loads((a/'failure.json').read_bytes())
 out['failure']={'sha256':sha(a/'failure.json'),'completed_task_ids':failure['completed_task_ids'],
                 'raw_failure_preserved_remote_not_exported':True}
if COLLECT:
 assert actual.get('absent')is True and(a/'seal.json').is_file()and(a/'terminal.json').is_file()
 seal=json.loads((a/'seal.json').read_bytes())
 for name,h in seal.items():assert sha(a/name)==h,name
 for q in a.glob('task-*/seal.json'):
  for name,h in json.loads(q.read_bytes()).items():assert sha(q.parent/name)==h,name
 for name,h in json.loads((r/'package/source-seal.json').read_bytes()).items():assert sha(r/'package'/name)==h,name
 selected=[r/'launch.json',*list((r/'package').glob('*.py')),r/'package/bindings-public.json',r/'package/source-seal.json']
 selected += [a/name for name in ['process.json','site-lease.json','receipt.json','seal.json']if(a/name).is_file()]
 for q in a.glob('task-*'):
  selected += [q/name for name in ['started.json','receipt.json','initial.png','same-live-recapture.png','seal.json']if(q/name).is_file()]
 archive=io.BytesIO();exported={}
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
  for q in sorted(selected):
   name=q.relative_to(r).as_posix()
   assert '.auth'not in q.parts and'PRIVATE'not in name and q.suffix!='.log'
   raw=q.read_bytes();exported[name]=hashlib.sha256(raw).hexdigest();z.writestr(name,raw)
 log=r/'attempt-01.log'
 out.update({'all_terminal_file_hashes':seal,'terminal_seal_sha256':sha(a/'seal.json'),
             'all_terminal_files_verified':len(seal),'exported_files':exported,
             'private_configs_auth_and_log_contents_excluded':True,
             'log_sha256':sha(log),'log_bytes':log.stat().st_size,
             'archive_sha256':hashlib.sha256(archive.getvalue()).hexdigest()})
 print(json.dumps({'receipt':out,'archive_base64':base64.b64encode(archive.getvalue()).decode()},ensure_ascii=False))
else:print(json.dumps({'receipt':out},ensure_ascii=False))
'''
    output, operation = remote('4090', code, 'inspect-native19-public-only-' + ('terminal' if collect else 'live'), timeout=55)
    value = json.loads(output)
    receipt = value['receipt']
    target = HERE / (('terminal-collection-' if collect else 'inspection-') + str(time.time_ns()))
    target.mkdir()
    if collect:
        raw = base64.b64decode(value['archive_base64'])
        assert hashlib.sha256(raw).hexdigest() == receipt['archive_sha256']
        (target / 'public-originals.zip').write_bytes(raw)
        root = target / 'original'
        root.mkdir()
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for item in z.infolist():
                q = root / item.filename
                assert q.resolve().is_relative_to(root.resolve())
                raw = z.read(item)
                assert hashlib.sha256(raw).hexdigest() == receipt['exported_files'][item.filename]
                q.parent.mkdir(parents=True, exist_ok=True)
                with q.open('xb') as stream:
                    stream.write(raw)
    receipt['operation'] = str(operation)
    save(target / 'receipt.json', receipt)
    save(target / 'seal.json', {q.relative_to(target).as_posix(): sha(q) for q in target.rglob('*') if q.is_file()})
    print(json.dumps({'collection': str(target), 'receipt_sha256': sha(target / 'receipt.json'),
                      'actual_process': receipt['actual_process'], 'terminal': receipt.get('terminal'),
                      'completed_initializations': len(receipt['public_task_receipts']),
                      'failure': receipt.get('failure'), 'model_agent_scorer_calls': 0}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--collect', action='store_true')
    main(parser.parse_args().collect)
