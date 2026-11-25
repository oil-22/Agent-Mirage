"""Seal the independent audit and report after verified worker exit."""

import argparse
from pathlib import Path

from live_common import load, save, sha


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('audit', type=Path)
    cli.add_argument('report', type=Path)
    cli.add_argument('figure', type=Path)
    cli.add_argument('postexit', type=Path)
    cli.add_argument('--out', type=Path, required=True)
    args = cli.parse_args()
    a, exit_state = load(args.audit), load(args.postexit)
    attempt = Path(a['attempt'])
    manifest = load(attempt / 'manifest.json')
    assert attempt.name == exit_state['attempt'] == manifest['name']
    assert a['status'] == exit_state['driver_terminal'] == 'completed_panel'
    assert a['audited_terminals'] == exit_state['completed'] == 96
    assert sha(attempt / 'local-seal.json') == a['input_seal_sha256']
    assert all(r['matches'] is False for r in exit_state['lease_processes'])
    assert len(a['resource_release']['locks']) == 12
    base = Path(__file__).resolve().parent
    preflight = attempt.parent / manifest['capture_preflight'] / 'local-seal.json'
    assert sha(preflight) == manifest['preflight_seal_sha256']
    artifacts = [args.audit, args.report, args.figure, args.postexit, preflight,
                 attempt / 'local-seal.json', attempt / 'manifest.json', attempt / 'remote-seal.json',
                 base / 'audit_panel.py', base / 'scale_report.py', base / 'render_evidence.py',
                 base / '原图复核记录.md', base / 'flash-native-audit-source/source-seal.json',
                 base / 'audit-attempts/审计工具修正.md', base / 'audit-attempts/audit-before-chrome-argv-fix.py']
    save(args.out, {
        'state': 'complete',
        'attempt': attempt.name,
        'model_calls': a['model_calls'],
        'terminal_count': 96,
        'independently_verified_capture_count': a['bound_signed_captures'],
        'four_injection_effective_recovery': {n: {
            'closed_loop': a['by_arm'][n]['effective_recovery'], 'planned': a['by_arm'][n]['planned'],
            'confirmed_first_fault': a['by_arm'][n]['first_fault_seen']}
            for n in ('defense', 'missing', 'white', 'buttons')},
        'files_sha256': {p.resolve().relative_to(base).as_posix(): sha(p) for p in artifacts},
    })
