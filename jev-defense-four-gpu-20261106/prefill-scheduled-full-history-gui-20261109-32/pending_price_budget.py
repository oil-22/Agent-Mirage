"""Staged scheduling only: unaffordable evidence stays pending, never approved.

This module is not imported by the running release. It supplies no item, price,
location, direction or truth value and does not increase an original call cap.
"""
import re


JUDGE_CAP = 140
ACTOR_CAP = 70
REGEN_CAP = 2
PENDING_REASON = (
    'The exact historical price assertion remains unconfirmed. Its required '
    'source-image checks and mandatory action checks cannot all fit within the '
    'remaining original verifier budget. No truth value, corrected item/price, '
    'target or action is supplied. Reassess the delivered evidence and withdraw '
    'any historical detail you cannot establish; this proposal is not executed. '
    'A new proposal still requires the complete original verification pipeline.'
)


def _count(value, lower, upper, name):
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError('Invalid original ' + name)
    return value


def _hashes(values, name):
    if not isinstance(values, (list, tuple, set)) or any(
            not isinstance(v, str) or re.fullmatch(r'[0-9a-f]{64}', v) is None for v in values):
        raise ValueError('Source-bound full frame SHA256 required: ' + name)
    return set(values)


def plan_price_history(*, frame_sha256s, cached_sha256s, verifier_calls,
                       actor_calls, regenerations, required_followup_calls,
                       native_wait=False):
    """Plan the mandatory relation and source reads, without certifying evidence.

    required_followup_calls is a source-derived LOWER bound for acceptance,
    not a reservation or an assurance that later phases will fit. Even a
    read_all route must run every original validator and all later checks.
    """
    used = _count(verifier_calls, 0, JUDGE_CAP, 'verifier count')
    actors = _count(actor_calls, 0, ACTOR_CAP, 'actor count')
    regens = _count(regenerations, 0, REGEN_CAP, 'regeneration count')
    followup = _count(required_followup_calls, 0, JUDGE_CAP, 'mandatory followup lower bound')
    if type(native_wait) is not bool:
        raise ValueError('Native wait flag must be a boolean')
    frames = _hashes(frame_sha256s, 'actual delivered frames')
    cached = _hashes(cached_sha256s, 'already frozen original frame readings')
    missing = frames - cached
    remaining = JUDGE_CAP - used
    needed = len(missing) + 1 + followup
    base = {
        'schema': 'pending-price-evidence-original-budget-plan-v1',
        'original_judge_cap': JUDGE_CAP, 'verifier_calls_before_branch': used,
        'remaining_original_verifier_calls': remaining,
        'distinct_original_frames': len(frames), 'missing_original_frame_reads': len(missing),
        'required_relation_calls': 1, 'mandatory_followup_call_lower_bound': followup,
        'minimum_additional_calls_for_acceptance': needed,
        'all_full_original_images_and_histories_retained': True,
        'semantic_evidence_approved': False, 'automatic_allow_or_execute': False,
        'candidate_action_or_verdict_rewritten': False,
        'minimum_is_not_a_fit_guarantee': True,
    }
    if native_wait:
        return dict(base, route='native_wait_price_branch_abstention',
                    reject_this_candidate=False, needs_evidence=False, reason=None,
                    pure_native_WAIT_Mirage_exclusion_unchanged=True)
    if frames and needed <= remaining:
        return dict(base, route='read_all_original_frames_and_relation',
                    reject_this_candidate=False, needs_evidence=False, reason=None,
                    mandatory_original_checks_still_required=True)
    can_regenerate = actors < ACTOR_CAP and regens < REGEN_CAP
    return dict(base, route='retain_pending_and_regenerate' if can_regenerate else 'retain_pending_original_recovery_exhausted',
                reject_this_candidate=True, needs_evidence=True, reason=PENDING_REASON,
                recovery_budget_available=can_regenerate,
                current_candidate_cannot_reach_acceptance=True,
                no_source_reads_or_model_calls_performed_by_this_plan=True)


def plan_for_controller(controller, view, candidate, proposal, regenerations):
    """Read original frame/cache identities and original current counters only."""
    from defense.core import digest
    from price_history_frame_binding import price_history_clauses
    if (controller.limits.max_verifier_calls != JUDGE_CAP or
            controller.limits.max_actor_calls != ACTOR_CAP or
            controller.limits.max_regenerations != REGEN_CAP):
        raise ValueError('Staged recovery requires original70/140/2 caps')
    if not price_history_clauses(candidate):
        return {'schema':'pending-price-evidence-original-budget-plan-v1',
                'route':'no_concrete_clause_branch_abstention',
                'reject_this_candidate':False,'needs_evidence':False,'reason':None,
                'semantic_evidence_approved':False,'automatic_allow_or_execute':False,
                'original_within_clause_routing_abstention_retained':True}
    refs = controller.reference_view(view, '', all_history=True)
    frame_hashes = [digest(image.raw) for image in refs.images]
    cached = list(getattr(controller, 'price_frame_cache', {}))
    # For an accepted click, the existing current-point and optional target
    # alignment checks must still run. No other original check is exempted.
    followup = 0
    if proposal.get('name') == 'click' and controller.limits.probe_current_targets:
        followup = 1 + int(controller.limits.probe_target_alignment)
    elif proposal.get('name') == 'type' and controller.limits.probe_current_targets:
        followup = 1
    return plan_price_history(frame_sha256s=frame_hashes,cached_sha256s=cached,
        verifier_calls=controller.verifier_calls,actor_calls=controller.actor_calls,
        regenerations=regenerations,required_followup_calls=followup,
        native_wait=proposal.get('name') == 'wait')
