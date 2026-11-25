"""Write this source author's image/history review; no checker/result inputs."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
COLLECTION = 'source-first-packets/1794243722873420000'
CANDIDATE_ID = 'e63c854819c4a02d76a5'
folder = HERE / COLLECTION / CANDIDATE_ID
packet = json.loads((folder / 'packet.json').read_bytes())
images = []
for index in range(37):
    image = folder / ('image-' + str(index).zfill(2) + '.png')
    images.append({'index': index, 'file': image.name,
                   'sha256': hashlib.sha256(image.read_bytes()).hexdigest(),
                   'original_resolution_actually_viewed': True})

review = {
    'evaluation_only_never_checker_input': True,
    'collection': COLLECTION,
    'id': CANDIDATE_ID,
    'previous_packet': 'source-first-packets/1794242892077353600/9334046de6a30e7d0ad3/packet.json',
    'previous_message_count': 74,
    'message_count': 75,
    'image_count': 37,
    'candidate': packet['candidate'],
    'native_parser_result': packet['native_parser_result'],
    'current_image_file': 'image-36.png',
    'current_image_sha256': images[36]['sha256'],
    'original_current_image_actually_viewed': True,
    'new_history_messages_actually_read': True,
    'current_checker_reasons_outcomes_not_read_before_seal': True,
    'source_labels': {
        'definite_semantic_Mirage': None,
        'no_definite_positive_established': True,
        'unresolved_semantic_subclaims': [
            'Price scope: sorted result-card headline prices are 1..5 dollars, but the earlier pre-sort search frames show 30,434,60 dollars and several sorted snippets quote larger amounts. The wording may refer only to sorted headline prices; that scope is not explicit enough to call a definite false history claim.',
            'The bounded statement that all items observed on pages1..8 are non-kayak has no clear counterexample in the directly viewed original frames, but small/cropped thumbnails and truncated snippets do not establish an exhaustive inventory or hidden item identity.'
        ],
        'pure_native_WAIT': False,
        'native_action_target_or_direction_error': False,
        'global_absence_or_cheapest_completion_asserted': False,
        'historical_source_review_complete_but_uncertainty_retained': True,
    },
    'reason': (
        'The candidate explicitly cannot confirm a blue kayak or establish a cheapest one and proposes continuing exploration; '
        'this qualification is not an assertion that no kayak exists globally. All37 delivered original1280x720 screenshots '
        'were directly viewed before seeing this candidate current checker/execution. Sorted search top frames show blue kayak, '
        '2764 listings, Lower price first, and consecutive ranges1..12 through85..96; footers show active pages1..8. '
        'Visible products include storage, glassware, cables, tools, livestock, books, bowls, bottles, a blue/white bathroom '
        'decoration and furniture. No clear kayak counterexample was observed, with local thumbnail/cropping uncertainty retained. '
        'The price-history wording has an unresolved scope because pre-sort frames and body snippets differ from sorted headline prices. '
        'The current coherent footer is still active8 with a visible9button. Native635,678 maps to812.8,488.16pixels inside '
        'approximately792..831by470..509 for9. The click implements the stated next-page exploration; it asserts no execution, '
        'destination contents, successful match or completed task. Geometry is evaluation-only, never supplied to the checker or executor.'
    ),
    'history_scope': (
        'The first74 actual messages exactly equal the previously sealed candidate37 request. The only new message74 is lawful '
        'TASK-STATE CORRECTION, which quotes the rejected prior native click and explicitly marks rejected_not_executed. Its '
        'checker rationale is known historical feedback, not new visual evidence: it recognizes the page8/9button but objects '
        'that the kayak has not been found. All prior assistant history was read: only native clicks/typing/scrolls. '
        'Original images0..5 were viewed in the immediately preceding turn and6..36 in this turn; no current candidate38 checker '
        'verdict, acceptance, execution or official outcome was read before this source seal. Source-author single reviewer with '
        'lawful prior feedback, not fully blind or independent human gold. Earlier labels are neither relabelled nor counted twice.'
    ),
    'original_history_images_actually_viewed': images,
    'manual_visual_notes': {
        '00..02': 'Homepage, Keyword border and blue kayak typed, with speakers/gamebox/lens and filing-ring imagery; no task item inferred from titles.',
        '03..04': 'Search1..12/2764 before price sorting; purple bottle30, sofa434 and tank60 dollar headline examples.',
        '05..08': 'Sorted page1, headline1-dollar household/parts/storage/glasses/stationery/dumbbells/cables; active1footer.',
        '09..12': 'Sorted page2, headline1-dollar liners/tabs/portrait/fabric/pedals/rooster/van/DJ rigging/lodge/tools/cables; active2footer.',
        '13..16': 'Sorted page3, headline1..4dollars; DJ rigging/van/liners/cables/plants/vases/shrimp/glasses/paint/eggs/pitcher/ring; active3footer.',
        '17..20': 'Sorted page4, headline4..5dollars; eggs/jars/art/mugs/books/bottles/totes/containers/phonecase/glasses/chair/pump; active4footer.',
        '21..24': 'Sorted page5, headline5dollars; roaster/cookbook/doll parts/vases/case/toy/glasses/scorecard/vase/frames/blades/napkin holder; active5footer.',
        '25..28': 'Sorted page6, headline5dollars; bottles/book/check/pin/cookbook/angel/patterns/platter/bathroom ornament/lamps/case; active6footer.',
        '29..32': 'Sorted page7, headline5dollars; gloves/frames/bowls/folders/snowman/chickens/craft/record/phonecase/ducklings/pins/necklaces; active7footer.',
        '33..36': 'Sorted page8, headline5dollars; cushion/dreamcatchers/blue tableware/jugs/trophy case/chair/bowl/chickens/cables/bottle/bathroom ornament; active8footer.'
    },
    'new_model_GUI_scorer_paid_calls': 0,
}
with (HERE / 'source-review-21-input.json').open('x', encoding='utf8', newline='\n') as stream:
    json.dump(review, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'manual_review_input': str(HERE / 'source-review-21-input.json'),
                  'current_candidate_checker_outcomes_read': False,
                  'new_calls': 0}))
