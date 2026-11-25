import json,os,pathlib,shutil,subprocess,time
root=pathlib.Path('/home/researcher/attention-20261031');folder=root/'qwen9';exe='/opt/whz/conda-envs/webmall-vlm/bin/python'
shutil.copyfile(folder/'runtime.json',folder/'runtime-before-stop-fix.json')
plan=json.loads((root/'campaign/plan.json').read_text());cid='T04-early-last2-stale_replace'
single=dict(plan,cases=[next(c for c in plan['cases'] if c['id']==cid)])
p=root/'campaign/stop-validation-plan.json';p.write_text(json.dumps(single))
base=[exe,'/home/researcher/run_attention_main_stops_fixed.py','--model','/home/researcher/models/Qwen3.5-9B','--model-id','qwen9','--assets',str(root/'campaign/assets')]
env=dict(os.environ,CUDA_VISIBLE_DEVICES='4,5',HF_HUB_DISABLE_PROGRESS_BARS='1')
with (root/'qwen9-stop-validation.log').open('w') as log:
    rc=subprocess.run(base+['--plan',str(p),'--out',str(root/'qwen9-stop-validation'),'--preflight'],env=env,stdout=log,stderr=log).returncode
assert rc==0
old=json.loads((folder/cid/'result.json').read_text());new=json.loads((root/'qwen9-stop-validation'/cid/'result.json').read_text());ids=old['output_ids'];stop=next(i+1 for i,x in enumerate(ids) if x in [248044,248046])
audit={'old_recorded_tokens':len(ids),'first_native_turn_end_tokens':stop,'new_tokens':new.get('output_tokens'),'new_equals_exact_old_first_reply':new.get('output_ids')==ids[:stop],'new_read_only_validation':new.get('capture_validation')}
(root/'qwen9-stop-validation.json').write_text(json.dumps(audit,indent=2))
assert audit['new_equals_exact_old_first_reply'] and audit['new_read_only_validation']['max_logit_abs_diff']==0
with (root/'qwen9-resumed.log').open('w') as log:
    rc=subprocess.run(base+['--plan',str(root/'campaign/plan.json'),'--out',str(folder)],env=env,stdout=log,stderr=log).returncode
(root/'qwen9-resume.json').write_text(json.dumps({'exit_code':rc,'time':time.time()},indent=2))
