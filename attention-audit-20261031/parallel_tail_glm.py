"""Use GPUs released by the completed 27B batch for disjoint GLM tail cases."""
import hashlib,json,os,pathlib,shutil,subprocess,time
root=pathlib.Path('/home/researcher/attention-20261031');statepath=root/'glm-tail-queue.json';exe='/opt/whz/conda-envs/webmall-vlm/bin/python'
def state(phase,**kw):statepath.write_text(json.dumps({'phase':phase,'time':time.time(),**kw},indent=2))
state('waiting_for_qwen27')
while True:
    s=json.loads((root/'qwen27/status.json').read_text())
    if s.get('phase')=='finished' and s.get('completed')==324:break
    time.sleep(10)
time.sleep(5)
main=json.loads((root/'glm/status.json').read_text());position=main.get('index',324)
if main.get('phase')=='finished':state('unneeded_main_finished');raise SystemExit()
plan=json.loads((root/'campaign/plan.json').read_text());workers=[]
for task,devices,minimum in [('T07','0,1',252),('T08','2,3',288)]:
    if position>=minimum-24:continue
    folder=root/('glm-tail-'+task);folder.mkdir(exist_ok=True)
    selected=[c for c in plan['cases'] if c['id'].startswith(task+'-') and not (root/'glm'/c['id']/'result.json').exists()]
    if not selected:continue
    subset=dict(plan,cases=selected,parent_plan_sha256=hashlib.sha256((root/'campaign/plan.json').read_bytes()).hexdigest())
    p=folder/'plan.json';p.write_text(json.dumps(subset));log=(folder/'run.log').open('w')
    cmd=[exe,'/home/researcher/run_attention_main_async.py','--model','/home/researcher/models/GLM-4.6V-Flash-411bb4d77144','--model-id','glm','--plan',str(p),'--assets',str(root/'campaign/assets'),'--out',str(folder)]
    proc=subprocess.Popen(cmd,env=dict(os.environ,CUDA_VISIBLE_DEVICES=devices,HF_HUB_DISABLE_PROGRESS_BARS='1'),stdout=log,stderr=log)
    workers.append((folder,selected,proc,log))
state('running',workers=[{'folder':str(f),'pid':p.pid,'cases':len(c)} for f,c,p,l in workers])
published=set();duplicates=[]
while any(p.poll() is None for f,c,p,l in workers):
    for folder,cases,proc,log in workers:
        for case in cases:
            cid=case['id'];key=str(folder)+'/'+cid
            if key in published:continue
            src=folder/cid;result=src/'result.json'
            if not result.exists():continue
            rr=json.loads(result.read_text())
            if rr.get('status')!='completed':continue
            dest=root/'glm'/cid
            if dest.exists():
                if (dest/'result.json').exists():
                    existing=json.loads((dest/'result.json').read_text());duplicates.append({'id':cid,'same_output_ids':existing['output_ids']==rr['output_ids'],'same_request_sha256':existing['request_sha256']==rr['request_sha256']})
                else:continue
            else:
                temp=root/'glm'/('.publish-'+cid)
                shutil.copytree(src,temp,copy_function=os.link)
                (temp/'execution-origin.json').write_text(json.dumps({'worker':str(folder),'runtime':json.loads((folder/'runtime.json').read_text())},indent=2))
                # Tail batches are published far ahead of the sequential worker.
                if dest.exists():raise RuntimeError('Sequential worker reached a case during publication; preserve both artifacts')
                temp.rename(dest)
            published.add(key)
    time.sleep(2)
# One final scan occurs after children exit by reusing the same publication loop
# until all completed child results are present in the main case directories.
for folder,cases,proc,log in workers:
    log.close()
    for case in cases:
        cid=case['id'];src=folder/cid;dest=root/'glm'/cid
        if not (src/'result.json').exists() or dest.exists():continue
        rr=json.loads((src/'result.json').read_text())
        if rr.get('status')!='completed':continue
        temp=root/'glm'/('.publish-'+cid);shutil.copytree(src,temp,copy_function=os.link)
        (temp/'execution-origin.json').write_text(json.dumps({'worker':str(folder),'runtime':json.loads((folder/'runtime.json').read_text())},indent=2));temp.rename(dest);published.add(str(folder)+'/'+cid)
state('finished',published=len(published),duplicates=duplicates,workers=[{'folder':str(f),'exit_code':p.returncode,'status':json.loads((f/'status.json').read_text())} for f,c,p,l in workers])
