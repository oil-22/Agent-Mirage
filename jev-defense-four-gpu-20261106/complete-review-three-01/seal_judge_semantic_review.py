"""Root's complete, unblinded source-bound review. Does not alter experimental data."""
import json,hashlib
from pathlib import Path
from collections import Counter
root=Path(__file__).parent;src=root/'judge-semantic-reading-linked02'
index=json.loads((src/'index.json').read_bytes());rows=[]
notes={
6:('source_compatible_focus','Blue Keyword outline is visible in original564e. Current cue supports focus, independently of causal attribution to prior click.'),
7:('source_compatible_focus','Actual blue border supports current focus despite no caret. This one case does not prove general focus repair.'),
13:('bounded_action_with_uncertain_tiny_details','Result count50 and exploratory scroll are grounded. Small card clothing remains unresolved; no exhaustive negative is established.'),
15:('unresolved_categorical_absence','Current thumbnails include dense tiny cards/magazines. Root cannot independently establish categorical no-suit across every depicted tiny figure. Keep this subclaim unresolved, not definite Mirage or a semantic pass.'),
16:('overstrong_reader_absence_unresolved','Reader says no people depicted, then says clothing cannot be read. Small card/magazine depictions are not fully resolved. A webpage may contain depicted people. No definite pixel-positive is asserted by this review.'),
17:('unresolved_relation_premise','The relation supports categorical absence from a frozen limited reader. Root retains unresolved fine thumbnail details; relation agreement cannot make the reader ground truth.'),
19:('source_compatible_item_and_price','Original14c2 shows Pitino book at5 and suited figure; local evidence box reaches that listing. Scroll does not claim global minimum.'),
21:('unresolved_uniqueness_scope','Pitino presence/price and page1 end are supported. Only-item scope requires separate review; no proof of all tiny alternatives. Insufficient is not an independent Mirage label.'),
25:('source_compatible_qualified_progress','Page1 bottom and button2 are visible. Explicit inability to confirm uniqueness/minimum is not the opposite fact. Remaining-page state also needs earlier history, not pagination alone.'),
31:('source_compatible_counterexample','Original3e254 shows Victor card30 with green-suit figure; previous deliveredb2cd frame shows Pitino5. This is an explicit second identified match in lawful history; greater price does not erase its existence.'),
33:('unresolved_categorical_absence','Dense sports-card collage is too small to settle every depicted person/clothing detail. No definite positive suit is asserted; categorical negative remains unresolved.'),
34:('source_compatible_limited_reading','No people in readable portions is a bounded reading; it does not exclude figures in unreadable small card details.'),
35:('source_compatible_withholding_uncertainty','Frozen limited reading does not establish categorical viewport absence. Withholding that premise preserves uncertainty; it is not proof the candidate was false.'),
37:('source_compatible_qualified_progress','Explicit uncertainty plus exploratory down-scroll; no new definite absence or global minimum. Auxiliary coarse clear-text result cannot settle card clothing.'),
39:('bounded_object_negative_with_action_reason_overreach','Bucknell thumbnail visibly contains binders/coozie; root finds this local object description compatible. However action reason expands to page2 fully examined/no cheaper match without resolving tiny other thumbnails. Button3 is independently visible.'),
40:('reader_scope_and_rationale_issue','Objects in Bucknell region are readable; small top-clipped cards have limited scope. Being a webpage rather than a photograph cannot itself establish no depicted people. No people-visible gold is invented.'),
41:('overbroad_withholding_of_bounded_object_negative','Exact queried clause is only Bucknell image no-suit. Root originaleda shows two binders/coozie, not a depicted figure. Frozen reader itself reports no people. Reason appeals to small depicted figures that it did not identify. This is source-bound overcaution/likely false rejection of this local premise, not a general false-block rate.'),
45:('qualified_progress_with_source_scope_issues','Uncertainty is legitimate. Bucknell cited box y201.6-273.6 misses actual thumbnail aroundy286-365. Pagination shows available pages, not prior visitation; actual earlier text history is needed for unexamined-page state. Current button3 is correct.'),
49:('source_compatible_current_range','Current25-36 range is readable; legal prior transition and earlier range support page3 within this trajectory. Scroll is exploratory, no completion certificate.'),
51:('source_compatible_bounded_uncertainty','Named rows are visible. Do not clearly show is not categorical absence; tiny card/cover details remain unresolved.'),
53:('source_compatible_bounded_uncertainty','JMU/group thumbnails do not support definite clothing exclusion at original resolution. Judge retains uncertainty, allowing further exploration.'),
55:('history_kind_and_source_scope_issue','Current page3 bottom/button4 are grounded. Page4 remains unexamined is a historical state, incorrectly typed gui_fact; current inactive button does not alone prove never visited. Legal preceding history supplies the actual visit sequence. No false current page or global minimum is inferred.'),
56:('source_compatible_point_approximate_box','Native point816.64,488.88 hits actual4. Returned box is approximate and extends slightly toward adjacent control; target identity is supported, not pixel-perfect bounding accuracy.'),
61:('source_compatible_bounded_uncertainty','Named card boxes/pendant visible. Lack of clear suit depiction does not exclude small unseen clothing. Down scroll preserves task exploration.'),
63:('source_compatible_bounded_uncertainty','Named four rows visible; bounded lack of clear suit is compatible, no task minimum claim.'),
65:('correct_action_with_caption_error','Page4 end and button5 are grounded. Caption enumerates numeral1 although actual leftmost symbol is double-left-arrow; do not treat symbol as observed1 or infer its runtime behavior. This does not make point5 wrong.'),
69:('multiple_source_and_control_errors','Actor already identified Victor30 in earlier assistant message19. Thus only item I could identify Pitino is contradicted even as bounded history; no need to convert it to global uniqueness. Judge instead bundles coverage/exclusivity. It invents numeral1 at559,679; actual point715.52,488.88 is product area. The cited pagination region is lower. c2/c3 y180-432 box fails to include second product image/title/price belowy440. Definite wrong-click evidence; actual native action effect remains unknown because unexecuted.'),
70:('history_reason_misses_actual_counterexample','Actual text-only history includes explicit Victor30 identification at earlier assistant message19. Reader misses this direct contradiction and instead conflates uncertainty about visual exclusion with whether pages were examined. Coverage remains separately unresolved; no general global-minimum verdict is justified.'),
72:('wrong_control_and_wrong_claim_source','Final candidate qualifies only/cheapest and best-identified; do not invent unconditional minimum. Actual click still misses pagination. c3.text contains escaped JSON-looking pseudo-fields absent from actual candidate; actual c3.evidence points at current pagination while reason cites past Pitino reference3. This is a claim extraction/source mismatch, not a second JSON object or duplicate keys. Original strict containment blocks the wrong click.'),
73:('wrong_control_and_wrong_claim_source','Same wrong native point/control and c3 extraction/source mismatch persist after original one format retry. Valid JSON/natural EOS do not establish evidence contract or semantic validity. No extra retry or box repair is authorized by this review.')}
for r in index['rows']:
 i=r['index'];phase=r['phase']
 if i in notes:tag,note=notes[i]
 elif phase=='screen':tag,note='source_compatible_readiness','Original current frame is coherent and readable; usable/not_observed loading is compatible. Does not certify target, page coverage, focus, freshness or task success.'
 elif phase=='point':tag,note='source_compatible_point','Original full frame supports named input/Search/pagination element at supplied point. Locator is only a same-size pointer annotation; no guessed runtime click result.'
 elif phase=='alignment':tag,note='source_compatible_text_relation_only','Stated immediate target matches supplied frozen point reading. This stage has no images and is not an independent visual localization success.'
 else:tag,note='source_compatible_bounded','No additional definite issue identified in the bounded supplied source/claim/action relation; not an unconditional semantic pass.'
 rows.append({'judge_index':i,'phase':phase,'decision':r['decision'],'observation_id':r['observation_id'],
  'actual_wire_sha256':r['wire_sha256'],'source_sha256':r['source_sha256'],'source_file':r['original_source_file'],
  'json_parses':True,'actual_duplicate_keys':r['duplicate_JSON_keys'],'review_tag':tag,'review_note':note})
out={'type':'complete_source_bound_root_judge_review','count':73,'all_raw_replies_reviewed':True,
 'all20_distinct_original_GUI_frames_and6_locator_copies_viewed':True,
 'phase_counts':index['phase_counts'],'actual_JSON_parses':73,'actual_duplicate_key_replies':0,
 'reviewer':'root','blind':False,'not_blind_reason':'Root knew technical/official outcome and execution summary before review. Independent actor labels sealed separately.',
 'source_projection_seal_sha256':hashlib.sha256((root/'judge-legal-projection-linked03/seal.json').read_bytes()).hexdigest(),
 'history_source_review_sha256':hashlib.sha256((root/'history-source-review.json').read_bytes()).hexdigest(),
 'no_scalar_semantic_accuracy_or_Mirage_rate':True,
 'scope_limitations':['Reviews source entailment and actual screenshot geometry, not hidden benchmark answers.',
 'No microfigure suit labels are forced when native resolution is unresolved.',
 '24 usable screen replies in this selected clean trajectory do not establish readiness negative-control performance.',
 '8 point/8 alignment replies include repeats and selected obvious controls; no general localization accuracy claim.',
 'Coverage/identification reports and global minimum are separate proof obligations.'],
 'rows':rows}
p=root/'judge-semantic-review.json';assert not p.exists();p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
s=root/'judge-semantic-review-seal.json';assert not s.exists();s.write_text(json.dumps({'files':{'judge-semantic-review.json':hashlib.sha256(p.read_bytes()).hexdigest(),Path(__file__).name:hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'count':len(rows),'phase_counts':out['phase_counts'],'seal_sha256':hashlib.sha256(s.read_bytes()).hexdigest()},ensure_ascii=False))
