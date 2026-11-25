"""Attribute direction-rule feedback without rewriting the original verdict."""
import copy
import hashlib

def attribute_direction_feedback(patch, original_action, direction_check):
    assert direction_check['reject'] is True
    assert patch['reason']==direction_check['reason']
    result=copy.deepcopy(patch)
    result.update(
        feedback_reason_source='native_direction_consistency',
        feedback_reason_sha256=hashlib.sha256(patch['reason'].encode()).hexdigest(),
        raw_verifier_reason_sha256=hashlib.sha256(original_action['reason'].encode()).hexdigest(),
        original_verifier_assessment=original_action['status'],
        direction_guard_candidate_sha256=direction_check['candidate_sha256'],
        direction_guard_supplies_replacement=False,
    )
    return result
