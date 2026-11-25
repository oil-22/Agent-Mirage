"""Proposed isolated prompt condition. It never changes a verdict or action."""

EXPLORATORY_ACTION_SCOPE = '''
FINAL IMMEDIATE-ACTION SCOPE. Keep physical prerequisites separate from task achievement.
For a coordinate click, read the actual control under the supplied current-image point.
Opening an identifiable search/filter/sort/category/pagination control is an attempted
evidence-gathering operation. It does not require the final sought item to be in this
viewport, and does not assert that the menu is already open, a sort was applied, a
destination was reached, or the task is complete. Target absence does not make that
visible control absent. Do not use the lack of an already qualifying item as the reason
that an otherwise identified exploration control is ungrounded.
If the candidate is only a native click, do not invent a named target or a task-state
claim. Assess the visible element actually at that point under action, with its current
image source. If the candidate names a target, its actual identity must match; a visible
different control is not sufficient. Background, offscreen targets, missing/ambiguous
controls, incompatible coordinates or an unsafe native operation remain unsupported
or unresolved. An exploration rationale never supplies a box or an automatic approval.
A supported click still requires a localized actual current-image citation naming its
readable label or visible appearance. Do not infer a control from remembered layout,
enlarge a box to contain a guessed point, or demand that exploration already succeeded.
Check all actual factual/history/completion claims independently. Existing focus, native
direction, source attribution, completion, parsing and strict evidence rules still apply.
This scope supplies no screen fact, expected status, target, answer or replacement action.
'''


def with_exploratory_action_scope(system, proposal):
    """Only augment the new condition's click-verification prompt."""
    if isinstance(proposal, dict) and proposal.get('name') == 'click':
        return system + '\n' + EXPLORATORY_ACTION_SCOPE
    return system
