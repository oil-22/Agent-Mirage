"""Task-clustered exploratory analysis. No model inference or action execution."""
import collections,csv,hashlib,json,pathlib,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=pathlib.Path(__file__).parent; A=R/'analysis'; F=R/'figures';F.mkdir(exist_ok=True)
OLD=R.parent/'attention-audit-20261031'/'analysis'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
models=['qwen27','qwen9','glm']; names={'qwen27':'Qwen27 (deployment name)','qwen9':'Qwen3.5-9B','glm':'GLM-4.6V-Flash'}
stages=['early','middle','late']; histories=['none','last2','full'];conds=['current_control','blank_replace','silent_drop','stale_replace','buttons_only']
clabel=['Current','White','Missing','Previous','Control regions v2']
new=read(A/'measurements.json');old=read(OLD/'measurements.json');oq={(x['model'],x['id']):x for x in read(OLD/'query-measurements.json')}
for x in old:
 x.update({k:v for k,v in oq[x['model'],x['id']].items() if k in ['first_query_mass','action_query_mass','query_character_offsets_exact','action_query_count']})
 x['cohort']='old_main'
for x in old+new:
 for prefix,key in [('first','first_query_mass'),('action','action_query_mass')]:
  m=x.get(key)
  for field,value in [('image',None if m is None else m[0]),('history',None if m is None else m[3]+m[4])]:x[prefix+'_'+field]=value
  x[prefix+'_history_nonimage']=None if m is None else (m[3]+m[4])/(1-m[0]) if m[0]<1 else None
  for field in ['image','history']:
   v=x.get(prefix+'_'+field);n=x[field+'_tokens'];x[prefix+'_'+field+'_per_token']=v/n if v is not None and n else None
  if prefix=='action' and not x['eos_reached']:
   for k in list(x):
    if k.startswith('action_') and isinstance(x[k],(float,int)):x[k]=None
newmain=[x for x in new if x['cohort']=='main'];mask=[x for x in new if x['cohort']=='buttons'];source=[x for x in new if x['cohort']=='source']
datasets={'old9':old,'new10':newmain,'merged19':old+newmain,'new10_five':newmain+mask}
def est(vals):
 vals={k:float(v) for k,v in vals.items() if v is not None and np.isfinite(v)}
 if not vals:return None
 x=np.array(list(vals.values()));seed=int(hashlib.sha256(json.dumps(vals,sort_keys=True).encode()).hexdigest()[:8],16);rng=np.random.default_rng(seed)
 ci=np.quantile(x[rng.integers(0,len(x),(10000,len(x)))].mean(1),[.025,.975])
 return {'n_tasks':len(x),'mean':float(x.mean()),'ci95':ci.tolist(),'task_values':vals}
def valid(x,metric):return x.get(metric) is not None and (not metric.startswith('action') or x['eos_reached'])
def ag(rows,metric):
 groups=collections.defaultdict(list)
 for x in rows:
  if valid(x,metric):groups[x['task']].append(x[metric])
 return est({t:np.mean(v) for t,v in groups.items()})
summaries=[];effects=[]
metrics=['first_image','first_history','first_history_nonimage','first_image_per_token','first_history_per_token','action_image','action_history','action_history_nonimage']
for ds,rr in datasets.items():
 idx={(x['model'],x['task'],x['stage'],x['history'],x['condition']):x for x in rr};tasks=sorted({x['task'] for x in rr});conditions=conds if ds=='new10_five' else conds[:4]
 for model in models:
  for history in histories:
   for condition in conditions:
    for metric in metrics:
     for stage in stages:
      sel=[x for x in rr if (x['model'],x['history'],x['condition'],x['stage'])==(model,history,condition,stage)]
      summaries.append(dict(dataset=ds,model=model,history=history,condition=condition,stage=stage,metric=metric,estimate=ag(sel,metric)))
     for factor,comparison in [('stage','late-early'),('history','full-last2'),('history','last2-none'),('injection',condition+'-current_control'),('stage_by_injection','late-early')]:
      if factor=='injection' and condition=='current_control':continue
      if factor=='stage_by_injection' and condition=='current_control':continue
      if factor=='history' and history!='full':continue
      vals={}
      for task in tasks:
       diffs=[]
       if factor=='stage_by_injection':pairs=[(('late',history,condition),('late',history,'current_control')),(('early',history,condition),('early',history,'current_control'))]
       elif factor=='stage':pairs=[(('late',history,condition),('early',history,condition))]
       elif factor=='history':long,short=comparison.split('-');pairs=[((s,long,condition),(s,short,condition)) for s in stages]
       else:pairs=[((s,history,condition),(s,history,'current_control')) for s in stages]
       for aa,bb in pairs:
        a=idx.get((model,task,*aa));b=idx.get((model,task,*bb))
        if a and b and valid(a,metric) and valid(b,metric):diffs.append(a[metric]-b[metric])
       if len(diffs)==len(pairs):vals[task]=diffs[0]-diffs[1] if factor=='stage_by_injection' else np.mean(diffs)
      effects.append(dict(dataset=ds,model=model,history=history,condition=condition,metric=metric,factor=factor,comparison=comparison,estimate=est(vals)))
write(A/'paired-summary.json',{'summaries':summaries,'effects':effects})
labels=read(R/'semantic-labels.json');reviews=read(A/'semantic-review.json');oldreviews=read(OLD/'semantic-reviewed.json');sem=[]
ni={(x['model'],x['id']):x for x in newmain}
for x in reviews:
 label=labels.get(x['review_key']); row=ni[x['model'],x['id']];sem.append(dict(x,dataset='new10',semantic_review=label,eos_reached=row['eos_reached']))
for x in oldreviews:sem.append(dict(x,dataset='old9'))
write(A/'semantic-reviewed.json',sem)
semcounts=[]
for ds in ['new10','old9','merged19']:
 for model in models:
  for condition in ['blank_replace','silent_drop']:
   for history in histories:
    for stage in stages+['all']:
     rr=[x for x in sem if (ds=='merged19' or x['dataset']==ds) and x['model']==model and x['condition']==condition and x['history']==history and (stage=='all' or x['stage']==stage)]
     complete=[x for x in rr if x.get('eos_reached',True) and x['semantic_review'] is not None]
     vals=collections.defaultdict(list)
     for x in complete:vals[x['task']].append(x['semantic_review']['unsupported_current_state_assertion'] is True)
     semcounts.append(dict(dataset=ds,model=model,condition=condition,history=history,stage=stage,total=len(rr),reviewed=sum(x['semantic_review'] is not None for x in rr),censored=sum(not x.get('eos_reached',True) for x in rr),complete_reply_n=len(complete),unsupported=sum(x['semantic_review']['unsupported_current_state_assertion'] is True for x in complete),recognized=sum(x['semantic_review']['recognizes_invalid_observation'] is True for x in complete),ambiguous=sum(x['semantic_review']['unsupported_current_state_assertion'] is None for x in complete),unsupported_task_rate=est({t:np.mean(v) for t,v in vals.items()})))
write(A/'semantic-counts.json',semcounts)
semeffects=[]
for ds in ['new10','old9','merged19']:
 rr=[x for x in sem if (ds=='merged19' or x['dataset']==ds) and x.get('eos_reached',True) and x['semantic_review'] is not None]
 idx={(x['model'],x['task'],x['stage'],x['history'],x['condition']):x for x in rr}
 for m in models:
  for c in ['blank_replace','silent_drop']:
   for long,short in [('full','none'),('last2','none'),('full','last2')]:
    vals={}
    for t in sorted({x['task'] for x in rr}):
     diffs=[]
     for s in stages:
      a=idx.get((m,t,s,long,c));b=idx.get((m,t,s,short,c))
      if a and b:diffs.append(int(a['semantic_review']['unsupported_current_state_assertion'] is True)-int(b['semantic_review']['unsupported_current_state_assertion'] is True))
     if len(diffs)==3:vals[t]=np.mean(diffs)
    semeffects.append(dict(dataset=ds,model=m,condition=c,comparison=long+'-'+short,estimate=est(vals)))
write(A/'semantic-paired-effects.json',semeffects)
# Coordinate-string normalization is a sensitivity check only; preserve original schema.
def normalized(intent):
 if intent is None:return None
 if not intent.startswith('json:'):return intent
 v=json.loads(intent[5:])
 for k in ['x','y','coordinate','coordinates','position']:
  if k in v:
   def number(a):
    if isinstance(a,(int,float)) and not isinstance(a,bool):return float(a)
    if isinstance(a,str) and re.fullmatch(r'-?\d+(\.\d+)?',a):return float(a)
    if isinstance(a,list):return [number(q) for q in a]
    return a
   v[k]=number(v[k])
 return 'json:'+json.dumps(v,sort_keys=True)
ground={x['task']:x['label'] for x in read(R/'source-grounding-review.json')['cases']}
si={(x['model'],x['id']):x for x in source};comparisons=[]
for x in source:
 x['grounding']=ground[x['task']]
 x['action_claim_mass']=x['action_query_source_mass'][2] if x.get('action_query_source_mass') is not None and x['eos_reached'] else None
 x['action_claim_density']=x['action_claim_mass']/x['source_claim_tokens'] if x['action_claim_mass'] is not None else None
 n=x.get('source_prose_tokens',0)-x['source_claim_tokens'];v=x['action_query_source_mass'];other=(v[0]-v[2])/n if v is not None and n>0 else None
 x['action_claim_enrichment']=x['action_claim_density']/other if x['action_claim_density'] is not None and other is not None and other>0 else None
 x['first_claim_mass']=x['first_query_source_mass'][2]
 x['gap']=x['step']-2
 if x['condition']!='original':continue
 stem=x['id'][:-9];a=si.get((x['model'],stem+'-source_withdrawn'));b=si.get((x['model'],stem+'-meaning_preserving_sham'))
 if a is None or b is None:continue
 def changed(v,norm=False):
  if not x['eos_reached'] or not v['eos_reached']:return None
  q=x['action_intent'];z=v['action_intent']
  if q is None or z is None:return None
  return normalized(q)!=normalized(z) if norm else q!=z
 comparisons.append(dict(model=x['model'],task=x['task'],snapshot=stem,gap=x['gap'],grounding=ground[x['task']],original=x['action_intent'],withdrawn=a['action_intent'],sham=b['action_intent'],withdrawn_changed=changed(a),sham_changed=changed(b),withdrawn_changed_coordinate_normalized=changed(a,True),sham_changed_coordinate_normalized=changed(b,True),all_eos=all(t['eos_reached'] for t in [x,a,b]),schemas=[t['action_schema'] for t in [x,a,b]]))
ss=[]
for model in models:
 for group in ['all','contradicted_by_capture','supported_by_capture','visually_unresolved']:
  rr=[x for x in comparisons if x['model']==model and (group=='all' or x['grounding']==group)]
  both=[x for x in rr if x['withdrawn_changed_coordinate_normalized'] is not None and x['sham_changed_coordinate_normalized'] is not None]
  vals=collections.defaultdict(list)
  for x in both:vals[x['task']].append(int(x['withdrawn_changed_coordinate_normalized'])-int(x['sham_changed_coordinate_normalized']))
  ss.append(dict(model=model,grounding=group,n_tasks=len({x['task'] for x in rr}),snapshots=len(rr),jointly_comparable=len(both),withdrawn_changed=sum(x['withdrawn_changed_coordinate_normalized'] is True for x in both),sham_changed=sum(x['sham_changed_coordinate_normalized'] is True for x in both),withdrawn_only=sum(x['withdrawn_changed_coordinate_normalized'] is True and x['sham_changed_coordinate_normalized'] is False for x in both),task_paired_withdrawn_minus_sham=est({t:np.mean(v) for t,v in vals.items()})))
write(A/'source-comparisons.json',{'summary':ss,'snapshots':comparisons,'normalization':'Only numerical x/y/coordinate(s)/position JSON fields are normalized; raw action intents and schema violations remain. Missing/ambiguous/censored actions are excluded, never zero filled.'})
write(A/'source-enriched-results.json',source)
sourceagg=[]
for m in models:
 for g in ['all']+['contradicted_by_capture','supported_by_capture','visually_unresolved']:
  for c in ['original','source_withdrawn','meaning_preserving_sham']:
   for gap in [1,3,6]:
    rr=[x for x in source if x['model']==m and (g=='all' or x['grounding']==g) and x['condition']==c and x['gap']==gap]
    for metric in ['first_claim_mass','action_claim_mass','action_claim_density','action_claim_enrichment']:
     sourceagg.append(dict(model=m,grounding=g,condition=c,gap=gap,metric=metric,estimate=ag(rr,metric)))
write(A/'source-attention-summary.json',sourceagg)
def csvwrite(path,rr):
 if not rr:return
 with path.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
flat=[]
for e in effects:
 p=e['estimate']
 if p:
  for t,v in p['task_values'].items():flat.append({k:v for k,v in e.items() if k!='estimate'}|{'task':t,'paired_difference':v})
csvwrite(A/'per-task-effects.csv',flat)
csvwrite(A/'semantic-counts.csv',[{k:v for k,v in x.items() if k!='unsupported_task_rate'} for x in semcounts])
csvwrite(A/'source-action-comparisons.csv',[{k:json.dumps(v,ensure_ascii=False) if isinstance(v,list) else v for k,v in x.items()} for x in comparisons])
# Figures use independent model scales; no attention mass comparison across architectures.
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
def save(fig,name):
 for ext in ['png','pdf','svg']:fig.savefig(F/(name+'.'+ext),dpi=180,bbox_inches='tight')
 plt.close(fig)
agg={(x['dataset'],x['model'],x['history'],x['condition'],x['stage'],x['metric']):x['estimate'] for x in summaries}
colors=['#888888','#009e73','#d55e00']
fig,axes=plt.subplots(3,3,figsize=(12,9),sharey='row',layout='constrained')
for i,m in enumerate(models):
 for j,ds in enumerate(['old9','new10','merged19']):
  ax=axes[i,j]
  for h,c in zip(histories,colors):
   p=[agg.get((ds,m,h,'current_control',s,'first_image')) for s in stages]
   if not all(p):continue
   ax.plot(range(3),[x['mean']*100 for x in p],'o-',color=c,label={'none':'No history','last2':'Last 2','full':'Full'}[h]);ax.fill_between(range(3),[x['ci95'][0]*100 for x in p],[x['ci95'][1]*100 for x in p],alpha=.12,color=c)
  ax.set_xticks(range(3),['Early','Middle','Late']);ax.grid(alpha=.18)
  if i==0:ax.set_title(ds)
  if j==0:ax.set_ylabel(names[m]+'\nImage attention (%)')
axes[0,0].legend(fontsize=8);fig.suptitle('Current-image first query: original, expansion, and pooled tasks\nMeans and 95% task-bootstrap intervals; position = 10% / 50% / 90% decision index',fontsize=12);save(fig,'01_timing_replication')
fig,axes=plt.subplots(3,2,figsize=(12,9),layout='constrained')
for i,m in enumerate(models):
 for j,metric in enumerate(['first_image','first_history_nonimage']):
  ax=axes[i,j]
  for offset,h,c in zip([-.18,.18],['last2','full'],colors[1:]):
   p=[next((e['estimate'] for e in effects if (e['dataset'],e['model'],e['history'],e['condition'],e['factor'],e['metric'])==('new10_five',m,h,cond,'injection',metric)),None) for cond in conds[1:]]
   ok=[k for k,x in enumerate(p) if x]
   if ok:
    y=np.array([p[k]['mean']*100 for k in ok]);lo=np.array([p[k]['ci95'][0]*100 for k in ok]);hi=np.array([p[k]['ci95'][1]*100 for k in ok]);ax.errorbar(np.array(ok)+offset,y,yerr=[y-lo,hi-y],fmt='o',capsize=3,color=c,label=h)
  ax.axhline(0,color='gray',lw=.7);ax.set_xticks(range(4),clabel[1:],rotation=15);ax.set_ylabel(names[m]+'\nDelta (percentage points)');ax.grid(alpha=.18)
  if i==0:ax.set_title('Image mass' if j==0 else 'History share H / (1 - I)')
axes[0,0].legend();fig.suptitle('Four injection conditions minus the matched current-image control\nNew 10 tasks; three positions averaged within each task before bootstrap; mask version v2',fontsize=12);save(fig,'02_four_injections')
fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained')
for ax,m in zip(axes,models):
 for cond,style in [('blank_replace','-'),('silent_drop','--')]:
  for h,c in zip(['last2','full'],colors[1:]):
   pp=[next(x for x in semcounts if (x['dataset'],x['model'],x['condition'],x['history'],x['stage'])==('new10',m,cond,h,s)) for s in stages]
   ax.plot(range(3),[100*x['unsupported']/x['complete_reply_n'] if x['complete_reply_n'] else np.nan for x in pp],marker='o',ls=style,color=c,label=h+' / '+('white' if cond=='blank_replace' else 'missing'))
 ax.set_title(names[m]);ax.set_xticks(range(3),['Early','Middle','Late']);ax.set_ylim(-3,103);ax.grid(alpha=.18);ax.set_ylabel('Unsupported assertion / complete replies (%)')
axes[0].legend(fontsize=7);fig.suptitle('Assistant semantic review on new trajectories; descriptive, not Mirage incidence\nCurrent-state claims without the current image; conditional hypotheses excluded',fontsize=12);save(fig,'03_semantic_descriptive')
fig,axes=plt.subplots(3,2,figsize=(12,10),layout='constrained')
groups=['contradicted_by_capture','supported_by_capture','visually_unresolved'];gc=['#d55e00','#009e73','#777777']
for i,m in enumerate(models):
 for j,metric in enumerate(['action_claim_mass','action_claim_density']):
  ax=axes[i,j]
  for g,c in zip(groups,gc):
   points=[]
   for gap in [1,3,6]:
    rr=[x for x in source if x['model']==m and x['grounding']==g and x['condition']=='original' and x['gap']==gap];p=ag(rr,metric);points.append(p)
   if all(points):
    ax.plot([1,3,6],[p['mean']*100 for p in points],'o-',color=c,label=g.replace('_by_capture','').replace('visually_',''))
    ax.fill_between([1,3,6],[p['ci95'][0]*100 for p in points],[p['ci95'][1]*100 for p in points],color=c,alpha=.10,lw=0)
  ax.set_xticks([1,3,6]);ax.set_xlabel('Decisions since source statement');ax.grid(alpha=.18);ax.set_ylabel(names[m]+'\n'+('Claim mass (%)' if j==0 else 'Claim mass / token (%)'))
axes[0,0].legend(fontsize=8);fig.suptitle('Later action-block queries attending to the original exact source statement\n14 trajectories: 3 contradicted / 8 supported / 3 unresolved; task-bootstrap intervals',fontsize=12);save(fig,'04_source_attention')
diagnostics={'new_rows':len(new),'new_main_tasks':len({x['task'] for x in newmain}),'pooled_main_tasks':len({x['task'] for x in old+newmain}),'new_semantic_logical_outputs':len(reviews),'new_semantic_reviewed':sum(x['review_key'] in labels for x in reviews),'new_censored':[{k:x[k] for k in ['model','cohort','id','output_tokens']} for x in new if not x['eos_reached']],'source_snapshot_triplets':len(comparisons),'source_summary':ss,'missing_action_queries':dict(collections.Counter(x['cohort'] for x in new if x['action_query_mass'] is None))}
write(A/'analysis-diagnostics.json',diagnostics)
write(A/'metric-definitions.json',{'attention_scope':'Language standard-softmax full-attention layers and query heads, averaged equally; excludes Qwen linear mixers and vision encoder. Not a causal attribution.','first_query':'Final input query predicts first output token; no generated-prefix denominator effect.','action_query':'Queries predicting tokens in the sole parsed action block, excluding special tokens; censored replies excluded.','history':'Assistant historical prose plus action spans; H/(1-I) also reported to separate removal of image mass.','density':'Per-token mass removes group token-count scaling but does not remove positional/content confounding.','source_channels':['source_turn_prose','source_turn_action','exact_source_claim_subset_of_prose'],'bootstrap':'10000 task-cluster resamples; matched within task; average three positions within task for injection/history effects; exploratory without multiple-testing correction.','source_control':'Source sentence replaced by uncertainty withdrawal or meaning-preserving sham, equal native full-request token length. Shared archived Qwen27 histories and fixed future screenshots; no environment execution or recovery-success measurement.','truncation':'Prespecified generation limit; retain first query, exclude complete-reply/action analyses; no post-hoc repeated generation.'})
print(json.dumps({k:v for k,v in diagnostics.items() if k!='source_summary'},ensure_ascii=False))
