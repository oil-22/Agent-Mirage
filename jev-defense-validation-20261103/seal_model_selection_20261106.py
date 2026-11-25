"""Seal public-evidence selection only. No network, models, GPU or service actions."""
import hashlib
import json
from pathlib import Path
import time

BASE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    roots = [
        'model-research-mirror/1793970517432356400',
        'model-research-targeted/1793970598557122600',
        'model-research-board-vision/1793970797241034400',
        'model-research-finalists/1793970930004290200',
    ]
    audits = []
    for relative in roots:
        root = (BASE / relative).resolve()
        entries = json.loads((root / 'seal.json').read_bytes())
        for name, expected in entries.items():
            path = (root / name).resolve()
            assert path.is_relative_to(root), 'Unexpected path in metadata seal'
            assert sha(path) == expected, (relative, name)
        audits.append({'root': relative, 'verified_files': len(entries),
                       'seal_sha256': sha(root / 'seal.json')})
    vision = json.loads((BASE / roots[2] / 'vision.json').read_bytes())
    engines = ['pplx-decider-flash-v1.2', 'neohorse-jev-4b',
               'jev-style-2b-v4', 'wemm-jev-27b', 'jev-27b-vl']
    comparison = []
    for engine in engines:
        row = next(r for r in vision['entrants'] if r['engine'] == engine)
        comparison.append({k: row.get(k) for k in
                           ['engine', 'name', 'url', 'rank_full', 'full', 'pub',
                            'priv', 'params', 'caveat']})
        comparison[-1]['Mind2Web'] = row['bench']['Mind2Web']
    report = BASE / '单Jev辅助模型选型-20261106.md'
    root = BASE / 'model-selection' / str(time.time_ns())
    root.mkdir(parents=True, exist_ok=False)
    (root / report.name).write_bytes(report.read_bytes())
    receipt = {
        'scope': 'Public evidence model selection; not local efficacy or deployment',
        'status': 'single_auxiliary_candidate_selected_not_deployed',
        'selected_repository': 'perplexity-ai/pplx-decider-flash-v1.2',
        'revision': '9ff7cf9838e59df461c276b7699d56b244d2af58',
        'planned_auxiliary_model_count': 1,
        'native_contract': 'pplx_decider images + noncausal full attention + marker readout',
        'weight_bytes_from_manifest': 9078531072,
        'readout_bytes_from_tree': 1305712,
        'single_3090_fit_verified': False,
        'actual_weight_access_and_identity_verified': False,
        'board_edition': vision['edition'],
        'board_generated_utc': vision['generated_utc'],
        'board_vision_sha256': sha(BASE / roots[2] / 'vision.json'),
        'board_metric': 'Chance-corrected skill; not accuracy or Mirage reduction',
        'board_exact_weight_revision_bound': False,
        'board_comparison': comparison,
        'verified_research_seals': audits,
        'research_report_sha256': sha(report),
        'new_weight_downloads': 0, 'new_model_calls': 0, 'GUI_actions': 0,
        'new_GPU_allocations': 0, 'service_process_changes': 0,
        'existing_two_service_runtime_replaced': False,
        'deployment_applied': False, 'full_GUI_ready': False,
        'new_background_scheduler': False,
        'provisional_neo_only_cpu_option': {
            'path': 'single-model-preparation-20261106',
            'tests_passed': 13, 'not_adapter_for_selected_new_model': True,
            'parent_release_python_files_unchanged': 77,
        },
    }
    (root / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf8')
    (root / 'seal.json').write_text(json.dumps({p.name: sha(p) for p in root.iterdir()
                                               if p.is_file()}, ensure_ascii=False, indent=2), encoding='utf8')
    pointer = {'status': receipt['status'], 'selected_repository': receipt['selected_repository'],
               'revision': receipt['revision'], 'planned_auxiliary_model_count': 1,
               'receipt': str((root / 'receipt.json').relative_to(BASE)).replace('\\', '/'),
               'receipt_sha256': sha(root / 'receipt.json'),
               'seal_sha256': sha(root / 'seal.json'), 'deployment_applied': False}
    (BASE / 'model-selection-current.json').write_text(json.dumps(pointer, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'root': str(root), 'verified_research_files': sum(a['verified_files'] for a in audits),
                      'receipt_sha256': pointer['receipt_sha256'], 'model_calls': 0}, ensure_ascii=False))


if __name__ == '__main__':
    main()
