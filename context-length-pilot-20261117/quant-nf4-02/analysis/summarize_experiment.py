"""Summarize preselected diagnostic outputs without fitting a desired trend."""
from pathlib import Path
import json,re,collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

P=Path(__file__).resolve().parent
natural=json.loads((P/'preliminary-summary.json').read_text())
fig,ax=plt.subplots(figsize=(7.5,4.3))
rs=[r for r in natural if r['n']]
xs=[r['bin'] for r in rs];ys=[100*r['non_wait_actions']/r['n'] for r in rs]
ax.plot(xs,ys,'o-',color='#4C72B0',linewidth=2)
for x,y,r in zip(xs,ys,rs):
    ax.annotate(f"{r['non_wait_actions']}/{r['n']} ({y:g}%)",(x,y),xytext=(0,10),textcoords='offset points',ha='center',fontsize=10)
ax.set_xscale('log');ax.set_xticks([2000,5000,10000,20000,40000],['2k','5k','10k','20k','40k'])
ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
ax.set_xlim(1600,54000);ax.set_ylim(0,100);ax.text(40000,47,'No samples',ha='center',color='#777777')
ax.set_xlabel('Normal input tokens before intervention');ax.set_ylabel('Non-wait action rate (%)')
ax.set_title('Natural-trajectory pilot: descriptive behavior only');ax.grid(axis='y',alpha=.2)
fig.text(.5,.015,'NOT an Agent-Mirage rate. 3 tasks; visual dependency requires audit.',ha='center',fontsize=9,color='#555555')
fig.tight_layout(rect=[0,.04,1,1]);fig.savefig(P/'natural-behavior-proxy.png',dpi=180);fig.savefig(P/'natural-behavior-proxy.pdf');plt.close(fig)

if not(P/'controlled-results.json').exists():raise SystemExit('Natural figure saved; controlled outputs not finished yet.')
rows=[]
def action(text):
    blocks=re.findall(r'<action>\s*(.*?)\s*</action>',text,re.S)
    return json.loads(blocks[0]) if len(blocks)==1 else None
for d in json.loads((P/'controlled-results.json').read_text()):
    m=d['meta'];rows.append(dict(task=m['task'],normal_input_tokens=m['normal_input_tokens'],condition=m['condition'],
        retained_turns=m['retained_turns'],text=d['text'],action=action(d['text']),actual_input_tokens=d['input_tokens'],
        provenance='new controlled history-retention replay',receipt=d['receipt']))
for task,b in [('T000',5000),('T017',10000),('T089',20000)]:
    cp=P/'evidence'/task/'clean'/f'checkpoint-{b}';info=json.loads((cp/'checkpoint.json').read_text())
    turns=len(json.loads((cp/'prefix-actions.json').read_text()))
    normal=json.loads((cp.parent/f"{info['step']:03}-response.json").read_text())
    for c,f in [('clean_control',None)]+[(c,cp/(c+'-decision.json'))for c in ['silent_drop','blank_replace','stale_replace','buttons_only']]:
        d=json.loads(f.read_text()) if f else normal
        rows.append(dict(task=task,normal_input_tokens=info['normal_input']['input_tokens'],condition=c,
            retained_turns=turns,text=d['text'],action=action(d['text']),actual_input_tokens=d['input_tokens'],
            provenance='existing full-history output reused; not a new repeat',receipt=d['receipt']))
rows.sort(key=lambda r:(r['task'],r['normal_input_tokens'],r['condition']))
assert len(rows)==45 and len({(r['task'],r['normal_input_tokens'],r['condition'])for r in rows})==45
for r in rows:
    r['non_wait_action']=r['action'] is not None and r['action']['type']!='wait'
    if r['condition']=='clean_control':r['audit']='normal control; task accuracy is separate'
    elif r['condition']=='stale_replace':r['audit']='candidate Mirage: old menu/result state treated as current; new history-retention outputs are not executed, while reused full-history execution is tracked separately'
    elif r['action']['type']=='wait':r['audit']='wait/re-observation, not dependent task action'
    elif r['condition']=='buttons_only':r['audit']='recognizes loading and scrolls for observation; not classified as unrecognized evidence failure'
    else:r['audit']='uncertain current visual dependency; do not treat all non-wait actions as Mirage'
(P/'controlled-comparison.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
summary=[]
for task in ['T000','T017','T089']:
    for length in sorted({r['normal_input_tokens']for r in rows if r['task']==task}):
        group=[r for r in rows if r['task']==task and r['normal_input_tokens']==length]
        summary.append(dict(task=task,normal_input_tokens=length,actions={r['condition']:r['action']['type']for r in group},
            non_wait_injected=sum(r['non_wait_action']for r in group if r['condition']!='clean_control')))
(P/'controlled-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')

fig,axes=plt.subplots(1,3,figsize=(11,4),sharey=True)
conditions=['silent_drop','blank_replace','stale_replace','buttons_only']
names=['Missing','Blank','Stale','Controls only']
for ax,task in zip(axes,['T000','T017','T089']):
    groups=[r for r in summary if r['task']==task]
    values=[[int(g['actions'][c]!='wait')for g in groups]for c in conditions]
    ax.imshow(values,aspect='auto',vmin=0,vmax=1,cmap='Blues')
    for i,c in enumerate(conditions):
        for j,g in enumerate(groups):ax.text(j,i,g['actions'][c],ha='center',va='center',color='white' if values[i][j] else 'black',fontsize=9)
    ax.set_xticks(range(len(groups)),[f"{g['normal_input_tokens']/1000:.2f}k"for g in groups],rotation=35)
    ax.set_yticks(range(4),names);ax.set_title(task+' fixed decision point');ax.set_xlabel('Retained-context input tokens')
fig.suptitle('Same current evidence, different retained histories',fontsize=13)
fig.text(.5,.015,'Cells show proposed actions, NOT a binary Mirage label. Earlier content and positions change with retention.',ha='center',fontsize=9)
fig.tight_layout(rect=[0,.04,1,.94]);fig.savefig(P/'controlled-history-actions.png',dpi=180);fig.savefig(P/'controlled-history-actions.pdf');plt.close(fig)
print(json.dumps(summary,indent=2))
