"""Stage a distinct CPU-only admission of the newly integrated auxiliary helper."""
import base64
import io
import json
from pathlib import Path
import sys
import time
import zipfile

HERE = Path(__file__).resolve().parent
GUI = HERE.parent / 'full-gui-bounded-evidence-20261109-03'
sys.path.insert(0, str(GUI))
from remote_control import remote, save, sha

package = HERE / 'integrated-runtime-linked02'
source_seal = json.loads((package / 'integrated-source-seal.json').read_bytes())
for name, expected in source_seal.items():
    assert sha(package / name) == expected
images = HERE.parent / 'exploration-grounding-repair-20261109-05' / 'source-controls-01' / 'public' / 'images'
buffer = io.BytesIO()
with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in package.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and path.name != 'private.token':
            archive.write(path, 'package/' + path.relative_to(package).as_posix())
    archive.write(HERE / 'check_integrated_lifecycle_cpu.py', 'check.py')
    for name in ['catalog.png', 'footer.png', 'form.png']:
        archive.write(images / name, 'images/' + name)
bundle = buffer.getvalue()
code = 'ARCHIVE=' + repr(base64.b64encode(bundle).decode()) + '\n' + r'''
from pathlib import Path
import base64,hashlib,io,json,os,subprocess,time,zipfile
root=Path('/home/researcher/jev-defense-four-gpu-20261106/stateless-auxiliary-20261109-07')/('CPU-integrated-'+str(time.time_ns()))
root.mkdir(parents=True,exist_ok=False)
raw=base64.b64decode(ARCHIVE);(root/'uploaded.zip').write_bytes(raw)
with zipfile.ZipFile(io.BytesIO(raw))as archive:archive.extractall(root)
command=['/opt/whz/conda-envs/webmall-vlm/bin/python','-B',str(root/'check.py'),'--package',str(root/'package'),'--images',str(root/'images'),'--output',str(root/'result')]
environment=dict(os.environ);environment['CUDA_VISIBLE_DEVICES']='';environment['PYTHONDONTWRITEBYTECODE']='1'
completed=subprocess.run(command,capture_output=True,text=True,env=environment,timeout=90)
(root/'stdout.txt').write_text(completed.stdout,encoding='utf8');(root/'stderr.txt').write_text(completed.stderr,encoding='utf8')
(root/'operation.json').write_text(json.dumps({'command':command,'returncode':completed.returncode,'UID':os.getuid(),'new_actual_model_GUI_calls':0,'CUDA_VISIBLE_DEVICES':''},indent=2)+'\n')
result=io.BytesIO()
with zipfile.ZipFile(result,'w',zipfile.ZIP_DEFLATED)as archive:
 for path in root.rglob('*'):
  if path.is_file()and('result'in path.relative_to(root).parts or path.name in {'stdout.txt','stderr.txt','operation.json'}):archive.write(path,path.relative_to(root).as_posix())
print(json.dumps({'remote':str(root),'returncode':completed.returncode,'stdout':completed.stdout,'stderr':completed.stderr,'archive':base64.b64encode(result.getvalue()).decode()}))
'''
text, operation = remote('3090', code, 'new-integrated-stateless-native-cache-CPU-protocol', timeout=115)
result = json.loads(text)
local = HERE / ('integrated-CPU-admission-' + str(time.time_ns()))
local.mkdir()
raw = base64.b64decode(result.pop('archive'))
(local / 'original.zip').write_bytes(raw)
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    archive.extractall(local / 'original')
save(local / 'collection.json', {'operation': str(operation), 'remote': result['remote'],
                               'returncode': result['returncode'], 'archive_sha256': sha(local / 'original.zip'),
                               'source_seal_sha256': sha(package / 'integrated-source-seal.json'),
                               'actual_model_GUI_calls': 0})
print(json.dumps({'local': str(local), **result}, ensure_ascii=False))
if result['returncode']:
    raise SystemExit(result['returncode'])
