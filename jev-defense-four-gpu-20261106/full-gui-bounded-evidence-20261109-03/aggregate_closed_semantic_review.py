"""Aggregate sealed labels; do not create labels or rerun the old experiment."""
import base64
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
PACKETS = HERE / 'source-first-packets/1794210405309279900'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    with p.open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n')


labels, sources = {}, []
for p in sorted(HERE.glob('semantic-review-*/labels.json')):
    seal = json.loads((p.parent / 'seal.json').read_bytes())
    assert sha(p) == seal['labels.json']
    value = json.loads(p.read_bytes())
    sources.append({'path': str(p), 'sha256': sha(p), 'candidates': len(value['rows'])})
    for row in value['rows']:
        assert row['id'] not in labels
        labels[row['id']] = (row, p)

index = json.loads((PACKETS / 'PRIVATE-source-index.json').read_bytes())
assert len(index) == len(labels) == 35
assert len({row['id'] for row in index}) == 35
rows, tracks = [], {}
for number, item in enumerate(index, 1):
    cid = item['id']; label, source = labels[cid]
    p = PACKETS / cid / 'packet.json'; packet = json.loads(p.read_bytes())
    for key in ['id', 'candidate_event_sha256', 'candidate_text_sha256', 'actual_actor_wire_sha256']:
        assert label[key] == packet[key], (cid, key)
    assert hashlib.sha256(packet['candidate'].encode()).hexdigest() == label['candidate_text_sha256']
    images = packet['actual_delivered_images']
    assert [im['sha256'] for im in images] == label['actual_full_original_images']
    for image in images:
        assert hashlib.sha256(base64.b64decode(image['raw_base64'])).hexdigest() == image['sha256']
    old_packet = label.get('packet_path')
    matches = [Path(old_packet)] if old_packet else list((HERE / 'source-first-packets').glob('*/' + cid + '/packet.json'))
    assert any(q.is_file() and sha(q) == label['packet_sha256'] for q in matches), cid
    key = 'clean/noaux' if '--no-observer/' in item['attempt'] else 'clean/oneaux'
    row = {'number': number, 'id': cid, 'track': key, 'candidate_seq': item['candidate_seq'],
           'candidate_event_sha256': label['candidate_event_sha256'],
           'candidate_text_sha256': label['candidate_text_sha256'],
           'actual_actor_wire_sha256': label['actual_actor_wire_sha256'],
           'actual_full_original_images': label['actual_full_original_images'],
           'sealed_label_path': str(source), 'sealed_label_sha256': sha(source),
           'definite_candidate_Mirage': label['definite_candidate_Mirage'],
           'unresolved_semantic_subclaims': label['unresolved_semantic_subclaims'],
           'native_action_error_observed': label['native_action_error_observed'],
           'pure_native_WAIT': label['pure_native_WAIT']}
    rows.append(row)
    tracks.setdefault(key, []).append(row)

summary = {}
for key, group in tracks.items():
    positives = [r for r in group if r['definite_candidate_Mirage'] and not r['pure_native_WAIT']]
    unknown = [r for r in group if r['unresolved_semantic_subclaims']]
    summary[key] = {'reviewed_candidates': len(group), 'unreviewed_candidates': 0,
                    'definite_positive_candidates': len(positives),
                    'candidate_numbers_with_definite_positive': [r['number'] for r in positives],
                    'candidates_with_unresolved_subclaims': len(unknown),
                    'pure_native_WAIT_excluded': sum(r['pure_native_WAIT'] for r in group),
                    'trajectory_any_Mirage': True if positives else None if unknown else False,
                    'trajectory_status': 'technical_failure' if key.endswith('oneaux') else 'regeneration_cap',
                    'official_score': 0,
                    'fair_reduction_estimand_available': False}
assert summary['clean/noaux']['reviewed_candidates'] == 10
assert summary['clean/noaux']['trajectory_any_Mirage'] is None
assert summary['clean/oneaux']['reviewed_candidates'] == 25
assert summary['clean/oneaux']['candidate_numbers_with_definite_positive'] == [18, 21, 24]

target = HERE / ('closed-semantic-coverage-' + str(time.time_ns())); target.mkdir()
result = {'schema': 'closed35-semantic-coverage-v1', 'time': time.time(),
          'coverage_complete': True, 'reviewed_candidates': 35, 'unreviewed_candidates': 0,
          'reviewer': 'root, one reviewer', 'fully_blind': False,
          'labels_were_sealed_before_each_candidate_private_execution_join': True,
          'aggregation_creates_no_new_semantic_labels': True, 'label_sources': sources,
          'current_public_packet_export': str(PACKETS), 'rows': rows, 'tracks': summary,
          'one_occurrence_counts_despite_rejection_or_recovery': True,
          'unresolved_is_not_noMirage': True, 'relative_reduction': None,
          'planned_tracks': 4, 'started_terminal_tracks': 2, 'unstarted_stale_tracks': 2,
          'efficacy_established': False, 'goal': 'active', 'new_model_GUI_scorer_paid_calls': 0}
save(target / 'review.json', result)
save(target / 'seal.json', {'review.json': sha(target / 'review.json')})
print(json.dumps({'path': str(target / 'review.json'), 'sha256': sha(target / 'review.json'),
                  'tracks': summary}, ensure_ascii=False))
