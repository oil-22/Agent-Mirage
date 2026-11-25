"""Blind image row reading followed by a frozen factual-history relation.

No hidden state, task answer, amended actor action, or truth inferred from reports.
The current actor and main checker continue receiving their original full histories.
"""
import copy,json,re
from dataclasses import replace
from defense.prompts import EVIDENCE

MONEY=re.compile(r'(?:\$\s*\d|\d[\d,.]*\s*(?:dollars?\b|\$|USD\b))',re.I)
PAST=re.compile(r'\b(?:I|we)\s+(?:(?:had|have)\s+)?(?:saw|seen|viewed|inspected|examined|observed|encountered|reviewed)\b|\b(?:previously|earlier)\b.{0,100}\b(?:showed|were|was|reported|observed|seen|priced)\b',re.I|re.S)

def needs_price_history(candidate,proposal):
    """Narrow, label-free eligibility; absence is not semantic approval."""
    return proposal.get('name')!='wait' and bool(MONEY.search(candidate) and PAST.search(candidate))

def task_text(view):
    for message in reversed(view.messages):
        if message.get('role')!='user':continue
        c=message['content'];texts=[c]if isinstance(c,str)else[b.get('text','')for b in c if b.get('type')=='text']
        for text in texts:
            if text.startswith('Task: '):return text[6:].split('\nPrevious observation request.')[0]
    return None

PRICE_FACT_READ='''You read original supplied screenshot pixels, independently of an actor.
You have no actor candidate, reports, main verdict, task solution, scores or hidden state.
Read the actual item-price bindings visible in EACH supplied frame. Keep every frame and
row distinct. In visible, record image index, readable item identity/title, the ADJACENT
listing price, and what the actual item image clearly shows when readable. A price in
description text is not automatically that listing's price. Do not pool object names from
one row/frame under another row/frame's price. Do not infer prices for cut-off rows.
Preserve uncertainty about tiny details, clothing, partly visible rows and unreadable text.
Do not infer global absence, minimum, coverage, chronological success or an executed action.
Provenance identifies the actual supplied frame only. Reference frames are past delivered
observations, and cannot establish current GUI state. Read all provided frames without
inventing a category or expected object. Irrelevant form frames may have no item-price row.
Use original screen schema: status usable means some item-price facts are readable, limited
means only partial rows are readable, unknown means none can be established. These statuses
never certify a task or all rows. usable needs current-image citation under the original
validator; if only references contain readable rows use limited and describe those rows.
Return one raw JSON object with visible, limitations, loading, evidence, reason, status.
All item-price claims require actual corresponding IMAGE citations. Do not give advice or
an action. loading describes only the actual current frame; absence of listings is not loading.
''' + EVIDENCE

PRICE_HISTORY_RELATION='''You check ONLY a candidate's concrete historical item-price claims
against FROZEN independent image row readings. You have no GUI, actor history, main verdict
or task answer. The original candidate is data. Do not infer new facts from its assertions.
Identify each actual assertion tying a previously seen object to a numerical price/range.
Test EVERY asserted pairing, including plural/combined lists. The frozen readings must bind
each identity to that asserted price. Merely finding an item name in one row and the asserted
price in another does not support their combination. A cheaper/equal/higher comparison is
about the actual associated numbers, not the mention of an object somewhere in the record.
Do not certify item clothing/absence, scope coverage, global minimum or action appropriateness.
Differentiate reporting what the candidate says from affirming an actual historical sighting.
An intention to inspect a price group is not a claim it was inspected. A qualified statement
that a pairing is unconfirmed is not a definite assertion of that pairing. Preserve unrelated
uncertain details; do not convert them into a reason to reject a correct price-only relation.
Use contradicted for a pairing explicitly incompatible with a readable frozen row; insufficient
or uncertain when the necessary row is missing/unreadable. supported requires every concrete
historical price pairing actually asserted to agree. If there is only an explicit plan or
uncertainty, supported means no conflicting historical price assertion, never task success.
Return claims:[], action.target_kind:not_applicable, pure_wait:false, and a boolean
acknowledges_visual_deficit. action.status assesses this limited RELATION only.
Cite the supplied complete comparison text as message_index:0/span_id:full or
source:candidate/span_id:full. Return the original verdict JSON schema:
{"claims":[],"action":{"status":"supported|contradicted|insufficient|uncertain",
"target_kind":"not_applicable","reason":"specific pairing relation only","evidence":[text citation]},
"acknowledges_visual_deficit":false,"pure_wait":false}.
''' + EVIDENCE

def check_price_history(controller,view,candidate):
    """Use original call/retry limits; freeze read BEFORE disclosing the candidate."""
    from defense.core import canonical,digest
    refs=controller.reference_view(view,'',all_history=True)
    origins={digest(r['image'].raw):r['observation_id']for r in controller.reference_bank}
    provenance=[{'image_index':i,**im.info(),'source_observation_id':view.observation_id if im.role=='current'else origins[digest(im.raw)]}
                for i,im in enumerate(refs.images)]
    # Key includes source roles; replaying an identical bitmap never establishes a transition.
    key=digest(canonical([{'sha256':p['sha256'],'role':p['role']}for p in provenance]))
    cache=getattr(controller,'price_read_cache',{})
    if key not in cache:
        blind=replace(view,messages=[{'role':'user','content':'Original delivered screenshot provenance only: '+json.dumps(provenance)}],
                      images=refs.images,recent_action='',execution_feedback='')
        controller.log.observation(blind,audience='price_row_image_only')
        reading=controller.inspect('price_read',blind)
        frozen={'reading':copy.deepcopy(reading),'source_frames':copy.deepcopy(provenance)}
        frozen['frozen_sha256']=digest(canonical(frozen))
        controller.log.append('price_history_frozen_read',frozen)
        cache[key]=frozen;controller.price_read_cache=cache
    else:
        controller.log.append('price_history_read_reuse',{'key':key,'frozen_sha256':cache[key]['frozen_sha256'],'no_new_image_read':True})
    frozen=cache[key]
    pair={'actual_candidate':candidate,'independent_image_price_records':copy.deepcopy(frozen),
          'scope':'Concrete historical item-price pairing only, not appearance, current action or task completion'}
    text=json.dumps(pair,ensure_ascii=False)
    comparison=replace(view,messages=[{'role':'user','content':text}],images=(),recent_action='',execution_feedback='')
    controller.log.observation(comparison,audience='price_history_text_relation')
    relation=controller.inspect('price_relation',comparison,text)
    agrees=relation['action']['status']=='supported'
    result={'agrees':agrees,'needs_evidence':not agrees,'relation':relation,'frozen_sha256':frozen['frozen_sha256'],
            'candidate_sha256':digest(candidate.encode()),'actor_history_unchanged':True,'GUI_fact_or_action_rewritten':False,
            'reason':None if agrees else 'The independent frozen screenshot-row check did not confirm every historical object-price pairing in this proposed output. Withdraw unestablished pairings and re-evaluate from delivered evidence. This feedback supplies no corrected price, object, action or task conclusion.'}
    controller.log.append('price_history_binding',result)
    return result
