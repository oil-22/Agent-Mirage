"""Display the latest local foreground snapshot without dumping old stream output."""
import json,time
from pathlib import Path
value=json.loads(Path(__file__).with_name('v3-foreground-watch-latest.json').read_text(encoding='utf-8'))
done=value.get('done')
print(json.dumps({'snapshot_age':round(time.time()-value['time']),'phase':value['batch_phase'],'event_age':value['event_age'],
    'counts':value['counts'],'candidate':value['candidate'].get('text'),
    'done':{k:done.get(k)for k in ['outcome','official_reward','scoring_status','actor_calls','verifier_calls','environment_actions','blocked_reason']}if done else None,
    'technical_failure':value['technical_failure']}))
