import collections,json,pathlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=pathlib.Path(__file__).parent;data=root/'analysis';fig=root/'figures';fig.mkdir(exist_ok=True)
results=json.loads((data/'source-results.json').read_text(encoding='utf-8'))
queries=json.loads((data/'source-query-measurements.json').read_text(encoding='utf-8'))
counts=json.loads((data/'source-token-counts.json').read_text(encoding='utf-8'))
index={(r['model'],r['id']):r for r in results};qi={(r['model'],r['id']):r for r in queries};ci={(r['model'],r['id']):r for r in counts}
joined=[]
for key,r in index.items():
    if key not in qi or key not in ci:continue
    q=qi[key];c=ci[key]
    row=dict(r,**{k:v for k,v in q.items() if k not in r},**{k:v for k,v in c.items() if k not in r and k not in q})
    row['action_query_source_mass']=q['action_query_source_mass'];row['action_query_count']=q['action_query_count']
    row['source_claim_mass_per_token']=q['source_mass'][2]/c['source_claim_tokens']
    row['action_source_claim_mass_per_token']=q['action_query_source_mass'][2]/c['source_claim_tokens'] if q['action_query_source_mass'] else None
    joined.append(row)
jj={(r['model'],r['id']):r for r in joined};comparisons=[]
for r in joined:
    if not r['id'].endswith('-original'):continue
    stem=r['id'][:-9];c=jj.get((r['model'],stem+'-state_corrected'));s=jj.get((r['model'],stem+'-meaning_preserving_sham'))
    if not c or not s:continue
    def changed(other):
        a=r.get('action_intent');b=other.get('action_intent')
        return a!=b if a is not None and b is not None else None
    comparisons.append({'model':r['model'],'snapshot':stem,'app':r['app'],'step':r['step'],'original_action':r['action_intent'],'corrected_action':c['action_intent'],'sham_action':s['action_intent'],'corrected_action_changed':changed(c),'sham_action_changed':changed(s),'corrected_output_exactly_same':r['output']==c['output'],'sham_output_exactly_same':r['output']==s['output'],'all_single_reply_eos':all(x['eos_reached'] for x in [r,c,s]),'source_claim_tokens':[x['source_claim_tokens'] for x in [r,c,s]],'action_query_claim_mass':[x['action_query_source_mass'][2] if x['action_query_source_mass'] else None for x in [r,c,s]]})
summary=[]
for model in ['qwen9','glm']:
    for app in ['WebMall','VisualWebArena']:
        rr=[r for r in comparisons if r['model']==model and r['app']==app]
        if not rr:continue
        summary.append({'model':model,'app':app,'snapshots':len(rr),'correction_comparable':sum(r['corrected_action_changed'] is not None for r in rr),'correction_changed':sum(r['corrected_action_changed'] is True for r in rr),'sham_comparable':sum(r['sham_action_changed'] is not None for r in rr),'sham_changed':sum(r['sham_action_changed'] is True for r in rr),'correction_only_changed':sum(r['corrected_action_changed'] is True and r['sham_action_changed'] is False for r in rr)})
(data/'source-comparisons.json').write_text(json.dumps({'summary':summary,'snapshots':comparisons},ensure_ascii=False,indent=2),encoding='utf-8')
(data/'source-enriched-results.json').write_text(json.dumps(joined,ensure_ascii=False,indent=2),encoding='utf-8')
(data/'metric-definitions.json').write_text(json.dumps({'attention_scope':'Standard softmax language full-attention layers only; excludes Qwen linear mixers, vision encoder and full causal attribution','query_index':'Index of the output token being predicted, not the token after it; first query is the final input position','source_channels':['source_turn_prose','source_turn_action','exact_source_claim'],'source_overlap':'Exact claim is a subset of source prose; do not sum all three channels','query_averaging':'Equal weight over selected queries, recorded full-attention layers and query heads','bootstrap_unit':'Independent task UUID for main timing/history comparisons, not output token/head/layer','first_query_truncation':'First query remains complete if later reply is truncated; whole-reply and action summaries exclude incomplete replies in canonical paired analysis','source_sampling':'Two selected original Qwen27 episodes, replayed across later correlated snapshots for new models; no population effect estimate'},indent=2),encoding='utf-8')
if joined:
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
    figure,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    for mi,model in enumerate(['qwen9','glm']):
        for ai,app in enumerate(['WebMall','VisualWebArena']):
            ax=axes[mi,ai]
            for variant,label,color,style in [('original','Original','#333333','-'),('state_corrected','Source state corrected','#0072b2','--'),('meaning_preserving_sham','Meaning-preserving edit','#d55e00',':')]:
                selected=sorted([r for r in joined if r['model']==model and r['app']==app and r['condition']==variant and r['action_query_source_mass'] is not None],key=lambda r:r['step'])
                if selected:ax.plot([r['step'] for r in selected],[r['action_query_source_mass'][2]*100 for r in selected],marker='o',ms=4,lw=1.4,label=label,color=color,ls=style)
            ax.set_title(('Qwen3.5-9B' if model=='qwen9' else 'GLM-4.6V-Flash')+' — '+app);ax.set_xlabel('Subsequent archived decision step');ax.set_ylabel('Attention to exact source claim (%)');ax.set_yscale('log');ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8)
    draft='INCOMPLETE SNAPSHOT — ' if len(joined)!=66 else ''
    figure.suptitle(draft+'Queries predicting the proposed action read the initial source claim\nTwo selected Qwen27 episodes replayed offline; independent subplot scales; no task rollout',fontsize=12)
    for ext in ['png','pdf','svg']:figure.savefig(fig/('03_source_claim_action_attention.'+ext),dpi=180,bbox_inches='tight')
    plt.close(figure)
print(json.dumps({'joined':len(joined),'summary':summary}))
