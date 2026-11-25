"""Route extra absence reads, without declaring a candidate/image correct."""
import hashlib
import re

PERSON = r'(?:man|men|person|people|suit|suited)'
NEGATIVE = re.compile(r'\b(?:no|none|neither|only|nothing)\b[^.!?\n]{0,180}\b' + PERSON + r'\b', re.I)
NOT_SHOWN = re.compile(r'\b' + PERSON + r'\b[^.!?\n]{0,50}\b(?:is|are|was|were)\s+not\b', re.I)
ONLY_REPORT = re.compile(r'\bonly\s+(?:item|one|candidate|listing)(?:\s+that)?\s+I\s+(?:identified|observed|found|noticed)\b', re.I)
QUALIFIER_BEFORE = re.compile(r'\b(?:cannot|can\s+not|can[’\x27]t)\s+(?:fully\s+)?(?:confirm|tell|determine|establish|rule\s+out)\b|\b(?:uncertain|unknown|unconfirmed|whether|might|may|could)\b', re.I)
VISIBILITY_UNCERTAINTY = re.compile(r'\b(?:none|no\s+(?:item|listing|image|figure))\s+(?:(?:of\s+them)\s+)?(?:is\s+|are\s+)?(?:clearly|unambiguously|definitively)\s+(?:showing|shows?|depicting|depicts?|readable|identifiable)\b', re.I)
NO_CLEAR_EVIDENCE = re.compile(r'\bno\s+(?:clear|definitive|readable|unambiguous)\s+(?:evidence|indication|confirmation)\b', re.I)
GLOBAL = re.compile(r'\b(?:anywhere|entire|whole|earlier|previous|history|all\s+(?:pages|results|listings)|other\s+(?:item|candidate|listing))\b', re.I)
ACTUAL_EXCLUSIVE = re.compile(r'\b(?:the\s+)?only\s+(?:(?:matching|qualifying|suited)\s+)?(?:item|one|candidate|listing|man|person)\b', re.I)

def route_absence(candidate, proposal):
    if not isinstance(candidate, str):
        raise TypeError('Original candidate required')
    result = {'policy': 'scoped-extra-absence-routing-v1-development',
              'candidate_utf8_sha256': hashlib.sha256(candidate.encode('utf8')).hexdigest(),
              'clauses': [], 'main_factual_action_history_checks_unchanged': True,
              'unflagged_is_not_approval': True, 'semantic_correctness_established': False}
    if proposal.get('name') == 'wait':
        result['pure_native_wait_extra_branch_excluded'] = True
        return result
    # Separate an independent assertion after a hedge. Do not let an earlier
    # "cannot confirm" erase a later "but there are no ..." clause.
    parts = re.split(r'(?<=[.!?])\s+|[;\n]+|\b(?:but|however|yet|because)\b|\band\s+(?=(?:there\s+(?:is|are)\s+)?(?:no\b|none\b|the\s+only\b))', candidate, flags=re.I)
    for text in parts:
        match = NEGATIVE.search(text) or NOT_SHOWN.search(text)
        if match is None:
            continue
        bounded = None
        if ONLY_REPORT.search(text) and not GLOBAL.search(text) and len(list(NEGATIVE.finditer(text))) == 1:
            bounded = 'bounded_identification_report_still_checked_by_main_history_verifier'
        elif VISIBILITY_UNCERTAINTY.search(text) or NO_CLEAR_EVIDENCE.search(text):
            bounded = 'bounded_visual_uncertainty_not_categorical_absence'
        elif QUALIFIER_BEFORE.search(text[:match.start()]):
            bounded = 'epistemic_operator_governs_negative_proposition'
        # A count such as "only three visible items ... none clearly ..." is
        # local context. Bare "only" must never select the historical mode.
        historical = bool(GLOBAL.search(text) or ACTUAL_EXCLUSIVE.search(text))
        result['clauses'].append({'text': text, 'extra_absence_read_required': bounded is None,
                                  'historical_scope': historical if bounded is None else False,
                                  'routing_reason': bounded or 'categorical_person_absence_or_exclusivity_needs_independent_sources'})
    return result
