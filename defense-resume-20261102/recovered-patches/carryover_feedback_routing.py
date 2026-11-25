"""Staged, inference-free feedback routing; original Controller is not modified."""
import copy,json
from defense.core import digest,validate_verdict
from pagination_derivation_guard import inspect_supported_claim


def build_feedback(view, prior_index, verdict):
    """Validate original verdict, then quarantine explicit inconsistent support.

    Routing is not a new verdict or a new GUI fact. No alternative page, action,
    model invocation or extra recapture/regeneration budget is supplied here.
    """
    assistant_indices=[i for i,m in enumerate(view.messages)if m.get('role')=='assistant']
    if not assistant_indices or type(prior_index)is not int or prior_index!=assistant_indices[-1]:
        raise ValueError('Only the actual latest earlier assistant report may be audited.')
    past=view.messages[prior_index]['content']
    if not isinstance(past,str):raise ValueError('Earlier report must be the exact native text.')
    checked=validate_verdict(copy.deepcopy(verdict),view,past)
    pending=[];supported=[];quarantined=[];mechanical=[]
    for claim in checked['claims']:
        if claim['kind']not in {'gui_fact','history_report'}:continue
        guard=inspect_supported_claim(claim,view.observation_id);mechanical.append(guard)
        entry={'earlier_message_index':prior_index,'earlier_report_words':claim['text'],
               'original_judge_status':claim['status'],'truth_of_past_report':'not_determined_by_this_current_reuse_check'}
        if guard['withhold_supported_feedback']:
            quarantined.append({**entry,'routing':'support_withheld_internal_inconsistency',
                'reason':guard['reason'],'current_claim_not_established':True,'alternative_state_inferred':False})
        elif claim['kind']=='gui_fact'and claim['status']=='supported':
            supported.append(copy.deepcopy(claim))
        elif claim['status']!='supported':
            pending.append({**entry,'reason':claim['reason'],'evidence':copy.deepcopy(claim['evidence'])})
    data={'source_observation_id':view.observation_id,
          'source_current_image_sha256':[digest(i.raw)for i in view.images if i.role=='current'],
          'earlier_report_sha256':digest(past.encode()),'pending_current_reuse':pending,
          'supported_current_reuse':supported,'quarantined_checker_support':quarantined,
          'supplementary_checks':mechanical,'checker_is_fallible':True,
          'unflagged_is_not_semantic_approval':True}
    text=('CURRENT-PREMISE AUDIT, before your next decision. Earlier reports are not new observations. '
          'Re-establish needed current premises using the actual delivered image. A checker support '
          'withheld for internal inconsistency supplies no opposite fact or corrected page. '
          'Do not reuse a quarantined assertion as a confirmed premise. Pending reuse does not prove '
          'a past report false or an operation failed. All original uncertainty remains. '
          'No target, direction, action or task completion is supplied by this feedback.\n'+json.dumps(data,ensure_ascii=False))
    return {'feedback':text,'data':data,'validated_original_verdict':checked,
            'new_model_calls':0,'additional_budget':0,'actor_or_action_executed':False}

