"""Conservative proposal-internal consistency check. No GUI or truth inference.

Only explicit, unconditional, sentence-initial present planning phrases are read.
Anything unrecognized/ambiguous is left to the original verifier, not approved.
"""
import hashlib
import re

PLAN = re.compile(
    r"(?:^|[.!?]\s+|\n)\s*(?:I(?:'ll| will| should| need to| am going to)|"
    r"let(?:'s| us| me)|we(?:'ll| will| should))\s+(?:now\s+)?scroll\s+(?:back\s+)?(up|down)\b",
    re.IGNORECASE)
CONDITIONAL = re.compile(r'\b(if|when|unless|would|might|could|then|after|before|instead|or)\b',re.IGNORECASE)


def check_direction(candidate, proposal):
    result={'candidate_sha256':hashlib.sha256(candidate.encode()).hexdigest(),
            'reject':False,'scope':'proposal_internal_consistency_only',
            'gui_state_inferred':False,'replacement_action_supplied':False,
            'unflagged_is_not_semantic_approval':True,'reason':None}
    if proposal.get('name')=='wait' and proposal.get('parsed') and not proposal.get('executor_fallback_wait'):
        return {**result,'status':'native_wait_excluded'}
    if proposal.get('name')!='scroll':
        return {**result,'status':'not_scroll'}
    payload=proposal.get('payload',{})
    if payload.get('type')!='scroll' or payload.get('direction')not in {'up','down'}:
        return {**result,'status':'unbound_native_direction'}
    # The original parser owns action extraction; never parse or repair its JSON here.
    prose=re.sub(r'<action>.*?</action>','',candidate,flags=re.DOTALL|re.IGNORECASE)
    matches=[]
    for m in PLAN.finditer(prose):
        end=re.search(r'[.!?\n]',prose[m.end():])
        tail=prose[m.end():m.end()+end.start()]if end else prose[m.end():]
        if CONDITIONAL.search(tail):continue
        matches.append({'direction':m.group(1).lower(),'start':m.start(),'end':m.end(),
                        'exact_words':prose[m.start():m.end()].strip()})
    directions={m['direction']for m in matches}
    if len(directions)!=1:
        return {**result,'status':'ambiguous_or_unrecognized_intent','recognized_plans':matches}
    intended=next(iter(directions))
    if intended==payload['direction']:
        return {**result,'status':'recognized_consistent','recognized_plans':matches}
    return {**result,'status':'explicit_internal_direction_conflict','reject':True,
            'recognized_plans':matches,'native_direction':payload['direction'],
            'reason':('An explicit current scrolling intention conflicts with this proposal\'s native direction field. '
                      'This proposal was not executed. Reassess the actual screenshot and your intention, '
                      'then generate one internally consistent native action. '
                      'This check supplies no preferred direction, target or GUI fact.')}
