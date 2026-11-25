"""Withhold exact page-count support whose own reason leaves the count open.

This checks an explanation/source conflict, never reads pixels, assumes a page
capacity, supplies a corrected count, or certifies an unflagged assertion.
"""
import re

EXACT = re.compile(r'\b(?:there\s+(?:are|is)\s+)?(\d+)\s+(?:more|remaining|additional)\s+pages?\b|\b(\d+)\s+pages?\s+(?:remain|remaining|left)\b', re.I)
QUALIFIED = re.compile(r'\b(?:at\s+least|at\s+most|approximately|about|maybe|perhaps|possibly|might\s+be|may\s+be|could\s+be)\s+(?:there\s+(?:are|is)\s+)?\d+\s+(?:(?:more|remaining|additional)\s+)?pages?\b', re.I)
OPEN_COUNT = re.compile(r'\b(?:potentially|possibly|perhaps|maybe)\s+(?:many\s+)?more\b|\b(?:may|might|could)\s+(?:be|exist|have)\s+(?:still\s+)?more\b|\b(?:unknown|undetermined|unconfirmed)\s+(?:total|number|count)\b', re.I)


def pagination_count_reason_check(value):
    errors = []
    for i, claim in enumerate(value.get('claims', [])):
        if claim.get('status') != 'supported' or claim.get('kind') not in {'gui_fact', 'history_report'}:
            continue
        text = claim.get('text', '')
        if not EXACT.search(text) or QUALIFIED.search(text):
            continue
        # The reply's own reason, rather than candidate text or another source,
        # must explicitly acknowledge the unknown extra pages.
        reason = claim.get('reason', '')
        if OPEN_COUNT.search(reason):
            errors.append({'claim_index': i, 'reason_scope_error': 'An exact remaining-page count is marked supported, but its own reason explicitly leaves additional pages or the total count open. A truncated pagination strip with next/last arrows does not establish an exact total. Reassess the unchanged delivered evidence; retain uncertainty if the count is not established. No corrected count or navigation action is supplied.'})
    return {'reject': bool(errors), 'errors': errors, 'value_modified': False,
            'corrected_count_supplied': False, 'capacity_assumed': False,
            'replacement_action_supplied': False, 'unflagged_is_not_approval': True,
            'scope': 'Narrow exact-count versus explicitly open-count explanation conflict only'}
