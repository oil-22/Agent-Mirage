"""Collect one source-reviewed endpoint of the frozen remaining29, read-only.

Reuse the sealed original GUI/run-end/counter/request-SHA checks. Never launch,
retry, stop or modify a trajectory. A pending observation creates no endpoint.
"""
import argparse
import base64
import copy
import importlib.util
import json
from pathlib import Path
import re
import time

from orchestrate import HERE, PACKAGE, OUTPUT, GUIROOT, REMOTE_PACKAGE, admitted, remote, save, sha
from join_source_reviews import verify_seal


EXPECTED_MANIFEST = '368b0a594822f5e294fcd21927aa924a18a80f23249f160857b5de7090c1c02d'
PLAN_SHA = '51e35415fc7df2d0309e67f117310de8ecffd59b51ece6bcfdda176e5ae4f98c'
EXCLUDED = ['fullhistory23-T000-clean-noaux', 'fullhistory23-T000-clean-aux',
            'fullhistory23-T000-stale_replace-aux']
SOURCE_ROOT = HERE.parent / 'prefill-scheduled-full-history-gui-20261109-32/logical-terminal-collection-1794251064196236500'
SOURCE_HASHES = {
    'collect_logical_terminal_once.py': '47bc44a3f3e6327b984e6b4f10ae5fae15e95f065703e1dc6fecfb9cf06512c0',
    'logical_terminal_checks.py': '262704c5fe73aafa5ab014e4687fe51e20e940f218c448ae6ea22e1e8e6611f6',
}


def read(path):
    return json.loads(path.read_bytes())


def require(value, message):
    if not value:
        raise ValueError(message)


def select_remaining_run(plan, manifest, continuation, run_id):
    require(isinstance(run_id, str) and re.fullmatch(r'[A-Za-z0-9_-]+', run_id), 'Unsafe run identity')
    queue = plan['queue']
    ids = [row['run_id'] for row in queue]
    require(len(ids) == len(set(ids)) == 32 and ids[:3] == EXCLUDED, 'Original32 order or scope changed')
    require(manifest['tracks'] == 29 and manifest['total_original_tracks'] == 32, 'Not the approved remaining29')
    require(continuation['excluded_run_ids'] == EXCLUDED, 'The three immutable endpoints must stay excluded')
    require(continuation['remaining_tracks'] == 29 and continuation['remaining_run_ids'] == ids[3:],
            'Remaining29 order differs from the full original32')
    zero = dict(actor=0, judge=0, evidence=0)
    require(continuation['initial_transport_counts'] == zero and
            manifest['initial_transport_counts_for_all_remaining_tracks'] == zero,
            'Fresh-zero original budgets required')
    require(continuation['unchanged_full32_plan_sha256'] == PLAN_SHA and
            manifest['files']['plan.json'] == PLAN_SHA, 'Original plan identity changed')
    require(run_id in ids[3:], 'A completed or foreign trajectory cannot be collected as a new endpoint')
    planned = next(row for row in queue[3:] if row['run_id'] == run_id)
    require(planned['arm'] == 'joint' and type(planned['observer_enabled']) is bool, 'Original arm changed')
    return copy.deepcopy(planned)


def source_components():
    seal = read(SOURCE_ROOT / 'seal.json')
    for name, expected in SOURCE_HASHES.items():
        require(seal[name] == sha(SOURCE_ROOT / name) == expected, 'Sealed original collector changed: ' + name)
    spec = importlib.util.spec_from_file_location('remaining29_sealed_original_collector',
                                                SOURCE_ROOT / 'collect_logical_terminal_once.py')
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    require(original.HERE == HERE and original.OUTPUT == OUTPUT and original.PACKAGE == PACKAGE,
            'Original checker resolved a different runtime')
    needle = "package=r.parent/'runtime-preparation'/r.name"
    require(original.SERVICE_CODE.count(needle) == 1, 'Expected source-bound package lookup missing')
    service_code = original.SERVICE_CODE.replace(needle, 'package=Path(PACKAGE_ROOT)', 1)
    helper = (SOURCE_ROOT / 'logical_terminal_checks.py').read_text(encoding='utf8')
    for name, code in [('GUI', original.GUI_CODE), ('service', service_code), ('helper', helper)]:
        compile(code, '<remaining29-read-only-' + name + '>', 'exec')
    return original, service_code, helper


def admission(run_id):
    manifest = admitted()
    require(sha(PACKAGE / 'manifest.json') == EXPECTED_MANIFEST, 'Approved runtime identity changed')
    plan, continuation = read(PACKAGE / 'plan.json'), read(PACKAGE / 'continuation.json')
    planned = select_remaining_run(plan, manifest, continuation, run_id)
    require(sha(PACKAGE / 'plan.json') == PLAN_SHA, 'Full32 plan bytes changed')
    for row in continuation['terminal_copies']:
        require(row['run_id'] in EXCLUDED and sha(PACKAGE / row['copy']) == row['sha256'],
                'An immutable predecessor endpoint changed')
    excluded_path = PACKAGE / 'completed-request-exclusions.json'
    require(sha(excluded_path) == continuation['completed_request_exclusions_sha256'],
            'Original request exclusions changed')
    request_ids = read(excluded_path)['unique_request_ids']
    require(len(request_ids) == len(set(request_ids)) == 362, 'Original362 requests must remain excluded')
    carry = read(PACKAGE / 'carryover/state.json')
    require(carry['original_track'] in EXCLUDED and planned['run_id'] != carry['original_track'],
            'A carried/completed endpoint cannot acquire a fresh budget')
    carry['disallowed_prior_request_ids'] = sorted(set(carry['disallowed_prior_request_ids']) | set(request_ids))
    original, service_code, helper = source_components()
    return planned, carry, original, service_code, helper


def main(run_id, prior_collection=None):
    planned, carry, original, service_code, helper = admission(run_id)
    pointer = HERE / ('logical-terminal-' + run_id + '-collected.json')
    require(not pointer.exists(), 'An already collected endpoint is immutable; inspect its existing pointer')
    prior = None
    if prior_collection is not None:
        require(prior_collection.parent == HERE and (prior_collection / 'collection-failure.json').is_file(),
                'Only a preserved observer failure may be linked as a technical collection retry')
        prior = dict(root=str(prior_collection), seal_sha256=verify_seal(prior_collection))
    reviewed, authorities = original.verified_reviews()
    target = HERE / ('remaining29-logical-terminal-collection-' + str(time.time_ns()))
    target.mkdir()
    (target / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    for name in SOURCE_HASHES:
        (target / ('original-' + name)).write_bytes((SOURCE_ROOT / name).read_bytes())
    save(target / 'intent.json', dict(time=time.time(), run_id=run_id, expected_manifest=EXPECTED_MANIFEST,
        original_full32_plan_sha256=PLAN_SHA, original_terminal_checks_source_SHA=SOURCE_HASHES,
        source_reviews=authorities, three_original_endpoints_excluded=True,
        original362_request_ids_excluded=True, explicit_service_package=REMOTE_PACKAGE,
        fresh_zero_per_remaining_run=True, prior_failed_observation=prior,
        no_model_GUI_capture_action_scorer_or_launch=True))
    prefix = ('RUN=' + repr(run_id) + '\nEXPECTED=' + repr(EXPECTED_MANIFEST)
              + '\nPLANNED=' + repr(planned) + '\nCARRYOVER=' + repr(carry)
              + '\nHELPER=' + repr(helper) + '\n')
    try:
        output, operation = remote('4090', 'ROOT=' + repr(GUIROOT) + '\nREVIEWED=' + repr(sorted(reviewed))
            + '\n' + prefix + original.GUI_CODE, 'remaining29-source-reviewed-logical-terminal-' + run_id, timeout=55)
        gui = json.loads(output)
        save(target / 'GUI-preservation.json', dict(gui, operation=str(operation)))
        if not gui['ready']:
            save(target / 'receipt.json', dict(time=time.time(), ready=False, reason=gui['reason'],
                observation_only_not_trajectory_terminal_or_retry=True, new_model_GUI_scorer_calls=0))
            save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
            print(json.dumps(dict(collection=str(target), ready=False, reason=gui['reason'],
                candidate_event_hashes=gui.get('candidate_event_hashes'), seal_sha256=sha(target / 'seal.json'))))
            return
        terminal = gui['terminal']
        counters = (dict(actor=terminal['actor_calls'], judge=terminal['verifier_calls'], evidence=terminal['auxiliary_calls'])
                    if gui['terminal_name'] in ['complete.json', 'technical-failure.json', 'paused.json'] else None)
        code = ('ROOT=' + repr(OUTPUT) + '\nPACKAGE_ROOT=' + repr(REMOTE_PACKAGE)
                + '\nGUI_END_BODY=' + repr(gui['run_end']['body']) + '\nCOUNTERS=' + repr(counters)
                + '\n' + prefix + service_code)
        output, operation = remote('3090', code, 'remaining29-terminal-original-request-SHAs-' + run_id, timeout=55)
        service = json.loads(output)
        save(target / 'service-preservation.json', dict(service, operation=str(operation)))
        exports = target / 'selected-originals'
        exports.mkdir()
        for name, encoded in gui['exported_originals'].items():
            require(Path(name).name == name, 'Unsafe exported original filename')
            (exports / name).write_bytes(base64.b64decode(encoded, validate=True))
            require(sha(exports / name) == gui['original_file_SHA256'][name], 'Exported original SHA mismatch')
        save(target / 'receipt.json', dict(time=time.time(), ready=True, run_id=run_id,
            GUI_original_terminal_sha256=gui['terminal_sha256'],
            GUI_original_files_full_SHA_verified=len(gui['original_file_SHA256']),
            service_original_requests_full_SHA_verified=len(service['selected_requests']),
            original_GUI_run_end_and_service_ack_and_budget_counters_bound=True,
            original_remaining29_zero_initial_counts_bound=service['initial_carried_counts'] == dict(actor=0, judge=0, evidence=0),
            original_source_reviews_sealed_before_terminal_score_join=True,
            three_completed_endpoints_and362_prior_requests_excluded=True,
            all_large_originals_retained_in_place=True, full_queue_not_stopped_or_modified=True,
            semantic_labels_or_efficacy_not_inferred_from_endpoint=True, new_model_GUI_scorer_paid_calls=0))
        save(target / 'seal.json', {p.relative_to(target).as_posix(): sha(p) for p in target.rglob('*') if p.is_file()})
        result = dict(collection=str(target), receipt_sha256=sha(target / 'receipt.json'),
                      seal_sha256=sha(target / 'seal.json'), run_id=run_id)
        save(pointer, result)
        print(json.dumps(result))
    except BaseException as error:
        save(target / 'collection-failure.json', dict(time=time.time(), error_type=type(error).__name__, error=str(error),
            observer_failure_not_model_or_GUI_terminal=True, original_files_preserved=True, new_model_GUI_scorer_calls=0))
        save(target / 'seal.json', {p.relative_to(target).as_posix(): sha(p) for p in target.rglob('*') if p.is_file()})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--prior-collection', type=Path)
    args = parser.parse_args()
    main(args.run_id, args.prior_collection.resolve() if args.prior_collection else None)
