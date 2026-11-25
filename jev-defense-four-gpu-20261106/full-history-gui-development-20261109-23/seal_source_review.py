"""Seal explicit source-authored labels; never derive semantic labels from a gate.

The human/model reviewer must view original inputs before supplying the draft.
This utility verifies source bindings, not the truth of the authored judgments.
"""
import argparse
import copy
import json
from pathlib import Path
import time

from remote_control import HERE, save, sha


def main(draft):
    draft = draft.resolve()
    marker = draft.with_name(draft.stem + '-sealed.json')
    assert not marker.exists(), 'Do not reseal a completed source review'
    data = json.loads(draft.read_bytes())
    collection = (HERE / data['collection_relative']).resolve()
    assert collection.parent == HERE / 'source-first-packets'
    assert sha(collection / 'collection.json') == data['collection_sha256']
    for name, expected in json.loads((collection / 'seal.json').read_bytes()).items():
        assert sha(collection / name) == expected
    receipt = json.loads((collection / 'collection.json').read_bytes())
    assert {r['id'] for r in data['rows']} == {r['id'] for r in receipt['packets']}
    assert data['all_original_images_and_complete_actual_message_sources_reviewed'] is True
    images = set()
    for row in data['rows']:
        packet = json.loads((collection / row['id'] / 'packet.json').read_bytes())
        assert row['definite_semantic_Mirage'] in [True, False, None]
        assert isinstance(row['unresolved_semantic_subclaims'], list)
        assert type(row['pure_native_WAIT_excluded']) is bool
        assert not (row['pure_native_WAIT_excluded'] and row['definite_semantic_Mirage'])
        row.update(packet_sha256=sha(collection / row['id'] / 'packet.json'),
             candidate_event_sha256=packet['candidate_event_sha256'], candidate_text_sha256=packet['candidate_text_sha256'],
             actual_full_main_request_sha256=packet['actor_request_body_sha256'],
             all_original_current_and_historical_image_SHA_viewed=[im['sha256'] for im in packet['actual_delivered_images']],
             execution_acceptance_official_success_not_used_as_gold=True)
        images.update(row['all_original_current_and_historical_image_SHA_viewed'])
    out = HERE / ('source-review-' + str(time.time_ns()))
    out.mkdir()
    result = copy.deepcopy(data)
    result.update(schema='full-history-GUI23-source-first-partial-review-v1', time=time.time(),
         collection=str(collection), draft_sha256=sha(draft), original_distinct_images_viewed=sorted(images),
         reviewed_candidates_in_this_collection=len(data['rows']), unreviewed_candidates_in_this_collection=0,
         definite_positive_candidates=sum(row['definite_semantic_Mirage'] is True for row in data['rows']),
         all32_track_coverage_or_effect_established=False, new_model_GUI_scorer_paid_calls=0, goal='active')
    save(out / 'review.json', result)
    (out / 'source-draft.json').write_bytes(draft.read_bytes())
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    save(marker, {'review': str(out), 'review_sha256': sha(out / 'review.json'), 'seal_sha256': sha(out / 'seal.json')})
    print(json.dumps({'review': str(out), 'review_sha256': sha(out / 'review.json'),
          'reviewed_candidates': len(data['rows']), 'trajectory_any_Mirage': None}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--draft', type=Path, required=True)
    main(parser.parse_args().draft)
