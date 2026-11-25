"""Linked CPU export repair; retain the first missing-filename audit unchanged."""
from pathlib import Path
from control import HERE, save, sha

original = Path(__file__).with_name('audit_same_png_freshness_boundary.py')
failed = HERE / 'operations/1794650244069467900-CPU-existing-same-PNG-freshness-boundary-audit'
assert (failed / 'receipt.json').exists()
source = original.read_text(encoding='utf8')
needle = "head=torch.load(d/'raw-head.pt',map_location='cpu',weights_only=True);heads.append(head)"
assert source.count(needle) == 1
replacement = "raw=json.loads((d/'raw-readout.json').read_bytes());head=torch.tensor(raw[0]['values'],dtype=getattr(torch,raw[0]['dtype'].split('.')[-1]));assert hashlib.sha256(head.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()==raw[0]['sha256'];heads.append(head)"
source = source.replace(needle, replacement)
source = source.replace('import hashlib,json,time,torch', "import hashlib,json,time,os\nos.environ['CUDA_VISIBLE_DEVICES']=''\nimport torch")
source = source.replace("print(json.dumps({'time':time.time(),'calls':rows", "assert not torch.cuda.is_initialized()\nprint(json.dumps({'time':time.time(),'calls':rows")
binding = HERE / 'same-PNG-freshness-audit-repair-binding.json'
save(binding, {'original_script_sha256': sha(original),
               'preserved_failure_operation': str(failed),
               'preserved_failure_files': {p.name: sha(p) for p in failed.iterdir() if p.is_file()},
               'repair': 'Read existing raw-readout.json with dtype and full raw-head SHA, as already used by the successful Flash CPU audit. No new inference or changed service/input.',
               'new_inference': 0})
exec(compile(source, str(Path(__file__)), 'exec'))
