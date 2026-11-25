"""Preserve a finished original-tail31 track; never start or repeat a GUI run.

Compose the sealed original GUI/file/counter checks with the new explicit
service-package path and fresh-zero tail selection. Large originals stay put.
"""
import argparse
import base64
import copy
import importlib.util
import json
from pathlib import Path
import re
import time

from orchestrate import HERE, PACKAGE, OUTPUT, GUIROOT, REMOTE_PACKAGE, remote, save, sha


EXPECTED_MANIFEST = 'e64fc8e42a144cd1cc426942093a6edaf51204fba13918286c41e51f8d7b15ef'
EXPECTED_ORIGINAL_MANIFEST = 'c83af050ba64c4edb4d9a1aeff6ebc9f4195e04ef576dd1906791d690e07a5f1'
SOURCE_ROOT = HERE.parent / 'prefill-scheduled-full-history-gui-20261109-32' / 'logical-terminal-collection-1794251064196236500'
SOURCE_HASHES = {
    'collect_logical_terminal_once.py': '47bc44a3f3e6327b984e6b4f10ae5fae15e95f065703e1dc6fecfb9cf06512c0',
    'logical_terminal_checks.py': '262704c5fe73aafa5ab014e4687fe51e20e940f218c448ae6ea22e1e8e6611f6',
}


def read(path):
    return json.loads(Path(path).read_bytes())


def select_tail_run(plan, manifest, predecessor, run_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        raise ValueError('Unsafe or foreign run identity')
    if manifest['original32_manifest_sha256'] != EXPECTED_ORIGINAL_MANIFEST:
        raise ValueError('Original32 manifest identity changed')
    queue = plan['queue']
    ids = [row['run_id'] for row in queue]
    excluded = predecessor['excluded_run_ids']
    if len(queue) != 32 or len(set(ids)) != 32 or excluded != ids[:1]:
        raise ValueError('The original32 plan and exact excluded terminal must remain bound')
    if manifest['tracks'] != 31 or manifest['total_original_tracks'] != 32 or predecessor['only_unstarted_tracks'] != 31:
        raise ValueError('Not the original remaining31 scope')
    zero = dict(actor=0, judge=0, evidence=0)
    if manifest['initial_transport_counts_for_all_remaining_tracks'] != zero or predecessor['current_root_initial_counts'] != zero:
        raise ValueError('A new tail track must begin with all-zero counters')
    if run_id not in ids[1:]:
        raise ValueError('Only the original never-started tail31 may be collected here')
    return copy.deepcopy(next(row for row in queue[1:] if row['run_id'] == run_id))


def source_components():
    seal = read(SOURCE_ROOT / 'seal.json')
    for name, expected in SOURCE_HASHES.items():
        assert seal[name] == expected == sha(SOURCE_ROOT / name), name
    spec = importlib.util.spec_from_file_location('sealed_original_terminal_collector_composition', SOURCE_ROOT / 'collect_logical_terminal_once.py')
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    # Import resolves orchestrate from this new directory, not the excluded run.
    assert original.HERE == HERE and original.OUTPUT == OUTPUT and original.PACKAGE == PACKAGE
    needle = "package=r.parent/'runtime-preparation'/r.name"
    assert original.SERVICE_CODE.count(needle) == 1
    service_code = original.SERVICE_CODE.replace(needle, 'package=Path(PACKAGE_ROOT)', 1)
    helper = (SOURCE_ROOT / 'logical_terminal_checks.py').read_text(encoding='utf8')
    for name, code in [('GUI', original.GUI_CODE), ('service', service_code), ('helper', helper)]:
        compile(code, '<read-only-tail31-' + name + '>', 'exec')
    return original, service_code, helper


def admission(run_id):
    assert sha(PACKAGE / 'manifest.json') == EXPECTED_MANIFEST
    manifest = read(PACKAGE / 'manifest.json')
    for name, expected in manifest['files'].items():
        assert (PACKAGE / name).resolve().is_relative_to(PACKAGE.resolve())
        assert sha(PACKAGE / name) == expected, name
    assert sha(PACKAGE / 'plan.json') == manifest['files']['plan.json']
    predecessor = read(PACKAGE / 'predecessor.json')
    assert sha(PACKAGE / 'predecessor.json') == manifest['predecessor_sha256']
    assert predecessor['original_terminal_never_rewritten_or_rerun'] is True
    plan = read(PACKAGE / 'plan.json')
    planned = select_tail_run(plan, manifest, predecessor, run_id)
    carry = read(PACKAGE / 'carryover/state.json')
    assert carry['original_track'] in predecessor['excluded_run_ids']
    carry['disallowed_prior_request_ids'] = sorted(set(carry['disallowed_prior_request_ids']) |
        set(predecessor['disallowed_completed_model_request_ids']))
    original, service_code, helper = source_components()
    return planned, carry, original, service_code, helper


def main(run_id, prior_collection=None):
    planned, carry, original, service_code, helper = admission(run_id)
    pointer = HERE / ('logical-terminal-' + run_id + '-collected.json')
    assert not pointer.exists(), 'A completed collection is immutable; inspect its pointer'
    previous = None
    if prior_collection is not None:
        assert prior_collection.parent == HERE and (prior_collection / 'collection-failure.json').is_file()
        previous = dict(path=str(prior_collection), seal_sha256=sha(prior_collection / 'seal.json'))
        for name, expected in read(prior_collection / 'seal.json').items():
            assert (prior_collection / name).resolve().is_relative_to(prior_collection.resolve())
            assert sha(prior_collection / name) == expected
    reviewed, authorities = original.verified_reviews()
    target = HERE / ('tail-terminal-collection-' + str(time.time_ns()))
    target.mkdir()
    (target / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    for name in SOURCE_HASHES:
        (target / ('original-' + name)).write_bytes((SOURCE_ROOT / name).read_bytes())
    save(target / 'intent.json', dict(time=time.time(), run_id=run_id, expected_manifest=EXPECTED_MANIFEST,
        explicit_service_output=OUTPUT, explicit_package=REMOTE_PACKAGE, explicit_GUI_output=GUIROOT,
        original_collector_source_hashes=SOURCE_HASHES, source_reviews=authorities,
        original_first_terminal_excluded=True, fresh_zero_counters=True,
        linked_prior_failed_collection=previous, remaining_queue_modified=False,
        new_model_GUI_scorer_paid_calls=0))
    prefix = ('RUN=' + repr(run_id) + '\nEXPECTED=' + repr(EXPECTED_MANIFEST) + '\nPLANNED=' + repr(planned)
        + '\nCARRYOVER=' + repr(carry) + '\nHELPER=' + repr(helper) + '\n')
    try:
        output, operation = remote('4090', 'ROOT=' + repr(GUIROOT) + '\nREVIEWED=' + repr(sorted(reviewed))
            + '\n' + prefix + original.GUI_CODE, 'source-reviewed-tail31-logical-terminal-' + run_id, timeout=55)
        gui = json.loads(output)
        save(target / 'GUI-preservation.json', dict(gui, operation=str(operation)))
        if not gui['ready']:
            save(target / 'receipt.json', dict(time=time.time(), ready=False, reason=gui['reason'],
                observation_only_not_experiment_terminal_or_retry=True, new_model_GUI_scorer_calls=0))
            save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
            print(json.dumps(dict(collection=str(target), ready=False, reason=gui['reason'],
                candidate_event_hashes=gui.get('candidate_event_hashes'), seal_sha256=sha(target / 'seal.json'))))
            return
        terminal = gui['terminal']
        counters = (dict(actor=terminal['actor_calls'], judge=terminal['verifier_calls'], evidence=terminal['auxiliary_calls'])
            if gui['terminal_name'] in ['complete.json', 'technical-failure.json', 'paused.json'] else None)
        code = ('ROOT=' + repr(OUTPUT) + '\nPACKAGE_ROOT=' + repr(REMOTE_PACKAGE)
            + '\nGUI_END_BODY=' + repr(gui['run_end']['body']) + '\nCOUNTERS=' + repr(counters) + '\n' + prefix + service_code)
        output, operation = remote('3090', code, 'tail31-original-terminal-full-request-SHAs-' + run_id, timeout=180)
        service = json.loads(output)
        save(target / 'service-preservation.json', dict(service, operation=str(operation)))
        exports = target / 'selected-originals'
        exports.mkdir()
        for name, encoded in gui['exported_originals'].items():
            assert Path(name).name == name
            raw = base64.b64decode(encoded, validate=True)
            (exports / name).write_bytes(raw)
            assert sha(exports / name) == gui['original_file_SHA256'][name]
        save(target / 'receipt.json', dict(time=time.time(), ready=True, run_id=run_id,
            GUI_original_terminal_sha256=gui['terminal_sha256'],
            GUI_original_files_full_SHA_verified=len(gui['original_file_SHA256']),
            service_original_requests_full_SHA_verified=len(service['selected_requests']),
            original_budget_counters_and_actual_end_ack_bound=True,
            original_tail31_zero_initial_counts_bound=service['initial_carried_counts'] == dict(actor=0, judge=0, evidence=0),
            original_source_judgments_sealed_before_terminal_join=True,
            completed_first_track_excluded_and_prior_request_IDs_disallowed=True,
            all_large_originals_retained_in_place=True, remaining_queue_not_stopped_or_modified=True,
            semantic_correctness_trajectory_labels_or_efficacy_not_established=True,
            new_model_GUI_scorer_paid_calls=0))
        save(target / 'seal.json', {p.relative_to(target).as_posix(): sha(p) for p in target.rglob('*') if p.is_file()})
        record = dict(collection=str(target), receipt_sha256=sha(target / 'receipt.json'),
            seal_sha256=sha(target / 'seal.json'), run_id=run_id)
        save(pointer, record)
        print(json.dumps(record))
    except BaseException as error:
        save(target / 'collection-failure.json', dict(time=time.time(), error_type=type(error).__name__, error=str(error),
            collection_observation_failure_not_model_terminal=True, originals_preserved=True, new_model_GUI_scorer_calls=0))
        save(target / 'seal.json', {p.relative_to(target).as_posix(): sha(p) for p in target.rglob('*') if p.is_file()})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--prior-collection', type=Path)
    args = parser.parse_args()
    main(args.run_id, args.prior_collection.resolve() if args.prior_collection else None)
