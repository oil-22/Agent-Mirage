"""Inspect live identities and source-bound event chains, export new real evidence."""
import base64
import hashlib
import json
import time
from pathlib import Path
from control import HERE, manifest, remote, save


def main():
    m = manifest(); results = {}; operations = {}
    for host in ['3090', '4090']:
        code = 'P=' + repr(m['package' + host]) + '\nOUT=' + repr(m['output3090']) + '\nHOST=' + repr(host) + '\n' + r'''
import base64,hashlib,json,os,time
from pathlib import Path
p=Path(P);out=Path(OUT)
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def ident(saved):
 proc=Path('/proc',str(saved['pid']))
 if not proc.exists():return {'saved':saved,'current':None,'same_live':False}
 s=(proc/'stat').read_text().rsplit(')',1)[1].split();v={'pid':saved['pid'],'uid':proc.stat().st_uid,'command':(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
 return {'saved':saved,'current':v,'same_live':s[0]not in['Z','X']and all(v[k]==saved[k]for k in ['uid','command','start_ticks'])}
def chain(path):
 raw=path.read_bytes();complete=raw[:raw.rfind(b'\n')+1];rows=[json.loads(b)for b in complete.splitlines()];head='0'*64
 for i,row in enumerate(rows):
  value={k:v for k,v in row.items()if k!='sha256'}
  assert row['seq']==i and row['previous']==head and row['sha256']==hashlib.sha256(canonical(value)).hexdigest(),str(path)
  head=row['sha256']
 return rows,{'events':len(rows),'head':head,'complete_prefix_bytes':len(complete),'prefix_sha256':hashlib.sha256(complete).hexdigest(),'source':str(path)}
value={'time':time.time(),'host':HOST,'processes':[]}
if HOST=='3090':
 for q in [out/'launcher-process.json',out/'primary/process.json',p/'flash/service/process.json']:
  if q.exists():value['processes'].append(ident(json.loads(q.read_bytes())))
 value['status']=json.loads((out/'primary/status.json').read_bytes())
 requests=[]
 for q in (out/'primary/requests').iterdir():
  if not(q/'response.json').exists()or not(q/'seal.json').exists():continue
  wire=json.loads((q/'wire-request.bin').read_bytes());reply=json.loads((q/'response.json').read_bytes());generated=json.loads((q/'actual-generation.json').read_bytes())
  requests.append({'path':str(q),'request_id':reply['request_id'],'run_id':wire['run_id'],'decision':wire['decision_index'],'text':reply['text'],'input_tokens':generated['input_tokens'],'output_tokens':generated['output_tokens'],'natural_EOS':generated['natural_EOS'],'seal_sha256':sha(q/'seal.json')})
 value['actor_replies']=sorted(requests,key=lambda r:r['path'])
 flashes=[]
 for q in (p/'flash/service/requests').iterdir():
  if(q/'response.json').exists()and(q/'seal.json').exists():
   reply=json.loads((q/'response.json').read_bytes());audit=json.loads((q/'audit.json').read_bytes())
   flashes.append({**reply,'path':str(q),'probabilities':audit['probabilities'],'seal_sha256':sha(q/'seal.json')})
 value['Flash_replies']=flashes
 if(out/'primary/journal/events.jsonl').exists():_,value['primary_journal']=chain(out/'primary/journal/events.jsonl')
 if(p/'flash/service/journal/events.jsonl').exists():_,value['Flash_journal']=chain(p/'flash/service/journal/events.jsonl')
 value['exit']=json.loads((out/'exit.json').read_bytes())if(out/'exit.json').exists()else None
else:
 for q in [p/'control/process.json',p/'control/runner-process.json']:
  if q.exists():value['processes'].append(ident(json.loads(q.read_bytes())))
 value['status']=json.loads((p/'batch/status.json').read_bytes())if(p/'batch/status.json').exists()else None
 value['attempts']=[];value['exported_images']={}
 for attempt in sorted((p/'batch/runs').glob('*/attempt-*')):
  rows,proof=chain(attempt/'controller/events.jsonl')
  attacks=[r for r in rows if r['kind']=='PRIVATE_delivery_ledger'and r['data']['injected']]
  nos=[r for r in rows if r['kind']=='gate_decision'and r['data']['decision']=='NO']
  chosen=[r for r in rows if r['kind']in ['PRIVATE_delivery_ledger','gate_decision','recapture_requested','capture','main_image_forwarded','actual_actor_request','actual_actor_reply','native_environment_action','native_proposal_dispatched','native_actor_or_parser_failure','native_execution_failure']]
  terminal=json.loads((attempt/'terminal.json').read_bytes())if(attempt/'terminal.json').exists()else None
  value['attempts'].append({'attempt':str(attempt),'run_id':attempt.parent.name,'chain':proof,'attacks':attacks,'NO_events':nos,'events':chosen,'terminal':terminal})
  if attacks:
   attack=attacks[0];seq=attack['seq']
   related=[r for r in chosen if seq<=r['seq']<=seq+30]
   hashes={attack['data']['captured_sha256'],attack['data']['delivered_sha256']}
   hashes.update(r['data']['image_sha256']for r in related if r['kind']in ['capture','main_image_forwarded'])
   for h in hashes:
    candidates=[attempt/'controller'/(h+'.png'),attempt/(str(attack['data']['step']).zfill(3)+'-actually-captured.png')]
    image=next((q for q in candidates if q.exists()and sha(q)==h),None)
    if image is not None and h not in value['exported_images']:
     value['exported_images'][h]={'source':str(image),'png_base64':base64.b64encode(image.read_bytes()).decode()}
print(json.dumps(value))
'''
        raw, op = remote(host, code, 'new-injection-source-bound-progress-' + host, timeout=40)
        results[host] = json.loads(raw); operations[host] = str(op)
    root = HERE / ('live-progress-' + str(time.time_ns())); root.mkdir()
    images = results['4090'].pop('exported_images', {})
    (root / 'images').mkdir()
    exported = {}
    for h, record in images.items():
        data = base64.b64decode(record['png_base64'], validate=True)
        assert hashlib.sha256(data).hexdigest() == h
        (root / 'images' / (h + '.png')).write_bytes(data)
        exported[h] = {'source': record['source'], 'file': 'images/' + h + '.png'}
    save(root / 'result.json', {'operations': operations, 'result': results, 'images': exported})
    members = {str(q.relative_to(root)).replace('\\', '/'): hashlib.sha256(q.read_bytes()).hexdigest()
               for q in root.rglob('*') if q.is_file()}
    save(root / 'seal.json', members)
    latest = {'root': str(root), 'seal_sha256': hashlib.sha256((root / 'seal.json').read_bytes()).hexdigest()}
    (HERE / 'live-progress-current.json').write_text(json.dumps(latest, indent=2), encoding='utf8')
    flashes = results['3090']['Flash_replies']
    print(json.dumps({'receipt': str(root), 'main_status': results['3090']['status'],
        'GUI_status': results['4090']['status'], 'actor_replies': len(results['3090']['actor_replies']),
        'Flash_YES': sum(r['decision']=='YES'for r in flashes), 'Flash_NO': sum(r['decision']=='NO'for r in flashes),
        'live_processes': {h:[{'pid':v['saved']['pid'],'same_live':v['same_live']}for v in r['processes']]for h,r in results.items()},
        'injections': [{'run_id':a['run_id'],'step':[x['data']['step']for x in a['attacks']],'NO':len(a['NO_events'])}for a in results['4090']['attempts']],
        'exported_images': len(images)}))


if __name__ == '__main__': main()
