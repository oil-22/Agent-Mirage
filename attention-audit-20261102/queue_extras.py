import json,os,pathlib,subprocess,sys,time
root=pathlib.Path('/home/researcher/attention-20261102');mid=sys.argv[1];state=root/(mid+'-extras-controller.json')
models={'qwen27':('/opt/whz/llms/Qwen3.8-27B','2,3,4'),'qwen9':('/home/researcher/models/Qwen3.5-9B','0,5'),'glm':('/home/researcher/models/GLM-4.6V-Flash-411bb4d77144','6,7')}
def update(phase,**kw):
 tmp=state.with_suffix('.tmp');tmp.write_text(json.dumps(dict(phase=phase,time=time.time(),pid=os.getpid(),**kw),indent=2));tmp.replace(state)
update('waiting_for_main')
while True:
 statuspath=root/mid/'status.json';controller=root/(mid+'-controller.json')
 if controller.exists():
  c=json.loads(controller.read_text())
  if c['phase'] in ['failed','preflight_failed']:update('main_failed',main=c);sys.exit(1)
  if c['phase']=='finished':break
 time.sleep(5)
model,gpus=models[mid];env=dict(os.environ,CUDA_VISIBLE_DEVICES=gpus,HF_HUB_DISABLE_PROGRESS_BARS='1')
for campaign,prefix in [('button-campaign','buttons'),('source-campaign','source')]:
 source=root/campaign;planpath=source/'plan.json'
 if prefix=='source':
  update('waiting_for_source_cpu_audit')
  while True:
   audit=source/'cpu-input-audit.json'
   if planpath.exists() and audit.exists():
    pp=json.loads(planpath.read_text());aa=json.loads(audit.read_text())
    if len(aa)==len(pp['cases'])*3 and all(x['status']=='passed' for x in aa):break
   time.sleep(5)
 plan=json.loads(planpath.read_text());assert plan['cases'];test=dict(plan)
 if prefix=='source':test['cases']=[plan['cases'][0],next(c for c in plan['cases'] if c['task']=='classifieds_231' and c['step']==3 and c['condition']=='original')]
 else:test['cases']=[plan['cases'][0],plan['cases'][-3]]
 pre=source/('preflight-'+mid+'.json');pre.write_text(json.dumps(test));out=root/(prefix+'-'+mid)
 base=['/opt/whz/conda-envs/webmall-vlm/bin/python',str(root/'run_attention.py'),'--model',model,'--model-id',mid,'--assets',str(source/'assets'),'--out',str(out)]
 update(prefix+'_preflight',gpus=gpus)
 with (root/(prefix+'-'+mid+'-preflight.log')).open('w') as log:rc=subprocess.run(base+['--plan',str(pre),'--preflight'],env=env,stdout=log,stderr=log).returncode
 s=json.loads((out/'status.json').read_text()) if (out/'status.json').exists() else {}
 if rc or s.get('completed')!=2 or s.get('failed'):update(prefix+'_preflight_failed',exit_code=rc,status=s);sys.exit(1)
 update(prefix+'_running',gpus=gpus)
 with (root/(prefix+'-'+mid+'.log')).open('w') as log:rc=subprocess.run(base+['--plan',str(planpath)],env=env,stdout=log,stderr=log).returncode
 s=json.loads((out/'status.json').read_text()) if (out/'status.json').exists() else {}
 if rc or s.get('completed')!=len(plan['cases']) or s.get('failed'):update(prefix+'_failed',exit_code=rc,status=s);sys.exit(1)
update('finished',all_batches_completed=True)
