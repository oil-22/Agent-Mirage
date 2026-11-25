import ast,collections,csv,hashlib,json,pathlib,re,time
from action_audit import audit_action
from response_view import view
import numpy as np
from PIL import Image
root=pathlib.Path('/home/researcher/attention-20261031');out=root/'analysis';out.mkdir(exist_ok=True)
plan=json.loads((root/'campaign/plan.json').read_text());cases={c['id']:c for c in plan['cases']}
def action(text):
    xml=re.findall(r'<action>(.*?)</action>',text,re.S)
    code=re.findall(r'```(?:python)?\s*\n(.*?)```',text,re.S)
    candidates=xml or code
    if candidates:
        if len(candidates)!=1:return 'AMBIGUOUS'
        value=candidates[0].strip()
        try:return 'json:'+json.dumps(json.loads(value),sort_keys=True)
        except Exception:pass
        try:
            tree=ast.parse(value)
            if len(tree.body)==1 and isinstance(tree.body[0],ast.Expr) and isinstance(tree.body[0].value,ast.Call):return ast.dump(tree.body[0].value,include_attributes=False)
        except Exception:pass
        return 'UNPARSED:'+value
    native=re.findall(r'(?m)^Action:\s*(.+)$',text)
    if len(native)==1:
        try:return ast.dump(ast.parse(native[0],mode='eval').body,include_attributes=False)
        except Exception:return 'UNPARSED:'+native[0]
    terminal=re.findall(r'(?m)^\s*(WAIT|DONE|FAIL)\s*$',text)
    return terminal[0] if len(terminal)==1 else 'NO_SINGLE_ACTION'

pixel={}
assets=root/'campaign/assets'
for c in plan['sources']:
    a=c['image_sha256'];b=c['previous_image_sha256'];p=next(assets.glob('*/'+a+'.*'));q=next(assets.glob('*/'+b+'.*'))
    aa=np.asarray(Image.open(p).convert('RGB'));bb=np.asarray(Image.open(q).convert('RGB'))
    changed=int(np.any(aa!=bb,axis=-1).sum()) if aa.shape==bb.shape else None
    pixel[c['task'],c['stage']]={'stale_pixel_changes':changed,'stale_image_pixels':int(aa.shape[0]*aa.shape[1]),'stale_pixels_identical_verified':changed==0}
rows=[];reviews=[];source_rows=[];progress={}
recognition=re.compile(r'blank|missing|unavailable|cannot see|can.t see|no (?:current )?(?:image|screenshot|visual)|without (?:an? )?(?:image|screenshot)|not (?:visible|provided)|white (?:screen|page)|screen (?:is|appears) (?:completely )?white',re.I)
for model in ['qwen27','qwen9','glm']:
    folder=root/model
    if (folder/'status.json').exists():progress[model]=json.loads((folder/'status.json').read_text())
    results=json.loads((folder/'results.json').read_text()) if (folder/'results.json').exists() else []
    for r in results:
        if r['status']!='completed':continue
        r=view(r,folder,model)
        c=cases[r['id']];original=r.get('reused_from',r['id'])
        inputs=json.loads((folder/original/'input.json').read_text());counts=np.bincount(inputs['groups'],minlength=len(r['groups']))
        mass=np.array(r['mass']);first=np.array(r['first_query_mass']);h=float(mass[3]+mass[4]);i=float(mass[0]);n_image=int(counts[0]);n_h=int(counts[3]+counts[4])
        row={k:r[k] for k in ['id','task','app','stage','step','history','condition','input_tokens','output_tokens','eos_reached','truncated']}
        row.update(model=model,reused_from=r.get('reused_from',''),history_turns=r['history_turns'],image_tokens=n_image,history_tokens=n_h,image_mass=i,first_query_image_mass=float(first[0]),history_mass=h,history_prose_mass=float(mass[3]),history_action_mass=float(mass[4]),generated_prefix_mass=float(mass[7]),history_conditional_nonimage=h/(1-i) if i<1 else None,image_mass_per_token=i/n_image if n_image else None,history_mass_per_token=h/n_h if n_h else None,action=action(r['output']),semantic_label='unreviewed',**pixel[c['task'],c['stage']])
        row.update(audit_action(r['output']))
        row.update({k:r[k] for k in ['raw_output_tokens','raw_eos_reached','raw_truncated','single_reply_tokens','discarded_after_reply_tokens']})
        rows.append(row)
        if r['condition'] in ['blank_replace','silent_drop']:
            reviews.append({'model':model,'id':r['id'],'condition':r['condition'],'stage':r['stage'],'history':r['history'],'task':r['task'],'eos_reached':r['eos_reached'],'recognition_keyword_screen':bool(recognition.search(r['output'])),**audit_action(r['output']),'output':r['output'],'label':'unreviewed','review_key':hashlib.sha256((r['condition']+'\0'+r['output']).encode()).hexdigest()})
    folder=root/('source-'+model)
    if not folder.exists():continue
    if (folder/'status.json').exists():progress['source-'+model]=json.loads((folder/'status.json').read_text())
    results=json.loads((folder/'results.json').read_text()) if (folder/'results.json').exists() else []
    for r in results:
        if r['status']=='completed':
            r=view(r,folder,model)
            source_rows.append({k:v for k,v in r.items() if k not in ['output_ids','mass','first_query_mass'] }|{'model':model,**audit_action(r['output'])})

def writecsv(path,data):
    if not data:return
    keys=list(dict.fromkeys(k for row in data for k in row))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(data)
writecsv(out/'measurements.csv',rows)
(out/'measurements.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));(out/'semantic-review.json').write_text(json.dumps(reviews,ensure_ascii=False,indent=2));(out/'source-results.json').write_text(json.dumps(source_rows,ensure_ascii=False,indent=2));(out/'progress.json').write_text(json.dumps(progress,indent=2))
index={(r['model'],r['task'],r['stage'],r['history'],r['condition']):r for r in rows if r['eos_reached']}
task_ids=sorted({r['task'] for r in rows});rng=np.random.default_rng(42)
def interval(values):
    x=np.array(values,dtype=float);x=x[np.isfinite(x)]
    if len(x)==0:return None
    boot=x[rng.integers(0,len(x),(10000,len(x)))].mean(1)
    return {'tasks':len(x),'mean':float(x.mean()),'ci95_task_bootstrap':np.quantile(boot,[.025,.975]).tolist(),'task_differences':x.tolist()}
effects=[]
for model in ['qwen27','qwen9','glm']:
    for history in ['none','last2','full']:
        for later in ['middle','late']:
            for condition in ['current_control','blank_replace','silent_drop','stale_replace']:
                for metric in ['image_mass','first_query_image_mass','history_mass','history_conditional_nonimage']:
                    values=[]
                    for task in task_ids:
                        a=index.get((model,task,later,history,condition));b=index.get((model,task,'early',history,condition))
                        if a and b and a[metric] is not None and b[metric] is not None:values.append(a[metric]-b[metric])
                    effects.append(dict(model=model,factor='stage',comparison=later+'-early',history=history,condition=condition,metric=metric,estimate=interval(values)))
    for stage in ['early','middle','late']:
        for condition in ['current_control','blank_replace','silent_drop','stale_replace']:
            for longer,shorter in [('full','last2'),('last2','none')]:
                for metric in ['image_mass','first_query_image_mass','history_mass','history_conditional_nonimage']:
                    values=[]
                    for task in task_ids:
                        a=index.get((model,task,stage,longer,condition));b=index.get((model,task,stage,shorter,condition))
                        if a and b and a[metric] is not None and b[metric] is not None:values.append(a[metric]-b[metric])
                    effects.append(dict(model=model,factor='history',comparison=longer+'-'+shorter,stage=stage,condition=condition,metric=metric,estimate=interval(values)))
(out/'effects.json').write_text(json.dumps(effects,indent=2))
review_groups=collections.defaultdict(list)
for r in reviews:review_groups[(r['condition'],r['output'])].append({k:r[k] for k in ['model','id','stage','history','task','eos_reached']})
packets=[]
for i,((condition,text),members) in enumerate(review_groups.items()):
    packets.append({'group':i,'review_key':hashlib.sha256((condition+'\0'+text).encode()).hexdigest(),'condition':condition,'text':text,'members':members,'keyword_recognizes_failure':bool(recognition.search(text)),**audit_action(text),'label':'unreviewed'})
(out/'unique-review-packets.json').write_text(json.dumps(packets,ensure_ascii=False,indent=2))
summary={model:{'completed':sum(r['model']==model for r in rows),'eos':sum(r['model']==model and r['eos_reached'] for r in rows),'reused':sum(r['model']==model and bool(r['reused_from']) for r in rows)} for model in ['qwen27','qwen9','glm']}
(out/'counts.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({'counts':summary,'unique_review_outputs':len(packets),'unrecognized_candidate_outputs':sum(not p['keyword_recognizes_failure'] for p in packets),'source_completed':len(source_rows)}))
