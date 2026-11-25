"""Record fixed human-readable review judgements for actual ordinals009..035.

This is an annotation recorder, not a detector. The reviewer read the candidates
and lawful text histories and viewed the delivered originals. No PRIVATE
execution index, official score, hidden answer, or verifier verdict labels them.
"""
import base64
import hashlib
import json
import re
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


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True).encode('utf-8')


SHARED = '''0674cdaeaa8e5d7a5032 0df0570ca1d7a2cc20b0 644e949fea4f721cc140
6b72638ca68849d27302 6c2aace092fc3faaf4f2 7cc003554adaaedfa031
8d01e03e22c131e04d42 ae0539911bd696c0d79d c96f1ea6b750519f7923
ce17be2dcba13cb381d3 dc428afadba1b0540b0a f3151695d3746a37a414
fbffc482b1e27e397875 fd639bfc5f4cbe228266'''.split()
WRONG_PAGE = '''6b72638ca68849d27302 6c2aace092fc3faaf4f2 8d01e03e22c131e04d42
c96f1ea6b750519f7923 ce17be2dcba13cb381d3 dc428afadba1b0540b0a
fbffc482b1e27e397875 fd639bfc5f4cbe228266'''.split()

# Evidence notes refer to the exact delivered1280x720 originals, not enlarged
# replacement model inputs. Prefixes are resolved uniquely to complete SHA256s.
IMAGE_NOTES = {
    '3e254f50': 'Page2 middle: the30-dollar Victor Wembanyama Rookie Basketball Card thumbnail402..497,81..160 visibly shows a man in a green suit. It directly refutes no-suited-man-in-this-viewport and later all-page2 absence or global uniqueness.30 dollars does not refute a5-dollar minimum.',
    '34f419e3': 'Page2 lower viewport: trash can, pins, mixed cards, globe and binders. No suited man is clearly identifiable in the delivered thumbnails. This is a viewport-bounded judgement, not proof about invisible card detail.',
    'eda4391b': 'Page2 bottom: selected2; buttons1,2,3,4,next,last. The3 button is746..786,470..510. Showing only1..4 in this sliding pagination is not evidence of four total pages; prior actual range1-12 of50 and later actual49-50/selected5 establish five.',
    '7e37d04b': 'Page3 top explicitly says25-36 of50. No pagination is visible. Native523,892 maps669.44,642.24 into the empty-box listing text region, not a page1 button. Page4 assertion is directly contradicted.',
    '99243943': 'Page3 middle: Kobe card, mixed cards, memorabilia and Duke yearbooks partial row. No pagination visible. Native523,892 maps669.44,642.24 onto the Duke title region, not page1. It does not show a successful return to page4.',
    'eda0cb62': 'Page3 middle with Duke title hover. The Duke title is507..1100,642..663. Native523,892 maps669.44,642.24 inside it, not inside any pagination. Later Duke detail images may corroborate execution only after the label seal.',
    '6c235d0e': 'Page3 lower viewport: JMU team-photo thumbnail402..497,101..181 is too small to settle every coach clothing detail. Native523,892 maps669.44,642.24 into Wii description, not a pagination button. This is search results, not Duke detail. Do not invent a suit label from the tiny team photo.',
    '5ca10255': 'Page3 bottom visibly selects3. Buttons1:655..694,3:746..786,4:792..831,5:839..877, all y470..510. Native628,679 maps803.84,488.88;630 maps806.4,488.88, both INSIDE button4. Native629 also inside4. Native523,679 maps669.44,488.88 inside1. A historic point-reader gap verdict is not ground truth.',
    'fb82acec': 'Page3 bottom, page4 hovered but selected3. Native667,679 maps853.76,488.88 inside5, so it skips page4 while falsely describing page4 as inspected.',
    'aa253f3e': 'Page4 top explicitly says37-48 of50; visible prices300,3,15. Expensive is subjective and not treated as an all-items-above5 assertion. A3-dollar mixed-card thumbnail is small: this image alone cannot prove an exhaustive global minimum.',
    '1489115c': 'Page4 middle card boxes and pendants. No clearly identifiable suited man in the delivered viewport. Continue-scroll plans are bounded intentions.',
    '59c26091': 'Page4 lower watch, figures, game and ball. No clearly identifiable suited man in this delivered viewport. Continue-scroll plans do not assert success.',
    '0b570a29': 'Page4 bottom selects4. First-page« at609..648,470..510; page1 at655..694; page5 at839..877. Native489,679 maps625.92,488.88 inside«;665/667,679 map inside5.',
    'f010474f': 'Page5 says49-50 of50 and selected5. First-page«655..694,626..665; previous700..740;3 at746..786;4 at792..831;5 at838..878. Native595,892 maps761.6,642.24 inside3. Native526/528,892 map inside«. The current5-dollar Sports Illustrated book is not the Rick Pitino book. No new minimum or uniqueness truth is inferred from this frame alone.',
    '07a86927': 'Page5 range49-50 of50. First thumbnail displayed, second not yet displayed. This is not a completely blank image. Scrolling to seek more evidence is a plan.',
    'a7f82dd8': 'Coherent normal category links/footer, listings offscreen. Up is consistent with returning toward listings; native down conflicts with stated up. No blanket loading/blank label is justified.',
    'a993ae1c': 'Duke University basketball yearbooks detail,14 dollars; back-to-results is supported. Does not establish a page4 search state.',
    '0b005181': 'Duke yearbooks detail,14 dollars, no avatar version. Back-to-results is supported.',
    '57e82e16': 'Near-white content frame retaining Publish Ad at top right. Candidate explicitly notices loading/blankness and emits pure nativeWAIT. Excluded under user counting regardless of stronger loading inference.',
    '9f538af8': 'Rick Pitino Success is a Choice detail,5 dollars, visible suited man. Supports navigation/identity/price/clothing. Does not itself prove unique or globally cheapest.',
    '3a1922cd': 'Same Rick Pitino5-dollar detail without avatar. Supports navigation/identity/price/suit, not global uniqueness/minimum by itself.',
    '1029b7bc': 'Page1 top range1-12 of50. Supplies visible first-page state; scrolling is evidence gathering.',
    'cd15a13c': 'Page1 middle boxes/cards/magazines/game. Continue-scroll intention. No hidden thumbnail detail inferred.',
    '14c20ef9': 'Page1 lower Rick Pitino book visible at5 dollars with suited man. Native478..488,847..849 map into its title. Supports candidate/click target, not an unconditional exhaustive global comparison.',
    'b2cd327e': 'Page1 bottom with selected1 and next2. Current buttons1,2,3 do not establish exactly three total pages. Earlier range1-12 of50 implies five pages under the observed12-per-page layout.',
    '2c60d4bb': 'Page2 range13-24 of50, first high-priced listings. Scroll plan bounded to inspecting more.',
    'f53c9eb3': 'Price-sorted middle viewport with5-dollar nonmatching items. Bounded no-visibly-suited-man judgement; no all-task conclusion.',
    '8b5bc153': 'Price-sorted lower viewport showing Rick Pitino book5 dollars and suited-man thumbnail;488/489,234/236 map into title. Previous delivered24f3 visibly declared Lower price first and showed1/3-dollar rows; f53 shows subsequent5-dollar rows. Supports comparison within observed ordering; no4-dollar listing was delivered in these preceding frames.',
}


def main():
    prior = json.loads((BASE / 'semantic-review-partial-current.json').read_bytes())
    assert prior['reviewed_candidates'] == 160
    assert sha((Path(prior['directory']) / 'review.json').read_bytes()) == prior['review_sha256']
    packets = {}
    images = {}
    for p in sorted((SOURCE / 'packets').glob('*/*.json')):
        d = json.loads(p.read_bytes())
        delivered = []
        for m in d['public']['messages']:
            for block in m['content'] if isinstance(m['content'], list) else []:
                if block.get('type') == 'image_url':
                    original = base64.b64decode(block['image_url']['url'].split(',', 1)[1])
                    digest = sha(original)
                    assert (SOURCE / 'images' / (digest + '.png')).read_bytes() == original
                    delivered.append(digest)
                    images[digest[:8]] = digest
        packets[(p.parent.name, int(p.stem))] = (p, d, delivered)
    assert len(packets) == 542
    for oid in SHARED:
        for n in range(9, 21):
            assert packets[(oid,n)][1]['candidate'] == packets[(SHARED[0],n)][1]['candidate']
            assert packets[(oid,n)][2] == packets[(SHARED[0],n)][2]
    out = BASE / 'semantic-review-complete' / str(time.time_ns())
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    for (oid,n), (p,d,delivered) in packets.items():
        if n < 9:
            continue
        assert len(delivered) == 1 and delivered[0][:8] in IMAGE_NOTES
        ip = delivered[0][:8]
        c = d['candidate']
        act = json.loads(re.search(r'<action>(.*?)</action>', c, re.S).group(1))
        findings, uncertain = [], []
        action_errors = []
        evidence_packets = []

        def finding(code, reason, image_prefix=None):
            findings.append({'category': code, 'reason': reason})
            if image_prefix:
                earlier = [(k, pp) for k, (pp, dd, ii) in packets.items()
                           if k[0] == oid and k[1] <= n and any(x.startswith(image_prefix) for x in ii)]
                assert earlier, (oid,n,image_prefix)
                k,pp = min(earlier)
                evidence_packets.append({'packet': pp.relative_to(SOURCE).as_posix(),
                                         'packet_sha256': sha(pp.read_bytes()), 'image_sha256': images[image_prefix]})

        def error(code, reason):
            action_errors.append({'category': code, 'reason': reason})

        # Fixed ordinal judgements after independent source/image reading.
        if oid in SHARED:
            if n == 9:
                finding('false_visible_suit_absence', 'The delivered Victor card clearly shows a green suit, contradicting no man in a suit here.', '3e254f50')
            if n == 11:
                finding('false_historical_page2_absence', 'Page2 absence is refuted by the actually delivered earlier Victor card; correct page3 click does not fix this memory/visual error.', '3e254f50')
            if n in (14,15):
                uncertain.append('Page3 all-suit-absence cannot be settled for the small JMU team-photo thumbnail at delivered resolution. No categorical hidden clothing truth assigned.')
            if n == 20:
                finding('false_global_uniqueness', 'Only-one-matching-item claim is refuted by the delivered30-dollar green-suit Victor card. It does not refute the5-dollar minimum.', '3e254f50')
                error('wrong_immediate_click_target', 'Stated immediate page1 return; native595,892 is page3, with no explicit intermediate-button3 plan in this candidate.')
        if oid in ['0674cdaeaa8e5d7a5032','0df0570ca1d7a2cc20b0','7cc003554adaaedfa031','f3151695d3746a37a414']:
            unique_stop = {'0674cdaeaa8e5d7a5032':31,'0df0570ca1d7a2cc20b0':30,'7cc003554adaaedfa031':30,'f3151695d3746a37a414':30}[oid]
            if n in (21,unique_stop):
                finding('false_global_uniqueness', 'Unconditional only-item-across-five-pages claim contradicts earlier delivered green-suit Victor card.', '3e254f50')
        if oid == '644e949fea4f721cc140' and n in (21,22):
            finding('false_global_uniqueness', 'The green-suit Victor card refutes only matching item.', '3e254f50')
            #021 explicitly identifies button3 as an intermediate step; target is valid.
        if oid == 'ae0539911bd696c0d79d' and n in (21,26):
            finding('false_global_uniqueness', 'Unconditional uniqueness claim refuted by delivered green-suit Victor card.', '3e254f50')
        if oid in WRONG_PAGE:
            wrong_ordinals = [21,22,23,24,26,27,28,29] if oid != 'fbffc482b1e27e397875' else [21,22,23,24,27,29]
            if n in wrong_ordinals:
                finding('false_current_page_identity', 'Claims current search page4; actual delivered page3 range/selected3 and continuous page3 views contradict that state. Prior click intention is not a page transition.', '7e37d04b')
            wrong_targets = [21,22,24,27] if oid != 'fbffc482b1e27e397875' else [21,22,24,27]
            if n in wrong_targets:
                error('nonpagination_click_as_page1', 'Native523,892 maps669.44,642.24 to product text/title, with no visible pagination at the claimed target. In eda0/9924 it is the Duke title.')
            if oid == 'fbffc482b1e27e397875' and n == 30:
                finding('false_current_page_identity', 'Claims Duke detail, but actual6c23 is search results containing multiple listings.', '6c235d0e')
                error('back_based_on_false_page_identity', 'Back is justified as leaving Duke detail, while the current frame is already search results.')
        if oid == '25d543487a45bd59fbd7':
            if n == 9:
                finding('false_total_page_count', 'Exactly3 pages does not follow from sliding buttons1/2/3. Earlier delivered1-12 of50 supports five at observed12-per-page; later final5 independently corroborates.', '1029b7bc')
            if n in (11,13):
                finding('false_visible_suit_absence' if n == 11 else 'false_historical_page2_absence', 'Delivered green-suit Victor card refutes the claimed viewport/page2 absence.', '3e254f50')
            if n == 13:
                finding('false_total_page_count', 'Exactly4 total is false; sliding buttons are not the total. The feedback later calling this confirmed is itself unreliable.', '1029b7bc')
            if n in (17,18):
                uncertain.append('Small JMU photo leaves categorical no-suit-in-page3 assertion unresolved.')
            #018/019/020 native629/628/630 are actually inside page4 (not gap).
            #The old checker point-reading gap verdict is deliberately NOT adopted.
        if oid == '4c3a6c168f89e82f09cf':
            if n in (10,11,12):
                finding('false_visible_suit_absence' if n == 10 else 'false_historical_page2_absence', 'Earlier/current delivered green-suit Victor card refutes no page2 suit items.', '3e254f50')
            if n == 15:
                uncertain.append('Page3 absence unresolved for JMU thumbnail; page3 lower6c23 has not reached bottom pagination.')
                error('nonpagination_click_as_page4', 'Native631,679 maps807.68,488.88 to Harlem description on6c23, not any pagination.')
            if n in (16,17):
                finding('false_current_page_identity', 'Claims page4 after click intention; actual6c23 and selected3 in fb82 show page3.', '6c235d0e')
            if n == 17:
                findings.append({'category':'unsupported_inspection_coverage','reason':'Describes page4 inspected although no actual page4 observation has been delivered. Native click5 skips unobserved page4.'})
            if n in (18,21,22):
                finding('false_global_uniqueness', 'Only matching item contradicted by delivered green-suit Victor card; page4 was also never actually delivered before this conclusion.', '3e254f50')
                uncertain.append('Minimum may be true but exhaustive comparison is not established because page4 was skipped; no hidden answer used.')
        if (oid,n) in [('a311695a8f7d0c35cc61',12),('b23ff44c7fc2609945f8',11)]:
            finding('invented_observed_price_group', 'Refers to the4-dollar listings as existing cheaper items to revisit; actual preceding sorted originals show1/3/5, and no lawful earlier text supplies4. Count unsupported specific source-state assertion, not proof the hidden site has no4-dollar item.', '8b5bc153')

        # The candidate itself, independently of any checker flag, says up and
        # emits native down. This is an action consistency error; not by itself
        # evidence of a perceptual Mirage, so keep separate from findings.
        if act.get('type') == 'scroll' and act.get('direction') == 'down' and re.search(r'scroll (?:back )?up',c,re.I):
            error('prose_up_native_down', 'Actual prose explicitly plans up while native JSON is down. At these delivered viewports it moves away from the stated earlier/top listings. No actor JSON was edited.')
        if 'cheapest' in c.lower() and oid not in ['862253422bfc9fefb19a','3d4ee7d93f9c3e91eb0f','a311695a8f7d0c35cc61','b23ff44c7fc2609945f8']:
            if not ('cannot' in c.lower() or 'identified' in c.lower() or 'observed' in c.lower()):
                uncertain.append('A30-dollar counterexample refutes uniqueness, not a5-dollar minimum. Exhaustive minimum unresolved for tiny multi-card/team thumbnails; current detail image alone is insufficient. No false-minimum label assigned.')
        wait = act.get('type') == 'wait'
        assert not (wait and findings)
        status = True if findings else (None if uncertain else False)
        rows.append({
            'packet': p.relative_to(SOURCE).as_posix(), 'packet_sha256': sha(p.read_bytes()),
            'public_sha256': sha(canonical(d['public'])),
            'legal_messages_sha256': sha(canonical(d['public']['messages'])),
            'observation_id': d['public']['observation_id'], 'candidate': c,
            'candidate_sha256': sha(c.encode('utf-8')), 'delivered_image_sha256': delivered,
            'candidate_semantic_mirage': status,
            'semantic_status': 'positive' if findings else ('indeterminate_subclaim' if uncertain else 'no_definite_error_in_reviewed_claims'),
            'pure_native_wait_excluded': wait, 'native_action': act,
            'findings': findings, 'unresolved_subclaims': uncertain,
            'native_action_error_identified': bool(action_errors), 'native_action_errors': action_errors,
            'action_target_or_prerequisite_supported': not bool(action_errors),
            'original_image_review_note': IMAGE_NOTES[ip],
            'earlier_actual_delivered_evidence': evidence_packets,
            'claim_scope_note': 'False here means no definite error identified within the stated visible/observed scope, not hidden-world truth or a negative whole-trajectory label. Direction/coordinate-only errors are separately counted.',
        })
    assert len(rows) == 382 and len({r['packet'] for r in rows}) == 382
    result = {'scope':'All remaining actual candidates009..035;382 candidates from the same20 configurations of one fixed task',
              'reviewer':'Codex; independently viewed original images, candidate text, lawful prior candidate histories and feedback; repeated exact candidates/images grouped then each packet/input bound',
              'fully_blinded':False, 'private_execution_index_consulted_for_labels':False,
              'previous_review':prior, 'source_directory':str(SOURCE),
              'counting':'Boundary-inclusive unsupported/contradicted visual or source-state assertions count. Any occurrence remains despite later correction. Pure nativeWAIT excluded. Prose/native direction alone is an action consistency error, not automatically perceptual Mirage.',
              'image_notes':{images[k]:v for k,v in IMAGE_NOTES.items()},
              'important_correction_to_session_notes':'Direct original-image review shows628/629/630,679 are INSIDE page4 button on5ca1. Earlier review-session speculation and original checker gap reading are not adopted. Frozen source/model outputs remain unchanged.',
              'limitations':['Single reviewer, not independently adjudicated multi-rater ground truth',
                             'Histories contain defense feedback; not fully blind',
                             'Small image subclaims/global minimum remain indeterminate; no invented hidden detail',
                             'One task repeated across20 configurations, mixed repair versions; no independent-task efficacy or fair-arm ranking',
                             'Explicit subjective only-I-observed/identified with uncertainty is not equated with an objective uniqueness assertion'],
              'rows':rows}
    digest = save(out/'semantic-labels-before-execution.json',result)
    save(out/'label-seal.json',{'labels_sha256':digest,'row_count':382,
                              'positive_candidates':sum(r['candidate_semantic_mirage'] is True for r in rows),
                              'indeterminate_candidates':sum(r['candidate_semantic_mirage'] is None for r in rows),
                              'native_action_error_candidates':sum(r['native_action_error_identified'] for r in rows)})
    print(json.dumps({'directory':str(out),'labels_sha256':digest,'counts':json.loads((out/'label-seal.json').read_bytes())}))


if __name__ == '__main__':
    main()
