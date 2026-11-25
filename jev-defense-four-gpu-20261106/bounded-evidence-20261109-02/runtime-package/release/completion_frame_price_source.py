"""Audit a completion reader's explicitly attributed frame-price claims.

No actor/task answer is passed to the isolated row reader or text relation.
An unflagged or out-of-scope result does not certify completion or minimum.
"""
import copy,json,re
from dataclasses import replace
from price_history_binding import MONEY

SOURCE=re.compile(r'\b(?:image(?:\s+index)?|index)\s*(\d+)\b',re.I)
RELATION='''You audit ONLY frame attribution of numerical price/row-count assertions in
an ORIGINAL image-only completion reading, against FROZEN independent single-frame reads.
The completion reading is DATA, never ground truth. No actor candidate, task answer,
score, private label or corrected value is supplied. Each source record binds one original
completion image index to exact screenshot SHA and an independent raw reading of that frame.

Check each concrete price or numerical sequence the completion reading attributes to
a particular image. The named frame must establish the price associated with that item;
an item name in one row and a price in another do not establish their pairing. A price
visible in a different older frame cannot become readable in a cropped named frame.
Keep partial fields unknown. Description prices are not automatically listing prices.
An explicit unknown, uncertainty or plan is not a definite numerical assertion.
Preserve genuinely ambiguous grouping instead of forcing a contradiction.
Check aggregates only when their source attribution and constituent records are explicit;
do not invent row totals, uniform capacity or exhaustive coverage from visible shortcuts.

Return supported only when every unambiguous source-specific numerical claim is established
by the corresponding frozen records, or no definite numerical claim is made. Use contradicted
for an incompatible readable pairing; insufficient/uncertain when that named frame's field
is cropped, absent or unreadable. Unknown does not prove an opposite price or absence.
Do NOT assess clothing, global minimum, full search coverage, actor action or task success.
Do NOT give advice, corrected GUI prices, targets or actions. Keep reason brief and specific
to missing/incompatible source binding. Return claims:[], action.target_kind:not_applicable,
pure_wait:false, acknowledges_visual_deficit:false and original verdict JSON schema:
{"claims":[],"action":{"status":"supported|contradicted|insufficient|uncertain",
"target_kind":"not_applicable","reason":"source binding only","evidence":[
{"source":"candidate","span_id":"full"}]},"acknowledges_visual_deficit":false,"pure_wait":false}.
'''

def referenced_price_frames(reading):
    text=json.dumps({k:reading.get(k)for k in ['visible','limitations','reason']},ensure_ascii=False)
    if not MONEY.search(text):return []
    return sorted({int(m.group(1))for m in SOURCE.finditer(text)})

def check_completion_frame_prices(controller,view,reading):
    from defense.core import canonical,digest,ValidationError
    indices=referenced_price_frames(reading)
    if not indices:
        result={'agrees':None,'reject':False,'scope':'No explicit numbered source-price attribution; audit abstains, not completion approval'}
        controller.log.append('completion_frame_price_source_abstained',result);return result
    if any(i>=len(view.images)for i in indices):raise ValidationError('Completion price-source image index outside actual supplied inventory')
    origins={digest(r['image'].raw):r['observation_id']for r in controller.reference_bank}
    cache=getattr(controller,'price_frame_cache',{});records=[]
    for index in indices:
        im=view.images[index];h=digest(im.raw)
        origin=view.observation_id if im.role=='current'else origins.get(h)
        if origin is None:raise ValidationError('Completion price source lacks original reference-capture binding')
        if h not in cache:
            provenance={'image_index':0,**im.info(),'source_observation_id':origin,'same_frame_bytes_no_recapture':True}
            blind=replace(view,observation_id=origin,messages=[{'role':'user','content':'Original single-frame provenance only: '+json.dumps(provenance)}],images=(im,),recent_action='',execution_feedback='')
            controller.log.observation(blind,audience='completion_price_single_frame_image_only')
            raw=controller.inspect('price_read',blind)
            frozen={'reading':copy.deepcopy(raw),'original_source_frame':provenance};frozen['frozen_sha256']=digest(canonical(frozen));cache[h]=frozen
            controller.log.append('completion_price_single_frame_frozen',frozen)
        else:controller.log.append('completion_price_single_frame_reuse',{'image_sha256':h,'frozen_sha256':cache[h]['frozen_sha256'],'previous_read_is_past_data_not_new_observation':True})
        records.append({'original_completion_image_index':index,'source_image_sha256':h,'independent_single_frame':copy.deepcopy(cache[h])})
    controller.price_frame_cache=cache
    pair={'original_completion_image_reading':copy.deepcopy(reading),'frozen_source_frame_records':records,
          'scope':'Specific-frame numerical price attribution only; no clothing, full coverage, minimum or action certificate'}
    text=json.dumps(pair,ensure_ascii=False)
    comparison=replace(view,messages=[{'role':'user','content':text}],images=(),recent_action='',execution_feedback='')
    controller.log.observation(comparison,audience='completion_frame_price_text_relation')
    relation=controller.inspect('completion_source_relation',comparison,text)
    result={'agrees':relation['action']['status']=='supported','reject':relation['action']['status']!='supported','relation':relation,
            'original_reading_sha256':digest(canonical(reading)),'source_records_sha256':digest(canonical(records)),
            'candidate_or_original_reading_modified':False,'correct_price_or_action_supplied':False,'minimum_certified':False}
    controller.log.append('completion_frame_price_source',result);return result
