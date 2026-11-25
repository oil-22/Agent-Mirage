"""Join execution and detector metadata only after immutable source labels exist."""
import argparse
import json
from pathlib import Path
import time

from remote_control import HERE, ROOT4090, remote, save, sha


SOURCE = r'''
from pathlib import Path
import hashlib,json
def h(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
r=Path(ROOT).resolve();cache={};out=[]
for row in ROWS:
 a=Path(row['attempt']).resolve();assert a.parent.parent==r/'batch/runs'
 if str(a)not in cache:
  raw=(a/'events.jsonl').read_bytes();raw=raw[:raw.rfind(b'\n')+1];previous='0'*64;events=[]
  for line in raw.splitlines():
   e=json.loads(line);sig=e.pop('sha256')
   assert e['seq']==len(events)and e['previous']==previous and h(canonical(e))==sig
   e['sha256']=sig;events.append(e);previous=sig
  cache[str(a)]={'events':events,'snapshot':{'count':len(events),'head':previous,'complete_prefix_sha256':h(raw)}}
 events=cache[str(a)]['events'];candidate=events[row['candidate_seq']]
 assert candidate['kind']=='candidate'and candidate['sha256']==row['candidate_event_sha256']
 assert h(candidate['data']['text'].encode())==row['candidate_text_sha256']
 stop=next((e['seq']for e in events[candidate['seq']+1:]if e['kind']=='candidate'),len(events))
 window=events[candidate['seq']+1:stop];accepted=[];executed=[];verdicts=[];blocks=[];unbound=[]
 for e in window:
  if e['kind']=='decision_accepted':
   assert e['data']['candidate']==candidate['data']['text']
   accepted.append(e)
  if e['kind']=='action_executed':
   assert accepted and e['data']['observation_id']==accepted[-1]['data']['observation_id']
   assert e['data']['proposal']==accepted[-1]['data']['proposal'];executed.append(e)
  if e['kind']=='verdict':verdicts.append(e)
  if e['kind']=='decision_blocked':
   (unbound if accepted else blocks).append(e)
 deliveries=[e for e in events[:candidate['seq']]if e['kind']=='private_delivery_ledger']
 delivery=deliveries[-1]if deliveries else None
 terminal=[]
 for name in ['complete.json','technical-failure.json','failure.json','paused.json']:
  p=a/name
  if p.is_file():
   value=json.loads(p.read_bytes());value.pop('calls',None)
   terminal.append({'file':name,'sha256':h(p.read_bytes()),'value':value})
 out.append({'id':row['id'],'candidate_event_sha256':candidate['sha256'],'snapshot':cache[str(a)]['snapshot'],
  'run':a.parent.name,'candidate_seq':candidate['seq'],'accepted':bool(accepted),'executed':bool(executed),
  'accepted_events':accepted,'executed_events':executed,'detector_verdict_events_not_gold':verdicts,
  'candidate_decision_block_events':blocks,'later_unbound_boundary_block_events':unbound,
  'PRIVATE_delivery_provenance_not_checker_input':delivery,'terminal_at_snapshot':terminal})
print(json.dumps({'read_only':True,'new_model_GUI_scorer_calls':0,'rows':out},ensure_ascii=False))
'''


def main(reviews):
    targets = []
    authorities = []
    labels = {}
    for folder in reviews:
        folder = folder.resolve()
        for name, expected in json.loads((folder / 'seal.json').read_bytes()).items():
            assert sha(folder / name) == expected
        review = json.loads((folder / 'review.json').read_bytes())
        collection = Path(review['collection'])
        assert sha(collection / 'collection.json') == review['collection_sha256']
        source_index = {row['id']: row for row in json.loads((collection / 'PRIVATE-source-index.json').read_bytes())}
        for label in review['rows']:
            assert label['id'] not in labels
            packet_path = collection / label['id'] / 'packet.json'
            assert sha(packet_path) == label['packet_sha256']
            packet = json.loads(packet_path.read_bytes())
            assert packet['candidate_event_sha256'] == label['candidate_event_sha256']
            row = dict(source_index[label['id']], candidate_event_sha256=label['candidate_event_sha256'])
            targets.append(row)
            labels[label['id']] = label
        authorities.append({'path': str(folder / 'review.json'), 'sha256': sha(folder / 'review.json')})
    prefix = 'ROOT=' + repr(ROOT4090) + '\nROWS=' + repr(targets) + '\n'
    output, operation = remote('4090', prefix + SOURCE, 'post-seal-candidate-execution-detector-join', timeout=55)
    joined = json.loads(output)
    for row in joined['rows']:
        row['sealed_source_label'] = labels[row['id']]
    out = HERE / ('post-review-join-' + str(time.time_ns()))
    out.mkdir()
    joined.update(schema='full-history-GUI23-post-source-seal-join-v1', time=time.time(),
         source_reviews=authorities, remote_operation=str(operation),
         selected_reviewed_candidates_only=True, full_trajectory_label_or_effect_established=False,
         all_source_labels_sealed_before_this_join=True, goal='active')
    save(out / 'join.json', joined)
    save(out / 'seal.json', {'join.json': sha(out / 'join.json')})
    print(json.dumps({'join': str(out), 'join_sha256': sha(out / 'join.json'),
          'reviewed_candidates': len(joined['rows']), 'accepted': sum(row['accepted'] for row in joined['rows']),
          'executed': sum(row['executed'] for row in joined['rows']),
          'definite_semantic_errors': sum(labels[row['id']]['definite_semantic_Mirage'] is True for row in joined['rows']),
          'source_labels_unchanged': True, 'trajectory_any_Mirage': None}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--review', type=Path, action='append', required=True)
    main(parser.parse_args().review)
