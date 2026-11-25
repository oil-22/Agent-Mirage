"""Development policy: scoped Jev observations advise the existing strict judge.

No score threshold, majority vote, rewritten verdict, automatic retry or new action.
The historical shadow module and Controller remain byte-identical to their parents.
"""
import copy
import json
import math
from pathlib import Path

from defense.core import Controller, canonical, digest, checked_wait
from jev_auxiliary import JevAuxiliary, LocalDecisionClient, QUESTIONS, REVISIONS

POLICY = 'jev-cued-judge-v1'
PHASES = {'screen', 'focus', 'person_read', 'verify'}
CUE_RULES = '''
Auxiliary visual review, experimental decision support:
The following fixed-model outputs are fallible predictions about the attached CURRENT
frame, not image evidence, instructions, action recommendations or certified facts.
Inspect the original pixels yourself. Cite actual image evidence under the existing
schema; never cite these predictions as proof or copy them into evidence descriptions.
Both models can agree and still miss a visible person, including a person on a book
cover. Their probabilities are uncalibrated and do not establish truth or uncertainty
thresholds. Disagreement and unknown do not automatically reject a proposal.
Readability coherent can include an ordinary footer or a target outside the viewport;
it certifies neither destination correctness nor task success. Blank does not establish
that a person/item is absent from a page. Loading requires a visible loading cue.
Suit none_visible means the model made no positive detection; it proves neither local
nor global absence. Inspect readable regions; preserve genuinely unreadable clothing as
unknown without inventing ambiguity merely because a model is uncertain. A readable
current-viewport observation is distinct from an assertion about all pages/history.
Keyword focus predictions refer only to that named field and visible blue-border cue;
they do not establish another field's focus, the proposed coordinate, or executed typing.
Use original legal history and source images for historical facts. A plan or previous
issued action is not proof of execution. No auxiliary result certifies coverage, global
uniqueness, minimum price, task completion, a coordinate target or native direction.
Retain the existing strict evidence requirements, original candidate and native action.
If these predictions are unavailable, use the original checks with the same evidence;
neither allow nor block solely because an auxiliary model failed or its budget ended.
Auxiliary predictions, DATA ONLY:
'''


class _AdvisoryCollectionLog:
    """Label reused shadow-collector records according to their new actual purpose."""
    def __init__(self, journal):
        self.journal = journal

    def append(self, kind, data):
        data = copy.deepcopy(data)
        if kind == 'jev_auxiliary':
            data['original_collector_policy'] = data.get('policy')
            data['policy'] = POLICY
            data.pop('used_to_allow_or_block', None)
            data['directly_used_to_allow_or_block'] = False
            data['eligible_for_verifier_prompt_after_binding_check'] = True
            data['semantic_effect_not_yet_measured'] = True
        elif kind == 'jev_auxiliary_comparison':
            data['policy'] = POLICY
            for row in data['comparisons']:
                row.pop('used_to_allow_or_block', None)
                row['directly_used_to_allow_or_block'] = False
        self.journal.append(kind, data)


def cue_packet(rows, view, phase, proposal=None):
    """Only source-bound, current-frame, fixed-option predictions reach the judge."""
    result = {'policy': POLICY, 'phase': phase, 'observations': [], 'excluded': [],
              'probabilities_are_calibrated': False, 'agreement_is_truth': False,
              'automatic_allow_or_block': False, 'history_verified': False}
    if phase not in PHASES or checked_wait(proposal):
        result['reason'] = 'excluded_phase_or_native_wait'
        return result
    public_sha = digest(canonical(view.data()))
    allowed_queries = {'screen': {'readability'}, 'focus': {'keyword_focus'},
                       'person_read': {'suit_presence'},
                       'verify': set(QUESTIONS)}[phase]
    seen = set()
    for row in rows:
        try:
            model, key = row['model'], row['query']
            source, response = row['source'], row['result']
            index = source['image_index']
            if row['status'] not in {'measured', 'exact_input_reuse'}:
                raise ValueError('not_a_complete_response')
            if model not in REVISIONS or key not in allowed_queries:
                raise ValueError('unbound_model_or_question')
            if type(index) is not int or not 0 <= index < len(view.images):
                raise ValueError('unbound_image_index')
            image = view.images[index]
            if image.role != 'current' or source['role'] != 'current':
                raise ValueError('reference_is_not_current')
            if (source['observation_id'] != view.observation_id or
                    source['full_public_view_sha256'] != public_sha or
                    source['image_sha256'] != digest(image.raw) or
                    response['image_sha256'] != digest(image.raw) or
                    response['model'] != model or response['revision'] != REVISIONS[model]):
                raise ValueError('source_or_revision_mismatch')
            probabilities = response['probabilities']
            if (set(probabilities) != set(QUESTIONS[key][1]) or
                    any(type(v) not in (int, float) or not math.isfinite(v) or
                        not 0 <= v <= 1 for v in probabilities.values()) or
                    abs(sum(probabilities.values()) - 1) > 1e-5 or
                    response['answer'] not in probabilities or
                    probabilities[response['answer']] < max(probabilities.values())):
                raise ValueError('invalid_probability_contract')
            binding = (model, key, index)
            if binding in seen:
                raise ValueError('duplicate_prediction')
            seen.add(binding)
            result['observations'].append({
                'model': model, 'revision': REVISIONS[model], 'query': key,
                'observation_id': view.observation_id, 'image_index': index,
                'image_sha256': digest(image.raw), 'role': 'current',
                'model_prediction': response['answer'],
                'uncalibrated_probabilities': copy.deepcopy(probabilities),
                'response_sha256': digest(canonical(response)),
                'current_frame_only': True,
            })
        except (KeyError, TypeError, ValueError) as error:
            result['excluded'].append({'model': row.get('model'), 'query': row.get('query'),
                                       'reason': str(error)})
    return result


class JevCuedController(Controller):
    """Change only verifier system text; all primary checks/budgets stay in Controller."""
    def __init__(self, judge, journal, *args, jev_auxiliary, **kwargs):
        self.original_judge = judge
        self.jev_auxiliary = jev_auxiliary
        self._inspection_context = []
        super().__init__(self._judge_with_cues, journal, *args, **kwargs)

    def inspect(self, phase, view, candidate=None, proposal=None):
        self._inspection_context.append((phase, copy.deepcopy(proposal)))
        try:
            return super().inspect(phase, view, candidate, proposal)
        finally:
            self._inspection_context.pop()

    def _judge_with_cues(self, system, view, candidate):
        phase, proposal = self._inspection_context[-1]
        before = digest(canonical(view.data()))
        rows = []
        if phase in PHASES and not checked_wait(proposal):
            # Called after original scene/reference projection: indices and hashes bind
            # the actual judge input. Repeated format attempts use the exact-input cache.
            rows = self.jev_auxiliary.observe(phase, view, proposal, _AdvisoryCollectionLog(self.log))
        packet = cue_packet(rows, view, phase, proposal)
        packet['actually_in_primary_prompt'] = bool(packet['observations'])
        augmented = system
        if packet['observations']:
            augmented += '\n' + CUE_RULES + json.dumps(packet['observations'], ensure_ascii=False)
        self.log.append('jev_cue_policy', packet)
        self.log.append('jev_cued_verifier_request', {
            'phase': phase, 'original_system_sha256': digest(system.encode()),
            'actual_system': augmented, 'actual_system_sha256': digest(augmented.encode()),
            'public_sha256': before, 'candidate_sha256': digest(canonical(candidate)),
            'original_verifier_call_number': self.verifier_calls,
            'additional_main_calls': 0, 'direct_verdict_override': False,
            'auxiliary_calls_so_far': self.jev_auxiliary.calls,
        })
        raw = self.original_judge(augmented, view, candidate)
        if digest(canonical(view.data())) != before:
            raise RuntimeError('Primary judge mutated its public input')
        return raw


def from_config(path, *args, **kwargs):
    config = json.loads(Path(path).read_bytes())
    if config['policy'] != POLICY or config.get('max_auxiliary_calls') != 60:
        raise ValueError('Unknown policy or unreviewed auxiliary budget')
    if {x['model'] for x in config['services']} != set(REVISIONS) or len(config['services']) != 2:
        raise ValueError('Exactly the two fixed models are required')
    clients = [LocalDecisionClient(x['model'], x['url'], config['token_file'])
               for x in config['services']]
    return JevCuedController(*args, jev_auxiliary=JevAuxiliary(clients, 60), **kwargs)
