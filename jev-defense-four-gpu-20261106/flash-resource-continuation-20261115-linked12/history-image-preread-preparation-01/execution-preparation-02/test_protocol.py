"""Adversarial execution checks with real frozen inputs and fake callbacks.

Never constructs a GPU engine. All returned 'replies' are clearly CPU fixtures;
they are not real WAIT, visual, semantic, generation, or capacity controls.
"""
import copy
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREP = HERE.parent
sys.path.insert(0, str(PREP))
import reading_contract as contract
from offline_protocol import APPROVAL_ANSWER, CONDITION, PHASE_CAPS, canonical, run_offline


def fixture(binding):
    return json.dumps({'version': contract.VERSION, 'coverage': 'partial_visual_reading',
        'frames': [{'image_id': r['image_id'], 'readability': 'unreadable', 'visible_text': [],
                    'visible_features': [], 'limitations': ['CPU fixture; no model or visual judgment.']}
                   for r in binding['image_occurrences']]})


def main():
    frozen = Path(json.loads((PREP / 'frozen-sources-current.json').read_bytes())['root'])
    ptr = json.loads((PREP / 'proposed-inputs-current.json').read_bytes())
    proposed = Path(ptr['root'])
    cases = []
    for index in range(1, 11):
        cid = 's%02d' % index
        cases.append({'case_id': cid, 'original_body': json.loads((frozen / cid / 'source/body.json').read_bytes()),
                      'binding': json.loads((proposed / cid / 'source-binding.json').read_bytes()),
                      'preread_body': json.loads((proposed / cid / 'preread-full-body.json').read_bytes()),
                      'original_effective_generation': {'test_fixture_only': True}})
    checks = []
    def check(name, value):
        assert value, name
        checks.append({'name': name, 'passed': True, 'scope': 'mocked CPU execution only'})
    with tempfile.TemporaryDirectory(prefix='mirage-preread-protocol-') as temp:
        temp = Path(temp)
        def scenario(name, mutation=None, invalid_reading=None, technical_at=None, foreign_after=False):
            study = temp / name
            auth = {'authorized': True, 'exact_answer': APPROVAL_ANSWER, 'condition': CONDITION,
                    'proposal_seal_sha256': 'CPU-PROPOSAL-FIXTURE', 'new_primary_calls_cap': 20,
                    'phase_output_caps': PHASE_CAPS, 'GUI_Flash_scorer_paid_calls': 0, 'automatic_retries': 0,
                    'formal_GUI_authorized': False, 'source': 'actual_human_reply',
                    'human_reply_receipt_sha256': 'CPU-MOCK-ONLY-NOT-ACTUAL-AUTHORIZATION',
                    'study_claim_root': str(study.resolve())}
            # This authorization-like dictionary is never written to a real package.
            if mutation:
                mutation(auth)
            calls, resources = [], []
            def cpu(body, folder):
                check(name + ':CPU_body_equals_persisted_exact_body', json.loads((folder / 'body.bin').read_bytes()) == body)
                return {'CPU_mock_not_real_native_input': True}
            def resource(loaded):
                resources.append(loaded)
                if foreign_after and calls:
                    raise RuntimeError('CPU fixture late foreign process; no process touched')
                return {'CPU_mock_resource_only': True, 'actual_GPU_lease': False}
            def native(body, folder, expected, generation, limit):
                key = folder.parent.name + '-' + folder.name
                calls.append((key, limit))
                if key == technical_at:
                    raise RuntimeError('CPU fixture model-call failure; not actual inference')
                binding = next(c['binding'] for c in cases if c['case_id'] == folder.parent.name)
                text = (invalid_reading if folder.parent.name == 's01' and folder.name == 'preread'
                        and invalid_reading is not None else fixture(binding)) if folder.name == 'preread' else '<action>{"type":"wait"}</action>'
                return {'text': text, 'natural_EOS': True, 'model_generate_calls': 1,
                        'first_forward_seen': True, 'CPU_fake_reply_not_real_model_output': True}
            try:
                result = run_offline(root=study / 'attempt01', study_claim_root=study, authorization=auth,
                    proposal_seal_sha256='CPU-PROPOSAL-FIXTURE', cases=cases, contract=contract,
                    native_cpu_prepare=cpu, resource_admission=resource, audited_native_call=native)
            except (RuntimeError, FileExistsError) as exc:
                result = {'early_rejection': str(exc)}
            return result, calls, resources, auth, study
        for name, mutation in [
            ('missing_approval', lambda a: a.update(authorized=False)),
            ('old_ten_call_scope', lambda a: a.update(exact_answer='批准10条离线开发预检（推荐）')),
            ('changed_proposal', lambda a: a.update(proposal_seal_sha256='changed')),
            ('expanded_budget', lambda a: a.update(new_primary_calls_cap=21)),
            ('wrong_actor_cap', lambda a: a.update(phase_output_caps={'preread':4096,'actor':4096})),
            ('unapproved_GUI', lambda a: a.update(formal_GUI_authorized=True)),
            ('CPU_fixture_not_human', lambda a: a.update(source='CPU_fixture')),
            ('different_claim_path', lambda a: a.update(study_claim_root=str(temp / 'other'))),
        ]:
            result, calls, resources, _, study = scenario(name, mutation)
            check(name + ':reject_before_calls_and_output_creation', 'early_rejection' in result and not calls and not resources and not study.exists())
        result, calls, _, auth, study = scenario('complete20')
        expected_order = [(c['case_id'] + '-' + phase, PHASE_CAPS[phase]) for c in cases for phase in ['preread', 'actor']]
        check('only20_phase_calls_exact_order_and_caps', calls == expected_order and result['status'] == 'completed')
        check('all20_claims_retained', len(list((study / 'attempt01/claims').glob('*.json'))) == 20)
        head, count = '0' * 64, 0
        for line in (study / 'attempt01/journal.jsonl').read_bytes().splitlines():
            event = json.loads(line); recorded = event.pop('sha256')
            assert event['seq'] == count and event['previous'] == head
            assert hashlib.sha256(canonical(event)).hexdigest() == recorded
            head, count = recorded, count + 1
        check('complete_event_SHA_chain_matches_terminal', result['journal_chain'] == {'head': head, 'events': count})
        for case in cases:
            base = study / 'attempt01/cases' / case['case_id']
            augmented = json.loads((base / 'actor/body.bin').read_bytes())
            old = case['original_body']
            check(case['case_id'] + ':full_original_history_preserved_in_dynamic_actor',
                  augmented['messages'][:-1] == old['messages'][:-1] and
                  augmented['messages'][-1]['content'][:-1] == old['messages'][-1]['content'])
        try:
            run_offline(root=study / 'different_attempt', study_claim_root=study, authorization=auth,
                proposal_seal_sha256='CPU-PROPOSAL-FIXTURE', cases=cases, contract=contract,
                native_cpu_prepare=lambda *_: (_ for _ in ()).throw(AssertionError('Should not prepare')),
                resource_admission=lambda *_: (_ for _ in ()).throw(AssertionError('Should not admit')),
                audited_native_call=lambda *_: (_ for _ in ()).throw(AssertionError('Should not call')))
        except FileExistsError:
            check('different_attempt_cannot_reuse_same_authorization', not (study / 'different_attempt').exists())
        else:
            raise AssertionError('Study authorization was replayed')
        result, calls, _, _, study = scenario('invalid_reading', invalid_reading='{}')
        check('invalid_reading_skips_actor_no_budget_filling', len(calls) == 19 and ('s01-actor',2048) not in calls
              and result['case_outcomes'][0]['status'] == 'reading_contract_invalid')
        check('invalid_raw_reply_preserved', json.loads((study/'attempt01/cases/s01/preread/native-returned.json').read_bytes())['text'] == '{}')
        result, calls, _, _, study = scenario('technical_failure', technical_at='s01-preread')
        check('technical_failure_consumes_claim_no_retry_or_next_prefix', calls == [('s01-preread',4096)] and result['status'] == 'preserved_failure'
              and result['attempted'] == ['s01-preread'] and result['completed'] == [])
        result, calls, _, _, study = scenario('late_foreign', foreign_after=True)
        check('late_resource_conflict_stops_without_actor', calls == [('s01-preread',4096)] and result['status'] == 'preserved_failure')
        check('late_resource_conflict_keeps_exact_returned_reply', (study/'attempt01/cases/s01/preread/native-returned.json').exists()
              and (study/'attempt01/cases/s01/preread/seal.json').exists())
    dest = HERE / ('CPU-protocol-checks-' + str(time.time_ns()))
    dest.mkdir()
    result = {'checks': checks, 'passed': len(checks), 'failed': 0,
              'callbacks_were_CPU_fakes_not_real_models_or_GPU_admissions': True,
              'dummy_WAIT_not_real_semantic_or_generation_control': True,
              'real_authorization_created': False, 'actual_model_GPU_GUI_calls': 0,
              'actual_native_wrapper_runtime_forward_or_GPU_capacity_tested': False}
    (dest/'result.json').write_bytes(canonical(result))
    for name in ['offline_protocol.py','checked_native_call.py','test_protocol.py']:
        (dest/name).write_bytes((HERE/name).read_bytes())
    (dest/'seal.json').write_bytes(canonical({p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in dest.iterdir()if p.is_file()}))
    with (HERE/'CPU-checks-current.json').open('x',encoding='utf8') as stream:
        json.dump({'root':str(dest),'seal_sha256':hashlib.sha256((dest/'seal.json').read_bytes()).hexdigest()},stream,indent=2)
    print(json.dumps({'CPU_checks':len(checks),'new_model_GPU_GUI_calls':0,'root':str(dest)}))


if __name__ == '__main__':
    main()
