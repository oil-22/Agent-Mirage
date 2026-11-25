"""Stage and run the finite CPU grammar check on the original native runtime."""
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
    assert not (HERE / 'native-CPU-submission.json').exists()
    source = json.loads((HERE / 'preparation-created.json').read_bytes())
    prepared = Path(source['root'])
    assert verify_seal(prepared) == source['seal_sha256']
    target = HERE / ('native-grammar-CPU-' + str(time.time_ns()))
    target.mkdir()
    (target / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (target / 'native_grammar_check.py').write_bytes((HERE / 'native_grammar_check.py').read_bytes())
    remote_root = '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + HERE.name + '/' + target.name
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in sorted((prepared / 'proposed-release').rglob('*.py')):
            if '__pycache__' not in file.parts:
                archive.writestr(file.relative_to(prepared).as_posix(), file.read_bytes())
        archive.writestr('primary-reference.json', (PREVIOUS / 'runtime-package/primary-reference.json').read_bytes())
        archive.writestr('native_grammar_check.py', (HERE / 'native_grammar_check.py').read_bytes())
    payload = buffer.getvalue()
    save(HERE / 'native-CPU-submission.json', dict(time=time.time(), output=str(target), remote_root=remote_root,
        preparation=source, package_sha256=hashlib.sha256(payload).hexdigest(),
        CPU_only_no_model_weights_or_GUI=True, once_only=True))
    prefix = 'PAYLOAD=' + repr(base64.b64encode(payload).decode()) + '\n'
    code = 'ROOT=' + repr(remote_root) + '\nORIGINAL=' + repr(OUTPUT) + '\n' + COMMON + r'''
import base64,io,zipfile,runpy
root=Path(ROOT);assert not root.exists();root.mkdir(parents=True,exist_ok=False)
assert os.getuid()==1033
with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD)))as archive:
 for name in archive.namelist():
  p=root/name;assert p.resolve().is_relative_to(root.resolve())
  p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb')as stream:stream.write(archive.read(name))
os.environ['CUDA_VISIBLE_DEVICES']=''
sys.path.insert(0,str(root))
import native_grammar_check
value=native_grammar_check.main(root,Path(ORIGINAL))
with(root/'receipt.json').open('x')as stream:json.dump(value,stream)
print(json.dumps(value,ensure_ascii=True))
'''
    try:
        output, operation = remote('3090', code, 'native-source-quote-grammar-CPU-only',
            timeout=55, private_prefix=prefix)
        receipt = json.loads(output)
        assert receipt['passed'] and receipt['new_model_GUI_capture_action_scorer_paid_calls'] == 0
        save(target / 'receipt.json', dict(receipt, operation=str(operation), preparation=source))
        save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
        result = dict(root=str(target), receipt_sha256=sha(target / 'receipt.json'),
                      seal_sha256=sha(target / 'seal.json'))
        save(HERE / 'native-CPU-completed.json', result)
        print(json.dumps(result))
    except BaseException as error:
        save(target / 'observation-failure.json', dict(error_type=type(error).__name__, error=str(error),
            remote_root=remote_root, no_experiment_terminal_retry=True, new_model_GUI_scorer_calls=0))
        save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
        raise


if __name__ == '__main__':
    main()
