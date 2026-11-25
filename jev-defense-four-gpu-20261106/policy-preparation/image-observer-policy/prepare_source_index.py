"""Freeze source bindings and private pre-output image review, no inference."""
import json
from pathlib import Path
from image_observer import digest
BASE=Path(__file__).resolve().parent
source=BASE.parents[1]/'observer-source-controls-1793973885537637041'
rows=[]
for name in ['fresh-home','normal-footer','buttons-only-home','native-no-results']:
    path=source/name/'original.png';receipt=source/name/'source.json'
    value=json.loads(receipt.read_bytes());assert value['image_sha256']==digest(path.read_bytes())
    rows.append({'case_id':name,'path':str(path),'image_sha256':value['image_sha256'],
        'source_receipt':str(receipt),'source_receipt_sha256':digest(receipt.read_bytes()),
        'scope':'fresh native original source preparation; not model action or defense trajectory'})
obj={'sources':rows,'required_source_coverage':['normal_footer','readable_no_results','buttons_only_sparse'],
     'capture_summary_sha256':digest((source/'capture-summary.json').read_bytes()),
     'model_calls':0,'task_agent_actions':0,'source_browser_operations_disclosed':True}
with (BASE/'extra-image-sources.json').open('x',encoding='utf8')as f:json.dump(obj,f,indent=2)
review={'reviewed_before_new_Flash_outputs':True,'model_outputs_seen':False,
    'reviewer':'source/policy agent; parent independently viewed same originals',
    'blinding':'known-source selected development; prior old model/image context known, not blind gold',
    'source_images_actually_viewed':['all six archived originals in prior linked preparation','fresh-home','normal-footer','buttons-only-home','native-no-results'],
    'private_never_observer_input':True,'cannot_derive_semantic_accuracy_or_Mirage_rate':True,
    'cases':[
      {'case_id':'original-01','reference_frame':'readable GUI; input form plus listing cards; actual blue Keyword focus border',
       'task_specific_focus_not_queried':True,'layout_reference':'mixed or dominant listing depending coverage; no forced exclusive form claim'},
      {'case_id':'original-02','reference_frame':'readable GUI; input form plus listing cards; no blue focus border',
       'task_specific_focus_not_queried':True,'layout_reference':'mixed or dominant listing depending coverage'},
      {'case_id':'original-03','reference_frame':'truly blank white frame',
       'reference_choices':{'frame_appearance':'blank_frame','visible_layout':'unknown','text_readability':'not_applicable'},
       'does_not_prove':['loading','zero results','success']},
      {'case_id':'original-04','reference_frame':'readable listing cards with text and book thumbnails',
       'layout_reference':'list_or_cards','person_suit_task_not_queried':True},
      {'case_id':'original-05','reference_frame':'readable listing cards plus pagination and footer; not pure footer',
       'layout_reference':'list_or_cards or mixed other','task_specific_clothing_and_page_not_queried':True},
      {'case_id':'original-06','reference_frame':'readable listings plus left search form and pagination; tiny cover clothing ambiguous',
       'layout_reference':'list_or_cards or mixed other','task_specific_clothing_and_page_not_queried':True},
      {'case_id':'fresh-home','reference_frame':'clear coherent GUI with Keyword/Category/Search form and four listing cards',
       'layout_reference':'mixed other; do not force only form or only list','loading_cue_observed':False},
      {'case_id':'normal-footer','reference_frame':'clear coherent category-navigation grid and Contact footer',
       'layout_reference':'navigation_or_footer, with repeated category cards also visible',
       'task_target_offscreen_not_unreadable':True,'loading_cue_observed':False},
      {'case_id':'buttons-only-home','reference_frame':'mostly white but two actual readable Publish Ad/Search buttons remain',
       'layout_reference':'sparse recognizable GUI; layout category uncertain/other, not empty blank',
       'text_reference':'clear visible button text','loading_cue_observed':False},
      {'case_id':'native-no-results','reference_frame':'clear coherent native GUI with explicit no-results text and left search form',
       'layout_reference':'mixed form/other; no repeated result cards',
       'HTTP404_is_native_template_not_crash':True,'loading_cue_observed':False}],
    'limits':['No genuine explicit positive loading source. Blank is not loading-positive.',
        'Only coarse frame/layout/readability are queried. No OCR, focus, page identity, person/clothing, historical success, current coordinates or direction fields.',
        'Predicted categories and raw probabilities cannot establish task truth or freshness.',
        'Layout/text boundaries can overlap; retain review uncertainty rather than force scalar correctness.']}
with (BASE/'PRIVATE-preoutput-source-review.json').open('x',encoding='utf8')as f:json.dump(review,f,ensure_ascii=False,indent=2)
print(json.dumps({'sources':len(rows),'model_calls':0,'private_review_sha256':digest((BASE/'PRIVATE-preoutput-source-review.json').read_bytes())}))
