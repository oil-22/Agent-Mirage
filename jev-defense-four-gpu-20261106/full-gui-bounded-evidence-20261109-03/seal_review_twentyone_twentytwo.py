"""Seal source-first human/model review before the per-candidate private join."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
source = HERE / 'source-first-packets' / '1794207642081539600'
target = HERE / 'semantic-review-candidates-twentyone-twentytwo-01'
target.mkdir(exist_ok=False)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
rows = []
reasons = {
    '20bf45cc7241fe4f4dbd': (
        True, 'current_person_clothing_false_absence',
        'The actual complete current screenshot visibly contains the Victor card at '
        'the top of the results. Its image shows a man in a green suit jacket, '
        'shirt and tie; categorical none show a man in a suit is false. The four '
        'displayed prices30/50/20000/22 are all greater than the prior observed5, '
        'and native DOWN matches the stated exploration. The error is a visual '
        'absence assertion, not a wrong native scroll or a proved global-minimum '
        'error. The auxiliary output contains mostly titles/prices and a wrong '
        'sidebar/text association, omitting the person. Omission does not establish '
        'absence; auxiliary causation is not established.'),
    '0a5034555449f5316bfb': (
        False, None,
        'The original delivered screenshot is byte-identical to the prior candidate. '
        'The displayed prices and comparison with the prior5 remain grounded. '
        'Candidate explicitly leaves appearance and complete page coverage unknown '
        'and proposes matching DOWN. This uncertainty is not another categorical '
        'absence assertion. No new definite error observed; correction cannot erase '
        'the preceding boundary-positive occurrence.'),
}
for name, (positive, category, reason) in reasons.items():
    folder = source / name
    seal = json.loads((folder / 'seal.json').read_bytes())
    for filename, expected in seal.items():
        assert sha(folder / filename) == expected
    packet = json.loads((folder / 'packet.json').read_bytes())
    assert hashlib.sha256(packet['candidate'].encode()).hexdigest() == packet['candidate_text_sha256']
    assert len(packet['actual_delivered_images']) == 1
    assert sha(folder / 'image-00.png') == packet['actual_delivered_images'][0]['sha256']
    rows.append({
        'id': name, 'packet_path': str(folder / 'packet.json'),
        'packet_sha256': sha(folder / 'packet.json'),
        'candidate_event_sha256': packet['candidate_event_sha256'],
        'candidate_text_sha256': packet['candidate_text_sha256'],
        'actual_actor_wire_sha256': packet['actual_actor_wire_sha256'],
        'actual_full_original_images': [v['sha256'] for v in packet['actual_delivered_images']],
        'definite_candidate_Mirage': positive, 'category': category,
        'unresolved_semantic_subclaims': [], 'native_action_error_observed': False,
        'pure_native_WAIT': False, 'review_reason': reason,
        'actual_auxiliary_reading_in_input': True,
    })
labels = {
    'time': time.time(), 'reviewer': 'root, single reviewer',
    'complete_actual_original_images_viewed': True,
    'full_actual_actor_messages_read': True,
    'source_first_before_per_candidate_private_execution_join': True,
    'fully_blind': False,
    'exposure': 'Aggregate live counts and prior terminal known. The actual image '
                'and candidate21 were reviewed before candidate22 lawful history '
                'revealed its correction feedback; that feedback was read before '
                'this seal. Source labels rely on the original image, not checker '
                'verdicts. No private execution/scorer join used.',
    'later_recovery_does_not_erase_occurrence': True,
    'rows': rows,
}
with (target / 'labels.json').open('x', encoding='utf8') as stream:
    json.dump(labels, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
with (target / 'seal.json').open('x', encoding='utf8') as stream:
    json.dump({'labels.json': sha(target / 'labels.json')}, stream, indent=2)
    stream.write('\n')
print(json.dumps({'labels': str(target / 'labels.json'),
                  'sha256': sha(target / 'labels.json'), 'new_reviewed_candidates': 2,
                  'new_definite_boundary_positive': 1, 'new_model_GUI_calls': 0}))
