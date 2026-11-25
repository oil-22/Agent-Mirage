"""Join current GUI outcomes only after verifying immutable source-only reviews."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

from orchestrate import HERE, GUIROOT, remote, save, sha


def verify_seal(folder):
    seal = json.loads((folder / 'seal.json').read_bytes())
    for name, expected in seal.items():
        path = folder / name
        assert path.resolve().is_relative_to(folder.resolve())
        assert sha(path) == expected, name
    return sha(folder / 'seal.json')


def main(reviews):
    labels, targets, sources = {}, [], []
    for folder in reviews:
        folder = folder.resolve()
        assert folder.parent == HERE
        seal = verify_seal(folder)
        review = json.loads((folder / 'review.json').read_bytes())
        assert review['independent_current_checker_execution_score_join_not_performed']
        for label in review['rows']:
            assert label['id'] not in labels
            packetpath = Path(label['public_source_packet'])
            assert packetpath.name == 'packet.json'
            collection = packetpath.parent.parent
            assert collection.parent == HERE / 'source-first-packets'
            verify_seal(collection)
            assert sha(packetpath) == label['packet_sha256']
            packet = json.loads(packetpath.read_bytes())
            assert packet['checker_labels_current_acceptance_execution_scoring_private_delivery_excluded']
            for field in ['candidate_event_sha256', 'candidate_text_sha256', 'actor_request_body_sha256']:
                assert packet[field] == label[field]
            assert hashlib.sha256(packet['candidate'].encode()).hexdigest() == label['candidate_text_sha256']
            index = json.loads((collection / 'PRIVATE-source-index.json').read_bytes())
            source = next(row for row in index if row['id'] == label['id'])
            assert source['candidate_text_sha256'] == label['candidate_text_sha256']
            assert source['actor_request_body_sha256'] == label['actor_request_body_sha256']
            targets.append(dict(source, candidate_event_sha256=label['candidate_event_sha256']))
            labels[label['id']] = label
        sources.append(dict(review=str(folder), review_sha256=sha(folder / 'review.json'), seal_sha256=seal))
    original = HERE.parent / 'full-history-gui-development-20261109-23/join_sealed_source_reviews.py'
    spec = importlib.util.spec_from_file_location('unchanged_source_only_outcome_join', original)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    code = 'ROOT=' + repr(GUIROOT) + '\nROWS=' + repr(targets) + '\n' + module.SOURCE
    output, operation = remote('4090', code, 'linked31-join-sealed-source-labels-with-actual-outcomes', timeout=55)
    joined = json.loads(output)
    assert len(joined['rows']) == len(labels)
    source_by_id = {row['id']: row for row in targets}
    for row in joined['rows']:
        label = labels[row['id']]
        assert row['candidate_event_sha256'] == label['candidate_event_sha256']
        row.update(sealed_source_label=label, original_attempt=source_by_id[row['id']]['attempt'])
    root = HERE / ('post-review-join-' + str(time.time_ns()))
    root.mkdir()
    joined.update(schema='linked31-post-source-seal-execution-join-v1', time=time.time(),
                  source_reviews=sources, remote_operation=str(operation),
                  original_remote_join_source_sha256=sha(original),
                  all_source_labels_sealed_before_this_join=True,
                  source_labels_unchanged=True, full_trajectory_label_or_effect_established=False,
                  goal='active')
    (root / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(root / 'join.json', joined)
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    result = dict(join=str(root), join_sha256=sha(root / 'join.json'), seal_sha256=sha(root / 'seal.json'),
                  reviewed_candidates=len(labels), accepted=sum(row['accepted'] for row in joined['rows']),
                  executed=sum(row['executed'] for row in joined['rows']),
                  definite_semantic_errors=sum(label['candidate_semantic_mirage'] is True for label in labels.values()),
                  source_labels_unchanged=True, trajectory_any_Mirage=None, new_model_GUI_scorer_calls=0)
    save(HERE / ('post-review-join-created-' + root.name.rsplit('-', 1)[1] + '.json'), result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--review', type=Path, action='append', required=True)
    main(parser.parse_args().review)
