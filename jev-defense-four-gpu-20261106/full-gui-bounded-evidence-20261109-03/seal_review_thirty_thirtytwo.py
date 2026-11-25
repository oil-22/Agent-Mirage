"""Seal source-first review of three newly delivered page-four candidates."""
from pathlib import Path
import hashlib
import json
import time

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'source-first-packets' / '1794209795617233000'
TARGET = HERE / 'semantic-review-candidates-thirty-thirtytwo-01'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

definitions = [
    ('c023f389341cad4d40af',
     'Current original first-results frame literally reads37-48 of50. Len Bias300, '
     'vintage cards3 and Dr Seuss clock15 are visible. The prominent poster depicts '
     'an athlete in sportswear; no definite suited-person counterexample identified. '
     'The small card collection and printed clock detail cannot establish exhaustive '
     'absence. Page4 is consistent with earlier actually delivered page3 and the '
     'visible count; native DOWN matches the stated exploration.',
     ['Whether every small figure on the vintage-card collection or printed clock lacks a suit remains unresolved.']),
    ('0a32324bb2763b4527e3',
     'Three NBA card boxes85/75/75 and silver pendant10 are visible in the complete '
     'image. Titles and prices are grounded. Small printed people on the boxes '
     'are insufficient for a categorical clothing exclusion. No definite suited '
     'counterexample identified. The auxiliary mostly repeats titles and prices, '
     'which does not establish all visual content. Native DOWN is consistent.',
     ['Exhaustive clothing absence across the small printed card-box images remains unresolved.']),
    ('8265ef08b216ce405ca4',
     'Complete current original shows watch20, Nene bobblehead10, game cartridge5 '
     'and Kentucky mini ball5. The visible bobblehead wears sportswear; object '
     'thumbnails do not establish a definite suited-person counterexample. Tiny '
     'printed cartridge artwork remains unresolved for an exhaustive exclusion. '
     'Names/prices and native DOWN are grounded. No global minimum or completed '
     'navigation is asserted.',
     ['Fine printed people or clothing in the small cartridge artwork remains unresolved.']),
]

TARGET.mkdir(exist_ok=False)
rows = []
for name, reason, unknown in definitions:
    folder = SOURCE / name
    for filename, expected in json.loads((folder / 'seal.json').read_bytes()).items():
        assert sha(folder / filename) == expected, filename
    packet = json.loads((folder / 'packet.json').read_bytes())
    assert hashlib.sha256(packet['candidate'].encode()).hexdigest() == packet['candidate_text_sha256']
    assert sha(folder / 'image-00.png') == packet['actual_delivered_images'][0]['sha256']
    rows.append({
        'id': name, 'packet_path': str(folder / 'packet.json'),
        'packet_sha256': sha(folder / 'packet.json'),
        'candidate_event_sha256': packet['candidate_event_sha256'],
        'candidate_text_sha256': packet['candidate_text_sha256'],
        'actual_actor_wire_sha256': packet['actual_actor_wire_sha256'],
        'actual_full_original_images': [im['sha256'] for im in packet['actual_delivered_images']],
        'definite_candidate_Mirage': False,
        'category': None, 'unresolved_semantic_subclaims': unknown,
        'native_action_error_observed': False, 'pure_native_WAIT': False,
        'review_reason': reason,
    })
value = {
    'time': time.time(), 'reviewer': 'root, single reviewer',
    'complete_actual_original_images_viewed': True,
    'full_actual_actor_messages_read': True,
    'repeated_unchanged_messages_compared_exactly_and_read_once_not_truncated': True,
    'source_first_before_per_candidate_private_execution_join': True,
    'fully_blind': False,
    'exposure': 'Earlier aggregate progress and preceding outcomes known. Full lawful '
                'histories contain earlier checker corrections. Original images viewed '
                'individually. No private per-candidate execution join or future scorer '
                'read for these three before sealing.',
    'one_occurrence_counts_despite_recovery_and_WAIT_excluded': True,
    'unresolved_is_not_negative_or_noMirage': True, 'rows': rows,
}
with (TARGET / 'labels.json').open('x', encoding='utf8') as stream:
    json.dump(value, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
with (TARGET / 'seal.json').open('x', encoding='utf8') as stream:
    json.dump({'labels.json': sha(TARGET / 'labels.json')}, stream, indent=2)
    stream.write('\n')
print(json.dumps({'labels': str(TARGET / 'labels.json'),
                  'sha256': sha(TARGET / 'labels.json'),
                  'new_reviewed_candidates': 3, 'new_definite_positive': 0,
                  'unresolved_cases': 3, 'new_actual_model_GUI_calls': 0}))
