"""Conservative internal comparison check; quoted prices are not GUI ground truth.

Only one unambiguous dollar amount before a literal cheaper-items parenthesis,
with an explicitly identified current/strong candidate, is considered. No image,
correct price, task answer or replacement action is supplied.
"""
import re
from decimal import Decimal

MONEY=re.compile(r'\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)\b')
GROUP=re.compile(r'\b(?:the\s+)?cheaper\s+items(?:[\x27\u2019]?\s*images)?\s*\(([^)\n]{1,180})\)',re.I)
ANCHOR=re.compile(r'\b(?:current\s+observation|current\s+(?:item|candidate|book)|(?:this|a)\s+(?:strong\s+)?candidate)\b',re.I)
UNCERTAIN_COMPARISON=re.compile(r'\b(?:whether|if)\s+(?:these\s+(?:are|were)\s+)?(?:the\s+)?$',re.I)


def check_strict_price_comparison(candidate,proposal):
    result={'reject':False,'conflicts':[],'candidate_modified':False,
            'quoted_prices_certified':False,'correct_price_supplied':False,
            'replacement_action_supplied':False,'unflagged_is_not_approval':True,
            'scope':'Explicit internally inconsistent strict-price list only; no image truth or global minimum inference'}
    if proposal.get('name')=='wait':
        result['scope']='Pure native WAIT excluded from this comparison route';return result
    text=candidate.split('<action>',1)[0]
    for group in GROUP.finditer(text):
        prefix=text[:group.start()]
        if not ANCHOR.search(prefix) or UNCERTAIN_COMPARISON.search(prefix):continue
        prices=list(MONEY.finditer(prefix))
        if not prices:continue
        values={Decimal(m.group(1).replace(',',''))for m in prices}
        # Do not choose among multiple possible comparators or certify a guessed
        # current price. Ambiguous/conditional target amounts abstain.
        if len(values)!=1:continue
        if any(re.search(r'\b(?:maybe|perhaps|about|around|possibly|might\s+be|may\s+be|could\s+be)\s*$',prefix[max(0,m.start()-30):m.start()],re.I)for m in prices):continue
        members=list(MONEY.finditer(group.group(1)))
        if not members:continue
        baseline=next(iter(values))
        if any(Decimal(m.group(1).replace(',',''))>=baseline for m in members):
            result['conflicts'].append({'exact_comparison_clause':group.group(0),'source_span':[group.start(),group.end()],
                'reason':'This proposal identifies one candidate dollar amount, but its explicitly cheaper-items list includes an amount that is not strictly lower than that quoted amount. This is an internal comparison conflict only. Reassess the unchanged evidence and withdraw unsupported comparisons; no corrected GUI price, target or action is supplied.'})
    result['reject']=bool(result['conflicts']);return result
