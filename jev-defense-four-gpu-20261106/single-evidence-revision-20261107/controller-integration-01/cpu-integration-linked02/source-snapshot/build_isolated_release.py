"""Build one CPU-only source release; never launch a model, service or GUI."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
SOURCE = PROJECT / 'policy-preparation/image-observer-policy/gui-migration-three-linked02/release'
REVISION = HERE.parent
DEST = HERE / 'release'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pure_closure():
    """Resolve source-local imports only; no transport/launcher import is permitted."""
    found, pending = set(), ['defense/core.py', 'defense/__init__.py']
    while pending:
        relative = pending.pop()
        if relative in found:
            continue
        found.add(relative)
        path = SOURCE / relative
        tree = ast.parse(path.read_text(encoding='utf8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    assert node.level == 1 and node.module
                    root = Path(relative).parent
                    possible = root / (node.module.replace('.', '/') + '.py')
                elif node.module:
                    possible = Path(node.module.replace('.', '/') + '.py')
                else:
                    continue
                if (SOURCE / possible).is_file():
                    pending.append(possible.as_posix())
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    possible = Path(alias.name.replace('.', '/') + '.py')
                    if (SOURCE / possible).is_file():
                        pending.append(possible.as_posix())
    banned = ('run_', 'launch', 'remote', 'transport', 'backend', 'observer', 'auxiliary')
    assert not any(any(word in Path(item).name for word in banned) for item in found), sorted(found)
    return sorted(found)


def main():
    DEST.mkdir(exist_ok=False)
    rows = []
    for relative in pure_closure():
        source, target = SOURCE / relative, DEST / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        rows.append({'relative_path': relative, 'source': str(source), 'source_sha256': sha(source)})
    for source in [REVISION / 'candidate-origin/claim_origin.py',
                   REVISION / 'history-consistency/history_utterance_ledger.py',
                   REVISION / 'history-consistency/compact_history_utterance_ledger.py']:
        target = DEST / source.name
        shutil.copyfile(source, target)
        rows.append({'relative_path': source.name, 'source': str(source), 'source_sha256': sha(source)})

    core_path = DEST / 'defense/core.py'
    core = core_path.read_text(encoding='utf8')
    imports = ('from claim_origin import EXACT_CLAIM_INSTRUCTIONS,check_claim_origins\n'
               'from compact_history_utterance_ledger import prepare_compact_main_judge_system\n')
    anchor = "DEFENSE_VERSION='evidence-v4.0.9-dev-appearance-absence-source-20261029'"
    assert core.count(anchor) == 1
    core = core.replace(anchor, imports + "\nDEFENSE_VERSION='evidence-v4.0.10-dev-candidate-origin-history-index-20261107'", 1)
    anchor = "        if phase in {'verify','history_report','completion','completion_relation'}:system+='\\n'+REPAIR_SCOPE\n"
    assert core.count(anchor) == 1
    core = core.replace(anchor, anchor + '''        # Additional DEVELOPMENT conditions, constructed before the original retry loop.
        # The exact system journaled below is the system passed to the backend callback.
        if phase=='verify':system+='\\n'+EXACT_CLAIM_INSTRUCTIONS
        if phase in {'verify','history_report'}:
            prepared=prepare_compact_main_judge_system(system,view,phase)
            self.log.append('history_utterance_ledger_prepared',{
                'phase':phase,'model_projection':'complete_compact_source_pointers',
                'original_system_utf8_sha256':digest(system.encode('utf8')),
                'augmented_system_utf8_sha256':digest(prepared.system.encode('utf8')),
                'full_ledger_sha256':prepared.full_ledger_sha256,
                'compact_model_index_sha256':prepared.compact_index_sha256,
                'added_utf8_bytes':prepared.added_utf8_bytes,
                'ledger':prepared.full_audit_ledger,
                'compact_model_index':prepared.compact_model_index,
                'source_metadata_not_a_verdict':True,
                'full_original_public_history_and_candidate_unchanged':True})
            system=prepared.system
''', 1)
    anchor = '                checked=validate_verdict(value,view,candidate,proposal)\n'
    assert core.count(anchor) == 1
    core = core.replace(anchor, anchor + '''                if phase=='verify':
                    origin=check_claim_origins(checked,candidate)
                    self.log.append('candidate_claim_origin_check',origin)
                    if origin['reject']:
                        raise ValidationError('Exact candidate extraction provenance invalid: '+json.dumps(origin['errors']))
''', 1)
    ast.parse(core)
    with core_path.open('w', encoding='utf8', newline='\n') as stream:
        stream.write(core)
    for row in rows:
        row['release_sha256'] = sha(DEST / row['relative_path'])
        row['copied_byte_identical'] = row['source_sha256'] == row['release_sha256']
    receipt = {'status': 'source_staged_cpu_only', 'parent_release': str(SOURCE),
        'release': str(DEST), 'files': rows,
        'modified_parent_files': [row['relative_path'] for row in rows if not row['copied_byte_identical']],
        'new_condition': 'verify exact candidate spans plus primary verify/history_report compact actor source index',
        'launch_ready': False, 'model_calls': 0, 'gui_actions': 0,
        'old_launch_entrypoints_copied': False,
        'unchanged_original_validator_not_replaced': True,
        'no_callback_system_rewriting': True}
    (HERE / 'source-build-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps({'source_files': len(rows), 'modified': receipt['modified_parent_files'],
        'release': str(DEST), 'launch_ready': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
