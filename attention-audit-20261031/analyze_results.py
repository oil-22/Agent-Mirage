"""Task-paired exploratory summaries and standalone scientific figures."""
import collections,csv,json,pathlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=pathlib.Path(__file__).parent;data=root/'analysis';fig=root/'figures';fig.mkdir(exist_ok=True)
rows=json.loads((data/'measurements.json').read_text(encoding='utf-8'))
queries=json.loads((data/'query-measurements.json').read_text(encoding='utf-8'))
qindex={(r['model'],r['id']):r for r in queries}
models=['qwen27','qwen9','glm'];names={'qwen27':'Qwen3.8-27B (deployment name)','qwen9':'Qwen3.5-9B','glm':'GLM-4.6V-Flash'}
stages=['early','middle','late'];conditions=['current_control','blank_replace','silent_drop','stale_replace']
labels={'current_control':'Current image','blank_replace':'White image','silent_drop':'Missing image','stale_replace':'Previous image'}
for r in rows:
    q=qindex.get((r['model'],r['id']))
    if not q:continue
    for prefix,key in [('first','first_query_mass'),('action','action_query_mass')]:
        mass=q.get(key)
        if mass is None:continue
        image=float(mass[0]);history=float(mass[3]+mass[4])
        r[prefix+'_image']=image
        r[prefix+'_history']=history
        r[prefix+'_history_nonimage']=history/(1-image) if image<1 else None
        r[prefix+'_image_per_token']=image/r['image_tokens'] if r['image_tokens'] else None
        r[prefix+'_history_per_token']=history/r['history_tokens'] if r['history_tokens'] else None
index={(r['model'],r['task'],r['stage'],r['history'],r['condition']):r for r in rows}
tasks=sorted({r['task'] for r in rows});rng=np.random.default_rng(20261031)
def estimate(values):
    x=np.asarray(values,dtype=float);x=x[np.isfinite(x)]
    if not len(x):return None
    boot=x[rng.integers(0,len(x),(10000,len(x)))].mean(1)
    return {'n_tasks':len(x),'mean':float(x.mean()),'ci95':np.quantile(boot,[.025,.975]).tolist(),'task_values':x.tolist()}
metrics=['first_image','first_history','first_history_nonimage','first_image_per_token','first_history_per_token','action_image','action_history','action_history_nonimage','image_mass','history_mass']
aggregates=[];effects=[]
def get(model,task,stage,history,condition,metric):
    row=index.get((model,task,stage,history,condition),{})
    if row and not row['eos_reached'] and not metric.startswith('first_'):return None
    return row.get(metric)
for model in models:
    for history in ['none','last2','full']:
        for condition in conditions:
            for metric in metrics:
                for stage in stages:
                    values=[get(model,t,stage,history,condition,metric) for t in tasks]
                    aggregates.append(dict(model=model,history=history,condition=condition,stage=stage,metric=metric,estimate=estimate([v for v in values if v is not None])))
                for later in ['middle','late']:
                    pairs=[(get(model,t,later,history,condition,metric),get(model,t,'early',history,condition,metric)) for t in tasks]
                    values=[a-b for a,b in pairs if a is not None and b is not None]
                    effects.append(dict(model=model,factor='stage',comparison=later+'-early',history=history,condition=condition,metric=metric,estimate=estimate(values)))
            if condition=='current_control':continue
            for metric in metrics:
                for stage in stages:
                    pairs=[(get(model,t,stage,history,condition,metric),get(model,t,stage,history,'current_control',metric)) for t in tasks]
                    effects.append(dict(model=model,factor='injection',comparison=condition+'-current_control',stage=stage,history=history,metric=metric,estimate=estimate([a-b for a,b in pairs if a is not None and b is not None])))
                for later in ['middle','late']:
                    diffs=[]
                    for t in tasks:
                        a,b,c,d=[get(model,t,s,history,cond,metric) for s,cond in [(later,condition),(later,'current_control'),('early',condition),('early','current_control')]]
                        if all(v is not None for v in [a,b,c,d]):diffs.append((a-b)-(c-d))
                    effects.append(dict(model=model,factor='stage_by_injection',comparison=later+'-early',history=history,condition=condition,metric=metric,estimate=estimate(diffs)))
    for stage in stages:
        for condition in conditions:
            for metric in metrics:
                for longer,shorter in [('full','last2'),('last2','none')]:
                    pairs=[(get(model,t,stage,longer,condition,metric),get(model,t,stage,shorter,condition,metric)) for t in tasks]
                    effects.append(dict(model=model,factor='history_window',comparison=longer+'-'+shorter,stage=stage,condition=condition,metric=metric,estimate=estimate([a-b for a,b in pairs if a is not None and b is not None])))
(data/'paired-summary.json').write_text(json.dumps({'aggregates':aggregates,'effects':effects},indent=2),encoding='utf-8')

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180,'pdf.fonttype':42,'svg.fonttype':'none'})
agg={(a['model'],a['stage'],a['history'],a['condition'],a['metric']):a['estimate'] for a in aggregates}
def plot_line(ax,model,history,condition,metric,color):
    points=[agg.get((model,s,history,condition,metric)) for s in stages]
    if not all(p is not None for p in points):return
    y=np.array([p['mean'] for p in points])*100;lo=np.array([p['ci95'][0] for p in points])*100;hi=np.array([p['ci95'][1] for p in points])*100
    ax.plot(range(3),y,'o-',label={'none':'No history','last2':'Last 2 turns','full':'Full history'}[history],color=color,lw=1.6,ms=4)
    ax.fill_between(range(3),lo,hi,color=color,alpha=.13,linewidth=0)
def save(figure,name):
    for ext in ['png','pdf','svg']:figure.savefig(fig/(name+'.'+ext),bbox_inches='tight')
    plt.close(figure)
colors={'none':'#888888','last2':'#1b9e77','full':'#d95f02'}
figure,axes=plt.subplots(3,3,figsize=(12,9),sharex=True,sharey='row',layout='constrained')
for mi,model in enumerate(models):
    for ci,condition in enumerate(['current_control','blank_replace','stale_replace']):
        ax=axes[mi,ci]
        for history in ['none','last2','full']:plot_line(ax,model,history,condition,'first_image',colors[history])
        ax.set_xticks(range(3),['Early','Middle','Late']);ax.grid(alpha=.2)
        if mi==0:ax.set_title(labels[condition])
        if ci==0:ax.set_ylabel(names[model]+'\nImage attention (%)')
axes[0,0].legend(fontsize=8)
draft='INCOMPLETE SNAPSHOT — ' if len(rows)!=972 else ''
figure.suptitle(draft+'First-query attention to the delivered image\nTask means and 95% task-bootstrap intervals; temporal positions in archived trajectories',fontsize=13)
save(figure,'01_timing_image_attention')

figure,axes=plt.subplots(3,4,figsize=(14,9),sharex=True,sharey='row',layout='constrained')
for mi,model in enumerate(models):
    for ci,condition in enumerate(conditions):
        ax=axes[mi,ci]
        for history in ['last2','full']:plot_line(ax,model,history,condition,'first_history_nonimage',colors[history])
        ax.set_xticks(range(3),['Early','Middle','Late']);ax.grid(alpha=.2)
        if mi==0:ax.set_title(labels[condition])
        if ci==0:ax.set_ylabel(names[model]+'\nH / (1 - I) (%)')
axes[0,0].legend(fontsize=8)
figure.suptitle(draft+'First-query history share conditional on non-image attention\nH = history prose + actions; I = delivered image; no-history mass is structurally zero',fontsize=13)
save(figure,'02_timing_history_attention')

labelpath=root/'semantic-labels.json';reviewpath=data/'semantic-review.json'
if labelpath.exists() and reviewpath.exists():
    reviews=json.loads(reviewpath.read_text(encoding='utf-8'));reviewlabels=json.loads(labelpath.read_text(encoding='utf-8'));counts=collections.defaultdict(collections.Counter)
    for r in reviews:
        label=reviewlabels.get(r['review_key'])
        key=(r['model'],r['stage'],r['history'],r['condition'])
        counts[key]['outputs']+=1
        if label is None:continue
        counts[key]['reviewed']+=1
        if label['unsupported_current_state_assertion'] is True:counts[key]['unsupported_current_state']+=1
        if label['unsupported_current_state_assertion'] is None:counts[key]['uncertain_state_claim']+=1
        if label['recognizes_invalid_observation'] is True:
            counts[key]['recognizes_invalid']+=1
            if r['action_kind'] not in ['wait','done','fail','unknown']:counts[key]['recognizes_but_proposes_nonterminal']+=1
        if r['action_kind'] in ['done','fail']:counts[key]['proposes_termination']+=1
        if r['matches_main_action_schema']:counts[key]['matches_main_action_schema']+=1
    (data/'semantic-counts.json').write_text(json.dumps([dict(model=k[0],stage=k[1],history=k[2],condition=k[3],**v) for k,v in counts.items()],indent=2),encoding='utf-8')
    joined=[dict(r,semantic_review=reviewlabels.get(r['review_key'])) for r in reviews]
    (data/'semantic-reviewed.json').write_text(json.dumps(joined,ensure_ascii=False,indent=2),encoding='utf-8')
    numeric={(r['model'],r['id']):r for r in rows};flat=[]
    for r in joined:
        m=numeric[(r['model'],r['id'])];label=r['semantic_review'] or {}
        flat.append({**{k:m.get(k) for k in ['model','id','task','stage','history','condition','eos_reached','reused_from','input_tokens','output_tokens','first_image','first_history','first_history_nonimage','action_image','action_history','action_history_nonimage','action_intent','matches_main_action_schema']},**{k:label.get(k) for k in ['recognizes_invalid_observation','unsupported_current_state_assertion','explicit_state_assumption']},'review_reason':label.get('reason'),'review_key':r['review_key']})
    with (data/'semantic-attention.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)

diagnostics={'logical_rows':len(rows),'task_count':len(tasks),'query_rows':len(queries),'stale_snapshots_pixel_identical':len({(r['task'],r['stage']) for r in rows if r['stale_pixels_identical_verified']}),'query_offset_unavailable':sum(not q['query_character_offsets_exact'] for q in queries),'action_query_missing_or_ambiguous':sum(q['action_query_mass'] is None for q in queries),'output_action_schemas':{m:dict(collections.Counter(r['action_schema'] for r in queries if r['model']==m)) for m in models}}
(data/'analysis-diagnostics.json').write_text(json.dumps(diagnostics,indent=2),encoding='utf-8')
print(json.dumps(diagnostics))
