"""Linked local envelope requested by root; preserve earlier preparation."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_bytes())


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


source = ROOT / 'source-first-compact-four-peer-notes-02'
expected = '688f27b2fa0f28b31f3e3cf5632efe1316f3dcaee364407478fcf94d078485c1'
assert sha(source / 'seal.json') == expected
target = HERE / 'source-first-labels-envelope-plainmap-linked02'
target.mkdir(exist_ok=False)
for row in read(source / 'seal.json')['entries']:
    original = source / row['path']
    assert original.resolve().is_relative_to(source.resolve())
    assert sha(original) == row['sha256'] and original.stat().st_size == row['bytes']
    with (target / row['path']).open('xb') as stream:
        stream.write(original.read_bytes())
    assert sha(target / row['path']) == row['sha256']
with (target / 'original-source-seal.json').open('xb') as stream:
    stream.write((source / 'seal.json').read_bytes())
write_new(target / 'envelope-provenance.json', {
    'original_source_root': str(source), 'original_source_seal_sha256': expected,
    'source_entries_verified_individually': True, 'source_file_bytes_unchanged': True,
    'scope': 'plain map seal for unchanged worker.verify_seal; no semantic label edits',
    'linked_prior_files_list_preparation': str(HERE / 'source-first-labels-envelope-02'),
    'model_GUI_network_requests': 0, 'labels_supplied_to_model': False,
})
write_new(target / 'seal.json', {path.name: sha(path) for path in sorted(target.iterdir()) if path.is_file()})
value = read(HERE / 'builder-inputs.final.json')
value['source_labels']['local_root'] = str(target)
value['source_labels']['seal_sha256'] = sha(target / 'seal.json')
write_new(HERE / 'builder-inputs.plainmap-linked02.json', value)
print(json.dumps({'source_labels_local_root': str(target), 'source_labels_seal_sha256': sha(target / 'seal.json'),
                  'submitted': False, 'prior_local_preparation_preserved': True}))
