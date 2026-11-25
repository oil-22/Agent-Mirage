"""Freeze a NEW four-trajectory study; never execute an old terminal or queue."""
import ast
import hashlib
import json
import secrets
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'flash-resource-continuation-20261115-linked12' / 'package'
PACKAGE = HERE / 'package'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)


def ast_member(source, class_name, name):
    tree = ast.parse(source)
    owner = next(v for v in tree.body if isinstance(v, ast.ClassDef) and v.name == class_name)
    return next(v for v in owner.body if isinstance(v, ast.FunctionDef) and v.name == name)


def main():
    assert not PACKAGE.exists(), 'Preparation already exists: do not overwrite it'
    original = json.loads((OLD / 'manifest.json').read_bytes())
    for name, digest in original['files'].items():
        assert sha(OLD / name) == digest, name
    shutil.copytree(OLD, PACKAGE)
    for name in ['manifest.json', 'plan.json', 'private.token', 'continuation_guard.py']:
        (PACKAGE / name).unlink()
    shutil.copyfile(HERE / 'injection.py', PACKAGE / 'injection.py')
    shutil.copyfile(HERE / 'new_study_guard.py', PACKAGE / 'continuation_guard.py')
    for name in ['user-authorization.json', 'prior-3090.json', 'prior-4090.json']:
        destination = 'user-current-authorization.json' if name == 'user-authorization.json' else name
        shutil.copyfile(HERE / name, PACKAGE / destination)
    with (PACKAGE / 'private.token').open('x', encoding='utf8') as f:
        f.write(secrets.token_hex(32))
    source = (OLD / 'gui_experiment.py').read_text(encoding='utf8')
    node = ast_member(source, 'LiveAdapter', 'initial_frame')
    before = ast.get_source_segment(source, node)
    after = '''def initial_frame(self):
        from injection import eligible, whiteout
        raw=self.png(self.obs);delivered=raw;injected=False
        trigger=eligible(self.fired,self.last_image,raw,self.previous)
        if self.item['condition']=='whiteout_once' and trigger:
            delivered=whiteout(raw);self.fired=True;self.trigger_step=self.step;injected=True
        (self.root/f'{self.step:03}-actually-captured.png').write_bytes(raw)
        (self.root/f'{self.step:03}-initial-delivered.png').write_bytes(delivered)
        self.log.emit('PRIVATE_delivery_ledger',{'step':self.step,'condition':self.item['condition'],
            'injected':injected,'captured_sha256':digest(raw),'delivered_sha256':digest(delivered),
            'injection_before_gate':True,'transformation':'whole-viewport-whiteout'if injected else None,
            'not_model_input':True})
        return Frame.captured(delivered)'''
    assert source.count(before) == 1
    changed = source.replace(before, after)
    ast.parse(changed)
    (PACKAGE / 'gui_experiment.py').write_text(changed, encoding='utf8')
    # Native history/actor/parser/executor/recapture/scoring paths remain exact ASTs.
    for name in ['capture', 'actor', 'call_main', 'parse', 'execute', 'commit']:
        assert ast.dump(ast_member(source, 'LiveAdapter', name), include_attributes=False) == ast.dump(
            ast_member(changed, 'LiveAdapter', name), include_attributes=False), name
    plan = json.loads((OLD / 'plan.json').read_bytes())
    plan.update({
        'version': 'injection-before-single-Flash-whiteout-development-v1',
        'queue': [{'run_id': f'inject15-T{task:03}-whiteout_once-{arm}', 'task_id': task,
                   'condition': 'whiteout_once', 'gate_enabled': arm == 'gate'}
                  for task in [17, 114] for arm in ['gate', 'baseline']],
        'expected_trajectories': 4, 'matched_pairs': 2, 'conditions': ['whiteout_once'],
        'injection': 'Once at first changed capture after click/type/press/back/tab: whole original-sized RGB viewport replaced by white BEFORE gate or baseline; same eligibility in both arms; no repeated injection on recapture.',
        'trigger_information_to_models': False,
        'main_system_or_auxiliary_feedback_changed': False,
        'new_primary_preread': False, 'old_terminal_retries': False,
        'interpretation': 'Known-task nonblind mechanism development. A model NO plus fresh YES is an intercepted visual injection; prevention of Mirage additionally requires a source-reviewed definite baseline error. No scalar or significant efficacy inference.',
        'excluded_prior_terminals': [r['run_id'] for r in json.loads((OLD / 'plan.json').read_bytes())['queue']],
        'technical_failure': 'Preserve new request/reply/log and stop this new queue; no automatic retry or terminal replay.',
        'current_user_authorization_sha256': sha(PACKAGE / 'user-current-authorization.json')})
    for key in ['unmatched_additional_trajectory', 'parent_failed_partial_preserved', 'parent_16_terminal_exclusion']:
        plan.pop(key, None)
    save(PACKAGE / 'plan.json', plan)
    files = {str(p.relative_to(PACKAGE)).replace('\\', '/'): sha(p)
             for p in PACKAGE.rglob('*') if p.is_file() and p.name != 'private.token'}
    manifest = {**original,
        'version': plan['version'], 'study': plan['version'], 'created': time.time(),
        'files': files, 'auth_token_sha256': sha(PACKAGE / 'private.token'),
        'package3090': '/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + HERE.name,
        'package4090': '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name,
        'output3090': '/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name,
        'trajectories': 4, 'remaining_queue': plan['queue'], 'new_GUI_queue': True,
        'current_user_authorization_sha256': sha(PACKAGE / 'user-current-authorization.json'),
        'source_prior_manifest_sha256': sha(OLD / 'manifest.json'),
        'old_completed_queues_are_provenance_only': True,
        'new_capacity_calls': 0, 'formal_Mirage_efficacy_proven': False}
    for key in ['parent_16_terminal_exclusion', 'parent_failed_partial_preserved']:
        manifest.pop(key, None)
    save(PACKAGE / 'manifest.json', manifest)
    for name, digest in files.items():
        assert sha(PACKAGE / name) == digest
    for name in ['primary_server.py', 'historical_memory.py', 'expanded_guard.py',
                 'launch_group.py', 'gui_outer.py', 'actor-template.json',
                 'flash/gate-contract.json', 'flash/gate_core.py', 'flash/flash_runtime.py',
                 'flash/flash_service.py', 'release/defense/qwen_backend.py']:
        assert sha(PACKAGE / name) == sha(OLD / name), name
    save(HERE / 'preparation.json', {'time': time.time(), 'manifest_sha256': sha(PACKAGE / 'manifest.json'),
        'source_files': len(files), 'trajectories': 4, 'new_model_GUI_calls': 0,
        'sole_changed_GUI_method': 'LiveAdapter.initial_frame', 'independent_Flash_contract_unchanged': True,
        'source_native_memory_and_main_generation_unchanged': True})
    print(json.dumps({'files': len(files), 'manifest_sha256': sha(PACKAGE / 'manifest.json'), 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
