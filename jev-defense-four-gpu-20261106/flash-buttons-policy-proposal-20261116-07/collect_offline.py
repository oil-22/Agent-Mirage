"""Collect sealed raw metadata; audited actual tensor files remain intact remotely."""
import base64
import hashlib
import io
import json
import time
import zipfile
from pathlib import Path
from control_offline import prepared
from remote_util import HERE, remote, save, sha


def main():
    assert not (HERE / 'collection-current.json').exists()
    audit = json.loads((HERE / 'completed-audit-current.json').read_bytes())
    assert sha(Path(audit['root']) / 'seal.json') == audit['seal_sha256']
    _, _, manifest = prepared()
    code = '''
import base64,hashlib,io,json,zipfile
from pathlib import Path
root=Path(O);assert(root/'postexit-seal.json').exists()
blob=io.BytesIO();paths=[q for q in root.rglob('*')if q.is_file()and q.suffix!='.pt']
with zipfile.ZipFile(blob,'w',zipfile.ZIP_DEFLATED)as archive:
 for q in paths:archive.write(q,q.relative_to(root).as_posix())
print(json.dumps({'zip_base64':base64.b64encode(blob.getvalue()).decode(),'zip_sha256':hashlib.sha256(blob.getvalue()).hexdigest(),'files':len(paths),'actual_forward_tensor_files_preserved_remote':20}))
'''
    raw, operation = remote('3090', 'O=' + repr(manifest['output']) + '\n' + code, 'collect-twenty-sealed-wire-native-and-probability-records', timeout=180)
    value = json.loads(raw); data = base64.b64decode(value['zip_base64'], validate=True)
    assert hashlib.sha256(data).hexdigest() == value['zip_sha256']
    root = HERE / ('collected-' + str(time.time_ns())); root.mkdir()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in archive.namelist():
            target = root / name; assert target.resolve().is_relative_to(root.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as handle: handle.write(archive.read(name))
    final = json.loads((root / 'postexit-seal.json').read_bytes()); skipped = []
    for name, expected in final.items():
        target = root / name
        if target.is_file():
            assert sha(target) == expected, name
        else:
            assert name.endswith('/actual-forward-inputs.pt'); skipped.append(name)
    assert len(skipped) == 20
    save(root / 'collection.json', {'operation': str(operation), 'zip_sha256': value['zip_sha256'], 'original_members_collected_and_verified': len(final) - len(skipped), 'actual_tensor_files_remain_remote_and_already_CPU_audited': skipped, 'complete_CPU_audit': audit, 'new_model_GUI_calls': 0})
    save(root / 'seal.json', {q.relative_to(root).as_posix(): sha(q) for q in root.rglob('*') if q.is_file()})
    save(HERE / 'collection-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps({'collected': str(root), 'metadata_files': len(final) - 20, 'actual_tensor_files_verified_and_preserved_remote': 20}))


if __name__ == '__main__':
    main()
