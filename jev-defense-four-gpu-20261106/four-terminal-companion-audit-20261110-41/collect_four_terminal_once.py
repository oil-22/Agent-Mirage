"""Consolidate immutable source labels, then read terminal event chains only."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
R37 = BASE / 'remaining29-full-history-gui-20261110-37'
sys.path.insert(0, str(R37))
spec = importlib.util.spec_from_file_location('four_terminal_readonly_transport', R37 / 'orchestrate.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
remote, save, sha = transport.remote, transport.save, transport.sha


class Sources:
    def __init__(self):
        self.seals = {}
        self.rows = {}

    def verify_seal(self, folder, expected=None):
        folder = folder.resolve()
        actual = sha(folder / 'seal.json')
        if expected is not None:
            assert actual == expected, str(folder)
        if str(folder) not in self.seals:
            for name, value in json.loads((folder / 'seal.json').read_bytes()).items():
                path = folder / name
                assert path.resolve().is_relative_to(folder)
                assert sha(path) == value, str(path)
            self.seals[str(folder)] = actual
        assert self.seals[str(folder)] == actual
        return actual

    def add(self, label, packetpath, authority, attempt, seq, primary, ordinal=None):
        self.verify_seal(Path(authority['path']).parent, authority['seal_sha256'])
        assert sha(Path(authority['path'])) == authority['sha256']
        packetpath = Path(packetpath)
        collection = packetpath.parent.parent
        self.verify_seal(collection)
        assert sha(packetpath) == label['packet_sha256']
        packet = json.loads(packetpath.read_bytes())
        event = packet['candidate_event_sha256']
        assert event == label['candidate_event_sha256']
        assert event not in self.rows, 'Duplicate original candidate: ' + event
        text = packet['candidate']
        assert hashlib.sha256(text.encode()).hexdigest() == packet['candidate_text_sha256'] == label['candidate_text_sha256']
        body = packet['actual_actor_request']
        canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        assert hashlib.sha256(canonical).hexdigest() == packet['actor_request_body_sha256']
        assert packet['checker_labels_current_acceptance_execution_scoring_private_delivery_excluded']
        run = Path(attempt).parent.name
        pure = label.get('pure_native_WAIT_excluded', label.get('pure_native_WAIT', False))
        uncertainties = label.get('unresolved_semantic_subclaims', label.get('unresolved_subclaims', label.get('uncertain_subclaims', [])))
        assert type(pure) is bool and primary in [True, False, None]
        self.rows[event] = dict(candidate_event_sha256=event, candidate_id=label['id'],
            source_attempt=attempt, source_candidate_seq=seq, original_ordinal=ordinal,
            run_id=run, source_packet=str(packetpath), source_packet_sha256=sha(packetpath),
            actor_request_body_sha256=packet['actor_request_body_sha256'],
            candidate_text=text, candidate_text_sha256=packet['candidate_text_sha256'],
            observation_id=packet['observation_id'], source_review=authority,
            original_label=label, primary_semantic_label=primary, pure_native_WAIT_excluded=pure,
            unresolved_subclaims=uncertainties,
            native_action_error=label.get('native_action_error', label.get('native_target_or_direction_error', label.get('native_action_target_or_direction_error'))))


def collect_sources():
    sources = Sources()
    p = BASE / 'prefill-scheduled-full-history-gui-20261109-32/first38-consolidated-source-ledger-created.json'
    pointer = json.loads(p.read_bytes())
    folder = Path(pointer['root'])
    sources.verify_seal(folder, pointer['seal_sha256'])
    assert sha(folder / 'ledger.json') == pointer['ledger_sha256']
    ledger = json.loads((folder / 'ledger.json').read_bytes())
    assert ledger['original_distinct_candidate_count'] == 38
    for row in ledger['rows']:
        label = row['original_label']
        primary = True if row['definite_semantic_Mirage'] else None if row['unresolved_semantic_subclaims'] else False
        sources.add(label, row['source_packet_path'], row['review_authority'], row['source_attempt'],
                    row['source_candidate_event_seq'], primary, row['original_unique_actor_candidate_ordinal'])
    for namespace in ['remaining-full-history-gui-20261110-33', 'remaining29-full-history-gui-20261110-37']:
        root = BASE / namespace
        pointers = sorted(p for p in root.glob('source-review-*-created.json')
                          if re.fullmatch(r'source-review-[0-9]+-created.json', p.name))
        for pointerpath in pointers:
            pointer = json.loads(pointerpath.read_bytes())
            folder = Path(pointer['review'])
            sources.verify_seal(folder, pointer['seal_sha256'])
            assert sha(folder / 'review.json') == pointer['review_sha256']
            review = json.loads((folder / 'review.json').read_bytes())
            assert review['independent_current_checker_execution_score_join_not_performed']
            authority = dict(path=str(folder / 'review.json'), sha256=pointer['review_sha256'],
                             seal_sha256=pointer['seal_sha256'])
            for label in review['rows']:
                packetpath = Path(label['public_source_packet'])
                sources.verify_seal(packetpath.parent.parent)
                index = json.loads((packetpath.parent.parent / 'PRIVATE-source-index.json').read_bytes())
                private = next(row for row in index if row['id'] == label['id'])
                assert private['candidate_text_sha256'] == label['candidate_text_sha256']
                assert private['actor_request_body_sha256'] == label['actor_request_body_sha256']
                sources.add(label, packetpath, authority, private['attempt'], private['candidate_seq'],
                            label['candidate_semantic_mirage'])
    assert len(sources.rows) == 84
    counts = Counter(row['run_id'] for row in sources.rows.values())
    assert counts == {'fullhistory23-T000-clean-noaux': 38, 'fullhistory23-T000-clean-aux': 15,
                     'fullhistory23-T000-stale_replace-aux': 16, 'fullhistory23-T000-stale_replace-noaux': 15}
    return sources


REMOTE_SOURCE = r'''
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def h(value):return hashlib.sha256(value).hexdigest()
kept={'candidate','carryover_replay_candidate','decision_accepted','carryover_replay_decision_accepted',
 'action_executed','verdict','decision_blocked','accepted_actor_history_retained',
 'cached_pending_decision_source_binding','cached_pending_decision_accepted_for_first_execution',
 'pending17_original_pipeline_returned','private_delivery_ledger'}
assert os.getuid()==1015
root=Path('/data/researcher/jev-defense-four-gpu-20261106').resolve();byattempt={};joined=[]
for target in ROWS:byattempt.setdefault(target['source_attempt'],[]).append(target)
chains=[]
for name,targets in byattempt.items():
 a=Path(name).resolve();assert a.is_relative_to(root)and a.parent.parent.parent.name=='batch'
 path=a/'events.jsonl';before=path.stat();events=[];previous='0'*64;count=0;full=hashlib.sha256()
 with path.open('rb')as stream:
  for line in stream:
   assert line.endswith(b'\n');full.update(line)
   event=json.loads(line);value=dict(event);signature=value.pop('sha256')
   assert value['seq']==count and value['previous']==previous and h(canonical(value))==signature
   count+=1;previous=signature
   if event['kind']in kept:events.append(event)
 after=path.stat();assert(before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino)
 snapshot={'path':str(path),'count':count,'head':previous,'full_file_sha256':full.hexdigest(),
  'bytes':after.st_size,'mtime_ns':after.st_mtime_ns,'inode':after.st_ino,'stable_during_read':True}
 terminals=[]
 for terminalname in ['complete.json','technical-failure.json','failure.json','paused.json']:
  p=a/terminalname
  if p.is_file():
   value=json.loads(p.read_bytes());value.pop('calls',None)
   terminals.append({'path':str(p),'sha256':sha(p),'value':value})
 assert terminals,'Only original terminal/paused namespaces may be inspected'
 for target in targets:
  candidates=[e for e in events if e['kind']=='candidate'and e['seq']==target['source_candidate_seq']]
  assert len(candidates)==1;candidate=candidates[0]
  assert candidate['sha256']==target['candidate_event_sha256']and candidate['data']['text']==target['candidate_text']
  assert h(candidate['data']['text'].encode())==target['candidate_text_sha256']
  stop=next((e['seq']for e in events if e['kind']=='candidate'and e['seq']>candidate['seq']),count)
  window=[e for e in events if candidate['seq']<e['seq']<stop]
  accepted=[e for e in window if e['kind']=='decision_accepted'];executed=[e for e in window if e['kind']=='action_executed']
  assert len(accepted)<=1 and len(executed)<=1
  for accepted_event in accepted:assert accepted_event['data']['candidate']==candidate['data']['text']
  for execution in executed:
   assert accepted and execution['data']['observation_id']==accepted[0]['data']['observation_id']
   assert execution['data']['proposal']==accepted[0]['data']['proposal']
   feedback=json.loads(execution['data']['feedback']);assert feedback['execution_returned']and not feedback['error']
  deliveries=[e for e in events if e['kind']=='private_delivery_ledger'and e['seq']<candidate['seq']]
  joined.append({'candidate_event_sha256':candidate['sha256'],'attempt':name,'candidate_event':candidate,
   'original_namespace_accepted':bool(accepted),'original_namespace_executed':bool(executed),
   'accepted_events':accepted,'executed_events':executed,
   'detector_verdicts_not_gold':[e for e in window if e['kind']=='verdict'],
   'candidate_window_blocks':[e for e in window if e['kind']=='decision_blocked'],
   'PRIVATE_delivery_evaluation_only':deliveries[-1]if deliveries else None,
   'snapshot':snapshot})
 chains.append({'attempt':name,'snapshot':snapshot,'terminals':terminals,'retained_events':events,
  'actual_environment_execution_events':sum(e['kind']=='action_executed'for e in events)})
print(json.dumps({'time':time.time(),'uid':os.getuid(),'chains':chains,'rows':joined,
 'remote_read_only':True,'new_model_GUI_capture_action_scorer_paid_calls':0},ensure_ascii=False))
'''


def main():
    assert not (HERE / 'four-terminal-collected.json').exists()
    sources = collect_sources()
    out = HERE / ('four-terminal-source-and-events-' + str(time.time_ns()))
    out.mkdir()
    save(out / 'source-labels-before-downstream-join.json', dict(time=time.time(), rows=list(sources.rows.values()),
        verified_original_collection_and_review_seals=sources.seals, original_labels_unchanged=True,
        label_source='reuse of previously sealed source-first reviews; not a new independent reviewer',
        PRIVATE_index_used_only_after_verifying_sealed_source_labels=True, no_new_semantic_labels=True))
    (out / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(out / 'pre-join-source-seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    targets = [{k: row[k] for k in ['source_attempt', 'source_candidate_seq', 'candidate_event_sha256',
                'candidate_text', 'candidate_text_sha256']} for row in sources.rows.values()]
    code = 'ROWS=' + repr(targets) + '\n' + transport.COMMON + REMOTE_SOURCE
    compile(code, 'four-terminal-event-chain-readonly', 'exec')
    output, operation = remote('4090', code, 'four-terminal-companion-all84-original-event-chains-readonly', timeout=55)
    data = json.loads(output)
    assert len(data['rows']) == 84 and len(data['chains']) == 6
    save(out / 'actual-terminal-event-evidence.json', dict(data, operation=str(operation),
        source_inventory_sha256=sha(out / 'source-labels-before-downstream-join.json')))
    save(out / 'seal.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
    pointer = dict(root=str(out), event_evidence_sha256=sha(out / 'actual-terminal-event-evidence.json'),
        source_inventory_sha256=sha(out / 'source-labels-before-downstream-join.json'),
        seal_sha256=sha(out / 'seal.json'), candidates=84, actual_attempts=6,
        actual_original_environment_executions=sum(c['actual_environment_execution_events'] for c in data['chains']))
    save(HERE / 'four-terminal-collected.json', pointer)
    print(json.dumps(pointer))


if __name__ == '__main__':
    main()
