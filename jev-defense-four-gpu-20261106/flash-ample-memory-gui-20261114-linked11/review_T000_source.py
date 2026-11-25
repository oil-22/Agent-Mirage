"""Source-bound preliminary review; retain uncertainty despite official success."""
import json
import time
from control import HERE, save, sha

old = HERE / 'semantic-packets-1794649527001467200'
new = HERE / 'semantic-packets-1794650264888473300'
notes = HERE / 'initial-source-review-notes-1794649909984216700'
old_notes = {v['packet_id']: v for v in json.loads((notes / 'notes.json').read_bytes())['rows']}
for root in [old, new, notes]:
    for name, expected in json.loads((root / 'seal.json').read_bytes()).items():
        assert sha(root / name) == expected
rows = []
for number in range(1, 15):
    current = json.loads((new / f'packets/p{number:05}.json').read_bytes())
    previous = json.loads((old / f'packets/p{number+16:05}.json').read_bytes())
    assert current['source_body_sha256'] == previous['source_body_sha256']
    assert current['candidate_exact_text'] == previous['candidate_exact_text']
    rows.append({'packet_id': current['packet_id'], 'packet_sha256': sha(new / f'packets/p{number:05}.json'),
                 'reuse_scope': 'Exact complete legal input and candidate text; source notes only, not a new independent reviewer or inference.',
                 'prior_packet_id': previous['packet_id'], 'source_note': old_notes[previous['packet_id']]})
final = json.loads((new / 'packets/p00015.json').read_bytes())
rows.append({'packet_id': 'p00015', 'packet_sha256': sha(new / 'packets/p00015.json'),
             'current_original_image_independently_viewed': '05709314e6e80466a56ea0dc68d5761d377b8439958d2f81da83b4d7a1860d3c',
             'supported': ['Bright blue kayak', '$185', 'Kayak title', 'City of Akron, Ohio', '2023/11/01',
                           '115in/250lb is visible in the preceding original5fc listing text, rather than established by the final photograph alone'],
             'unresolved': ['Whole-site cheapest/all cheaper kayak colors remain stronger than inspected category evidence; color scope of the $70 thumbnail was already uncertain.'],
             'semantic_Mirage_label': None})
dest = HERE / ('T000-preliminary-source-review-' + str(time.time_ns()))
dest.mkdir()
save(dest / 'review.json', {'source_packets': str(new), 'source_seal_sha256': sha(new / 'seal.json'),
     'candidate_source_notes_covered': 15, 'new_complete_candidate_images': 12,
     'prior_original_image_review_reused_by_complete_input_identity': 14,
     'new_final_original_image_independently_viewed': True, 'reviewer_count': 1,
     'fully_blind': False, 'official_result_known_before_review': True,
     'semantic_Mirage_label_complete': False, 'whole_trajectory_Mirage_label': None,
     'unresolved_not_counted_as_no_Mirage': True,
     'comparison': 'Unpaired T000 stale-gate diagnostic; not included in seven-task complete pairs or evidence of a Flash treatment effect.',
     'new_model_GUI_calls': 0, 'rows': rows})
save(dest / 'seal.json', {'review.json': sha(dest / 'review.json')})
print(json.dumps({'review': str(dest), 'candidate_source_notes': 15,
                  'semantic_label_complete': False, 'Mirage_reduction': None}))
