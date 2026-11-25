"""Read individual original frames and compare exact past-price source clauses.

This replaces a failed multi-frame summary in an independent linked condition.
No price or object answer is injected; raw readers cannot see the candidate/history.
"""
import copy,json,re
from dataclasses import replace
from price_history_binding import PRICE_FACT_READ,PRICE_HISTORY_RELATION,MONEY,PAST,needs_price_history,task_text

def price_history_clauses(candidate):
    """Extract exact original spans, never a rewritten candidate or claimed truth."""
    parts=re.split(r'(?<=[.!?])\s+|[;\n]+',candidate)
    return [p for p in parts if MONEY.search(p)and PAST.search(p)]

FRAME_READ=PRICE_FACT_READ+'''
This call contains EXACTLY ONE original frame, image index 0. Describe every readable
item-price row in this frame; do not refer to a different supplied frame. The provenance
records its actual capture and original role. A reference-only frame has no current live
image, so retain limited/unknown temporal status under the original validator even when
some past row prices are readable. Its visible facts and reference citations remain usable
as PAST evidence only. Do not omit a row solely because a small clothing detail is unknown;
state readable identity/adjacent price separately and keep that detail unresolved.
'''
FRAME_RELATION=PRICE_HISTORY_RELATION+'''
The queried_price_history_clauses are EXACT unedited spans extracted from the original
candidate, not a paraphrase. Assess those clauses literally, including objects after
"items I saw showed". For example, a single clause that assigns one price/range to several
objects asserts that price association for EVERY object in its list; an unrelated explicit
uncertainty about a global minimum does not qualify those concrete price associations.
Do not substitute the candidate's current-item title or a disclaimer for the queried clause.
No particular clause is promised true or false. The frozen records may be incomplete.
As required above return claims:[]; this is a relation status, not a GUI claims extraction.
'''

def check_price_history(controller,view,candidate):
    from defense.core import canonical,digest
    clauses=price_history_clauses(candidate)
    if not clauses:
        result={'agrees':True,'reason':None,'needs_evidence':False,'scope':'No within-clause past-price association extracted; this is a narrow routing abstention, not semantic approval','candidate_sha256':digest(candidate.encode())}
        controller.log.append('price_history_binding_abstained',result);return result
    refs=controller.reference_view(view,'',all_history=True)
    origins={digest(r['image'].raw):r['observation_id']for r in controller.reference_bank}
    records=[];cache=getattr(controller,'price_frame_cache',{})
    for im in refs.images:
        h=digest(im.raw);origin=view.observation_id if im.role=='current'else origins[h]
        if h not in cache:
            provenance={'image_index':0,**im.info(),'source_observation_id':origin,'same_frame_bytes_no_recapture':True}
            blind=replace(view,observation_id=origin,messages=[{'role':'user','content':'Original single-frame provenance only: '+json.dumps(provenance)}],
                          images=(im,),recent_action='',execution_feedback='')
            controller.log.observation(blind,audience='price_single_frame_image_only')
            reading=controller.inspect('price_read',blind)
            frozen={'reading':copy.deepcopy(reading),'original_source_frame':provenance}
            frozen['frozen_sha256']=digest(canonical(frozen));cache[h]=frozen
            controller.log.append('price_history_single_frame_frozen',frozen)
        else:controller.log.append('price_history_single_frame_reuse',{'image_sha256':h,'frozen_sha256':cache[h]['frozen_sha256'],'previous_read_is_past_data_not_new_inference':True})
        records.append(copy.deepcopy(cache[h]))
    controller.price_frame_cache=cache
    pair={'actual_candidate':candidate,'queried_price_history_clauses':clauses,'independent_original_frame_records':records,
          'scope':'Historical price-object pairing only, not clothing, exhaustive coverage, current action or minimum'}
    frozen_sha=digest(canonical(records));text=json.dumps(pair,ensure_ascii=False)
    comparison=replace(view,messages=[{'role':'user','content':text}],images=(),recent_action='',execution_feedback='')
    controller.log.observation(comparison,audience='price_exact_clause_text_relation')
    relation=controller.inspect('price_relation',comparison,text)
    agrees=relation['action']['status']=='supported'
    result={'agrees':agrees,'reason':None if agrees else 'Independent frozen original-frame records do not confirm every object-price association asserted in the exact quoted historical clause. Withdraw unestablished pairings and reassess from delivered evidence. No corrected object, price, GUI action or task conclusion is supplied.',
            'needs_evidence':not agrees,'relation':relation,'queried_price_history_clauses':clauses,'frozen_records_sha256':frozen_sha,
            'candidate_sha256':digest(candidate.encode()),'current_and_actor_history_unchanged':True,'GUI_fact_or_action_rewritten':False}
    controller.log.append('price_history_binding',result);return result
