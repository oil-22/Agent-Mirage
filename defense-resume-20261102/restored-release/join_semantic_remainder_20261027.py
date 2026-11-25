"""Join already sealed semantic annotations with PRIVATE execution provenance."""
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

from remote import remote

BASE = Path(__file__).resolve().parent
OUT = BASE / 'semantic-review-complete/1793111865686362200'
SOURCE = BASE / 'semantic-review-packets/1793051239384246800'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, obj):
    raw = (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    path.write_bytes(raw)
    return sha(raw)


def main():
    assert not (OUT/'review.json').exists()
    labels_raw = (OUT/'semantic-labels-before-execution.json').read_bytes()
    assert sha(labels_raw) == json.loads((OUT/'label-seal.json').read_bytes())['labels_sha256']
    labels = json.loads(labels_raw)
    prior = labels['previous_review']
    assert json.loads((BASE/'semantic-review-partial-current.json').read_bytes()) == prior
    prior_raw = (Path(prior['directory'])/'review.json').read_bytes()
    assert sha(prior_raw) == prior['review_sha256']
    old = json.loads(prior_raw)
    index_raw = (SOURCE/'PRIVATE-source-and-execution-index.json').read_bytes()
    index = json.loads(index_raw)
    code = 'INDEX=' + repr([{k:r[k] for k in ['opaque_id','attempt','complete_sha256','events_sha256','candidates']} for r in index]) + '\n' + '''
import hashlib,json,pathlib,time,os,pwd
def canon(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
rows=[]
for row in INDEX:
 p=pathlib.Path(row['attempt'])
 for fn,key in [('events.jsonl','events_sha256'),('complete.json','complete_sha256')]:
  assert hashlib.sha256((p/fn).read_bytes()).hexdigest()==row[key],(row['opaque_id'],fn)
 events=[json.loads(line)for line in(p/'events.jsonl').read_bytes().splitlines()]
 previous='0'*64
 for n,e in enumerate(events):
  unhashed={k:v for k,v in e.items()if k!='sha256'}
  assert e['seq']==n and e['previous']==previous
  assert hashlib.sha256(canon(unhashed)).hexdigest()==e['sha256']
  previous=e['sha256']
 bindings=[]
 for c in row['candidates']:
  e=events[c['source_candidate_seq']];req=events[c['source_request_seq']]
  assert e['kind']=='candidate'and e['sha256']==c['source_candidate_sha256']
  assert req['kind']=='actor_request'
  bindings.append({'packet':c['packet'],'candidate_event_sha256':e['sha256'],
                   'candidate_text_sha256':hashlib.sha256(e['data']['text'].encode()).hexdigest(),
                   'public_canonical_sha256':hashlib.sha256(canon(req['data']['public'])).hexdigest()})
 rows.append({'opaque_id':row['opaque_id'],'attempt':str(p),'events_and_terminal_sha_verified':True,
              'event_chain_verified':True,'event_count':len(events),'candidate_bindings':bindings,
              'terminal':json.loads((p/'complete.json').read_bytes())})
print(json.dumps({'time':time.time(),'uid':os.getuid(),'username':pwd.getpwuid(os.getuid()).pw_name,'read_only':True,'rows':rows}))
'''
    verification = json.loads(remote(code,host='4090',timeout=60))
    assert verification['uid'] == 1015 and len(verification['rows']) == 20
    save(OUT/'source-event-terminal-binding-verification.json',verification)
    remote_bindings={c['packet']:c for r in verification['rows'] for c in r['candidate_bindings']}
    lookup = {c['packet']:(r,c) for r in index for c in r['candidates']}
    rows = copy.deepcopy(old['rows']) + copy.deepcopy(labels['rows'])
    assert len(rows) == 542 and len({r['packet'] for r in rows}) == 542
    assert set(lookup) == {r['packet'] for r in rows}
    for row in rows:
        run,src = lookup[row['packet']]
        assert row['packet_sha256'] == src['packet_sha256'] == sha((SOURCE/row['packet']).read_bytes())
        packet = json.loads((SOURCE/row['packet']).read_bytes())
        assert row['candidate'] == packet['candidate']
        rb=remote_bindings[row['packet']]
        assert src['source_candidate_sha256']==rb['candidate_event_sha256']
        assert sha(row['candidate'].encode('utf-8'))==rb['candidate_text_sha256']
        assert sha(json.dumps(packet['public'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())==rb['public_canonical_sha256']
        for field in ['accepted','environment_action_executed','source_request_seq','source_candidate_seq']:
            if field in row:
                assert row[field] == src[field]
            row[field] = src[field]
        row['source_events_sha256'] = run['events_sha256']
        row['source_complete_sha256'] = run['complete_sha256']
        row['source_candidate_sha256'] = src['source_candidate_sha256']
    by_packet = {r['packet']:r for r in rows}
    recoveries=[]

    def transition(oid, before, after, description):
        a,b = [by_packet[f'packets/{oid}/{n:03d}.json'] for n in (before,after)]
        recoveries.append({'from_packet':a['packet'],'from_packet_sha256':a['packet_sha256'],
                           'accepted':a['accepted'],'executed':a['environment_action_executed'],
                           'next_packet':b['packet'],'next_packet_sha256':b['packet_sha256'],
                           'next_delivered_image_sha256':b['delivered_image_sha256'],
                           'description':description,'scope':'local visual transition only; earlier errors remain counted'})

    wrong = '''6b72638ca68849d27302 6c2aace092fc3faaf4f2 8d01e03e22c131e04d42 c96f1ea6b750519f7923 ce17be2dcba13cb381d3 dc428afadba1b0540b0a fd639bfc5f4cbe228266'''.split()
    for oid in wrong:
        transition(oid,24,25,'Intended page1 click actually lands on Duke title; next delivered original is Duke detail. This confirms a wrong-target execution when the joined executed flag is true.')
        transition(oid,25,26,'Back returns from Duke detail to actual page3 search rows, though next candidate still falsely calls it page4.')
        transition(oid,29,30,'Correct page1-button coordinates finally yield actual page1 range1-12; the old page4 narrative is not evidence of a real page4 state.')
    fb='fbffc482b1e27e397875'
    transition(fb,24,25,'Wrong page1-intended Duke-title click is followed by near-white frame and pureWAIT; Duke detail becomes visible at026.')
    transition(fb,27,28,'Repeated alleged-page1 click opens Duke detail again.')
    transition(fb,30,31,'Back was justified by a false Duke-detail state although current was search results; next actual observation is page5.')
    transition(fb,31,32,'Actual first-page« click yields page1.')
    for oid in ['0674cdaeaa8e5d7a5032','0df0570ca1d7a2cc20b0','7cc003554adaaedfa031','f3151695d3746a37a414']:
        transition(oid,21,22,'Explicit previous-page intermediate click yields actual page4; target is supported despite false global uniqueness in the prose.')
        transition(oid,25,26,'Actual first-page« click yields page1.')
    transition('644e949fea4f721cc140',22,23,'Correct first-page« coordinates yield page1. Prior021 explicitly chose button3 as intermediate and was not independently an immediate-target mismatch.')
    transition('ae0539911bd696c0d79d',21,22,'Correct first-page« click yields page1; false uniqueness remains separate.')
    transition('25d543487a45bd59fbd7',20,21,'630,679 is inside actual page4 button and the next delivered frame is page4. Do not reproduce the original gap-reading error.')
    transition('4c3a6c168f89e82f09cf',15,16,'Attempted page4 click hits product description; next frame remains page3, not a successful pagination.')
    transition('4c3a6c168f89e82f09cf',17,18,'From selected3 a click on5 yields page5, skipping actual page4 inspection.')
    trajectory=[]
    terminals={r['opaque_id']:r['terminal'] for r in verification['rows']}
    for run in index:
        oid=run['opaque_id'];rr=sorted([r for r in rows if r['packet'].split('/')[1]==oid],key=lambda r:r['packet'])
        pos=[r for r in rr if r['candidate_semantic_mirage'] is True]
        executed_pos=[r for r in pos if r['accepted'] and r['environment_action_executed']]
        native_bad=[r for r in rr if r.get('native_action_error_identified')]
        native_ex=[r for r in native_bad if r['accepted'] and r['environment_action_executed']]
        trajectory.append({'opaque_id':oid,'run_id':run['run_id'],'candidate_count':len(rr),
                           'has_boundary_inclusive_semantic_mirage':bool(pos),
                           'first_candidate_mirage':pos[0]['packet'] if pos else None,
                           'positive_candidates':len(pos),'indeterminate_candidates':sum(r['candidate_semantic_mirage'] is None for r in rr),
                           'accepted_executed_positive_candidates':len(executed_pos),
                           'native_action_error_candidates':len(native_bad),'accepted_executed_native_action_errors':len(native_ex),
                           'pure_wait_excluded':sum(r['pure_native_wait_excluded'] for r in rr),
                           'terminal_outcome':terminals[oid].get('outcome'),
                           'official_reward':terminals[oid].get('official_reward'),
                           'terminal_sha256':run['complete_sha256'],
                           'recovery_scope':'See sealed local transition notes. Official score is separate from semantic correctness and does not erase any earlier event.'})
    assert len(trajectory)==20 and all(r['has_boundary_inclusive_semantic_mirage'] for r in trajectory)
    counts = {
        'reviewed_candidates':542,'all_candidates':542,'unreviewed_candidates':0,
        'candidate_semantic_mirage':sum(r['candidate_semantic_mirage'] is True for r in rows),
        'indeterminate_candidates':sum(r['candidate_semantic_mirage'] is None for r in rows),
        'accepted_and_executed_mirage_candidates':sum(r['candidate_semantic_mirage'] is True and r['accepted'] and r['environment_action_executed'] for r in rows),
        'excluded_pure_native_wait':sum(r['pure_native_wait_excluded'] for r in rows),
        'native_action_error_candidates':sum(bool(r.get('native_action_error_identified')) for r in rows),
        'accepted_and_executed_native_action_errors':sum(bool(r.get('native_action_error_identified')) and r['accepted'] and r['environment_action_executed'] for r in rows),
        'configurations_with_at_least_one_positive':sum(r['has_boundary_inclusive_semantic_mirage'] for r in trajectory),
    }
    categories=Counter(f['category'] for r in rows for f in r.get('findings',[]))
    action_categories=Counter(f['category'] for r in rows for f in r.get('native_action_errors',[]))
    result={'scope':'All542 actual candidates in20 logical configurations of ONE fixed task. Mixed-version archived exploratory audit, not20 independent tasks.',
            'all_candidates_examined':True,'full_audit_complete':True,'all_subclaims_semantically_resolved':False,
            'fully_blinded':False,'source_directory':str(SOURCE),'previous_review':prior,
            'semantic_labels_precede_execution_join_sha256':sha(labels_raw),
            'private_index_sha256':sha(index_raw),'counts':counts,
            'new_positive_categories_multilabel':dict(categories),'native_action_error_categories_multilabel':dict(action_categories),
            'limitations':labels['limitations']+['54 new candidates retain unresolved subclaims; complete coverage is not complete semantic certainty',
                                               'Counters count logical candidate occurrences including regeneration repeats, not independent failures/tasks',
                                               'Accepted/executed Mirage candidates need not have a wrong native action',
                                               'Coordinate/prose-native action errors are separate, not automatically perceptual Mirage',
                                               'No fair causal efficacy/arm comparison; mixed versions and historical preserved results',
                                               'Global uniqueness refuted by30-dollar suit card does not refute5-dollar minimum'],
            'local_transitions':recoveries,'trajectories':trajectory,'rows':rows}
    digest=save(OUT/'review.json',result)
    save(OUT/'sha256.json',{p.name:sha(p.read_bytes()) for p in OUT.iterdir() if p.is_file()})
    pointer={'directory':str(OUT),'review_sha256':digest,'reviewed_candidates':542,'all_candidates':542,
             'full_audit_complete':True,'all_subclaims_semantically_resolved':False}
    save(BASE/'semantic-review-complete-current.json',pointer)
    save(BASE/'semantic-review-partial-current.json',pointer)
    print(json.dumps({**pointer,'counts':counts,'categories':dict(categories),'action_categories':dict(action_categories),'trajectories':trajectory}))


if __name__=='__main__':
    main()
