"""Verify the early native inputs before interpreting the bounded diagnostic."""
import json
from pathlib import Path
from remote import remote
here=Path(__file__).resolve().parent;formal=json.loads((here/'v3.8.3-vwa-resume.json').read_text());baseline=json.loads((here/'v3.8.3-baseline-diagnostic-launch.json').read_text())
code=r'''import pathlib,json,copy,hashlib,time
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def load(root,run):
 attempt=sorted((pathlib.Path(root)/'runs'/run).glob('attempt-*'))[-1];raw=(attempt/'events.jsonl').read_bytes();events=[json.loads(l)for l in raw.splitlines()]
 return attempt,raw,events
fp,fr,fe=load(FORMAL,'vwa--classifieds_112--blank_replace--joint');bp,br,be=load(BASELINE,'vwa--classifieds_112--blank_replace--baseline')
fq=[e['data']['public']['messages']for e in fe if e['kind']=='actor_request'];bq=[e['data']['public']['messages']for e in be if e['kind']=='actor_request'];assert len(fq)>=2 and len(bq)>=2
def without_image_bytes(messages):
 result=copy.deepcopy(messages)
 for m in result:
  if isinstance(m['content'],list):
   for b in m['content']:
    if b['type']=='image_url':b['image_url']={'url':'ACTUAL_IMAGE_BYTES_OMITTED_FOR_TEXT_COMPARISON'}
 return result
fl=next(e['data']for e in fe if e['kind']=='private_delivery_ledger'and e['data']['fired']);bl=next(e['data']for e in be if e['kind']=='private_delivery_ledger'and e['data']['fired'])
fc=[e['data']['text']for e in fe if e['kind']=='candidate'];bc=[e['data']['text']for e in be if e['kind']=='candidate'];assert len(bc)>=2
print(json.dumps({'time':time.time(),'formal_attempt':str(fp),'baseline_diagnostic_attempt':str(bp),'formal_snapshot_sha256':hashlib.sha256(fr).hexdigest(),'baseline_snapshot_sha256':hashlib.sha256(br).hexdigest(),'same_release':RELEASES_EQUAL,'same_initial_full_actor_messages':fq[0]==bq[0],'initial_messages_sha256':hashlib.sha256(canonical(fq[0])).hexdigest(),'same_first_candidate':fc[0]==bc[0],'same_next_actor_text_and_history':without_image_bytes(fq[1])==without_image_bytes(bq[1]),'same_underlying_postclick_capture':fl['capture_sha256']==bl['capture_sha256'],'same_blank_replacement':fl['delivered_sha256']==bl['delivered_sha256'],'baseline_blank_reply':bc[1],'defense_recaptured_reply':fc[1],'baseline_parsed_action':json.loads(bc[1].split('<action>')[1].split('</action>')[0]),'semantic_mirage':None,'scope':'Four-step diagnostic compared with early formal trajectory. Same native initial messages/history/capture checks; not whole-task or rate evidence.'}))
'''.replace('FORMAL',repr(formal['root'])).replace('BASELINE',repr(baseline['root'])).replace('RELEASES_EQUAL',repr(formal['release']==baseline['release']))
data=json.loads(remote(code,host='4090'));(here/'v3.8.3-early-input-comparison.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(data))
