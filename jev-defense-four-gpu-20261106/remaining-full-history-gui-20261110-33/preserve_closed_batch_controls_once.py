"""Read-only postexit log/control preservation; never launch or stop a process."""
import base64
import json
from pathlib import Path
import time

from orchestrate import HERE, OUTPUT, GUIROOT, COMMON, remote, save, sha
from join_source_reviews import verify_seal


SOURCE = r'''
import base64
root=Path(ROOT)
records=[]
for name in PROCESS_RECORDS:
 p=root/name
 if not p.is_file():continue
 value=json.loads(p.read_bytes());record=value.get('identity',value)
 actual=identity(record['pid'])
 same=not actual.get('absent') and all(str(actual.get(k))==str(record.get(k)) for k in ['pid','uid','command','start_ticks'])
 assert not same or actual.get('state') in ['Z','X'],'Original process has not exited; preserve after natural exit only'
 records.append({'file':name,'record':record,'actual':actual,'original_process_exited':True})
exports={};files={}
for name in FILES:
 p=root/name
 if not p.is_file():continue
 before=p.stat();raw=p.read_bytes();after=p.stat()
 assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
 assert len(raw)==after.st_size
 files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw),'mtime_ns':after.st_mtime_ns}
 exports[name]=base64.b64encode(raw).decode()
print(json.dumps({'time':time.time(),'root':ROOT,'processes':records,'files':files,'exports':exports,
 'read_only':True,'new_model_GUI_scorer_calls':0}))
'''


def main():
    pointer = HERE / 'closed-batch-postexit-preservation-created.json'
    assert not pointer.exists()
    terminal = json.loads((HERE / 'logical-terminal-fullhistory23-T000-stale_replace-aux-collected.json').read_bytes())
    assert verify_seal(Path(terminal['collection'])) == terminal['seal_sha256']
    root = HERE / ('closed-batch-postexit-preservation-' + str(time.time_ns()))
    root.mkdir()
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    specifications = [
        ('3090', OUTPUT,
         ['launcher-process.json', 'worker/process.json'],
         ['worker.log', 'launcher.log', 'launcher-process.json', 'worker/process.json',
          'worker/status.json', 'worker/terminal.json', 'worker/failure.json', 'exit.json']),
        ('4090', GUIROOT,
         ['background/launch.json', 'control/process.json', 'control/runner-process.json'],
         ['background/outer.log', 'control/outer.log', 'control/runner.log',
          'background/launch.json', 'control/process.json', 'control/runner-process.json',
          'control/exit.json', 'batch/status.json', 'batch/uncaught-failure.json']),
    ]
    try:
        receipts = {}
        for machine, folder, processes, files in specifications:
            code = ('ROOT=' + repr(folder) + '\nPROCESS_RECORDS=' + repr(processes)
                    + '\nFILES=' + repr(files) + '\n' + COMMON + SOURCE)
            output, operation = remote(machine, code, 'preserve-closed-original-batch-logs-and-identities', timeout=55)
            value = json.loads(output)
            for name, encoded in value.pop('exports').items():
                path = root / machine / name
                assert path.resolve().is_relative_to(root.resolve())
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(base64.b64decode(encoded, validate=True))
                assert sha(path) == value['files'][name]['sha256']
            receipts[machine] = dict(value, operation=str(operation))
        save(root / 'receipt.json', dict(time=time.time(), passed=True, machines=receipts,
             original_GUI_and83_request_preservation=terminal,
             originals_retained_in_place=True, completed_tracks_never_reexecuted=True,
             new_model_GUI_scorer_calls=0, goal='active'))
    except BaseException as error:
        save(root / 'preservation-observer-failure.json', dict(time=time.time(), error=repr(error),
             model_or_GUI_not_retried=True, originals_not_modified=True))
        save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
        raise
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
    authority = dict(root=str(root), receipt_sha256=sha(root / 'receipt.json'), seal_sha256=sha(root / 'seal.json'))
    save(pointer, authority)
    print(json.dumps(authority))


if __name__ == '__main__':
    main()
