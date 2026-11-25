"""Preserve the newline-only failed check and verify published original bytes."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    assert not (HERE / 'source-progress22-readback-created.json').exists()
    pointer = read(HERE / 'source-progress22-publication-created.json')
    publication = Path(pointer['publication'])
    out = HERE / ('source-progress22-readback-linked02-' + str(time.time_ns()))
    out.mkdir()
    original_check = (
        "note=(out/'new-head.md').read_bytes()\n"
        "for name in ['README.md','HANDOFF.md']:\n"
        " assert (base/name).read_bytes()==note+(out/'previous-heads'/name).read_bytes()\n"
    )
    (out / 'original-failed-readback-check.py').write_text(original_check, encoding='utf8', newline='\n')
    raw_note = (publication / 'new-head.md').read_bytes()
    prefix = (publication / 'new-head.md').read_text(encoding='utf8').encode('utf8')
    assert b'\r\n' in raw_note and b'\r\n' not in prefix
    assert raw_note.replace(b'\r\n', b'\n') == prefix
    save(out / 'original-readback-failure.json', {
        'type': 'AssertionError',
        'cause': 'Readback checker compared the CRLF write_text presentation copy with the LF note encoded directly into published headers. Preserve both original serializations; repair only the readback check.',
        'original_publisher_was_successful': True,
        'publication': str(publication), 'original_publication_seal_sha256': sha(publication / 'seal.json'),
        'new_model_GUI_scorer_calls': 0, 'authoritative_files_modified_by_repair': False,
    })
    assert sha(publication / 'status.json') == pointer['status_sha256']
    assert sha(publication / 'seal.json') == pointer['seal_sha256']
    for name, expected in read(publication / 'seal.json').items():
        assert sha(publication / name) == expected, name
    assert (BASE / 'full-gui-current.json').read_bytes() == (publication / 'status.json').read_bytes()
    for name in ['README.md', 'HANDOFF.md']:
        assert (BASE / name).read_bytes() == prefix + (publication / 'previous-heads' / name).read_bytes()
    status = read(publication / 'status.json')
    receipt = {
        'time': time.time(), 'publication_verified': True, 'three_heads_and_prior_snapshots_bound': True,
        'publication': str(publication), 'publication_seal_sha256': sha(publication / 'seal.json'),
        'all_publication_original_bytes_unchanged': True,
        'actual_header_prefix_reconstructed_from_original_note_text': True,
        'head_sha256': {name: sha(BASE / name) for name in ['README.md', 'HANDOFF.md', 'full-gui-current.json']},
        'confirmed_actions': status['confirmed_original_actions_total'],
        'audit_through': status['native_request_tensor_EOS_and_prefill_audit_completed_through_new32_request'],
        'goal': status['goal'], 'efficacy_established': status['efficacy_established'],
        'new_model_GUI_scorer_calls': 0,
    }
    save(out / 'receipt.json', receipt)
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    record = {'root': str(out), 'receipt_sha256': sha(out / 'receipt.json'), 'seal_sha256': sha(out / 'seal.json')}
    save(HERE / 'source-progress22-readback-created.json', record)
    print(json.dumps(dict(record, publication_verified=True, goal='active'), ensure_ascii=False))


if __name__ == '__main__':
    main()
