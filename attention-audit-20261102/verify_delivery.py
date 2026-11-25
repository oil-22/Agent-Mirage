"""Final independent grid and analysis-artifact checks; no inference."""
import collections,json,pathlib,hashlib
R=pathlib.Path(__file__).parent;A=R/'analysis'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
rows=read(A/'measurements.json');audit=read(A/'terminal-audit.json');diag=read(A/'analysis-diagnostics.json')
assert audit['all_expected_complete'] and audit['logical_completed']==1728 and not audit['errors']
assert len(rows)==1728 and len({(x['cohort'],x['model'],x['id']) for x in rows})==1728
newtasks={x['task'] for x in rows if x['cohort']=='main'};oldtasks={x['task'] for x in read(R.parent/'attention-audit-20261031/analysis/measurements.json')}
assert len(newtasks)==10 and len(oldtasks)==9 and not newtasks&oldtasks
expected={'main':360,'buttons':90,'source':126}
for m in ['qwen27','qwen9','glm']:
 for c,n in expected.items():
  rr=[x for x in rows if x['model']==m and x['cohort']==c];assert len(rr)==n,(m,c,len(rr))
  keys=[(x['task'],x['stage'],x['history'],x['condition']) if c!='source' else (x['task'],x['step'],x['condition']) for x in rr]
  assert len(set(keys))==n
  if c=='main':assert set(keys)=={(t,s,h,k) for t in newtasks for s in ['early','middle','late'] for h in ['none','last2','full'] for k in ['current_control','blank_replace','silent_drop','stale_replace']}
  if c=='buttons':assert set(keys)=={(t,s,h,'buttons_only') for t in newtasks for s in ['early','middle','late'] for h in ['none','last2','full']}
  if c=='source':
   tasks={x['task'] for x in rr};assert len(tasks)==14
   assert set(keys)=={(t,s,k) for t in tasks for s in [3,5,8] for k in ['original','source_withdrawn','meaning_preserving_sham']}
  for x in rr:
   assert abs(sum(x['first_query_mass'])-1)<2e-4
   assert x['query_character_offsets_exact'] or x['action_query_mass'] is None
assert audit['source_cpu_matches_actual']==378 and audit['source_pairs_audited']==252
assert len(read(A/'source-pair-audit.json'))==252
assert diag['new_semantic_reviewed']==diag['new_semantic_logical_outputs']==540
for b in audit['batches']:
 assert len(b['preflights'])>=2 and all(x['output_ids_equal'] and x['max_logit_abs_diff']==0 for x in b['preflights'])
 prefix={'main':'','buttons':'buttons-','source':'source-'}[b['cohort']];folder=R/'remote-metadata'/(prefix+b['model'])
 runtime=read(folder/'runtime.json');cfg=R/'model-configs'/(b['model']+'.json');assert runtime['config_sha256']==hashlib.sha256(cfg.read_bytes()).hexdigest()
 plan=R/'remote-metadata'/({'main':'campaign','buttons':'button-campaign','source':'source-campaign'}[b['cohort']])/'plan.json';assert runtime['plan_sha256']==hashlib.sha256(plan.read_bytes()).hexdigest()
 assert runtime['runner_sha256']==hashlib.sha256((R/'run_attention.py').read_bytes()).hexdigest()
 raw=read(folder/'results.json');assert len(raw)==b['expected'] and all(x['status']=='completed' for x in raw)
assert len(read(A/'source-comparisons.json')['snapshots'])==126
mask=read(A/'mask-pixel-audit.json');assert len(mask)==30 and all(all(x[k] for k in ['original_file_sha_verified','mask_file_sha_verified','inside_pixels_identical','outside_pixels_white']) for x in mask)
ground=collections.Counter(x['label'] for x in read(R/'source-grounding-review.json')['cases']);assert dict(ground)=={'supported_by_capture':8,'contradicted_by_capture':3,'visually_unresolved':3}
result={'status':'passed','logical_configurations':len(rows),'grid_counts_per_model':expected,'independent_main_tasks_old_new_pooled':[9,10,19],'source_tasks':14,'source_snapshot_triplets':126,'source_pair_audits':252,'source_actual_inputs_verified':378,'semantic_outputs_reviewed':540,'masks_rechecked':30,'censored_replies':len(diag['new_censored'])}
(A/'delivery-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
