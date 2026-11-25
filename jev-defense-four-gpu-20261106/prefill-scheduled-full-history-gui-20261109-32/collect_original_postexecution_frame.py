"""Export an existing observation after a source-reviewed executed action."""
import argparse
import base64
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'full-history-gui-development-20261109-23'))
from remote_control import remote, save, sha


def main(joinpath, ident, ordinal):
    pointer = HERE / ('candidate' + str(ordinal) + '-postexecution-frame-created.json')
    assert not pointer.exists()
    assert sha(joinpath) == json.loads((joinpath.parent / 'seal.json').read_bytes())['join.json']
    joined = json.loads(joinpath.read_bytes())
    assert joined['all_source_labels_sealed_before_this_join']
    row = next(row for row in joined['rows'] if row['id'] == ident)
    assert row['accepted'] and row['executed']
    sourcepath = HERE / 'collect_candidate21_postexecution_frame_once.py'
    scope = {'__name__': 'original_frame_exporter_source_only', '__file__': str(sourcepath)}
    exec(compile(sourcepath.read_text(encoding='utf8'), str(sourcepath), 'exec'), scope)
    code = scope['CODE']
    before = 'c94c66947622a0224b5f'
    assert code.count(before) == 1
    code = code.replace(before, ident)
    output, operation = remote('4090', code, 'read-existing-original-frame-after-reviewed' + str(ordinal), timeout=55)
    value = json.loads(output)
    assert value['candidate_event_sha256'] == row['candidate_event_sha256']
    assert value['executed_event_sha256'] == row['executed_events'][0]['sha256']
    picture = base64.b64decode(value.pop('original_capture_png_base64'), validate=True)
    out = HERE / ('candidate' + str(ordinal) + '-postexecution-frame-' + str(time.time_ns()))
    out.mkdir()
    name = value['next_observation_id'].split('-', 1)[0] + '-originally-captured.png'
    assert name.split('-', 1)[0].isdigit()
    (out / name).write_bytes(picture)
    assert sha(out / name) == value['next_observation_current_image']['sha256']
    value.update(remote_operation=str(operation), source_sealed_execution_join=str(joinpath),
                 source_sealed_execution_join_sha256=sha(joinpath), image_requires_visual_review=True)
    save(out / 'receipt.json', value)
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    record = {'root': str(out), 'receipt_sha256': sha(out / 'receipt.json'), 'seal_sha256': sha(out / 'seal.json')}
    save(pointer, record)
    print(json.dumps(dict(record, next_observation=value['next_observation_id'], new_GUI_captures_or_actions=0), ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--join', type=Path, required=True)
    parser.add_argument('--id', required=True)
    parser.add_argument('--ordinal', type=int, required=True)
    args = parser.parse_args()
    assert len(args.id) == 20 and all(c in '0123456789abcdef' for c in args.id)
    assert 1 <= args.ordinal <= 70
    main(args.join.resolve(), args.id, args.ordinal)
