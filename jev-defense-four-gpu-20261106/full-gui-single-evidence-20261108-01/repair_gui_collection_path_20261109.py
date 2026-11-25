"""Linked LOCAL path repair: reuse sealed SSH output; zero remote/model calls."""
import base64,hashlib,io,json,time,zipfile
from pathlib import Path
from remote_control import HERE,save,sha

operations=sorted((HERE/'operations').glob('*-collect-terminal-4090'))
op=next(p for p in reversed(operations) if (p/'stdout.txt').is_file() and json.loads((p/'receipt.json').read_bytes())['returncode']==0)
failed=next(p for p in reversed(sorted((HERE/'terminal-collections-20261109').glob('*-4090'))) if not (p/'audit.json').exists())
preserved={'failure_type':'Windows WinError206 filename/path too long during LOCAL zip extraction',
    'original_collector_source_sha256':sha(HERE/'collect_two_terminals_20261109.py'),
    'successful_remote_audit_operation':str(op),'successful_remote_stdout_sha256':sha(op/'stdout.txt'),
    'partial_files':{p.relative_to(failed).as_posix():sha(p) for p in failed.rglob('*') if p.is_file()},
    'no_model_or_remote_retry':True,'time_unix':time.time()}
save(failed/'local-extraction-failure-preservation.json',preserved)
value=json.loads((op/'stdout.txt').read_text(encoding='utf8'))
target=Path('D:/MultiModel/gui1109')/(str(time.time_ns())+'-4090');target.mkdir(parents=True,exist_ok=False)
(target/'original').mkdir()
archive=base64.b64decode(value['archive_base64'])
with zipfile.ZipFile(io.BytesIO(archive)) as z:
    for n in z.namelist():assert (target/'original'/n).resolve().is_relative_to((target/'original').resolve())
    z.extractall(target/'original')
for n,h in value['audit']['public_mirrored_files'].items():assert sha(target/'original'/n)==h,n
save(target/'audit.json',value['audit'])
save(target/'collection.json',{'operation':str(op),'archive_sha256':hashlib.sha256(archive).hexdigest(),
    'audit_sha256':sha(target/'audit.json'),'public_files_verified':len(value['audit']['public_mirrored_files']),
    'linked_failed_local_collection':str(failed),'failure_preservation_sha256':sha(failed/'local-extraction-failure-preservation.json'),
    'only_local_output_path_changed':True,'new_remote_model_HTTP_GUI_calls':0})
save(target/'seal.json',{'audit.json':sha(target/'audit.json'),'collection.json':sha(target/'collection.json')})
save(HERE/'terminal-collections-20261109/GUI-public-collection-linked.json',{'directory':str(target),'audit_sha256':sha(target/'audit.json'),'collection_sha256':sha(target/'collection.json')})
print(json.dumps({'collection':str(target),'audit_sha256':sha(target/'audit.json'),'public_files_verified':len(value['audit']['public_mirrored_files']),
    'remote_batch_terminal_files_SHA_verified':value['audit']['remote_batch_files_SHA_verified'],'new_model_GUI_calls':0}))
