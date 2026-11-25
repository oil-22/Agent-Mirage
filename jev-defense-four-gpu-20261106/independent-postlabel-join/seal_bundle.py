import hashlib
import json
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXCLUDED = {'manifest.json', 'seal.json', 'seal.sha256'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def put(path, value):
    path.write_bytes(json.dumps(value, ensure_ascii=False, indent=2).encode() + b'\n')


def verify():
    manifest_path = ROOT / 'manifest.json'
    seal_path = ROOT / 'seal.json'
    manifest = json.loads(manifest_path.read_bytes())
    seal = json.loads(seal_path.read_bytes())
    assert seal['manifest_sha256'] == sha(manifest_path)
    assert (ROOT / 'seal.sha256').read_text().strip() == f'{sha(seal_path)}  seal.json'
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name not in EXCLUDED}
    assert actual == {entry['path'] for entry in manifest['files']}
    for entry in manifest['files']:
        path = ROOT / entry['path']
        assert path.stat().st_size == entry['bytes']
        assert sha(path) == entry['sha256'], entry['path']
    for name, digest in seal['primary_artifact_sha256s'].items():
        assert sha(ROOT / name) == digest
    print(json.dumps({'verified': True, 'payload_files': len(manifest['files']), 'seal_sha256': sha(seal_path), 'manifest_sha256': sha(manifest_path), 'primary_artifact_sha256s': seal['primary_artifact_sha256s']}, ensure_ascii=False))


if '--verify' not in sys.argv:
    assert not any((ROOT / name).exists() for name in EXCLUDED), 'Refuse to replace an existing seal'
    files = sorted((p for p in ROOT.rglob('*') if p.is_file()), key=lambda p: p.relative_to(ROOT).as_posix())
    manifest = {'schema': 'sha256-artifact-manifest-v1', 'created_at_utc': datetime.now(timezone.utc).isoformat(), 'files': [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in files]}
    put(ROOT / 'manifest.json', manifest)
    seal = {'schema': 'independent-postlabel-join-seal-v1', 'sealed_at_utc': datetime.now(timezone.utc).isoformat(), 'manifest_sha256': sha(ROOT / 'manifest.json'), 'primary_artifact_sha256s': {name: sha(ROOT / name) for name in ('audit.json', 'summary.json', 'brief.zh.md', 'joined-candidates.csv')}, 'unchanged_frozen_label_sha256s': {batch: sha(ROOT / 'sources' / f'labels-batch{batch}.json') for batch in ('01', '02', '03')}, 'semantic_labels_changed': False, 'new_model_calls': 0, 'gui_actions': 0, 'private_answer_files_opened': False, 'followup_rule': 'Any correction must be an appended separately sealed addendum; preserve this bundle.'}
    put(ROOT / 'seal.json', seal)
    (ROOT / 'seal.sha256').write_text(f'{sha(ROOT / "seal.json")}  seal.json\n', encoding='ascii')
    for path in ROOT.rglob('*'):
        if path.is_file():
            path.chmod(stat.S_IREAD)

verify()
