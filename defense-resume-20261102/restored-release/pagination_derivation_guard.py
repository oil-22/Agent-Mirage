"""Staged supplementary audit of explicit pagination arithmetic, never image truth.

Does not edit verdicts/actions, derive a new visual fact, or replace strict validators.
Only an explicitly stated uniform capacity permits arithmetic checks. An absent
capacity is never estimated from the length of the visible range (last-page trap).
"""
import re


def check_relation(page, start, end, total, capacity):
    values=[page,start,end,total,capacity]
    if any(v is None for v in values):
        return {'status':'not_checkable','reason':'Explicit page, range, total and uniform capacity are all required.'}
    if any(type(v)is not int for v in values)or min(values)<1 or not start<=end<=total:
        return {'status':'invalid_relation','reason':'Invalid explicit pagination values.'}
    if end-start+1>capacity:
        return {'status':'internally_inconsistent','reason':'Declared range exceeds declared per-page capacity.'}
    if start!=(page-1)*capacity+1 or end!=min(page*capacity,total):
        return {'status':'internally_inconsistent','reason':'Declared page, range and uniform per-page capacity are incompatible.'}
    return {'status':'arithmetically_consistent','reason':'Arithmetic is consistent; no claim about image-reading accuracy or actual current page.'}


def inspect_supported_claim(claim, observation_id):
    """Read existing current-image citations and explicit prose; no task/hidden state."""
    row={'claim_id':claim.get('id'),'status':'not_checkable','withhold_supported_feedback':False}
    if claim.get('kind')!='gui_fact'or claim.get('status')!='supported':
        return row
    page_match=re.fullmatch(r"\s*(?:(?:I(?:'m| am)|We(?:'re| are))(?: still)? on page|(?:The )?current page(?: is)?)\s+(\d+)\s*[.!]?\s*",claim.get('text',''),flags=re.I)
    if not page_match:return row
    pages=[page_match.group(1)]
    current=[e for e in claim.get('evidence',[])if e.get('observation_id')==observation_id and 'image_index'in e and 'box_xyxy'in e]
    # Historical text or an unrelated judge reason cannot supply the raw range.
    snippets=[e.get('description','')for e in current]
    ranges=[tuple(map(int,x))for t in snippets for x in re.findall(r'(?<!\d)(\d+)\s*[-–]\s*(\d+)\s+of\s+(\d+)(?!\d)',t)]
    caps=[int(x)for t in snippets+[claim.get('reason','')]for x in re.findall(r'\b(\d+)[ -](?:per[ -]page|(?:items|listings)\s+per\s+page)\b',t,flags=re.I)]
    if len(set(ranges))!=1 or len(set(caps))!=1:return row
    start,end,total=ranges[0];result=check_relation(int(pages[0]),start,end,total,caps[0])
    row.update(result,explicit_inputs={'claimed_page':int(pages[0]),'start':start,'end':end,'total':total,'declared_capacity':caps[0]},current_observation_id=observation_id,withhold_supported_feedback=result['status']in {'internally_inconsistent','invalid_relation'})
    return row

