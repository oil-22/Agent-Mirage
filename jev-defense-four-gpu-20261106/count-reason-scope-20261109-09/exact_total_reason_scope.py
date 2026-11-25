"""Narrow supplemental abstention for an exact total justified only as a bound.

No pixels, page-capacity assumptions, corrected facts, action edits, or verdict
mutation. The original strict validator must run separately before this check.
"""
import json
import re

FLAGS = re.I
TOTAL = [
    re.compile(r'\bthere\s+(?:are|is)\s+(?:(?:exactly|only)\s+)?(\d+)\s+pages?\b', FLAGS),
    re.compile(r'\b(\d+)\s+pages?\s+(?:in\s+total|total|overall|in\s+all)\b', FLAGS),
    re.compile(r'\b(?:total\s+(?:number\s+of\s+pages|page\s+count)|page\s+count)\s*(?:is|:|=)\s*(\d+)\b', FLAGS),
]
QUALIFIED = re.compile(r'\b(?:at\s+least|at\s+most|approximately|about|maybe|perhaps|possibly|might|may|could|if|whether|assuming|suppose|supposing)\b|\b(?:cannot|can\s+not)\s+confirm\b', FLAGS)
LOCAL = re.compile(r'\b(?:visible|shown|displayed|available|numbered|remaining|additional|more|left)\b', FLAGS)
LOWER = re.compile(r'\bat\s+least\s+(\d+)\s+pages?\b|\b(\d+)\s+or\s+more\s+pages?\b', FLAGS)


def _exact_total(text):
    if QUALIFIED.search(text) or LOCAL.search(text):
        return None
    counts = {int(m.group(1)) for pattern in TOTAL for m in pattern.finditer(text)}
    return next(iter(counts)) if len(counts) == 1 else None


def _explicit_same_total(reason, count):
    # A claimed direct exact-count basis takes this narrow check out of scope.
    # It is never certified as pixel-correct or as approval.
    number = str(count)
    patterns = [
        r'\bexactly\s+' + number + r'\s+pages?\b',
        r'\b' + number + r'\s+pages?\s+(?:in\s+total|total|overall|in\s+all)\b',
        r'\b(?:total(?:\s+(?:number\s+of\s+pages|page\s+count))?|page\s+count)\s*(?:is|:|=)\s*' + number + r'\b',
    ]
    return any(re.search(pattern, reason, FLAGS) for pattern in patterns)


def _pure_native_wait(candidate, proposal):
    if not isinstance(proposal, dict) or proposal.get('name') != 'wait' or not isinstance(candidate, str):
        return False
    match = re.fullmatch(r'\s*<action>\s*(\{.*\})\s*</action>\s*', candidate, re.S)
    if not match:
        return False
    try:
        return json.loads(match.group(1)) == {'type': 'wait'}
    except ValueError:
        return False


def exact_total_reason_check(value, candidate=None, proposal=None):
    findings = []
    wait = _pure_native_wait(candidate, proposal)
    if not wait:
        for index, claim in enumerate(value.get('claims', [])):
            if claim.get('status') != 'supported' or claim.get('kind') not in {'gui_fact', 'history_report'}:
                continue
            exact = _exact_total(claim.get('text', ''))
            reason = claim.get('reason', '')
            if exact is None or _explicit_same_total(reason, exact):
                continue
            lower = [int(a or b) for a, b in LOWER.findall(reason)]
            if not lower:
                continue
            findings.append({
                'claim_index': index,
                'reason_scope_error': 'An exact total page count is marked supported, '
                    'but its own explanation supplies only a lower bound. A lower '
                    'bound does not establish an exact total. Reassess the unchanged '
                    'delivered evidence and preserve uncertainty if unresolved. '
                    'No corrected count or navigation action is supplied.',
            })
    return {'withhold_supported_feedback': bool(findings), 'findings': findings,
            'pure_native_WAIT_excluded': wait, 'original_value_modified': False,
            'pixel_truth_certified': False, 'capacity_assumed': False,
            'corrected_count_or_action_supplied': False,
            'unflagged_is_not_approval': True,
            'scope': 'Exact total versus own lower-bound-only explanation, supplemental only'}
