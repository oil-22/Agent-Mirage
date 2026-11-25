"""Inspect the submitted CPU job; terminal export never relaunches the job."""
import argparse
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / 'remaining29-full-history-gui-20261110-37'
sys.path.insert(0, str(PREVIOUS))
from orchestrate import remote, save, sha, COMMON


def main(prefix='native-CPU'):
    assert prefix in ['native-CPU', 'native-CPU-linked02', 'full-input-CPU']
    submission = json.loads((HERE / (prefix + '-submission.json')).read_bytes())
    target = Path(submission['output'])
    expected = json.loads((target / 'launch.json').read_bytes())['identity']
    code = 'ROOT=' + repr(submission['remote_root']) + '\nEXPECTED=' + repr(expected) + '\n' + COMMON + r'''
root=Path(ROOT);actual=identity(EXPECTED['pid'])
if not actual.get('absent'):
 assert all(str(actual[k])==str(EXPECTED[k])for k in['pid','uid','command','start_ticks'])
live=not actual.get('absent')and actual['state']not in['Z','X']
value=dict(time=time.time(),actual=actual,live=live,read_only=True,new_model_GUI_scorer_calls=0)
for name in['receipt.json','failure.json']:
 if(root/name).exists():value[name]=json.loads((root/name).read_bytes())
value['log_tail']=(root/'worker.log').read_bytes()[-2400:].decode(errors='replace')
if not live:
 assert ('receipt.json'in value) != ('failure.json'in value)
 files={str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()and'__pycache__'not in p.parts and p.name!='postexit-seal.json'}
 seal=root/'postexit-seal.json'
 if seal.exists():assert json.loads(seal.read_bytes())==files
 else:
  with seal.open('x')as stream:json.dump(files,stream,sort_keys=True)
 value['postexit_files_SHA256']=files;value['postexit_seal_sha256']=sha(seal)
 value['postexit_export']={name:(root/name).read_text()for name in['launch.json','worker.log','package-index.json','postexit-seal.json']}
print(json.dumps(value,ensure_ascii=True))
'''
    output, operation = remote('3090', code, 'inspect-same-native-quote-reference-CPU-job', timeout=55)
    value = json.loads(output)
    observed = target / ('observation-' + str(time.time_ns()) + '.json')
    save(observed, dict(value, operation=str(operation)))
    if value['live']:
        print(json.dumps(dict(live=True, actual=value['actual'], observation=str(observed))))
        return
    assert not (target / 'seal.json').exists(), 'Use the existing completed authority'
    for name, raw in value['postexit_export'].items():
        path = target / ('remote-' + name)
        path.write_text(raw, encoding='utf8', newline='\n')
        expected_sha = value['postexit_seal_sha256'] if name == 'postexit-seal.json' else value['postexit_files_SHA256'][name]
        assert sha(path) == expected_sha
    result_name = 'receipt.json' if 'receipt.json' in value else 'failure.json'
    save(target / result_name, dict(value[result_name], operation=str(operation),
        actual_postexit=value['actual'], original_postexit_seal_sha256=value['postexit_seal_sha256']))
    save(target / 'seal.json', {p.name: sha(p) for p in target.iterdir() if p.is_file()})
    result = dict(root=str(target), receipt_file=result_name, receipt_sha256=sha(target / result_name), seal_sha256=sha(target / 'seal.json'))
    save(HERE / (prefix + ('-completed.json' if result_name=='receipt.json' else '-failed.json')), result)
    print(json.dumps(dict(result, passed=result_name=='receipt.json', controls=value.get('receipt.json',{}).get('controls_count'),
        failure=value.get('failure.json'), log_tail=value['log_tail'][-1000:])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', choices=['native-CPU','native-CPU-linked02','full-input-CPU'], default='native-CPU')
    main(parser.parse_args().prefix)
