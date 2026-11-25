"""CPU-only new-request audit with all original raw-head and native-input checks.

Old raw checks keep their original timestamps; their sealed report and remote
request-seal identities are rechecked. This does not claim a fresh full rehash.
"""
import argparse
import ast
import json
import time
from pathlib import Path

from control import HERE, R3090, remote, save, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', type=Path, required=True)
    args = parser.parse_args()
    base = args.base.resolve()
    if base.parent != HERE:
        assert base.name == 'cumulative-report.json' and base.parent.parent == HERE
        assert base.parent.name.startswith('Flash-CPU-increment-')
        prior_seal = json.loads((base.parent / 'seal.json').read_bytes())
        assert all(sha(base.parent / name) == expected for name, expected in prior_seal.items())
    previous = json.loads(base.read_bytes())['result']
    old = previous['requests']
    assert len(old) == previous['verified_complete_Flash_replies']
    names = {v['request_id']: v['seal_sha256'] for v in old}
    assert len(names) == len(old)
    original = HERE / 'audit_flash_live.py'
    constants = [n.value for n in ast.walk(ast.parse(original.read_text('utf8')))
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    sources = [v for v in constants if v.startswith('\nimport hashlib,json,os,time')]
    assert len(sources) == 1
    source = sources[0].replace('ROOT', repr(R3090))
    loop = "for d in sorted((root/'service/requests').iterdir()):"
    assert source.count(loop) == 1
    source = source.replace(loop, "for d in [root/'service/requests'/name for name in NEW_NAMES]:")
    source = source.replace('assert rows and not torch.cuda.is_initialized()',
                            'assert not torch.cuda.is_initialized()')
    source = source.replace("target=p/('Flash-runtime-CPU-audit-'", "target=p/('Flash-increment-CPU-audit-'")
    binding = ('OLD=' + repr(names) + '\nPACKAGE=' + repr(R3090) + '\n' + '''
import hashlib,json,time
from pathlib import Path
root=Path(PACKAGE)/'flash/service/requests'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name,h in OLD.items():assert sha(root/name/'seal.json')==h
complete=[d.name for d in sorted(root.iterdir())if(d/'seal.json').exists()and not(d/'failure.json').exists()]
assert set(OLD).issubset(set(complete))
print(json.dumps({'time':time.time(),'new_names':[n for n in complete if n not in OLD],
 'previous_request_seal_identities_verified':len(OLD),'old_raw_tensors_rehashed':False}))
''')
    raw, op = remote('3090', binding, 'Flash-increment-previous-seal-identities')
    snapshot = json.loads(raw)
    dest = HERE / ('Flash-CPU-increment-' + str(time.time_ns()))
    dest.mkdir()
    (dest / 'inspector-source.py').write_bytes(Path(__file__).read_bytes())
    (dest / 'original-inspector.py').write_bytes(original.read_bytes())
    (dest / 'remote-source-template.py').write_text(source, encoding='utf8')
    save(dest / 'binding.json', {'base': str(base), 'base_sha256': sha(base),
         'previous_raw_check_time': previous['time'],
         'old_raw_tensors_rehashed': False, 'original_inspector_sha256': sha(original),
         'snapshot_operation': str(op), 'snapshot': snapshot,
         'new_model_GUI_calls': 0, 'GPU_allocations': 0,
         'final_full_postexit_audit_still_required': True})
    additions = []
    # Small batches bound SSH latency without changing a single raw-input check.
    for index in range(0, len(snapshot['new_names']), 8):
        selected = snapshot['new_names'][index:index + 8]
        raw, op = remote('3090', 'NEW_NAMES=' + repr(selected) + '\n' + source,
                         'Flash-new-only-full-native-CPU-' + str(index // 8), timeout=55)
        result = json.loads(raw)
        assert len(result['requests']) == len(selected)
        save(dest / ('batch-%03d.json' % (index // 8)), {'result': result, 'operation': str(op)})
        additions.extend(result['requests'])
    result = {'time': time.time(), 'requests': old + additions,
              'verified_complete_Flash_replies': len(old) + len(additions),
              'prior_raw_check_time': previous['time'],
              'new_raw_inputs_and_heads_verified': len(additions),
              'old_raw_tensors_rehashed': False,
              'new_inference_by_audit': 0, 'GPU_allocations_by_audit': 0}
    save(dest / 'cumulative-report.json', {'result': result})
    save(dest / 'seal.json', {p.name: sha(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'audit': str(dest), 'new_raw_inputs_and_heads_verified': len(additions),
                      'cumulative_replies': len(old) + len(additions), 'GPU_allocations': 0}))


if __name__ == '__main__':
    main()
