"""Freeze exact 19 NEW Flash requests; never run a model, GUI or old queue."""
import ast
import base64
import json
from pathlib import Path
import shutil

from defense.core import PublicView, VisibleImage, canonical, digest
from flash_policy import MODEL, REVISION, POLICY, STATE, QUESTIONS, CUE_RULES

BASE = Path(__file__).resolve().parent
WORKSPACE = BASE.parents[1]
OLD = WORKSPACE / 'jev-defense-local-20261102'
SOURCE = WORKSPACE / 'defense-resume-20261102/package-retry2/restored-inputs'
PARENT = WORKSPACE / 'jev-defense-validation-20261103/release'


def save(path, value):
    with path.open('x', encoding='utf8') as file:
        json.dump(value, file, ensure_ascii=False, indent=2)


def main():
    root = BASE / 'flash-preflight-frozen-01'
    root.mkdir(exist_ok=False)
    (root / 'images').mkdir()
    (root / 'requests').mkdir()
    old_plan = json.loads((OLD / 'preflight-plan.json').read_bytes())
    requests, admission = [], []
    for case in old_plan['cases']:
        raw = (SOURCE / 'images' / (case['image_sha256'] + '.png')).read_bytes()
        assert digest(raw) == case['image_sha256']
        (root / 'images' / (case['image_sha256'] + '.png')).write_bytes(raw)
        # Explicit isolated development observation, NOT an original actor wire body.
        view = PublicView(case['id'], [{'role': 'user', 'content':
            'Independent single-frame evidence development control.'}],
            (VisibleImage(raw, 'current'),), observed_at=old_plan['created'])
        provenance = {'observation_id': view.observation_id, 'image_index': 0,
            'role': 'current', 'image_sha256': digest(raw),
            'full_public_view_sha256': digest(canonical(view.data())),
            'history_verified': False, 'not_live_capture': True,
            'source_case': case['id'], 'original_preflight_plan_sha256': digest((OLD/'preflight-plan.json').read_bytes())}
        todo = list(QUESTIONS.items())
        if case['id'] == 'p01':
            todo.insert(0, ('native_smoke', ('Does this screenshot contain a readable GUI?',
                {'yes': 'A readable GUI is visible.', 'no': 'No readable GUI is visible.',
                 'unknown': 'The screenshot is too unclear to determine.'})))
        for key, (question, options) in todo:
            case_id = case['id'] + '-' + key
            body = {'image_base64': base64.b64encode(raw).decode(),
                'image_sha256': digest(raw), 'state': STATE, 'question': question,
                'options': options, 'query_key': key, 'provenance': provenance}
            fingerprint = digest(canonical(body))
            relative = 'requests/' + case_id + '.json'
            save(root / relative, body)
            requests.append({'case_id': case_id, 'request': relative,
                'fingerprint_excluding_request_id': fingerprint,
                'image_sha256': digest(raw), 'query_key': key,
                'purpose': 'transport_smoke' if key=='native_smoke' else 'new_model_visual_development'})
            admission.append({'case_id': case_id, 'fingerprint': fingerprint})
    assert len(requests) == 19
    save(root / 'plan.json', {
        'model': MODEL, 'repository': 'perplexity-ai/pplx-decider-flash-v1.2',
        'revision': REVISION, 'max_new_flash_calls': 19, 'max_primary_calls': 0,
        'separate_smoke_calls': 1, 'visual_development_calls': 18,
        'automatic_retry': False, 'output_generation_tokens': 0,
        'native_fast': False, 'questions_per_request': 1,
        'same_known_task_nonblind_development': True, 'independent_task_efficacy': False,
        'native_full_actor_history_supplied': False,
        'private_expected_labels_sent_to_model': False,
        'old_neohorse_style_calls_to_rerun': 0,
        'old_results_reuse_for_evaluation_only': True,
        'same_questions_state_options_as_old_visual_controls': True,
        'questions_state_sha256': digest(canonical([STATE, QUESTIONS])),
        'source_plan_sha256': digest((OLD/'preflight-plan.json').read_bytes()),
        'private_review_sha256_for_evaluation_only': digest((OLD/'PRIVATE-source-review.json').read_bytes()),
        'uncertainties': ['p06 clothing unresolved', 'p06 Keyword/Your search field identity ambiguous',
            'no positive-loading original frame in these six', 'no pure-footer original frame in these six',
            'smoke is transport only, not a semantic control'],
        'requests': requests, 'GUI_actions': 0, 'paid_API_calls': 0,
        'formal_GUI_release': False})
    save(root / 'server-admission.json', {'mode': 'preflight', 'max_new_calls': 19, 'requests': admission})
    save(root / 'gui-single-flash-config.proposed.json', {'policy': POLICY,
        'model': MODEL, 'revision': REVISION, 'max_auxiliary_calls': 60,
        'url': 'http://127.0.0.1:18223',
        'token_file': '/home/researcher/jev-defense-four-gpu-20261106/transport.token',
        'deployment_applied': False, 'GUI_ready': False})
    # Do not manufacture original request identity for two recovered prompts.
    tree = ast.parse((PARENT / 'defense/prompts.py').read_text(encoding='utf8'))
    namespace = {}
    exec(compile(tree, '<frozen prompt constants>', 'exec'), namespace)
    binding = json.loads((WORKSPACE/'jev-defense-validation-20261103/recovery-evidence/prompt-binding-audit-1793684243130128922.json').read_bytes())
    prompts = {}
    for name in ['COMPLETION_RELATION', 'NATIVE_NAVIGATION']:
        text = namespace[name]
        prompts[name] = {'current_text': text, 'sha256': digest(text.encode()),
                         'historical_actual_request_identity': None,
                         'declared_condition': 'recovered current source, not proved historical wire text'}
    save(root / 'active-prompt-disclosure.json', {
        'potentially_active_unbound_prompts': prompts,
        'prior_requests_examined': binding['requests_examined'],
        'whole_historical_prompts_file_restored': False,
        'remaining_formal_GUI_condition_issue': True,
        'note': 'Current exact text is frozen and disclosed; no invented historical diff or match.'})
    (root / 'seal.json').write_text(json.dumps({str(p.relative_to(root)).replace('\\','/'):digest(p.read_bytes())
        for p in root.rglob('*') if p.is_file()}, indent=2), encoding='utf8')
    print(json.dumps({'root': str(root), 'Flash_call_cap': 19, 'primary_calls': 0,
                      'exact_request_fingerprints': len(admission), 'model_calls': 0}))


if __name__ == '__main__': main()
