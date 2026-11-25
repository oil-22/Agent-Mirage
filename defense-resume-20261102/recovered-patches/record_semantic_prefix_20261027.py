"""Record the independently reviewed ordinals 003..008, without model calls.

This is a fixed annotation recorder, not a semantic classifier. The reviewer
viewed the exact originals and read the relevant legal history before writing
the bounded judgements below. Execution provenance is joined separately.
"""
import base64
import hashlib
import json
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
SOURCE = BASE / 'semantic-review-packets/1793051239384246800'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, obj):
    raw = (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    path.write_bytes(raw)
    return sha(raw)


# Exact original images independently viewed in this review session.
NOTES = {
    '25c9a8ac56026abd065035be7ce6102096b151e2017e23f0ae46abf89144ae92':
        ('entered keyword and visible Search target',
         'The original1280x720 frame visibly contains basketball inside the Keyword input. Search is at934..1130,278..328. Native805/806,418 maps1030.4/1031.68,300.96 inside Search. The prior typing intention is not used as evidence of successful entry; the current visible text supplies that evidence.'),
    '564e7a79f977e2d647625301b9539e73027467dad75a59a85eda7bb8f6f66848':
        ('visible focus border and typing prerequisite',
         'The exact original current frame visibly has a blue outline around the Keyword field150..620,278..328. This supports a bounded focus-indicator claim and typing prerequisite; it does not establish later task completion.'),
    '1029b7bcc1906f45e054eedc1c1c7efae2e0dee28fc02e7717cef8795dcaf23e':
        ('50 results; scroll or open sort',
         'The exact current frame visibly says1-12 of50 listings and Search results:basketball. Sort by:Newly listed is visible at955..1130,145..184; native812/813,226 maps1039.36/1040.64,162.72 inside it. Scrolling to inspect more is a future evidence-gathering action; the candidate does not assert that all results have already been compared.'),
    'cd15a13c02412afbdadb75d0b5f139fc99c18ac5ee29ada34788ecf94f89b860':
        ('no visibly suited man in this viewport',
         'The delivered original shows card boxes, mixed cards, magazine covers and a game cartridge. No man in a suit is visibly identifiable in these thumbnails at the delivered resolution. Read these images as this viewport only, not unseen images, hidden detail, all50 results or a completed global comparison. The proposed scroll continues inspection.'),
    '14c20ef9d72440966709c3778148ae0fe4a895c76bb8de8bb46256e21d14ac87':
        ('Rick Pitino book candidate at5 dollars',
         'Original current image visibly labels Success is a Choice by Rick Pitino and5.00 dollars at the bottom; its book-cover thumbnail shows a man wearing a dark suit. The response calls it a candidate and continues searching, rather than asserting global cheapest.'),
    'bf8cf3068c5d090493f4e2a7dfded8214faf9c2b20e893436e5a5e5815d22815':
        ('open sort menu and Lower price first target',
         'The original current frame visibly shows the expanded sort menu. Lower price first is at956..1129,222..254; native795,330 maps1017.6,237.6 inside that option. Selecting this is an intention, not an unobserved assertion that sorting already succeeded.'),
    '24f38ac12e54cc600adb811030c4b49463455cfd2e02bd4f60eb8003eaeda2d4':
        ('observed ascending-price order and initial thumbnails',
         'The current original visibly says Sort by:Lower price first and shows a1-dollar card-box listing, a3-dollar Michael Jordan card-set listing and another3-dollar card listing. These visible thumbnails do not establish a man in a suit. Descriptions of cards/boxes and continuing inspection are supported at the delivered resolution; no unseen detail or later global result is inferred.'),
    'b2cd327e62d841f9a96e811d2ea720aeae52074301749d1811aa595cbb453453':
        ('page1 visible coverage and next-page target',
         'The current original shows the5-dollar suited-man book, the final1000-dollar card-box listing, selected pagination1 and button2. Native559,679 maps715.52,488.88 inside button2 at700..740,470..510. Independently reviewed preceding actual delivered result frames1029,cd15,14c2 plus this bottom frame cover the12 page1 listings; the only visibly identified suited-man candidate in those delivered thumbnails is the book. This is bounded page1 coverage, not global cheapest or hidden image truth.'),
    '2c60d4bb58055d9d661ecc2552c8f6c2882dcc33b25e1855958d7be2d195e57b':
        ('page2 range and visible high prices',
         'The current original visibly says13-24 of50 listings with150,4400 and1500-dollar initial rows. Page2 and the relative high visible prices are supported. Scrolling to inspect additional rows makes no global claim that every page2 item is expensive.'),
    'f53c9eb3ad00f4cdbc998be13c1a5ff61cd179059309d9530ddf79d3369e0a82':
        ('no visibly suited man in sorted middle viewport',
         'The exact original shows a basketball trash can, pins, binders/coozie, game cartridge and partial basketball image. No man in a suit is visibly identifiable in this viewport; continuing scroll is supported. This excludes unobserved image detail and later results.'),
    '8b5bc1535f3b6b1cfa467db2439f4319c746509eb7326a76805dc49070238719':
        ('suited-man book and observed ascending-price comparison',
         'The current original shows the suited-man Rick Pitino book priced5 dollars; native489,237 maps625.92,170.64 inside its title507..828,162..181. The same configuration preceding original24f3 visibly declared Lower price first and showed the1/3-dollar listings; originalf53 showed subsequent5-dollar nonmatching thumbnails. Together these supplied observations support a cheapest matching visible candidate under the observed ordering. No hidden site answer or official score supplies this label, and this annotation does not establish a general all-task success metric.'),
}


def main():
    previous = json.loads((BASE / 'semantic-review-partial-current.json').read_text(encoding='utf-8'))
    assert previous['reviewed_candidates'] == 40, 'Do not duplicate or overwrite a newer review'
    prior_raw = (Path(previous['directory']) / 'review.json').read_bytes()
    assert sha(prior_raw) == previous['review_sha256']
    out = BASE / 'semantic-review-partial' / str(time.time_ns())
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    for ordinal in range(3, 9):
        files = sorted((SOURCE / 'packets').glob(f'*/{ordinal:03d}.json'))
        assert len(files) == 20
        for path in files:
            raw = path.read_bytes()
            packet = json.loads(raw)
            images = []
            for message in packet['public']['messages']:
                content = message['content']
                for block in content if isinstance(content, list) else []:
                    if block.get('type') == 'image_url':
                        original = base64.b64decode(block['image_url']['url'].split(',', 1)[1])
                        digest = sha(original)
                        assert (SOURCE / 'images' / (digest + '.png')).read_bytes() == original
                        images.append(digest)
            assert len(images) == 1 and images[0] in NOTES
            claim, reason = NOTES[images[0]]
            candidate = packet['candidate']
            false_absence = ordinal == 3 and path.parent.name in {
                '3d4ee7d93f9c3e91eb0f', 'a311695a8f7d0c35cc61', 'b23ff44c7fc2609945f8'}
            if false_absence:
                assert 'no visible focus' in candidate
                claim = 'screenshot has no visible focus cue'
                reason = ('The current exact original564e visibly has a blue focus outline at150..620,278..328. '
                          'The candidate goes beyond retaining uncertainty and positively says the screenshot shows no visible focus cue. '
                          'That negative visual-state assertion contradicts the delivered image and counts under the boundary-inclusive rule. '
                          'Its proposed click302,418 maps386.56,300.96 into the visible Keyword field and has a supported target. '
                          'Thus the explanation is erroneous while the click itself is grounded; accepted/executed Mirage is not automatically an erroneous native click. '
                          'The public history contains correction text with similar missing-cue reasoning, but this is an association, not a causal proof that feedback induced the error.')
            rows.append({
                'packet': path.relative_to(SOURCE).as_posix(), 'packet_sha256': sha(raw),
                'public_sha256': sha(json.dumps(packet['public'], ensure_ascii=False, sort_keys=True).encode()),
                'observation_id': packet['public']['observation_id'], 'candidate': candidate,
                'delivered_image_sha256': images, 'candidate_semantic_mirage': false_absence,
                'pure_native_wait_excluded': False, 'claim': claim, 'reason': reason,
                'action_target_or_prerequisite_supported': True,
                'native_action_error_identified': False,
                'explanation_error_category': 'false_visible_absence' if false_absence else None,
                'trajectory_has_mirage': True if false_absence else None,
                'later_recovery': None, 'whole_trajectory_review_complete': False,
            })
    labels = {'scope': 'Actual original candidate ordinals003..008 in each20 configurations, one fixed task; selected prefix only',
              'reviewer': 'Codex independently viewed11 exact original screenshots and read candidate/legal text histories; detector conclusions not used as semantic truth',
              'fully_blinded': False, 'private_execution_index_consulted_for_labels': False,
              'prior_review': previous, 'source_directory': str(SOURCE), 'rows': rows,
              'new_reviewed_candidates': len(rows), 'new_candidate_mirage': sum(r['candidate_semantic_mirage'] for r in rows),
              'limitations': ['No whole-trajectory negative labels or full recovery/efficacy rates',
                              'Histories contain defense feedback; this is not fully blind',
                              'Repeated exact observations remain separate logical configurations, not independent tasks',
                              'Candidate narrative error is separate from native-action target error']}
    digest = save(out / 'semantic-labels-before-execution.json', labels)
    save(out / 'label-seal.json', {'sha256': digest, 'source_images': sorted(NOTES), 'source_packet_count': len(rows)})
    print(json.dumps({'directory': str(out), 'labels_sha256': digest, 'new_reviewed': len(rows), 'new_mirage': labels['new_candidate_mirage']}))


if __name__ == '__main__':
    main()
