"""Select the archived scroll mismatch, using only events before regeneration."""
import copy
from defense.core import PublicView, pending_action_patch

def scroll_reconsideration(events):
    for req in events:
        if req['kind']!='actor_request':continue
        corrections=copy.deepcopy(req['data']['corrections'])
        entries=[x for x in corrections if x.get('claim')=='proposed_action']
        if not entries:continue
        prior=[e for e in events if e['seq']<req['seq']]
        candidate=next((e for e in reversed(prior)if e['kind']=='candidate'),None)
        if not candidate or '"direction":"down"'not in candidate['data']['text'].replace(' ',''):continue
        verdict=next(e for e in reversed(prior)if e['kind']=='verdict')['data']['verdict']
        if verdict['action']['status']=='supported':continue
        text=candidate['data']['text'];assert 'up'in text.lower()
        # Native parsing is performed by caller; never synthesize or edit JSON.
        return req,candidate,verdict,corrections
    raise AssertionError('No source-bound rejected down proposal followed by regeneration')

def with_native_action_feedback(events, parse_proposal):
    req,candidate,verdict,corrections=scroll_reconsideration(events)
    p=next(e['data']['public']for e in reversed(events)if e['seq']<candidate['seq']and e['kind']=='actor_request')
    view=PublicView(p['observation_id'],p['messages'],(),p['recent_action'],p['execution_feedback'],p['observed_at'])
    proposal=parse_proposal(candidate['data']['text'])
    old=next(x for x in corrections if x.get('claim')=='proposed_action')
    patch=pending_action_patch(candidate['data']['text'],proposal,view,verdict['action']['status'],old['reason'])
    corrections=[patch if x is old else x for x in corrections]
    return req,corrections,candidate['seq']
