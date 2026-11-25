import json
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent
saved=json.loads((r/'v3.9.7-scroll-failure-preservation.json').read_bytes())
live=json.loads((r/'v3.9.7-live-launch.json').read_bytes())
code='SAVED='+repr(saved)+'\nLIVE='+repr(live)+'\n'+r'''
import json,pathlib
for row in SAVED['rows']:
 p=pathlib.Path(row['source']);ev=[json.loads(x)for x in(p/'events.jsonl').read_text().splitlines()]
 print(json.dumps({'arm':row['arm'],'tail':[{'seq':e['seq'],'kind':e['kind'],'keys':list(e['data']),'data':{k:v for k,v in e['data'].items()if k in ['candidate','proposal','observation_id','reason','corrections','action']}}for e in ev[-35:] if e['kind']not in ['verifier_request','verifier_response','observation','actor_request']],'requests':[{'seq':e['seq'],'observation':e['data']['public']['observation_id'],'corrections':e['data']['corrections']}for e in ev if e['kind']=='actor_request'and e['data']['corrections']]}))
root=pathlib.Path(LIVE['root']);print(json.dumps({'live_alive':pathlib.Path('/proc',str(LIVE['pid'])).exists(),'status':(root/'status.json').read_text()if(root/'status.json').exists()else None,'log':pathlib.Path(LIVE['log']).read_text()[-1500:]}))
'''
print(remote(code,host='4090'))
