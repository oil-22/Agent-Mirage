"""Read completed formal outcomes and terminal evidence, with immutable hashes."""
import base64,json,time
from pathlib import Path
from remote import remote
here=Path(__file__).resolve().parent
receipt_path=next(here/n for n in ['v3.9.6-vwa-resume.json','v3.9.5-site-recovery-resume.json','v3.8.3-vwa-resume.json']if(here/n).exists())
receipt=json.loads(receipt_path.read_text())
code=r'''
import pathlib,json,hashlib,time,base64
root=pathlib.Path(ROOT);rows=[];images={}
for marker in sorted((root/'runs').glob('*/complete.json')):
 pointer=json.loads(marker.read_text());attempt=pathlib.Path(pointer['attempt']);p=attempt/'complete.json'
 assert hashlib.sha256(p.read_bytes()).hexdigest()==pointer['sha256']
 result=json.loads(p.read_text());events=[json.loads(l)for l in(attempt/'events.jsonl').read_text().splitlines()]
 kinds={'candidate','screen_result','decision_blocked','completion_crosscheck'}
 chosen=[e for e in events if e['kind']in kinds]
 final=attempt/'final-actually-captured.png'
 name=marker.parent.name+'-final.png'
 if final.exists():images[name]=base64.b64encode(final.read_bytes()).decode()
 rows.append({'run_id':marker.parent.name,'attempt':str(attempt),'result':{k:v for k,v in result.items()if k!='calls'},
  'summary_sha256':pointer['sha256'],'events_sha256':hashlib.sha256((attempt/'events.jsonl').read_bytes()).hexdigest(),
  'terminal_events':chosen[-8:],'final_image':name if final.exists()else None})
print(json.dumps({'time':time.time(),'status':json.loads((root/'status.json').read_text()),'rows':rows,'images':images}))
'''.replace('ROOT',repr(receipt['root']))
data=json.loads(remote(code,host='4090'))
dest=here/'outcome-reviews'/str(time.time_ns());dest.mkdir(parents=True)
for name,value in data.pop('images').items():(dest/name).write_bytes(base64.b64decode(value))
(dest/'outcomes.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'saved':str(dest),'status':data['status'],
 'rows':[{'run_id':r['run_id'],'result':r['result'],'terminal_events':[e for e in r['terminal_events']if e['kind']in {'decision_blocked','screen_result'}][-3:]}for r in data['rows']]},ensure_ascii=False))
