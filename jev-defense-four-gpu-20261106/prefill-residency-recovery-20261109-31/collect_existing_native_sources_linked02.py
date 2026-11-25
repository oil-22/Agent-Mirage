"""Recover the successful read-only transport with byte-exact local writes."""
import hashlib
import json
from pathlib import Path
import shutil
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, v):
    with p.open('x', encoding='utf8') as stream:
        json.dump(v, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    operation = BASE / 'full-history-gui-development-20261109-23/operations/1794228343181169700-new31-read-native-forward-hook-source-no-load'
    assert json.loads((operation / 'receipt.json').read_bytes())['returncode'] == 0
    failure = HERE / ('local-newline-failure-preservation-' + str(time.time_ns()))
    failure.mkdir()
    shutil.copyfile(HERE / 'inspect_native_scheduling_sources.py', failure / 'source.py')
    failed_root = HERE / 'native-source-evidence-1794228343180899800'
    save(failure / 'failure.json', {'type': 'AssertionError',
         'cause': 'Windows text writer translated LF to CRLF before byte SHA comparison',
         'failed_local_files': {str(p.relative_to(failed_root)):sha(p) for p in failed_root.rglob('*') if p.is_file()},
         'successful_remote_operation': str(operation), 'successful_stdout_sha256': sha(operation / 'stdout.txt'),
         'no_model_call_or_native_source_mutation': True})
    save(failure / 'seal.json', {p.name:sha(p) for p in failure.iterdir() if p.is_file()})
    result = json.loads((operation / 'stdout.txt').read_bytes())
    target = HERE / ('native-source-evidence-linked02-' + str(time.time_ns()))
    target.mkdir()
    for key in ['native_source', 'accelerate_hooks']:
        item = result[key]
        path = target / (key + '.py')
        path.write_bytes(item.pop('text').encode('utf8'))
        assert sha(path) == item['sha256']
        item['local_source'] = str(path)
    save(target / 'receipt.json', dict(result, successful_remote_operation=str(operation),
                                      local_reporter_failure_preservation=str(failure), new_remote_calls=0))
    save(target / 'seal.json', {p.name:sha(p) for p in target.iterdir() if p.is_file()})
    save(HERE / 'native-source-current.json', {'root':str(target), 'receipt_sha256':sha(target / 'receipt.json'),
                                              'seal_sha256':sha(target / 'seal.json')})
    f = result['failed_request']
    print(json.dumps({'root':str(target), 'input_shape':f['prepared.json']['input_ids']['shape'],
         'images':f['prepared.json']['image_grid_thw']['shape'][0], 'memory':f['failed-memory.json'],
         'forwards':f['forward-count.json'], 'available_RAM':[s for s in result['meminfo'].splitlines() if s.startswith('MemAvailable:')],
         'new_model_GUI_scorer_calls':0}, ensure_ascii=False))


if __name__ == '__main__':
    main()
