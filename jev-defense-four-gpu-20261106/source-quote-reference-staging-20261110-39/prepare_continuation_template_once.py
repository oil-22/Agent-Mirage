"""Prepare a denied-by-default remaining28 package; never deploy or launch it."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / 'remaining29-full-history-gui-20261110-37'
OLD = PREVIOUS / 'runtime-package'
NAMESPACE = 'remaining28-source-reference-gui-20261110-40'
sys.path.insert(0, str(PREVIOUS))
from join_source_reviews import verify_seal
from orchestrate import sha, save


def read(path):
    return json.loads(Path(path).read_bytes())


def main():
    assert not (HERE / 'continuation-template-created.json').exists()
    manifest = read(OLD / 'manifest.json')
    assert sha(OLD / 'manifest.json') == '368b0a594822f5e294fcd21927aa924a18a80f23249f160857b5de7090c1c02d'
    for name, expected in manifest['files'].items():
        assert sha(OLD / name) == expected, name
    preparation = read(HERE / 'preparation-created.json')
    prepared = Path(preparation['root'])
    assert verify_seal(prepared) == preparation['seal_sha256']
    native = read(HERE / 'native-CPU-linked02-completed.json')
    native_root = Path(native['root'])
    assert verify_seal(native_root) == native['seal_sha256']
    receipt = read(native_root / 'receipt.json')
    assert receipt['passed'] and receipt['exact_source_ids_tested'] == 15
    assert receipt['no_real_model_negative_WAIT_semantic_or_capacity_pass']
    collection = PREVIOUS / 'remaining29-logical-terminal-collection-1794305230832617700'
    collection_seal = verify_seal(collection)
    gui = read(collection / 'GUI-preservation.json')
    service = read(collection / 'service-preservation.json')
    assert gui['terminal']['scoring_status'] == 'complete'
    assert service['run_id'] == gui['terminal']['run']['run_id'] == 'fullhistory23-T000-stale_replace-noaux'
    plan = read(OLD / 'plan.json')
    assert sha(OLD / 'plan.json') == '51e35415fc7df2d0309e67f117310de8ecffd59b51ece6bcfdda176e5ae4f98c'
    prior = read(OLD / 'continuation.json')
    excluded = prior['excluded_run_ids'] + [service['run_id']]
    assert excluded == [r['run_id'] for r in plan['queue'][:4]]
    old_ids = read(OLD / 'completed-request-exclusions.json')
    new_ids = [r['request_id'] for r in service['selected_requests']]
    assert len(old_ids['unique_request_ids']) == 362 and len(new_ids) == len(set(new_ids)) == 75
    assert not set(old_ids['unique_request_ids']) & set(new_ids)
    combined = sorted(set(old_ids['unique_request_ids']) | set(new_ids))
    assert len(combined) == 437
    out = HERE / ('remaining28-runtime-template-' + str(time.time_ns()))
    out.mkdir()
    for name in ['prepare_continuation_template_once.py', 'check_continuation_template.py', 'source_reference_decision_gate.py']:
        (out / name).write_bytes((HERE / name).read_bytes())
    package = out / 'runtime-template'
    for name in manifest['files']:
        path = package / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((OLD / name).read_bytes())
    (package / 'private.token').write_text(secrets.token_hex(32), encoding='ascii')
    assert sha(package / 'private.token') != manifest['auth_token_sha256']
    for path in (prepared / 'proposed-release').rglob('*.py'):
        if '__pycache__' not in path.parts:
            target = package / 'release' / path.relative_to(prepared / 'proposed-release')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
    terminal_copies = copy.deepcopy(prior['terminal_copies'])
    name = 'predecessor-terminals/' + service['run_id'] + '.json'
    raw = base64.b64decode(gui['exported_originals'][gui['terminal_name']], validate=True)
    assert hashlib.sha256(raw).hexdigest() == gui['terminal_sha256']
    (package / name).write_bytes(raw)
    terminal_copies.append(dict(run_id=service['run_id'], copy=name, sha256=gui['terminal_sha256']))
    exclusions = copy.deepcopy(old_ids)
    exclusions['sources'].append(dict(source='immutable_T000_stale_noaux_terminal75',
        collection=str(collection), collection_seal_sha256=collection_seal,
        file=str(collection / 'service-preservation.json'), sha256=sha(collection / 'service-preservation.json'), ids=new_ids))
    exclusions.update(unique_request_ids=combined, unique_count=437)
    (package / 'completed-request-exclusions.json').write_text(json.dumps(exclusions, indent=2)+'\n', encoding='utf8')
    continuation = copy.deepcopy(prior)
    continuation.update(schema='unchanged-original32-minus-four-terminal-remaining28-v1', excluded_run_ids=excluded,
        terminal_copies=terminal_copies, remaining_run_ids=[r['run_id'] for r in plan['queue'][4:]], remaining_tracks=28,
        completed_request_exclusions_sha256=sha(package / 'completed-request-exclusions.json'),
        source_reference_preparation_seal_sha256=preparation['seal_sha256'])
    (package / 'continuation.json').write_text(json.dumps(continuation, indent=2)+'\n', encoding='utf8')
    code = (OLD / 'continuation_manifest.py').read_text(encoding='utf8')
    code = code.replace('29 never-started', '28 never-started').replace("    'fullhistory23-T000-stale_replace-aux',\n]", "    'fullhistory23-T000-stale_replace-aux',\n    'fullhistory23-T000-stale_replace-noaux',\n]")
    code = code.replace("source['remaining_tracks'] == 29", "source['remaining_tracks'] == 28")
    code = code.replace("plan['queue'][:3]", "plan['queue'][:4]")
    code = code.replace('len(queue) == 29', 'len(queue) == 28').replace('== 362', '== 437')
    (package / 'continuation_manifest.py').write_text(code, encoding='utf8')
    (package / 'source_decision_gate.py').write_bytes((HERE / 'source_reference_decision_gate.py').read_bytes())
    for name in ['gpu_server.py', 'launch_gui_service_once.py']:
        code = (package / name).read_text(encoding='utf8')
        if name == 'gpu_server.py':
            assert code.count('19142') == 2
            code = code.replace('19142','19143')
        else:
            assert code.count('remaining29-full-history-gui-20261110-37') == 2
            code = code.replace('remaining29-full-history-gui-20261110-37', NAMESPACE)
        (package / name).write_text(code, encoding='utf8')
    reference = read(package / 'primary-reference.json')
    reference['previous_primary_backend_sha256'] = reference['primary_backend_sha256']
    reference['primary_backend_sha256'] = sha(package / 'release/defense/qwen_backend.py')
    reference['new_backend_change'] = 'verify-only source-reference schema dispatch; native generate AST unchanged'
    (package / 'primary-reference.json').write_text(json.dumps(reference, indent=2)+'\n', encoding='utf8')
    support = package / 'preflight_support.py'
    code = support.read_text(encoding='utf8')
    before = "'original_grammar_functions_and_schema_unchanged': True"
    assert code.count(before) == 1
    code = code.replace(before, "'canonical_grammar_library_functions_unchanged': True,\n            'verifier_schema_bound_separately_by_current_release': True", 1)
    support.write_text(code, encoding='utf8')
    admission = dict(admit_new_GUI_development=False, source_condition_decision_received=False,
        source_condition_choice=None, staging_template_only=True,
        scope='original32_minus_four_immutable_terminals_remaining28',
        already_approved_exact_STOP_source_repair_retained=True,
        distinct_source_reference_wire_condition_not_yet_approved=True,
        original_caps_images_full_main_history_and_native_actions_preserved=True)
    (package / 'admission.json').write_text(json.dumps(admission, indent=2)+'\n', encoding='utf8')
    new_manifest = copy.deepcopy(manifest)
    for key in ['human_decision_receipt_sha256','approved_source_proposal','approved_Controller_source_sha256',
                'Controller_changes_exactly_sealed_approved_source_mapping','original_Controller_and_all_forward_sources_unchanged',
                'all_forward_prompts_history_native_actions_and_budgets_unchanged','previous_human_decision_blocker_resolved']:
        new_manifest.pop(key, None)
    new_manifest.update(schema='STAGING-original32-remaining28-source-reference-template-v1',
        template_only=True, launch_ready=False, authorized_finite_joint_development=False,
        source_condition_choice=None, source_condition_decision_received=False,
        tracks=28, skipped_completed_terminal_tracks=4, total_original_tracks=32,
        outputs='/data/researcher/jev-defense-four-gpu-20261106/' + NAMESPACE,
        GUI_output='/data/researcher/jev-defense-four-gpu-20261106/' + NAMESPACE + '/batch',
        model_url='http://192.0.2.11:19143', planned_port_only_not_checked_or_reserved=True,
        original29_manifest_sha256=sha(OLD/'manifest.json'), original32_full_plan_sha256=sha(package/'plan.json'),
        continuation_sha256=sha(package/'continuation.json'), auth_token_sha256=sha(package/'private.token'),
        worker_source_sha256=sha(package/'gpu_server.py'), holder_identity_not_reverified_for_this_template=True,
        source_reference_preparation=preparation, native_reference_witness_checks=native,
        prior_exact_STOP_source_decision_sha256=sha(package/'human-source-condition-decision.json'),
        source_reference_condition_requires_distinct_user_decision=True,
        no_real_model_source_reference_semantic_or_capacity_preflight_yet=True,
        original_native_generate_validators_decide_full_main_history_and_auxiliary_unchanged=True,
        verify_wire_and_prompt_and_decode_choices_changed=True, completed_request_exclusions_count=437,
        source_condition_tradeoffs=read(prepared/'condition-boundary.json')['tradeoff'],
        source_table_example_system_token_delta=receipt['proposed_source_table_system_only_token_measurement'],
        new_model_GPU_GUI_scorer_paid_calls=0, efficacy_established=False)
    new_manifest['files'] = {p.relative_to(package).as_posix(): sha(p) for p in sorted(package.rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts and p.name not in ['manifest.json','private.token']}
    save(package/'manifest.json', new_manifest)
    for p in package.rglob('*.py'):
        compile(p.read_text(encoding='utf8'),str(p),'exec')
    tested = subprocess.run([sys.executable,'-B',str(out/'check_continuation_template.py'),str(package),str(OLD),str(prepared/'proposed-release')],capture_output=True,timeout=55)
    (out/'checks.stdout.txt').write_bytes(tested.stdout)
    (out/'checks.stderr.txt').write_bytes(tested.stderr)
    if tested.returncode:
        save(out/'failure.json',dict(returncode=tested.returncode,new_model_GUI_scorer_calls=0))
        save(out/'seal.json',{p.relative_to(out).as_posix():sha(p)for p in out.rglob('*')if p.is_file()and'__pycache__'not in p.parts})
        raise RuntimeError(str(out)+'\n'+tested.stderr.decode(errors='replace')[-2000:])
    checks=json.loads(tested.stdout)
    save(out/'receipt.json',dict(time=time.time(),CPU_checks=checks,manifest_sha256=sha(package/'manifest.json'),
        original32_plan_unchanged=True,excludes_four_complete_endpoints_and437_requests=True,
        template_only_not_deployed=True,original16_pairs_retained_14_prospective_pairs_are_version_stratum=True,
        original_remaining28_zero_counters_only=True,source_decision_received=False,
        no_model_GUI_resource_or_network_launch=True,new_model_GPU_GUI_scorer_paid_calls=0,goal='active'))
    save(out/'seal.json',{p.relative_to(out).as_posix():sha(p)for p in out.rglob('*')if p.is_file()and'__pycache__'not in p.parts})
    result=dict(root=str(out),receipt_sha256=sha(out/'receipt.json'),seal_sha256=sha(out/'seal.json'),
        manifest_sha256=sha(package/'manifest.json'),launch_ready=False,source_condition_pending=True)
    save(HERE/'continuation-template-created.json',result)
    print(json.dumps(result))


if __name__=='__main__':
    main()
