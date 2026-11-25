from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
import json,urllib.request,hashlib,io,shutil,ast,time,base64
from PIL import Image

P=Path(__file__).resolve().parent;SRC=P.parent/'batch01'
REMOTE='/data/researcher/context-length-natural-20261117/scale100'
all_tasks=json.loads((P/'source/PRIVATE-test_classifieds.raw.json').read_text(encoding='utf8'))
selected=json.loads((P/'source/selected-public-tasks.json').read_text(encoding='utf8'))
commit=json.loads((P/'source/repository-commit.json').read_text(encoding='utf8'))['commit']
assert len(selected)==100 and len({x['task_id'] for x in selected})==100
ids=[x['task_id'] for x in selected];full={x['task_id']:x for x in all_tasks}
refs=[]
for t in selected:
    raw=t['image'];paths=[] if not raw else raw if isinstance(raw,list) else [raw]
    t['reference_image_paths']=[]
    for i,path in enumerate(paths):
        assert path.startswith('environment_docker/') and '..' not in Path(path).parts
        rel='reference-images/T'+str(t['task_id']).zfill(3)+'-'+str(i)+Path(path).suffix
        t['reference_image_paths'].append(rel);refs.append((path,rel))

def fetch(item):
    path,rel=item;out=P/rel;out.parent.mkdir(parents=True,exist_ok=True)
    url='https://cdn.jsdelivr.net/gh/web-arena-x/visualwebarena@'+commit+'/'+path
    if not out.exists():
        last=None
        for attempt in range(3):
            try:
                fetch_url=url if attempt==0 else 'https://api.github.com/repos/web-arena-x/visualwebarena/contents/'+path+'?ref='+commit
                req=urllib.request.Request(fetch_url,headers={'User-Agent':'Agent-Mirage-research','Accept':'application/vnd.github.raw+json'})
                raw=urllib.request.urlopen(req,timeout=25).read()
                if raw.lstrip().startswith(b'{'):
                    obj=json.loads(raw)
                    if obj.get('encoding')=='base64':raw=base64.b64decode(obj['content'])
                im=Image.open(io.BytesIO(raw));im.verify();out.write_bytes(raw);break
            except Exception as e:last=e;time.sleep(1)
        else:raise RuntimeError(path+': '+str(last))
    raw=out.read_bytes();im=Image.open(io.BytesIO(raw));size=im.size;im.verify()
    return {'source_path':path,'local_path':rel,'source_url':url,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'size':size}
with ThreadPoolExecutor(max_workers=6) as pool:records=list(pool.map(fetch,refs))
(P/'reference-image-manifest.json').write_text(json.dumps(records,indent=2),encoding='utf8')
(P/'tasks.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf8')
private=P/'PRIVATE-evaluator-configs';private.mkdir(exist_ok=True)
bindings=[]
for t in selected:
    d=full[t['task_id']]
    assert d['require_reset'] is False and d['eval']['eval_types']==['url_match'] and d['sites']==['classifieds']
    assert '|AND|' not in d['start_url']
    raw=json.dumps(d,ensure_ascii=False).replace('__CLASSIFIEDS__','http://192.0.2.10:29980')
    # All scored URLs and task inputs are mapped together. Scorer fields never enter actor messages.
    assert '__REDDIT__' not in raw and '__SHOPPING__' not in raw
    f=private/('T'+str(t['task_id']).zfill(3)+'.json');f.write_text(raw,encoding='utf8')
    bindings.append({'task_id':t['task_id'],'original_private_path':REMOTE+'/PRIVATE-evaluator-configs/'+f.name,
        'original_private_SHA':hashlib.sha256(f.read_bytes()).hexdigest(),'eligible':True,'eval_types':['url_match']})
(P/'native-bindings-public.json').write_text(json.dumps({'tasks':bindings},indent=2),encoding='utf8')
for name in ['actor-template.json','native_environment.py','native-parser-source.py']:
    shutil.copy2(SRC/name,P/name)
cfg=json.loads((SRC/'config.json').read_text(encoding='utf8'))
cfg.update(task_ids=ids,max_model_calls=8000,service_port=19319,attempt='natural-scale100',
    stage='100 unique natural main trajectories with isolated probes; actual continuations deferred',
    schedule='complete all 100 independent natural main trajectories before any additional branch continuation',
    task_selection='first 100 ascending task IDs among 116 official classifieds read-only URL-match single-tab candidates',
    task_reference_policy='reference images inserted once as a separate initial user message, retained in natural history, never removed by current-observation intervention',
    selected_at=datetime.now(timezone(timedelta(hours=8))).isoformat())
(P/'config.json').write_text(json.dumps(cfg,indent=2),encoding='utf8')
import secrets
if not(P/'service.token').exists():(P/'service.token').write_text(secrets.token_hex(32),encoding='ascii')
service=(SRC/'model_service.py').read_text(encoding='utf8')
(P/'model_service.py').write_text(service,encoding='utf8')
runner=(SRC/'run_natural.py').read_text(encoding='utf8')
old="    body['messages']=[copy.deepcopy(TEMPLATE['messages'][0])]+copy.deepcopy(history)+[dict(role='user',content=blocks)]"
new="""    reference_prefix=[]
    if not history and task.get('reference_image_paths'):
        reference_blocks=[dict(type='text',text='Task reference image(s). Use these to interpret the task; they are not current browser observations.')]
        reference_blocks.extend(imgblock((P/rel).read_bytes()) for rel in task['reference_image_paths'])
        reference_prefix=[dict(role='user',content=reference_blocks)]
    body['messages']=[copy.deepcopy(TEMPLATE['messages'][0])]+reference_prefix+copy.deepcopy(history)+[dict(role='user',content=blocks)]"""
assert old in runner;runner=runner.replace(old,new)
runner=runner.replace("and not task.get('image')", "and all((P/rel).is_file() for rel in task.get('reference_image_paths',[]))")
runner=runner.replace("        continuation_queue=[]\n        for tid in CFG['task_ids']:","""        continuation_queue=[]
        imports=json.loads((P/'reuse-ledger.json').read_text())
        reused={r['task_id']:r for r in imports['completed_natural_trajectories']}
        save(R/'reuse-ledger.json',imports)
        for tid in CFG['task_ids']:
            if tid in reused:
                source=Path(reused[tid]['clean_path'])
                terminal=json.loads((source/'terminal.json').read_text())
                assert terminal['outcome'] in ['model_stop','step_cap']
                assert sha((source/'terminal.json').read_bytes())==reused[tid]['terminal_sha256']
                save(R/f'T{tid:03}'/'reused-clean.json',reused[tid])
                continue""")
old="""        for job in continuation_queue:
            continue_branch(tasks[job['task_id']],Path(job['private']),Path(job['checkpoint']),job['condition'],Path(job['folder']))
        state(phase='completed',semantic_labels='pending_audit')"""
new="""        save(R/'deferred-continuations.json',dict(queue=continuation_queue,executed=False,
            reason='100 natural main trajectories and their initial probes are the current priority; continuation branches are counted separately'))
        completed=[json.loads(f.read_text()) for f in R.glob('T*/clean/terminal.json')]
        assert len(completed)+len(reused)==100
        state(phase='completed_100_natural',new_natural=len(completed),reused_natural=len(reused),
            total_natural=100,semantic_labels='pending_audit',branch_continuations='deferred')"""
assert old in runner;runner=runner.replace(old,new)
ast.parse(runner);ast.parse(service)
(P/'run_scale100.py').write_text(runner,encoding='utf8')
plan={'task_ids':ids,'total_unique_tasks':100,'selected_before_new_outputs':True,'selection':cfg['task_selection'],
    'source_receipt':json.loads((P/'source/source-receipt.json').read_text(encoding='utf8')),
    'repository_commit':commit,'reference_images':len(records),'bins':cfg['bins'],'tolerance':cfg['tolerance'],
    'reuse_policy':'reuse already completed natural prefixes among this exact panel; incomplete prefixes preserved but not counted',
    'counting':'one completed normal main trajectory per distinct task; isolated decisions, partial runs and branch continuations do not increase the 100 count',
    'context_policy':cfg['history_policy'],'max_steps':50,'continuations':'deferred separately',
    'created_at':cfg['selected_at'],'engineering_failures':'preserve and report; do not count as completed normal trajectories'}
(P/'prospective-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
manifest={str(f.relative_to(P)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in P.rglob('*') if f.is_file() and f.name not in ['service.token','source-manifest.json']}
(P/'source-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print(json.dumps({'tasks':len(ids),'reference_images':len(records),'reference_bytes':sum(r['bytes'] for r in records),'first_ids':ids[:8],'last_ids':ids[-8:],'prepared':True}))
