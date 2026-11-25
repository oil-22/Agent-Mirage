"""Verify live ownership/chains, prior seals and every newly sealed binary.

Previously hashed binaries retain their exact immutable evidence authority.
This is not a claim that old binary files are fully rehashed in this poll.
Finalization must still perform a complete original-file SHA verification.
No model, GUI, source, validator or experiment condition is changed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'full-history-gui-development-20261109-23'
sys.path.insert(0, str(OLD))
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def verified_evidence(path):
    assert path.parent == HERE and path.name.startswith('actual-evidence-')
    seal = read(path / 'seal.json')
    for name, expected in seal.items():
        assert sha(path / name) == expected, str(path / name)
    return read(path / '3090.json')


def main(baseline):
    previous = verified_evidence(baseline)
    cache = {str(baseline): previous}
    prior = {}
    for row in previous['sealed_requests']:
        authority = row.get('full_SHA_verification_authority', {
            'evidence': str(baseline), 'request': row['request'],
            'request_seal_sha256': row['seal_sha256'],
        })
        origin_path = Path(authority['evidence'])
        if str(origin_path) not in cache:
            cache[str(origin_path)] = verified_evidence(origin_path)
        origin = next(item for item in cache[str(origin_path)]['sealed_requests'] if item['request'] == row['request'])
        assert origin['files_verified'] > 0
        assert authority['request'] == row['request']
        assert authority['request_seal_sha256'] == origin['seal_sha256'] == row['seal_sha256']
        prior[row['request']] = {'seal_sha256': row['seal_sha256'],
                                'full_SHA_verification_authority': authority}
    assert list(prior) == [str(i).zfill(4) for i in range(1, len(prior) + 1)]
    source = (OLD / 'inspect_actual_evidence.py').read_text(encoding='utf8')
    source = source.replace('from remote_control import remote, save, sha, ROOT3090, ROOT4090',
        "from remote_control import remote, save, sha\nROOT3090='/home/researcher/jev-defense-four-gpu-20261106/" + HERE.name + "'\nROOT4090='/data/researcher/jev-defense-four-gpu-20261106/" + HERE.name + "'")
    assert source.count('timeout=55') == 2
    source = source.replace('timeout=55', 'timeout=120')
    before = "r=Path(ROOT);package=r.parent/'runtime-preparation'/r.name"
    assert source.count(before) == 1
    source = source.replace(before, 'PRIOR=' + repr(prior) + '\n' + before)
    before = 'for name,h in bindings.items():assert sha(p.parent/name)==h,str(p.parent/name)'
    assert source.count(before) == 1
    source = source.replace(before,
        "fresh=p.parent.name not in PRIOR\n"
        " if fresh:\n"
        "  for name,h in bindings.items():assert sha(p.parent/name)==h,str(p.parent/name)\n"
        " else:\n"
        "  assert sha(p)==PRIOR[p.parent.name]['seal_sha256']\n"
        "  for name in bindings:assert Path(name).name==name and (p.parent/name).is_file(),str(p.parent/name)")
    before = "'files_verified':len(bindings)"
    assert source.count(before) == 1
    source = source.replace(before,
        "'files_verified':len(bindings)if fresh else 0,"
        "'previously_full_SHA_verified_files':0 if fresh else len(bindings),"
        "'prior_seal_freshly_revalidated':not fresh,"
        "'full_SHA_verification_authority':({'evidence':LOCAL_EVIDENCE_PATH,'request':p.parent.name,'request_seal_sha256':sha(p)}if fresh else PRIOR[p.parent.name]['full_SHA_verification_authority'])")
    before = "output, operation = remote('3090', code, 'actual-service-locks-sealed-requests-no-probe', timeout=120)"
    assert source.count(before) == 1
    source = source.replace(before,
        "code = 'LOCAL_EVIDENCE_PATH=' + repr(str(target)) + '\\n' + code\n    " + before)
    before = 'primary = json.loads(output)'
    assert source.count(before) == 1
    policy = {
        'baseline': str(baseline), 'baseline_evidence_seal_sha256': sha(baseline / 'seal.json'),
        'already_verified_request_count': len(prior),
        'all_new_request_binary_SHA_checks_retained': True,
        'prior_request_seals_revalidated_and_full_SHA_authorities_preserved': True,
        'not_a_claim_old_binary_files_fully_rehashed_this_poll': True,
        'complete_original_file_SHA_audit_required_at_finalization': True,
        'live_UID_fullcmd_start_nine_locks_GPU_sources_and_event_chain_checks_retained': True,
        'new_model_GUI_scorer_calls': 0,
    }
    source = source.replace(before, before + "\n    primary['incremental_inspection_policy']=" + repr(policy))
    exec(compile(source, str(Path(__file__).resolve()), 'exec'), {'__name__': '__main__', '__file__': str(Path(__file__).resolve())})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    main(parser.parse_args().baseline.resolve())
