"""Read installed fallback code and failed-request size; never runs inference."""
import json
from pathlib import Path
from remote import remote
here = Path(__file__).resolve().parent
service = json.loads((here / 'v7-service-launch.json').read_text())
code = '''import pathlib,json,hashlib
p=pathlib.Path('/opt/whz/conda-envs/webmall-vlm/lib/python3.11/site-packages/transformers/models/qwen3_5/modeling_qwen3_5.py')
source=p.read_text();lines=source.splitlines()
body=json.loads((pathlib.Path(ROOT)/'requests/1792911523173290976/request.json').read_text())
v=body['view']
print(json.dumps({'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'fallback':'\\n'.join(lines[185:335]),'request':{'images':len(v['images']),'messages':len(v['messages']),'text_chars':sum(len(json.dumps(m,ensure_ascii=False))for m in v['messages']),'operation':body['operation'],'candidate_chars':len(body.get('candidate',''))}},ensure_ascii=False))
'''.replace('ROOT', repr(service['root']))
data = json.loads(remote(code, host='3090'))
(here / 'v362-oom-backend-inspection.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
print(json.dumps(data, ensure_ascii=True))
