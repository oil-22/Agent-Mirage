CFG={'resource': '/data/researcher/jev-defense-four-gpu-20261106/online-three-resource-conditions/1793986896126859644/resource-conditions.json', 'resource_sha256': '5dbb2b6d459d479d4c8f687e166f9835ae927a0d1c6bca95786707d629890c64', 'ownership': '/data/researcher/jev-defense-four-gpu-20261106/ownership-transport-proof-1793987040339197700/ownership-transport-proof.json', 'ownership_sha256': '66a3918cbf29cbd262674bdc630800ebf7534b96d542a37da51d49e9c1f6e6e9', 'control_seal_sha256': 'db723d2f2b4b24c1dd2085d40fe3f56db8f61f9b411a4791ea1d95a72764956a'}

import hashlib,json,pathlib,subprocess,sys
B=pathlib.Path('/data/researcher/jev-defense-four-gpu-20261106')
C=B/'gui-three-control-preparation-01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(C/'seal.json')==CFG['control_seal_sha256']
for name,expected in json.loads((C/'seal.json').read_bytes()).items():assert sha(C/name)==expected,name
P='/data/researcher/venvs/qwen35-9b-full-20261019/bin/python'
argv=[P,'-B',str(C/'prepare_bound_once.py'),'--resource',CFG['resource'],'--resource-sha256',CFG['resource_sha256'],
 '--ownership',CFG['ownership'],'--ownership-sha256',CFG['ownership_sha256'],
 '--output',str(B/'gui-three-evidence-binding-01')]
r=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
sys.stdout.buffer.write(r.stdout);sys.stdout.buffer.flush()
sys.stderr.buffer.write(r.stderr);sys.stderr.buffer.flush()
if r.returncode:raise SystemExit(r.returncode)
spec=B/'gui-final-readiness-three-01/launch-spec.json'
actual=sha(spec)
print(json.dumps({'actual_launch_spec':str(spec),'sha256':actual}),flush=True)
r=subprocess.run([P,'-B',str(C/'background_three_once.py'),'--spec',str(spec),'--spec-sha256',actual],
 stdout=subprocess.PIPE,stderr=subprocess.PIPE)
sys.stdout.buffer.write(r.stdout);sys.stdout.buffer.flush()
sys.stderr.buffer.write(r.stderr);sys.stderr.buffer.flush()
raise SystemExit(r.returncode)
