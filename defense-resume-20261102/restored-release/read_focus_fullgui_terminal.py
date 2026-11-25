"""Compact source-bound analysis packet, no new inference or labels from detector flags."""
import json
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'focus-history-fullgui-development'
r=Path(json.loads((PREP/'terminal-current.json').read_bytes())['directory']);a=next(r.glob('runs/*/attempt-*'))
events=[json.loads(s)for s in(a/'events.jsonl').read_text(encoding='utf-8').splitlines()]
rows=[]
for e in events:
 d=e['data'];k=e['kind']
 if k=='candidate':rows.append({'seq':e['seq'],'kind':k,'observation':d['observation_id'],'text':d['text']})
 if k=='verdict':
  v=d['verdict'];rows.append({'seq':e['seq'],'kind':k,'claims':[{'text':x['text'],'kind':x['kind'],'status':x['status'],'reason':x['reason'],'evidence':x['evidence']}for x in v['claims']],'action':v['action'],'pure_wait':v['pure_wait']})
 if k in ['current_only_execution_history_scope','historical_event_source_scope','native_direction_consistency']and d.get('reject'):rows.append({'seq':e['seq'],'kind':k,'data':d})
 if k in ['action_executed','focus_crosscheck','history_report_crosscheck','verifier_format_failure','decision_blocked']:rows.append({'seq':e['seq'],'kind':k,'data':d})
out=PREP/'terminal-analysis-packet.json';assert not out.exists();out.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
compact=[]
for row in rows:
 if row['kind']=='verdict':compact.append({'seq':row['seq'],'kind':row['kind'],'claims':[{'text':x['text'],'status':x['status'],'reason':x['reason']}for x in row['claims']],'action':row['action']['status']})
 elif row['kind']=='action_executed':compact.append({'seq':row['seq'],'kind':row['kind'],'data':row['data'].get('proposal')})
 else:compact.append(row)
print(json.dumps({'attempt':str(a),'rows':compact},ensure_ascii=True))
