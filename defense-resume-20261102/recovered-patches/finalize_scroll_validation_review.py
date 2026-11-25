"""Freeze reviewed outcomes; never rerun or modify any remote experimental result."""
import hashlib,json,time
from pathlib import Path

base=Path(__file__).resolve().parent
marker=json.loads((base/'scroll-validation-outcomes-current.json').read_bytes())
folder=Path(marker['folder']);evidence=json.loads((folder/'evidence.json').read_bytes())
inspection=json.loads((base/'scroll-validation-progress.json').read_bytes())
assert len(evidence['rows'])==2 and evidence['state']['phase']=='completed'
assert inspection['original20_pointer_and_terminal_sha_verified']
assert all(x['hash_chain_ok']and not x['partial_line']for x in inspection['audit']['rows'])
rows=[]
for row in evidence['rows']:
 c=row['complete'];calls=c['calls']
 assert len(calls)==c['actor_calls']+c['verifier_calls']
 rows.append({'run':row['run'],'attempt':row['attempt'],
 'pointer_sha256':row['pointer_sha256'],'terminal_sha256':row['terminal_sha256'],'events_sha256':row['events_sha256'],
 'outcome':c['outcome'],'official_reward':c['official_reward'],'blocked_reason':c.get('blocked_reason'),
 'scoring_status':c['scoring_status'],'technical_status':c['technical_status'],
 'actual_actions':c['environment_actions'],'actor_calls':c['actor_calls'],'verifier_calls':c['verifier_calls'],
 'recapture_requests':row['counts'].get('recapture_requested',0),'format_failures':row['counts'].get('verifier_format_failure',0),
 'point_evidence_unavailable_events':len(row['all_point_recovery_events']),
 'tokens_and_cost':{'input_tokens':sum(x.get('input_tokens',0)for x in calls),'output_tokens':sum(x.get('output_tokens',0)for x in calls),
 'summed_model_seconds':sum(x.get('seconds',0)for x in calls),'paid_api_calls':0,'currency_cost':'not measured','gpu_energy':'not measured'},
 'terminal_original_image_sha256':row['final_image_sha256'],'semantic_mirage_full_trajectory':None})
post=evidence['rows'][1]
bad=next(e for e in post['all_candidates']if e['seq']==301)
good=next(e for e in post['all_candidates']if e['seq']==310)
action=next(e for e in post['all_native_actions']if e['seq']==317)
assert 'scroll back up' in bad['data']['text'] and '"direction":"down"' in bad['data']['text']
assert action['data']['proposal']['payload']=={'type':'scroll','direction':'up'}
assert not any(e['data']['observation_id']==bad['data']['observation_id']for e in post['all_native_actions'])
review={'time':time.time(),'root':evidence['rows'][0]['attempt'].split('/runs/')[0],
 'version':'evidence-v3.9.9-bounded-point-evidence-recovery-20261027','scope':'Two new-version full runs of ONE fixed task; all terminal results immutable. Not a same-version broad efficacy comparison.',
 'worker_exited_normally_after_two_terminals':inspection['process'] is None,'original20_unchanged':True,'all_attempt_event_chains_valid':True,
 'source_evidence_folder':str(folder),'source_evidence_sha256':hashlib.sha256((folder/'evidence.json').read_bytes()).hexdigest(),
 'rows':rows,'independent_visual_review':{
 'joint':{'finding':'Normal interpretable category list and footer, no visible loading or blank. Three readiness reads incorrectly demand task product context, despite an evidence-seeking scroll being possible. Scoped false block of observation readiness; no future actor proposal was generated or certified.','task_recovered':False,'image_sha256':rows[0]['terminal_original_image_sha256']},
 'post_only':{'finding':'Original footer and next original image independently viewed: accepted native up changed viewport to page5 listings49-50 and pagination. Final original image shows Rick Pitino detail, visible man in suit and5.00 dollars. Official score1; this single final frame alone does not prove global minimum.',
 'direction_conflict_candidate_event_sha256':bad['sha256'],'corrected_candidate_event_sha256':good['sha256'],'up_execution_event_sha256':action['sha256'],
 'conflict_candidate_not_executed':True,'new_candidate_error_direction_conflicts_reviewed':1,'accepted_or_executed_this_direction_conflict':0,'task_recovered_official':True}},
 'limitations':['Direction conflict did occur at candidate stage; subsequent correction does not erase it.',
 'No full independent semantic labeling of either trajectory; no no-Mirage or Mirage-rate claim.',
 'No naturally observed point_evidence_unavailable recovery event in either latest full attempt.',
 'Joint observation false block remains unresolved; cannot claim both runs repaired.',
 'Current85+79 local model calls exclude prior failed technical attempts and development controls.'],
 'follow_up':{'joint_readiness':'Preserve terminal, prepare source-bound diagnosis/controls separately; no additional budget or repeat of completed run. Do not silently force usable or relax candidate validators.',
 'uitars':'Independent candidate identity/processor/full-input controls, then gated real inference; no replacement of these outcomes.',
 'monitor':'Keep active;60 defense configs, independent semantic review,27B attention andUI candidate remain outstanding.'}}
dest=base/'v3.9.9-scroll-validation-completed-20261027.json'
raw=json.dumps(review,ensure_ascii=False,indent=2).encode('utf8')
with dest.open('xb')as f:f.write(raw)
manifest={'report':str(dest),'sha256':hashlib.sha256(raw).hexdigest(),'evidence_folder':str(folder),
 'local_artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in folder.iterdir()if p.is_file()},
 'inspection_sha256':hashlib.sha256((base/'scroll-validation-progress.json').read_bytes()).hexdigest()}
(base/'v3.9.9-scroll-validation-completion-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print(json.dumps({'report':str(dest),'sha256':manifest['sha256'],'rows':rows},ensure_ascii=True))
