"""Read actual native forward/hook code and host RAM; no load or inference."""
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE / 'full-history-gui-development-20261109-23'))
from remote_control import remote, save, sha

CODE = r'''
from pathlib import Path
import hashlib,json,os,time
assert os.getuid()==1033
base=Path('/home/researcher/jev-defense-four-gpu-20261106')
old=base/'memory-scheduled-full-history-gui-20261109-29'
package=base/'runtime-preparation/memory-scheduled-full-history-gui-20261109-29'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=Path('/opt/whz/conda-envs/webmall-vlm/lib/python3.11/site-packages/transformers/models/qwen3_5/modeling_qwen3_5.py')
hooks=Path('/opt/whz/conda-envs/webmall-vlm/lib/python3.11/site-packages/accelerate/hooks.py')
source=p.read_text(); hs=hooks.read_text()
failure=old/'worker/requests/0021'
out={'time':time.time(),'native_source':{'path':str(p),'sha256':sha(p),'text':source},
     'accelerate_hooks':{'path':str(hooks),'sha256':sha(hooks),'text':hs},
     'meminfo':Path('/proc/meminfo').read_text(),'new_model_GUI_scorer_calls':0,
     'failed_request':{name:json.loads((failure/name).read_bytes())for name in
       ['prepared.json','first-forward.json','failed-memory.json','forward-count.json','effective-generation.json','failure.json']},
     'old_manifest_sha256':sha(package/'manifest.json')}
print(json.dumps(out,ensure_ascii=False))
'''


def main():
    root = HERE / ('native-source-evidence-' + str(time.time_ns()))
    root.mkdir()
    output, operation = remote('3090', CODE, 'new31-read-native-forward-hook-source-no-load', timeout=55)
    result = json.loads(output)
    for key in ['native_source', 'accelerate_hooks']:
        item = result[key]
        path = root / (key + '.py')
        path.write_text(item.pop('text'), encoding='utf8')
        assert sha(path) == item['sha256']
        item['local_source'] = str(path)
    save(root / 'receipt.json', dict(result, remote_operation=str(operation)))
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    failed = result['failed_request']
    print(json.dumps({'root':str(root), 'prepared':failed['prepared.json'],
          'failed_memory':failed['failed-memory.json'], 'forward':failed['forward-count.json'],
          'native_source_SHA':result['native_source']['sha256'],
          'available_RAM':[s for s in result['meminfo'].splitlines() if s.startswith('MemAvailable:')],
          'new_experiment_calls':0},ensure_ascii=False))


if __name__ == '__main__':
    main()
