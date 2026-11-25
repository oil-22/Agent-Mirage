"""Once-only CPU job with a real process handle; observer timeouts never restart it."""
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import zipfile

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / 'remaining29-full-history-gui-20261110-37'
sys.path.insert(0, str(PREVIOUS))
from orchestrate import remote, save, sha, COMMON, OUTPUT
from join_source_reviews import verify_seal


def main():
    assert not (HERE / 'native-CPU-submission.json').exists(), 'Inspect the same remote job instead'
    source = json.loads((HERE / 'preparation-created.json').read_bytes())
    prepared = Path(source['root'])
    assert verify_seal(prepared) == source['seal_sha256']
    target = HERE / ('native-reference-CPU-' + str(time.time_ns()))
    target.mkdir()
    for name in [Path(__file__).name, 'native_grammar_check.py']:
        (target / name).write_bytes((HERE / name).read_bytes())
    remote_root = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + HERE.name + '/' + target.name
    buffer, inventory = io.BytesIO(), {}
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((prepared / 'proposed-release').rglob('*.py')):
            if '__pycache__' in path.parts:
                continue
            name = path.relative_to(prepared).as_posix()
            archive.writestr(name, path.read_bytes()); inventory[name] = sha(path)
        for name, path in [('primary-reference.json', PREVIOUS / 'runtime-package/primary-reference.json'),
                           ('native_grammar_check.py', HERE / 'native_grammar_check.py')]:
            archive.writestr(name, path.read_bytes()); inventory[name] = sha(path)
        archive.writestr('package-index.json', json.dumps(inventory))
    body = buffer.getvalue()
    save(HERE / 'native-CPU-submission.json', dict(time=time.time(), output=str(target), remote_root=remote_root,
        preparation=source, package_sha256=hashlib.sha256(body).hexdigest(), CPU_only_no_model_weights_or_GUI=True,
        once_only=True, real_job_handle_receipt='launch.json', no_observer_timeout_restart=True))
    prefix = 'PAYLOAD=' + repr(base64.b64encode(body).decode()) + '\n'
    code = 'ROOT=' + repr(remote_root) + '\nORIGINAL=' + repr(OUTPUT) + '\n' + COMMON + r'''
import base64,io,zipfile
root=Path(ROOT);assert not root.exists();root.mkdir(parents=True,exist_ok=False)
assert os.getuid()==1033
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as archive:
 for name in archive.namelist():
  p=root/name;assert p.resolve().is_relative_to(root.resolve())
  p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb')as stream:stream.write(archive.read(name))
index=json.loads((root/'package-index.json').read_bytes())
for name,expected in index.items():assert sha(root/name)==expected,name
assert not(root/'launch.json').exists()
environment=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1')
command=[sys.executable,'-B','-u',str(root/'native_grammar_check.py'),'--package',str(root),'--original',ORIGINAL]
with(root/'worker.log').open('xb')as log:
 worker=subprocess.Popen(command,cwd=str(root),env=environment,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
actual=identity(worker.pid)
assert not actual.get('absent')and actual['uid']==1033 and ROOT in actual['command']
value=dict(time=time.time(),root=ROOT,identity=actual,command=command,CPU_only=True,new_model_GUI_scorer_calls=0)
with(root/'launch.json').open('x')as stream:json.dump(value,stream)
print(json.dumps(value))
'''
    output, operation = remote('3090', code, 'launch-native-quote-reference-CPU-only-once', timeout=55, private_prefix=prefix)
    save(target / 'launch.json', dict(json.loads(output), operation=str(operation)))
    print(json.dumps(dict(output=str(target), remote_root=remote_root, launch=json.loads(output))))


if __name__ == '__main__':
    main()
