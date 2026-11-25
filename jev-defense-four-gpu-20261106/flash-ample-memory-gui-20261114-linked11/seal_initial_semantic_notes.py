"""Seal single-reviewer source notes before any execution join; no rate claim."""
import json
import time
from pathlib import Path
from control import HERE, save, sha

source = HERE / 'semantic-packets-1794649527001467200'
index = json.loads((source / 'review-index.json').read_bytes())
seal = json.loads((source / 'seal.json').read_bytes())
assert len(index['packets']) == 30
for name, expected in seal.items():
    assert sha(source / name) == expected
notes = {}
def add(numbers, **data):
    for n in numbers:
        notes.setdefault(n, {}).update(data)

add([2, 10], visual_note='Original564e has a blue Keyword focus outline; focus assertion and subsequent typing are supported.')
add([4, 12], visual_note='Originalb226 reads1–12of2764, with decanter/sofa/aquarium; loose-search wording is qualified as an appearance/hypothesis, not established search implementation.')
add([6, 14, 22], unresolved_subclaims=['Search implementation/loose keyword matching inferred from a few visible results; implementation is not established by the supplied screenshot.'])
add([7, 15], native_action_direction_conflict=True, exact_conflicting_quote='Let me scroll up to verify there are no kayaks among the cheapest listings.',
    native_direction='down', visual_note='Original27a shows Mustang parts, ceramic scenes, storage boxes and blue glass; visible absence does not establish whole-site absence.',
    unresolved_subclaims=['Scope of no actual kayaks; qualified site-wide alternative is not automatically a definite false observation.'])
add([8, 16], unresolved_subclaims=['The STOP answer extends absence from a few visible listings to all2764 results and asserts an unseen search implementation.'],
    exact_scope_quote='but none of them are actually kayaks.',
    visual_note='Originale0c shows four miscellaneous items. It does not establish absence across all2764 results. Separate later Boats frames show actual kayaks, but are not legal input to either clean STOP candidate.',
    semantic_Mirage_label=None)
add([18], visual_note='Deliveredc600 is the plain-outline screenshot, but candidate only plans typing and makes no definite focus-state assertion.')
add([23], visual_note='Original27a has a readable Boats link at approximately(180,139); native(140,194) maps to(179.2,139.68).')
add([24], visual_note='Originald149 shows Boats,1–12of99, lower price first and a$50 kayak; plan explicitly seeks color verification.')
add([25], visual_note='Original39aa shows a$50 olive/gray-green inflatable kayak; candidate says olive/green, not blue.')
add([26], unresolved_subclaims=['Small$70 thumbnail has yellow outer hull and blue/gray interior against blue water; initial blue characterization is followed by an explicit plan to verify. Color scope is uncertain, not automatically a definite Mirage.'], semantic_Mirage_label=None)
add([27], visual_note='Original8283 shows the$70 yellow outer hull with gray/blue interior; yellow/gray description is supported.')
add([28], visual_note='History really includes$50 olive/green and$70 yellow/gray detail inspections; the$65 rack text is visible in originald149.')
add([29], visual_note='Originale8db shows$85 yellow,$85 green,$90 purple and$115 yellow thumbnails; assertions describe this visible viewport.')
add([30], visual_note='Original5fc has a visibly blue$185 Kayak in Akron and costlier listings below; native(408,119) maps inside its visible image.',
    unresolved_subclaims=['Cheapest blue across the whole site is stronger than the visible category ordering and sampled earlier color checks; global minimum remains unverified.'], semantic_Mirage_label=None)

rows = []
for entry in index['packets']:
    packet = json.loads((source / entry['file']).read_bytes())
    n = int(entry['packet_id'][1:])
    item = {'packet_id': entry['packet_id'], 'packet_sha256': entry['sha256'],
            'candidate_source_response_sha256': packet['source_response_sha256'],
            'full_legal_history_and_original_image_chain_reviewed': True,
            'review_status': 'single-reviewer source notes; no execution join',
            'semantic_Mirage_label': None,
            'native_action_direction_conflict': False,
            'unresolved_subclaims': [],
            'default_observation': 'No additional definite visual-state error identified in the examined literal assertions; this note is not a global no-Mirage certificate.'}
    item.update(notes.get(n, {}))
    rows.append(item)
dest = HERE / ('initial-source-review-notes-' + str(time.time_ns()))
dest.mkdir()
save(dest / 'notes.json', {'source_packets': str(source), 'source_seal_sha256': sha(source / 'seal.json'),
     'candidate_texts_read': 30, 'original_images_independently_viewed': 13,
     'image_scope': 'All13 original exported PNGs viewed at original resolution, no generated/cropped substitutes.',
     'reviewer_count': 1, 'fully_blind': False, 'old_T000_three_card_results_remain_separate': True,
     'labels_are_preliminary_not_Mirage_gold': True, 'completed_semantic_Mirage_labels': 0,
     'definite_native_direction_conflicts_in_source': 2, 'executed_error_count_not_joined': None,
     'Mirage_rate': None, 'Mirage_reduction': None, 'new_model_GUI_calls': 0, 'rows': rows})
save(dest / 'seal.json', {'notes.json': sha(dest / 'notes.json')})
print(json.dumps({'source_notes': str(dest), 'texts_read': 30, 'images_viewed': 13,
                  'completed_semantic_labels': 0, 'new_model_GUI_calls': 0}))
