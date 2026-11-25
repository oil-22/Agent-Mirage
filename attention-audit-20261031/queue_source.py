import json,os,pathlib,subprocess,sys,time
model_id=sys.argv[1];root=pathlib.Path('/home/researcher/attention-20261031');queuepath=root/('source-queue-'+model_id+'.json')
def state(phase,**kw):queuepath.write_text(json.dumps(dict(phase=phase,time=time.time(),**kw),indent=2))
models={'qwen9':('/home/researcher/models/Qwen3.5-9B','4,5'),'glm':('/home/researcher/models/GLM-4.6V-Flash-411bb4d77144','6,7')}
state('waiting_for_main')
while True:
    p=root/model_id/'status.json'
    if p.exists():
        status=json.loads(p.read_text())
        if status.get('phase')=='finished' and status.get('total')==324:break
    time.sleep(10)
time.sleep(3)
source=root/'source-campaign';plan=json.loads((source/'plan.json').read_text())
plan['cases']=[next(c for c in plan['cases'] if c['id']==cid) for cid in ['WM-10-original','VWA-11-original']]
preflight=source/'preflight-plan.json';preflight.write_text(json.dumps(plan))
path,visible=models[model_id];env=dict(os.environ,CUDA_VISIBLE_DEVICES=visible,HF_HUB_DISABLE_PROGRESS_BARS='1')
out=root/('source-'+model_id)
base=['/opt/whz/conda-envs/webmall-vlm/bin/python','/home/researcher/run_attention_source.py','--model',path,'--model-id',model_id,'--assets',str(source/'assets'),'--out',str(out)]
state('source_preflight')
with (root/('source-'+model_id+'-preflight.log')).open('w') as log:
    rc=subprocess.run(base+['--plan',str(preflight),'--preflight'],env=env,stdout=log,stderr=log).returncode
status=json.loads((out/'status.json').read_text()) if (out/'status.json').exists() else {}
if rc or status.get('completed')!=2 or status.get('failed'):
    state('preflight_failed',exit_code=rc,status=status);sys.exit(1)
state('source_running')
with (root/('source-'+model_id+'.log')).open('w') as log:
    rc=subprocess.run(base+['--plan',str(source/'plan.json')],env=env,stdout=log,stderr=log).returncode
state('finished',exit_code=rc,status=json.loads((out/'status.json').read_text()))
