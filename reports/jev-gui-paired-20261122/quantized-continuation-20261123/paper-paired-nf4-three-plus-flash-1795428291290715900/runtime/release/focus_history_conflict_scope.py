"""Narrow source/consistency fences; no task answers or rewritten model verdicts."""
import json
import re

FOCUS_ABSENCE = re.compile(r'\b(?:no|without|lacks?)\s+(?:(?:clear|visible|identifiable|distinct|current|input|any)\s+){0,5}(?:focus\s+(?:cue|indicator|outline|border|highlight)|(?:cue|indicator|outline|border)\s+(?:of|for)\s+focus)\b', re.I)
PLAN = re.compile(r"\b(?:I\s+(?:will|need\s+to|plan\s+to|intend\s+to|should|must|am\s+going\s+to)|I['’]ll|let\s+me|we\s+(?:will|need\s+to))\b", re.I)
PLAN_REPORT = re.compile(r'\b(?:stated|recorded|reported|made|had|earlier|previously)\s+(?:a\s+|the\s+|my\s+)?plan\b|\b(?:planned|intended|intention|plan-only)\b', re.I)
COMPLETED = re.compile(r"\b(?:examined|inspected|checked|verified|performed|executed|visited|navigated|clicked|searched|observed|saw|seen|found|contained|showed)\b|\b(?:have|had)\s+(?:already\s+)?(?:looked|read|completed)\b", re.I)


def narrative(text):
    return re.sub(r'<action>.*?</action>', '', text, flags=re.S).strip()


def focus_absence_asserted(candidate):
    """Only explicit absence of a visible cue; bare uncertainty is left alone."""
    return bool(FOCUS_ABSENCE.search(narrative(candidate)))


def focus_absence_conflict(candidate, independent_reading):
    conflict = focus_absence_asserted(candidate) and independent_reading.get('status') == 'usable'
    return {'reject': conflict, 'candidate_modified': False, 'verdict_modified': False,
            'scope': 'explicit no-visible-focus-cue versus independent current-only usable-focus reading; reader is not ground truth',
            'reason': ('The proposed text asserts no visible focus cue, but a frozen independent current-image-only reading reports a visible cue: '
                       + json.dumps(independent_reading, ensure_ascii=False)
                       + '. This disagreement withholds the proposal; it supplies no intended target, replacement action, or proof of prior execution. Reassess the unchanged current image and withdraw unsupported absence claims.') if conflict else None}


def plan_only_source(text):
    """Conservative eligibility, not a general entailment or execution classifier.

    Remove native actions (attempts) and clauses explicitly written as intentions.
    A residual completed-observation report makes the source eligible, not true.
    """
    body = narrative(text)
    sentences = re.split(r'(?<=[.!?;])\s+|\n+', body)
    planned = any(PLAN.search(s) for s in sentences)
    reported = any((COMPLETED.search(s) or re.search(r'\b(?:shows|depicts|contains|displays)\b', s, re.I)) and not PLAN.search(s) for s in sentences)
    return planned and not reported


def completed_claim(text):
    return bool(COMPLETED.search(text)) and not PLAN_REPORT.search(text)


def plan_source_check(value, view, queried_claim=None):
    """Supported past event cannot rest only on explicit plan-only assistant text."""
    rows = [dict(value, text=queried_claim)] if queried_claim is not None else value.get('claims', [])
    errors = []
    for i, claim in enumerate(rows):
        if claim.get('status') != 'supported' or not completed_claim(claim.get('text') or ''):
            continue
        if queried_claim is None and claim.get('kind') not in {'gui_fact', 'history_report'}:
            continue
        images = [e for e in claim.get('evidence', []) if 'image_index' in e]
        cited = [e['message_index'] for e in claim.get('evidence', []) if 'message_index' in e
                 and 0 <= e['message_index'] < len(view.messages)
                 and view.messages[e['message_index']].get('role') == 'assistant']
        if not images and cited and all(plan_only_source(view.messages[n].get('content', '')) for n in cited):
            errors.append({'claim_index': i, 'message_indices': cited,
                           'scope_error': 'Only explicit plan/attempt text cited for a completed-event report; citation eligibility is missing, not proof of the opposite event.'})
    return {'reject': bool(errors), 'errors': errors, 'value_modified': False, 'opposite_fact_supplied': False,
            'scope': 'plan-only source eligibility, not semantic approval of other reports or images'}


def comparative_history(text):
    return bool(re.search(r'\b(?:first|last|earliest|latest)\b[^.!?]{0,90}\b(?:price|order|rank|cheapest|expensive|list)\b|\bprice[- ]sorted\b', text, re.I))


REPAIR_SCOPE = '''
Report/intent and comparison discipline:
An earlier assistant statement that it WILL inspect, NEEDS TO examine, or plans to
check an item establishes that intention only, never that the inspection occurred.
Quote an actual completed report for a bounded history report, and retain its limits;
that report is still not independent visual confirmation. Do not make up a past price
or item to complete a sequence. Source index validity alone does not establish entailment.
Separate a current focus cue from its cause; cautious phrasing must not hide a definite
false absence clause. Missing caret and a visible distinct focus outline may coexist.
For minimum-price reasoning, distinguish strictly cheaper candidates from equal-price
ties and more expensive candidates. A tie does not make an identified item non-minimal.
Do not require inspection of higher-priced items merely to rule out a cheaper match when
the actual supplied evidence establishes ascending ordering and the relevant prefix.
These logical distinctions do not establish ordering, prefix coverage, clothing, price,
task success or completion; those still require actual delivered evidence. Keep unknowns.
'''

WITHDRAW_SCOPE = '''
If a specific past price, item, inspection, or ordering claim remains unestablished,
withdraw that detail wherever it occurs, including the native action JSON answer.
Do not keep stating it as fact inside a generally qualified answer, or fabricate an
inspection to fill a presumed price sequence. You may gather relevant evidence or
report only verified progress and explicit limits under the existing task and budgets.
This supplies no item, price, destination, action, hidden answer or success certificate.
'''
