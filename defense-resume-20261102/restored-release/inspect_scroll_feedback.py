"""Compact real process/results inspection, immutable development evidence export."""
import json
from pathlib import Path
from remote import remote

r=Path(__file__).resolve().parent
receipt=next(r/n for n in ['v3.9.7-sourcefix-launch.json','v3.9.7-staging-retry.json','v3.9.7-staging.json']if(r/n).exists())
launch=json.loads(receipt.read_bytes())
code=r'''
import pathlib,json,time,hashlib
root=pathlib.Path(LAUNCH['root']);proc=pathlib.Path('/proc')/str(LAUNCH['pid'])
summary=json.loads((root/'summary.json').read_bytes())if(root/'summary.json').exists()else None
rows=[json.loads(p.read_bytes())for p in sorted(root.glob('*-result.json'))]
record={'time':time.time(),'launch':LAUNCH,'actual_process':{'uid':proc.stat().st_uid,'cmd':(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode()}if proc.exists()else None,'state':json.loads((root/'status.json').read_bytes())if(root/'status.json').exists()else None,'results':rows,'summary':summary,'summary_sha256':hashlib.sha256((root/'summary.json').read_bytes()).hexdigest()if summary else None,'log_tail':pathlib.Path(LAUNCH['log']).read_text(errors='replace')[-2400:]}
print(json.dumps(record))
'''
record=json.loads(remote('LAUNCH='+repr(launch)+'\n'+code,host='4090',timeout=45))
(r/'v3.9.7-development-progress.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'alive':bool(record['actual_process']),'state':record['state'],'summary_passed':record['summary']['passed']if record['summary']else None,'results':[{'case':row['case'],'passed':row['passed'],'candidate':row.get('candidate'),'action_status':row.get('verdict',{}).get('action',{}).get('status'),'traceback':row.get('traceback')}for row in record['results']],'log_tail':record['log_tail']},ensure_ascii=True))
