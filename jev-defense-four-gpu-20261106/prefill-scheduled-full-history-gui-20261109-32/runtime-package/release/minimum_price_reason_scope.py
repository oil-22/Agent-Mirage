"""Narrow internal-reason consistency check, never a minimum-price certificate."""
import re

PREFIX_CONFIRMED=re.compile(r'\bascending\s+order\s+and\s+(?:the\s+)?(?:strictly\s+)?cheaper\s+prefix\s+(?:(?:are|is|have\s+been|has\s+been)\s+)?(?:(?:fully|completely)\s+)?(?:covered|established|confirmed)\b',re.I)
TIE_GAP=re.compile(r'\b(?:equal[- ]price|same[- ]price)\b.{0,180}?(?:\bnot\s+(?:(?:fully|completely)\s+)?(?:inspected|covered)\b|\bun(?:viewed|seen|inspected)\b)',re.I|re.S)
MINIMUM=re.compile(r'\b(?:cheapest|lowest[- ]price|minimum[- ]price|global\s+minimum)\b',re.I)
EXTRA_GOAL=re.compile(r'\b(?:unique|uniqueness|exactly\s+one|only\s+matching|all\s+matches|every\s+matching)\b',re.I)

def minimum_reason_check(value,task):
    """Quarantine only an explicit acknowledged-prefix/equal-price rejection conflict.

    This does not validate that order/prefix/appearance really are established, that
    a particular price is correct, or that the model should allow STOP. Other missing
    prerequisites stay missing. The unchanged validator and original retry remain.
    """
    errors=[]
    if not isinstance(task,str)or not MINIMUM.search(task)or EXTRA_GOAL.search(task):
        return {'reject':False,'errors':[],'value_modified':False,'minimum_certified':False,'scope':'Not an established minimum-only task scope'}
    for i,claim in enumerate(value.get('claims',[])):
        if claim.get('status')not in {'insufficient','uncertain','contradicted'}or not MINIMUM.search(claim.get('text','')):
            continue
        reason=claim.get('reason','')
        if PREFIX_CONFIRMED.search(reason)and TIE_GAP.search(reason):
            errors.append({'claim_index':i,'reason_scope_error':'The reason explicitly says ascending order and the cheaper prefix are covered, yet withholds a minimum because equal-price candidates are uninspected. Equal prices cannot be strictly cheaper. This identifies an internal explanation conflict only; it proves neither actual prefix coverage nor task success.'})
    return {'reject':bool(errors),'errors':errors,'value_modified':False,'minimum_certified':False,'opposite_GUI_fact_supplied':False,'replacement_action_supplied':False,'scope':'Narrow explicit internal equal-price/minimum explanation conflict; unflagged is not semantic approval'}
