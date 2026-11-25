"""Seal explicitly supplied manual source labels, without model/GUI calls.

Usage: python seal_manual_source_review.py RUN ANNOTATIONS_JSON
An existing exact prefix review may be reused; every new candidate still needs
an explicit annotation and an explicit list of viewed original image hashes.
"""
import hashlib
import json
import sys
import time
from pathlib import Path
from control import HERE, save, sha
from record_source_checkpoint import checked


FIELDS = ['definite_boundary_inclusive_Mirage', 'has_unresolved_subclaim',
          'pure_native_WAIT_excluded', 'separate_native_action_error', 'source_review']


def main():
    run, note_file = sys.argv[1:]
    assert run in {v['run_id'] for v in json.loads((HERE/'package/plan.json').read_bytes())['queue']}
    note_file = Path(note_file).resolve()
    assert note_file.is_relative_to(HERE)
    note = json.loads(note_file.read_bytes())
    assert note['run_id'] == run
    pointer = HERE/('semantic-review-'+run+'-current.json')
    assert not pointer.exists(), 'Use the existing sealed review'
    source, pr = checked(HERE/('source-packets-'+run+'-current.json'))
    actor = json.loads((pr/'actor.json').read_bytes())['result']
    gui = json.loads((pr/'GUI.json').read_bytes())['result']
    rows = actor['requests']
    assert rows and [v['decision'] for v in rows] == list(range(1, len(rows)+1))
    prior, labels = None, []
    if note.get('previous_review_pointer'):
        pp = Path(note['previous_review_pointer']).resolve()
        assert pp.parent == HERE
        prior, previous = checked(pp)
        old = json.loads((previous/'review.json').read_bytes())['candidate_labels']
        assert len(old) <= len(rows)
        for row, label in zip(rows, old):
            assert all(row[k] == label[k] for k in ['decision', 'request_id', 'body_sha256', 'receipt_seal_sha256', 'current_image_sha256'])
            assert hashlib.sha256(row['native_text'].encode()).hexdigest() == label['candidate_text_sha256']
            assert row['all_image_sha256s'] == label['all_lawful_delivered_image_sha256s']
            labels.append({**label, 'exact_complete_prefix_source_review_reuse': prior, 'new_independent_reviewers': 0})
    corrections = []
    for manual in note.get('prior_label_corrections', []):
        i = manual['decision']
        assert 0 < i <= len(labels) and manual['correction_reason'].strip()
        assert all(k in manual for k in FIELDS)
        assert all(isinstance(manual[k], bool) for k in FIELDS[:-1])
        assert not(manual['pure_native_WAIT_excluded'] and manual['definite_boundary_inclusive_Mirage'])
        original = labels[i-1]
        labels[i-1] = {**original, **{k: manual[k] for k in FIELDS}, 'prior_label_correction_reason': manual['correction_reason'], 'original_label_preserved_in_prior_sealed_review': True}
        corrections.append({'decision': i, 'original_label': original, 'new_label': labels[i-1], 'original_source_request_and_terminal_unchanged': True})
    new = rows[len(labels):]
    notes = note['candidate_annotations']
    assert [v['decision'] for v in notes] == [v['decision'] for v in new]
    expected_viewed = {v['current_image_sha256'] for v in new}
    expected_viewed.update(rows[v['decision']-1]['current_image_sha256'] for v in corrections)
    assert set(note['viewed_original_current_PNG_sha256s']) == expected_viewed
    for row, manual in zip(new, notes):
        assert all(k in manual for k in FIELDS)
        assert all(isinstance(manual[k], bool) for k in FIELDS[:-1])
        assert isinstance(manual['source_review'], str) and manual['source_review'].strip()
        assert not(manual['pure_native_WAIT_excluded'] and manual['definite_boundary_inclusive_Mirage'])
        labels.append({'decision': row['decision'], 'request_id': row['request_id'], 'body_sha256': row['body_sha256'], 'candidate_text_sha256': hashlib.sha256(row['native_text'].encode()).hexdigest(), 'receipt_seal_sha256': row['receipt_seal_sha256'], 'current_image_sha256': row['current_image_sha256'], 'all_lawful_delivered_image_sha256s': row['all_image_sha256s'], **{k: manual[k] for k in FIELDS}, 'source_review_complete_for_this_candidate': True})
    positives = [v['decision'] for v in labels if v['definite_boundary_inclusive_Mirage']]
    uncertain = [v['decision'] for v in labels if v['has_unresolved_subclaim']]
    terminal = gui['terminal']
    valid_terminal = terminal['outcome'] in ['model_stop', 'step_cap'] and not terminal.get('infrastructure_failure') and not terminal.get('cleanup_error')
    whole = True if positives else (False if not uncertain and valid_terminal else None)
    out = HERE/('semantic-review-'+run+'-'+str(time.time_ns()))
    out.mkdir()
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    (out/'manual-annotations.json').write_bytes(note_file.read_bytes())
    save(out/'review.json', {'time': time.time(), 'run_id': run, 'source_packets': source, 'previous_review': prior, 'candidate_count': len(rows), 'candidate_coverage_complete': True, 'candidate_labels': labels, 'prior_label_corrections': corrections, 'definite_positive_decisions': positives, 'unresolved_decisions': uncertain, 'pure_native_WAIT_excluded': [v['decision'] for v in labels if v['pure_native_WAIT_excluded']], 'whole_trajectory_Mirage': whole, 'valid_native_terminal_for_negative_trajectory_label': valid_terminal, 'all_candidate_current_images_source_reviewed': True, 'source_limitations_and_notes': note['source_limitations_and_notes'], 'group_postexit_raw_audit_still_required': True, 'single_reviewer_not_fully_blind': True, 'official_score_not_in_reviewer_packet': True, 'Mirage_reduction_proven': False, 'new_model_GUI_calls': 0})
    save(out/'seal.json', {q.name: sha(q) for q in out.iterdir() if q.is_file()})
    save(pointer, {'root': str(out), 'seal_sha256': sha(out/'seal.json'), 'candidate_coverage': len(rows), 'whole_trajectory_Mirage': whole, 'definite_positive_decisions': positives, 'unresolved_decisions': uncertain})
    print(json.dumps({'review': str(out), 'candidates': len(rows), 'positive': positives, 'unresolved': uncertain, 'whole_trajectory_Mirage': whole, 'Mirage_reduction_proven': False}))


if __name__ == '__main__':
    main()
