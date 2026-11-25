"""Read failed input/placement and compute weight-only alternative placements."""
from pathlib import Path
import json
import subprocess
import time

HERE = Path(__file__).resolve().parent
target = HERE / 'capacity-diagnosis-02' / str(time.time_ns())
target.mkdir(parents=True, exist_ok=False)
code = r'''
from pathlib import Path
import json,hashlib,os,time,subprocess
b=Path('/home/researcher/jev-defense-four-gpu-20261106')
p=b/'runtime-preparation/joint-main-controls-20261108-02'
r=b/'single-evidence-revision-20261107/joint-main-controls-20261108-02'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((r/'terminal-manifest.json').read_bytes())
for n,h in m.items():assert sha(r/n)==h,n
for n in ['launcher-process.json','worker/process.json']:
 pid=json.loads((r/n).read_bytes())['pid'];assert not Path('/proc',str(pid)).exists()
ref=json.loads((p/'primary-reference.json').read_bytes())
bound=json.loads(Path(ref['primary_native_layout_receipt']).read_bytes())
rows=json.loads((Path(bound['meta_root'])/'meta-state.json').read_bytes())
placements=[]
for a in range(17,24):
 for c in range(18,25):
  bb=64-a-c
  dm={'model.visual':0,'model.language_model.embed_tokens':0,'model.language_model.norm':2,
      'model.language_model.rotary_emb':2,'lm_head':2}
  for i in range(64):dm['model.language_model.layers.'+str(i)]=0 if i<a else 1 if i<a+bb else 2
  amounts={i:0 for i in range(3)}
  for row in rows:
   matching=[key for key in dm if row['name']==key or row['name'].startswith(key+'.')]
   amounts[dm[max(matching,key=len)]]+=row['bytes']
  # Measured 12651-token peaks minus original weights; a linear projection is
  # only prioritization for a new real input, never a capacity guarantee.
  transient=[4542061400,4337239680,4278964480]
  projected=[amounts[i]+transient[i]*17113/12651 for i in range(3)]
  placements.append({'layers':[a,bb,c],'parameter_bytes':amounts,
                     'weight_plus_projected_activation_bytes':projected,'score':max(projected)})
placements.sort(key=lambda x:x['score'])
failed=json.loads((r/'worker/judges/06/prepared.json').read_bytes())
failure=json.loads((r/'worker/failure.json').read_bytes())
print(json.dumps({'time_unix':time.time(),'parent_manifest_sha256':sha(r/'terminal-manifest.json'),
 'parent_all_files_verified':len(m),'old_processes_absent':True,
 'failed_input_tokens':failed['input_ids']['shape'][1],'failed_prepared':failed,
 'generated_tokens_before_failure':0 if not(r/'worker/judges/06/generated-token-progress.jsonl').stat().st_size else None,
 'last_error_lines':failure['traceback'].splitlines()[-3:],
 'top_weight_and_activation_estimates':placements[:8],
 'estimates_not_real_capacity':True,
 'GPU':subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True),
 'compute':subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)}))
'''
(target / 'source.py').write_text(code, encoding='utf8')
res = subprocess.run(['D:/Git/usr/bin/ssh.exe', '-F', 'C:/Users/researcher/.ssh/config', '-o', 'BatchMode=yes',
    '3090', '/opt/whz/conda-envs/webmall-vlm/bin/python', '-'], input=code.encode(), capture_output=True, timeout=60)
(target / 'stdout.json').write_bytes(res.stdout)
(target / 'stderr.txt').write_bytes(res.stderr)
if res.returncode:
    raise RuntimeError(res.stderr.decode(errors='replace'))
d = json.loads(res.stdout)
print(json.dumps({'directory':str(target),'failure_tokens':d['failed_input_tokens'],
    'estimates': d['top_weight_and_activation_estimates'], 'GPU':d['GPU'],'compute':d['compute']}, ensure_ascii=False))
