"""Preserve stdout parsing failure; collect existing setup, never reexecute it."""
import base64
import hashlib
import io
import json
from pathlib import Path
import shutil
import time
import zipfile
from remote_control import remote, save, sha, ROOT4090

HERE = Path(__file__).resolve().parent


def main():
    assert not (HERE / 'environment-admission.json').exists()
    ops = sorted((HERE / 'operations').glob('*-native-same-live-environment'))
    assert len(ops) == 1
    failed = ops[0]
    assert json.loads((failed / 'receipt.json').read_bytes())['returncode'] == 0
    preserved = HERE / ('preflight-reporter-failure-preservation-' + str(time.time_ns()))
    preserved.mkdir()
    shutil.copy2(HERE / 'orchestrate.py', preserved / 'original-orchestrate.py')
    shutil.copytree(failed, preserved / 'original-operation')
    save(preserved / 'failure.json', {
        'type': 'JSONDecodeError', 'message': 'Expecting value: line 1 column 1 (char 0)',
        'location': 'orchestrate.py preflight json.loads(stdout)', 'remote_command_returncode': 0,
        'source_and_raw_stdout_stderr_preserved_before_reporter_repair': True,
        'no_model_GUI_or_environment_retry': True, 'original_preflight_not_modified': True})
    save(preserved / 'seal.json', {p.relative_to(preserved).as_posix(): sha(p) for p in preserved.rglob('*') if p.is_file()})
    code = 'ROOT=' + repr(ROOT4090) + '\n' + r'''
from pathlib import Path
import base64,hashlib,io,json,os,time,zipfile
r=Path(ROOT)/'environment-preflight';assert os.getuid()==1015
def sha(p):
 before=p.stat();value=hashlib.sha256(p.read_bytes()).hexdigest();after=p.stat()
 assert(before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino)
 return value
receipt=json.loads((r/'receipt.json').read_bytes())
assert receipt['status']=='passed' and receipt['model_calls']==receipt['task_agent_actions']==receipt['scorer_calls']==0
assert receipt['same_live_recapture'] and receipt['native_scorer_loaded_not_invoked'] and not receipt['site_reset']
assert sha(r/'initial.png')==receipt['first_image_sha256']
assert sha(r/'same-live-recapture.png')==receipt['recapture_sha256']
index={p.relative_to(r).as_posix():sha(p)for p in r.rglob('*')if p.is_file()}
public=['receipt.json','initial.png','same-live-recapture.png'];stream=io.BytesIO()
with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED)as archive:
 for name in public:archive.writestr(name,(r/name).read_bytes())
print(json.dumps({'time':time.time(),'receipt':receipt,'all_original_files_SHA':index,'public_originals':[{'name':name,'sha256':index[name]}for name in public],
 'remote_read_only':True,'environment_check_reexecuted':False,'new_model_GUI_scorer_calls':0,
 'archive_sha256':hashlib.sha256(stream.getvalue()).hexdigest(),'archive_base64':base64.b64encode(stream.getvalue()).decode()}))
'''
    output, operation = remote('4090', code, 'linked02-read-existing-environment-receipt', timeout=55)
    value = json.loads(output)
    target = HERE / ('environment-collection-linked02-' + str(time.time_ns()))
    target.mkdir()
    raw = base64.b64decode(value.pop('archive_base64'))
    assert hashlib.sha256(raw).hexdigest() == value['archive_sha256']
    (target / 'public-originals.zip').write_bytes(raw)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for row in value['public_originals']:
            data = archive.read(row['name'])
            assert hashlib.sha256(data).hexdigest() == row['sha256']
            with (target / row['name']).open('xb') as stream:
                stream.write(data)
    save(target / 'collection.json', dict(value, operation=str(operation), original_failure_preservation=str(preserved)))
    save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
    save(HERE / 'environment-admission.json', {
        'passed': True, 'result': value['receipt'], 'operation': str(operation),
        'collection': str(target), 'collection_sha256': sha(target / 'collection.json'),
        'failure_preservation': str(preserved), 'failure_preservation_seal_sha256': sha(preserved / 'seal.json'),
        'reporter_only_read_only_repair': True, 'environment_check_reexecuted': False,
        'new_model_GUI_scorer_calls': 0})
    print(json.dumps({'passed': True, 'collection': str(target), 'failure_preservation': str(preserved),
                      'native_source_and_site_ownership_and_same_live_capture_verified': True,
                      'environment_reexecuted': False, 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
