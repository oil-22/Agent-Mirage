"""Preserve a finished logical GUI track without stopping the remaining queue.

Original large journals/tensors/traces remain in place, fully hashed remotely.
Only selected original terminal bytes and final capture are copied locally.
This is a post-source-review provenance collection, not a semantic adjudicator.
"""
import argparse
import base64
import json
from pathlib import Path
import re
import time

from orchestrate import HERE, PACKAGE, OUTPUT, GUIROOT, remote, save, sha


GUI_CODE = r'''
from pathlib import Path
import base64,hashlib,json,os,time
def sha(p):
 value=hashlib.sha256()
 with Path(p).open('rb')as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):value.update(chunk)
 return value.hexdigest()
scope={};exec(HELPER,scope)
events_from_bytes=scope['events_from_bytes'];unreviewed_candidates=scope['unreviewed_candidates']
run_end_binding=scope['run_end_binding'];check_terminal_counters=scope['check_terminal_counters']
r=Path(ROOT).resolve();assert os.getuid()==1015 and sha(r/'manifest.json')==EXPECTED
run=r/'batch/runs'/RUN
attempts=list(run.glob('attempt-*'))
assert len(attempts)==1,'Frozen original run must have exactly one attempt here'
a=attempts[0];assert a.is_dir() and not a.is_symlink()
events,chain=events_from_bytes((a/'events.jsonl').read_bytes(),live_prefix=True)
unreviewed=unreviewed_candidates(events,set(REVIEWED))
if unreviewed:
 print(json.dumps({'ready':False,'reason':'unreviewed_candidates_before_terminal_join','candidate_event_hashes':unreviewed,'new_model_GUI_scorer_calls':0}));raise SystemExit(0)
names=[name for name in ['complete.json','technical-failure.json','failure.json','paused.json','cleanup-failure.json'] if(a/name).is_file()]
if not names:
 print(json.dumps({'ready':False,'reason':'same_logical_GUI_track_has_no_terminal','new_model_GUI_scorer_calls':0}));raise SystemExit(0)
assert len(names)==1,'Ambiguous terminal originals must not be selected between'
name=names[0];terminal_raw=(a/name).read_bytes();terminal_sha=hashlib.sha256(terminal_raw).hexdigest()
binding=run_end_binding(events,RUN,terminal_sha)
if binding is None:
 print(json.dumps({'ready':False,'reason':'terminal_exists_but_original_run_end_not_acknowledged','terminal_name':name,'new_model_GUI_scorer_calls':0}));raise SystemExit(0)
events,chain=events_from_bytes((a/'events.jsonl').read_bytes())
assert not unreviewed_candidates(events,set(REVIEWED))
assert run_end_binding(events,RUN,terminal_sha)==binding
terminal=json.loads(terminal_raw)
if name in ['complete.json','technical-failure.json','paused.json']:
 check_terminal_counters(terminal,PLANNED,CARRYOVER)
if name=='complete.json':
 pointer=json.loads((run/'complete.json').read_bytes())
 assert pointer['attempt']==str(a) and pointer['sha256']==terminal_sha and binding['body']['status']=='completed'
else:assert binding['body']['status']!='completed'
inventory={};stats={}
def stat(p):
 s=p.stat();return {'bytes':s.st_size,'mtime_ns':s.st_mtime_ns,'inode':s.st_ino,'uid':s.st_uid}
for p in sorted(a.rglob('*')):
 assert not p.is_symlink()
 if not p.is_file():continue
 rel=p.relative_to(a).as_posix();before=stat(p);inventory[rel]=sha(p);assert stat(p)==before;stats[rel]=before
assert inventory[name]==terminal_sha
for event in events:
 if event['kind']!='observation':continue
 for im in event['data']['artifacts']:
  assert Path(im['file']).name==im['file'] and inventory[im['file']]==im['sha256']
exports={}
for rel in [name,'final-actually-captured.png','native-restoration-receipt.json']:
 if rel not in inventory:continue
 raw=(a/rel).read_bytes();assert hashlib.sha256(raw).hexdigest()==inventory[rel]
 exports[rel]=base64.b64encode(raw).decode()
for rel,before in stats.items():assert stat(a/rel)==before
print(json.dumps({'ready':True,'time':time.time(),'attempt':str(a),'terminal_name':name,'terminal_sha256':terminal_sha,
 'terminal':terminal,'run_end':binding,'GUI_chain':chain,'original_file_SHA256':inventory,'original_file_stats':stats,
 'original_files_all_retained_in_place':True,'all_original_GUI_files_full_SHA_verified':True,
 'exported_originals':exports,'original_candidate_event_hashes':[e['sha256']for e in events if e['kind']=='candidate'],
 'source_gate_scope':'New-root candidate events only; carried prefix requires its separate original authorities',
 'original_carryover_prefix_semantic_coverage_not_proven_here':True,
 'original_private_config_pickle_trace_are_hash_provenance_only':True,'new_model_GUI_scorer_paid_calls':0}))
'''


SERVICE_CODE = r'''
from pathlib import Path
import hashlib,json,os,time
def sha(p):
 value=hashlib.sha256()
 with Path(p).open('rb')as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):value.update(chunk)
 return value.hexdigest()
scope={};exec(HELPER,scope)
events_from_bytes=scope['events_from_bytes'];canonical=scope['canonical']
r=Path(ROOT).resolve();package=r.parent/'runtime-preparation'/r.name
assert os.getuid()==1033 and sha(package/'manifest.json')==EXPECTED
events,chain=events_from_bytes((r/'worker/journal/events.jsonl').read_bytes(),live_prefix=True)
ends=[e for e in events if e['kind']=='GUI_run_end'and e['data']['trajectory_id']==RUN]
assert len(ends)==1 and ends[0]['data']==GUI_END_BODY
initial=CARRYOVER['initial_transport_counts']if RUN==CARRYOVER['original_track']else {'actor':0,'judge':0,'evidence':0}
counts=dict(initial);selected=[]
request_events={e['data']['request']:e for e in events if e['kind']=='model_request'and e['data']['trajectory_id']==RUN}
sealed={e['data']['request']:e for e in events if e['kind']=='model_reply_sealed'}
def stat(p):
 s=p.stat();return {'bytes':s.st_size,'mtime_ns':s.st_mtime_ns,'inode':s.st_ino,'uid':s.st_uid}
for rel,event in sorted(request_events.items()):
 p=r/'worker'/rel;assert p.parent==r/'worker/requests'and not p.is_symlink()
 raw=(p/'external-wire.json').read_bytes();body=json.loads(raw)
 assert body['trajectory_id']==RUN and body['request_id']not in CARRYOVER['disallowed_prior_request_ids']
 op=event['data']['operation'];counts[op]+=1
 assert body['attempt_index']==event['data']['attempt_index']==counts[op]
 assert body['decision_index']==event['data']['decision_index'] and 1<=body['decision_index']<=50
 assert hashlib.sha256(canonical(body['payload'])).hexdigest()==event['data']['payload_sha256']
 assert rel in sealed and sha(p/'seal.json')==sealed[rel]['data']['seal_sha256']
 seal=json.loads((p/'seal.json').read_bytes());inventory={};stats={}
 for f in sorted(p.iterdir()):
  assert f.is_file()and not f.is_symlink();before=stat(f);inventory[f.name]=sha(f);assert stat(f)==before;stats[f.name]=before
 for name,expected in seal.items():assert Path(name).name==name and inventory[name]==expected
 reply=json.loads((p/'response.json').read_bytes())if(p/'response.json').exists()else None
 if reply is not None:
  assert reply['request_id']==body['request_id'] and reply['external_wire_sha256']==hashlib.sha256(raw).hexdigest()
 for name,before in stats.items():assert stat(p/name)==before
 selected.append({'request':p.name,'operation':op,'attempt_index':body['attempt_index'],
  'decision_index':body['decision_index'],'request_id':body['request_id'],
  'seal_sha256':inventory['seal.json'],'original_file_SHA256':inventory,'original_file_stats':stats})
assert all(counts[k]<=v for k,v in {'actor':70,'judge':140,'evidence':60}.items())
assert COUNTERS is None or counts==COUNTERS
assert PLANNED['observer_enabled']or counts['evidence']==0
print(json.dumps({'time':time.time(),'run_id':RUN,'run_end_event':ends[0],'service_chain_committed_prefix':chain,
 'all_selected_original_request_files_full_SHA_verified':True,'selected_requests':selected,
 'original_transport_counts_including_carried_technical_expenditure':counts,'initial_carried_counts':initial,
 'original_files_all_retained_in_place':True,'new_model_GUI_scorer_paid_calls':0}))
'''


def verified_reviews():
    hashes, authorities = set(), []
    for pointer in sorted(HERE.glob('source-review-*-created.json')):
        if not re.fullmatch(r'source-review-\d+-created\.json',pointer.name):
            continue
        authority=json.loads(pointer.read_bytes());folder=Path(authority['review'])
        assert folder.parent==HERE and sha(folder/'review.json')==authority['review_sha256']
        assert sha(folder/'seal.json')==authority['seal_sha256']
        for name,expected in json.loads((folder/'seal.json').read_bytes()).items():
            assert Path(name).name==name and sha(folder/name)==expected
        for row in json.loads((folder/'review.json').read_bytes())['rows']:
            full=row['candidate_event_sha256'];assert len(full)==64 and full not in hashes
            hashes.add(full)
        authorities.append(authority)
    return hashes,authorities


def main(run_id):
    plan=json.loads((PACKAGE/'plan.json').read_bytes())
    planned=next(row for row in plan['queue'] if row['run_id']==run_id)
    pointer=HERE/('logical-terminal-'+run_id+'-collected.json')
    assert not pointer.exists(),'Completed original collection must not be repeated'
    assert re.fullmatch(r'[A-Za-z0-9_-]+',run_id)
    manifest_sha=sha(PACKAGE/'manifest.json')
    assert manifest_sha=='c83af050ba64c4edb4d9a1aeff6ebc9f4195e04ef576dd1906791d690e07a5f1'
    carry=json.loads((PACKAGE/'carryover/state.json').read_bytes())
    reviewed,authorities=verified_reviews()
    target=HERE/('logical-terminal-collection-'+str(time.time_ns()));target.mkdir()
    for name in ['collect_logical_terminal_once.py','logical_terminal_checks.py']:
        (target/name).write_bytes((HERE/name).read_bytes())
    save(target/'intent.json',dict(time=time.time(),run_id=run_id,previous_goal_turn_classification='progress',
        previous_authority='matched-analysis-preparation-publication-created.json',review_authorities=authorities,
        new_model_GUI_scorer_paid_calls=0,full_queue_not_stopped_or_modified=True))
    prefix=('RUN='+repr(run_id)+'\nEXPECTED='+repr(manifest_sha)+'\nPLANNED='+repr(planned)
        +'\nCARRYOVER='+repr(carry)+'\nHELPER='+repr((HERE/'logical_terminal_checks.py').read_text(encoding='utf8'))+'\n')
    try:
        output,operation=remote('4090','ROOT='+repr(GUIROOT)+'\nREVIEWED='+repr(sorted(reviewed))+'\n'+prefix+GUI_CODE,
            'source-reviewed-original-logical-terminal-GUI-preservation-'+run_id,timeout=120)
        gui=json.loads(output)
        save(target/'GUI-preservation.json',dict(gui,operation=str(operation)))
        if not gui['ready']:
            save(target/'receipt.json',dict(time=time.time(),ready=False,reason=gui['reason'],
                observation_only_not_experiment_terminal_or_retry=True,new_model_GUI_scorer_calls=0))
            save(target/'seal.json',{p.name:sha(p)for p in target.iterdir()if p.is_file()})
            print(json.dumps(dict(collection=str(target),ready=False,reason=gui['reason'],
                candidate_event_hashes=gui.get('candidate_event_hashes'),seal_sha256=sha(target/'seal.json'))))
            return
        terminal=gui['terminal']
        counters=(dict(actor=terminal['actor_calls'],judge=terminal['verifier_calls'],evidence=terminal['auxiliary_calls'])
            if gui['terminal_name']in ['complete.json','technical-failure.json','paused.json']else None)
        code=('ROOT='+repr(OUTPUT)+'\nGUI_END_BODY='+repr(gui['run_end']['body'])+'\nCOUNTERS='+repr(counters)+'\n'
              +prefix+SERVICE_CODE)
        output,operation=remote('3090',code,'original-logical-terminal-all-selected-request-SHA-'+run_id,timeout=180)
        service=json.loads(output)
        save(target/'service-preservation.json',dict(service,operation=str(operation)))
        original=target/'selected-originals';original.mkdir()
        for name,encoded in gui['exported_originals'].items():
            assert Path(name).name==name
            raw=base64.b64decode(encoded,validate=True)
            (original/name).write_bytes(raw)
            assert sha(original/name)==gui['original_file_SHA256'][name]
        save(target/'receipt.json',dict(time=time.time(),ready=True,run_id=run_id,
            GUI_original_terminal_sha256=gui['terminal_sha256'],
            GUI_original_files_full_SHA_verified=len(gui['original_file_SHA256']),
            service_original_requests_full_SHA_verified=len(service['selected_requests']),
            GUI_terminal_server_end_and_original_budget_counts_bound=True,
            current_new_root_candidate_source_reviews_sealed_before_join=True,
            carried_prefix_requires_its_separate_original_source_authorities=True,
            source_review_completeness_semantic_correctness_efficacy_not_established_here=True,
            all_original_large_tensors_journals_and_traces_retained_in_place=True,
            remaining_frozen_queue_not_stopped_restarted_or_modified=True,new_model_GUI_scorer_paid_calls=0))
        save(target/'seal.json',{p.relative_to(target).as_posix():sha(p)for p in target.rglob('*')if p.is_file()})
        record=dict(collection=str(target),receipt_sha256=sha(target/'receipt.json'),seal_sha256=sha(target/'seal.json'),run_id=run_id)
        save(pointer,record)
        print(json.dumps(record))
    except BaseException as error:
        save(target/'collection-failure.json',dict(time=time.time(),error_type=type(error).__name__,error=str(error),
            collection_failure_not_model_terminal=True,previous_originals_preserved=True,new_model_GUI_scorer_calls=0))
        save(target/'seal.json',{p.relative_to(target).as_posix():sha(p)for p in target.rglob('*')if p.is_file()})
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True)
    main(p.parse_args().run_id)
