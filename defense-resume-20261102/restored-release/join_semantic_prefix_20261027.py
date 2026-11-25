"""Join sealed semantic labels to separately verified execution provenance."""
import copy
import hashlib
import json
from pathlib import Path

from remote import remote

BASE = Path(__file__).resolve().parent
OUT = BASE / 'semantic-review-partial/1793104440363853700'
SOURCE = BASE / 'semantic-review-packets/1793051239384246800'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, obj):
    raw = (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    path.write_bytes(raw)
    return sha(raw)


def main():
    assert not (OUT / 'review.json').exists(), 'Immutable review already exists'
    raw = (OUT / 'semantic-labels-before-execution.json').read_bytes()
    assert sha(raw) == json.loads((OUT / 'label-seal.json').read_bytes())['sha256']
    labels = json.loads(raw)
    prior_ptr = labels['prior_review']
    assert json.loads((BASE / 'semantic-review-partial-current.json').read_bytes()) == prior_ptr
    old_raw = (Path(prior_ptr['directory']) / 'review.json').read_bytes()
    assert sha(old_raw) == prior_ptr['review_sha256']
    old = json.loads(old_raw)
    index_raw = (SOURCE / 'PRIVATE-source-and-execution-index.json').read_bytes()
    index = json.loads(index_raw)
    # Read-only remote revalidation of all exported event/terminal sources.
    code = 'INDEX=' + repr([{k: r[k] for k in ['opaque_id', 'attempt', 'complete_sha256', 'events_sha256']} for r in index]) + '\n' + '''
import hashlib,json,pathlib,time
rows=[]
for row in INDEX:
 p=pathlib.Path(row['attempt'])
 for filename,key in [('events.jsonl','events_sha256'),('complete.json','complete_sha256')]:
  assert hashlib.sha256((p/filename).read_bytes()).hexdigest()==row[key],(row['opaque_id'],filename)
 rows.append({'opaque_id':row['opaque_id'],'events_and_terminal_sha_verified':True})
print(json.dumps({'time':time.time(),'read_only':True,'rows':rows}))
'''
    verification = json.loads(remote(code, host='4090', timeout=60))
    save(OUT / 'source-event-terminal-verification.json', verification)
    lookup = {c['packet']: (r, c) for r in index for c in r['candidates']}
    new = copy.deepcopy(labels['rows'])
    for row in new:
        run, source = lookup[row['packet']]
        assert source['packet_sha256'] == row['packet_sha256']
        assert sha((SOURCE / row['packet']).read_bytes()) == row['packet_sha256']
        for field in ['accepted', 'environment_action_executed', 'source_request_seq', 'source_candidate_seq']:
            row[field] = source[field]
        row['source_events_sha256'] = run['events_sha256']
        row['source_complete_sha256'] = run['complete_sha256']
        row['source_candidate_sha256'] = source['source_candidate_sha256']
    by_packet = {r['packet']: r for r in new}
    for row in new:
        if row['explanation_error_category'] == 'false_visible_absence':
            followup = row['packet'].replace('/003.json', '/004.json')
            next_row = by_packet[followup]
            assert not next_row['candidate_semantic_mirage'] and next_row['accepted'] and next_row['environment_action_executed']
            row['later_recovery'] = {'scope': 'next-candidate focus statement and typing only',
                                     'packet': followup, 'packet_sha256': next_row['packet_sha256'],
                                     'description': 'Next actual delivered frame retains the blue border; candidate explicitly recognizes it and types basketball. Does not erase earlier false absence or establish whole-task recovery.'}
    rows = old['rows'] + new
    assert len(rows) == 160 and len({r['packet'] for r in rows}) == 160
    review = {
        'scope': 'First eight actual candidate ordinals in each20 configurations, one fixed task; incomplete trajectories',
        'reviewer': labels['reviewer'], 'fully_blinded': False,
        'source_directory': str(SOURCE), 'prior_review': prior_ptr,
        'semantic_labels_precede_execution_join_sha256': sha(raw),
        'source_private_index_sha256': sha(index_raw),
        'selected_candidates': len(rows), 'all_candidates': 542,
        'candidate_mirage': sum(r['candidate_semantic_mirage'] for r in rows),
        'excluded_pure_wait': sum(r['pure_native_wait_excluded'] for r in rows),
        'accepted_and_executed_mirage': sum(r['candidate_semantic_mirage'] and r['accepted'] and r['environment_action_executed'] for r in rows),
        'new_false_visual_absence_explanations': 3,
        'new_false_absence_with_grounded_native_click': 3,
        'new_native_action_target_errors': 0,
        'unreviewed_candidates': 542-len(rows), 'full_audit_complete': False,
        'limitations': labels['limitations'] + ['Accepted/executed candidate Mirage is not necessarily a wrong native action',
                                               'Later focus recovery is bounded; task recovery and terminal semantics remain unreviewed'],
        'rows': rows,
    }
    digest = save(OUT / 'review.json', review)
    files = {p.name: sha(p.read_bytes()) for p in OUT.iterdir() if p.is_file()}
    save(OUT / 'sha256.json', files)
    current = {'directory': str(OUT), 'review_sha256': digest, 'reviewed_candidates': len(rows),
               'all_candidates': 542, 'full_audit_complete': False}
    save(BASE / 'semantic-review-partial-current.json', current)
    print(json.dumps({**current, **{k:review[k] for k in ['candidate_mirage','accepted_and_executed_mirage','unreviewed_candidates']}}))


if __name__ == '__main__':
    main()
