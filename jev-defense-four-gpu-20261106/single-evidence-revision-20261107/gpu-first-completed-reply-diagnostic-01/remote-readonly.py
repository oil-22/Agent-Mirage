import base64,hashlib,json,pathlib
p=pathlib.Path('/home/researcher/jev-defense-four-gpu-20261106/single-evidence-revision-20261107/gpu-four-first-attempts-01/worker/r000')
raw=(p/'raw-output.txt').read_bytes();result=json.loads((p/'result.json').read_bytes());assert hashlib.sha256(raw).hexdigest()==result['raw_output_sha256']
print(json.dumps({'raw_base64':base64.b64encode(raw).decode(),'result':result}))
