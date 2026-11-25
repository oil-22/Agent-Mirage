import json,os,pathlib,shutil,subprocess,time
import numpy as np
root=pathlib.Path('/home/researcher/attention-20261031');folder=root/'glm';exe='/opt/whz/conda-envs/webmall-vlm/bin/python'
shutil.copyfile(folder/'runtime.json',folder/'runtime-before-async.json')
plan=json.loads((root/'campaign/plan.json').read_text());cid='T00-early-full-current_control'
p=root/'campaign/async-validation-plan.json';p.write_text(json.dumps(dict(plan,cases=[next(c for c in plan['cases'] if c['id']==cid)])))
base=[exe,'/home/researcher/run_attention_main_async.py','--model','/home/researcher/models/GLM-4.6V-Flash-411bb4d77144','--model-id','glm','--assets',str(root/'campaign/assets')]
env=dict(os.environ,CUDA_VISIBLE_DEVICES='6,7',HF_HUB_DISABLE_PROGRESS_BARS='1')
out=root/'glm-async-validation'
with (root/'glm-async-validation.log').open('w') as log:rc=subprocess.run(base+['--plan',str(p),'--out',str(out),'--preflight'],env=env,stdout=log,stderr=log).returncode
assert rc==0
old=json.loads((folder/cid/'result.json').read_text());new=json.loads((out/cid/'result.json').read_text())
a=np.load(folder/cid/'attention.npz');b=np.load(out/cid/'attention.npz')
equal={k:np.array_equal(a[k],b[k]) for k in a.files}
syncout=root/'glm-sync-repeat-validation'
syncbase=[exe,'/home/researcher/run_attention_main_stops_fixed.py','--model','/home/researcher/models/GLM-4.6V-Flash-411bb4d77144','--model-id','glm','--assets',str(root/'campaign/assets')]
with (root/'glm-sync-repeat-validation.log').open('w') as log:rc=subprocess.run(syncbase+['--plan',str(p),'--out',str(syncout)],env=env,stdout=log,stderr=log).returncode
assert rc==0
c=np.load(syncout/cid/'attention.npz');sr=json.loads((syncout/cid/'result.json').read_text())
floatkeys=['mass','turn_mass'];diffs={k:float(np.max(np.abs(a[k]-b[k]))) for k in floatkeys};repeatdiffs={k:float(np.max(np.abs(a[k]-c[k]))) for k in floatkeys}
tolerance=2e-6
audit={'old_output_tokens':old['output_tokens'],'new_output_tokens':new['output_tokens'],'output_ids_exactly_equal':old['output_ids']==new['output_ids'],'synchronous_repeat_output_ids_exactly_equal':old['output_ids']==sr['output_ids'],'all_saved_arrays_exactly_equal':equal,'async_max_absolute_differences':diffs,'synchronous_repeat_max_absolute_differences':repeatdiffs,'absolute_tolerance_for_fp32_atomic_reductions':tolerance,'new_read_only_logit_validation':new.get('capture_validation')}
(root/'glm-async-validation.json').write_text(json.dumps(audit,indent=2))
assert audit['output_ids_exactly_equal'] and audit['synchronous_repeat_output_ids_exactly_equal'] and all(d<=tolerance for d in diffs.values()) and all(equal[k] for k in equal if k not in floatkeys) and audit['new_read_only_logit_validation']['max_logit_abs_diff']==0
with (root/'glm-resumed.log').open('w') as log:rc=subprocess.run(base+['--plan',str(root/'campaign/plan.json'),'--out',str(folder)],env=env,stdout=log,stderr=log).returncode
(root/'glm-resume.json').write_text(json.dumps({'exit_code':rc,'time':time.time()},indent=2))
