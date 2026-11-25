import json,os,pathlib,subprocess,sys,time
root=pathlib.Path('/home/researcher/attention-20261102');mid=sys.argv[1]
models={'qwen27':('/opt/whz/llms/Qwen3.8-27B','2,3,4'),'qwen9':('/home/researcher/models/Qwen3.5-9B','0,5'),'glm':('/home/researcher/models/GLM-4.6V-Flash-411bb4d77144','6,7')}
model,gpus=models[mid];out=root/mid;source=root/'campaign';state=root/(mid+'-controller.json')
def update(phase,**kw):
 tmp=state.with_suffix('.tmp');tmp.write_text(json.dumps(dict(phase=phase,pid=os.getpid(),time=time.time(),**kw),indent=2));tmp.replace(state)
plan=json.loads((source/'plan.json').read_text());test=dict(plan);test['cases']=[plan['cases'][0],plan['cases'][-11]]
pre=source/('preflight-'+mid+'.json');pre.write_text(json.dumps(test))
env=dict(os.environ,CUDA_VISIBLE_DEVICES=gpus,HF_HUB_DISABLE_PROGRESS_BARS='1')
base=['/opt/whz/conda-envs/webmall-vlm/bin/python',str(root/'run_attention.py'),'--model',model,'--model-id',mid,'--assets',str(source/'assets'),'--out',str(out)]
update('preflight',gpus=gpus)
with (root/(mid+'-preflight.log')).open('w') as log:rc=subprocess.run(base+['--plan',str(pre),'--preflight'],env=env,stdout=log,stderr=log).returncode
s=json.loads((out/'status.json').read_text()) if (out/'status.json').exists() else {}
if rc or s.get('completed')!=2 or s.get('failed'):update('preflight_failed',exit_code=rc,status=s);sys.exit(1)
update('running',gpus=gpus)
with (root/(mid+'.log')).open('w') as log:rc=subprocess.run(base+['--plan',str(source/'plan.json')],env=env,stdout=log,stderr=log).returncode
s=json.loads((out/'status.json').read_text()) if (out/'status.json').exists() else {}
update('finished' if rc==0 and s.get('completed')==len(plan['cases']) and not s.get('failed') else 'failed',exit_code=rc,status=s)
