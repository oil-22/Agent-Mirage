"""Seal review of new actual candidates before their private execution joins."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
source = HERE / 'source-first-packets' / '1794209232216035000'
target = HERE / 'semantic-review-candidates-twentythree-twentynine-01'
target.mkdir(exist_ok=False)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
definitions = [
    ('e3b52e9c89143d3401b9', False, None,
     ['Categorical suit absence inside the small multi-card collage is unresolved.'],
     'Current original frame has trash basket5, Olympic pins5, a dense cards montage500, '
     'globe150 and a partially cropped Bucknell5 row. Names and prices are grounded, and '
     'native DOWN matches exploration. No definite suited-person counterexample is '
     'identified in this frame, but the tiny cards do not establish exhaustive absence. '
     'Auxiliary text samples are not evidence of all visual content.'),
    ('0d9c05556968f5a2e1f0', True, 'historical_page_person_false_absence', [],
     'None of the listings on page2 showed a man in a suit is false relative to the '
     'earlier actually delivered original3e254 frame: Victor card30 visibly contains a '
     'man in a green suit. Current globe/binders footer cannot erase that source. '
     'The current selected page2, end of list and native page3 click are separately '
     'grounded:594,678 maps760.32,488.16 inside3 at747..785,470..510. '
     'This is a repeated historical false absence, not a native wrong-target error.'),
    ('8d47eb930c639eb343f7', False, None,
     ['The small cropped preceding montage at the top is not fully interpretable.'],
     'Candidate explicitly retains uncertainty about all page2. Current readable globe '
     'and binders images do not depict people, while the narrow cropped prior row '
     'cannot establish an exhaustive appearance claim. The page3 point remains inside3. '
     'No new definite error; withdrawal does not erase candidate24.'),
    ('425f13152acb95835535', False, None,
     ['Fine printed imagery on the small glasses/ball packaging cannot prove an exhaustive clothing exclusion.'],
     'Current complete first-results frame literally reads25-36 of50 and selected '
     'context is page3. Titles and25/100/50 prices are visible. Thumbnails show glasses, '
     'a ball/packaging and empty cases; no definite suited-person counterexample '
     'identified. DOWN matches the plan. Small printed details remain unresolved.'),
    ('2d17206ce4ce01434b49', False, None,
     ['Absence of suits across all people on the small card montage and cropped Duke cover remains unresolved.'],
     'Current125/100/2000/14 prices and titles are literal. The prominent first card '
     'shows a basketball player, not an identified suited person. Other tiny cards and '
     'the cropped cover do not permit exhaustive exclusion. No definite counterexample '
     'is identified here; DOWN is consistent. Unknown is not noMirage.'),
    ('0894917aca1ce8b7bed2', False, None,
     ['Business clothing of every person in the tiny two JMU team photos remains unresolved.'],
     'Literal JMU20/cards25/program10/Wii150 titles and prices match the complete image. '
     'The team photographs contain multiple small figures whose clothing cannot all '
     'be established. Candidate categorical absence is unresolved, not certified true '
     'and not automatically a definite false claim. Native DOWN is consistent.'),
    ('5d504c4f0f0149a5cec7', False, None, [],
     'Current original footer shows Wii150 and glove25, selected3, numbered1..5 and '
     'next arrow without the earlier skip-to-last arrow. The actually delivered '
     'preceding first-results frame shows25-36 of50. These cues are consistent with '
     'five pages; this does not reuse the earlier erroneous total3 or invent a '
     'missing page capacity. Current object-only thumbnails do not show a suited '
     'person. Native632,678 maps808.96,488.16 inside visible4 at792..831,470..510. '
     'No definite error observed; no global cheapest or task-success claim is made.'),
]
rows = []
for name, positive, category, unresolved, reason in definitions:
    folder = source / name
    seal = json.loads((folder / 'seal.json').read_bytes())
    for filename, expected in seal.items():
        assert sha(folder / filename) == expected
    packet = json.loads((folder / 'packet.json').read_bytes())
    assert hashlib.sha256(packet['candidate'].encode()).hexdigest() == packet['candidate_text_sha256']
    assert sha(folder / 'image-00.png') == packet['actual_delivered_images'][0]['sha256']
    rows.append({
        'id': name, 'packet_path': str(folder / 'packet.json'),
        'packet_sha256': sha(folder / 'packet.json'),
        'candidate_event_sha256': packet['candidate_event_sha256'],
        'candidate_text_sha256': packet['candidate_text_sha256'],
        'actual_actor_wire_sha256': packet['actual_actor_wire_sha256'],
        'actual_full_original_images': [image['sha256'] for image in packet['actual_delivered_images']],
        'definite_candidate_Mirage': positive, 'category': category,
        'unresolved_semantic_subclaims': unresolved,
        'native_action_error_observed': False, 'pure_native_WAIT': False,
        'review_reason': reason,
    })
earlier = HERE / 'source-first-packets' / '1794207642081539600' / '20bf45cc7241fe4f4dbd' / 'packet.json'
labels = {
    'time': time.time(), 'reviewer': 'root, single reviewer',
    'complete_actual_original_images_viewed': True,
    'full_actual_actor_messages_read': True,
    'repeated_unchanged_messages_read_once_and_compared_exactly_not_truncated': True,
    'source_first_before_per_candidate_private_execution_join': True,
    'fully_blind': False,
    'exposure': 'Aggregate progress and previous outcomes known. Actual lawful '
                'histories include prior corrections, including the candidate24 '
                'correction visible while reading candidate25. Original images were '
                'viewed first. No private execution joins or future scorer used.',
    'earlier_actually_delivered_counterexample_packet': str(earlier),
    'earlier_counterexample_packet_sha256': sha(earlier),
    'one_occurrence_counts_despite_recovery_and_WAIT_excluded': True,
    'rows': rows,
}
with (target / 'labels.json').open('x', encoding='utf8') as stream:
    json.dump(labels, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
seal = {'labels.json': sha(target / 'labels.json')}
with (target / 'seal.json').open('x', encoding='utf8') as stream:
    json.dump(seal, stream, indent=2)
    stream.write('\n')
print(json.dumps({'labels': str(target / 'labels.json'),
                  'sha256': sha(target / 'labels.json'), 'new_reviewed_candidates': 7,
                  'new_definite_boundary_positive': 1, 'actual_model_GUI_calls': 0}))
