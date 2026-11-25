"""Classify an original local call-cap terminal without granting any recovery.

Admission requires separately frozen source checks of the exact local exception
and catch strings. Does not certify semantic truth, scorer success or execution.
"""


LOCAL_VERIFIER_CAP_REASONS = frozenset(prefix + ':verifier_call_cap' for prefix in [
    'screen_verifier_error', 'focus_claim_verifier_error', 'candidate_verifier_error',
    'history_report_verifier_error', 'price_history_verifier_error', 'appearance_absence_verifier_error',
    'point_verifier_error', 'alignment_verifier_error', 'focus_verifier_error', 'completion_verifier_error'])


def classify_run_termination(outcome, reason, scoring_status, verifier_calls, verifier_cap):
    if type(verifier_calls) is not int or type(verifier_cap) is not int or not 0 <= verifier_calls <= verifier_cap == 140:
        raise ValueError('Original local140call accounting required')
    original = ('verifier_failure' if outcome == 'blocked' and 'verifier_error:' in reason else
                'scoring_failure' if scoring_status == 'failed' else 'no_reported_infrastructure_failure')
    local_cap = outcome == 'blocked' and reason in LOCAL_VERIFIER_CAP_REASONS and verifier_calls == verifier_cap
    technical = ('scoring_failure' if scoring_status == 'failed' else
                 'no_reported_infrastructure_failure' if local_cap else original)
    return dict(technical_status=technical, original_terminal_classification_without_repair=original,
        local_verifier_budget_exhausted=local_cap,
        termination_axis='local_verifier_budget_terminal' if local_cap else 'original_terminal_category',
        new_calls_or_retries_granted=0, original_blocked_candidate_still_not_executed=True,
        semantic_Mirage_or_defense_efficacy_not_inferred=True)
