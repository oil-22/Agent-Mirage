"""Start a new 20-run batch only after source-aware replay acceptance. Never overwrite v1."""
import json,sys
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent
assert not(r/'v2-vwa-launch.json').exists(),'Inspect existing v2 batch before any launch'
post_diagnostic='--diagnostic-post'in sys.argv
diagnostic='--diagnostic'in sys.argv or post_diagnostic
receipt_name='v2-post-diagnostic-launch.json'if post_diagnostic else'v2-live-diagnostic-launch.json'if diagnostic else'v2-vwa-launch.json'
assert not(r/receipt_name).exists(),'Inspect existing attempt; do not duplicate'
staged=json.loads((r/'v2-staging.json').read_text());replay=json.loads((r/'v2-replay-launch.json').read_text())
code='''import pathlib,json,os,subprocess,time,hashlib,urllib.request
r=pathlib.Path('/data/researcher/mirage-defense-pilot-20261023');replay=pathlib.Path(REPLAY);release=pathlib.Path(RELEASE)
diagnostic=DIAGNOSTIC;receipt_name=RECEIPT
post_diagnostic=POST_DIAGNOSTIC
assert not(r/receipt_name).exists(),'Remote launch receipt exists'
replayed_release=pathlib.Path(REPLAYED_RELEASE)
bindings={n:hashlib.sha256((release/n).read_bytes()).hexdigest()for n in ['defense/core.py','defense/prompts.py','defense/schema.py','defense/qwen_backend.py','replay_v2.py']}
assert all(hashlib.sha256((replayed_release/n).read_bytes()).hexdigest()==sha for n,sha in bindings.items()),'Defense differs from validated replay'
summary=json.loads((replay/'summary.json').read_text());rows=json.loads((replay/'results.json').read_text())
assert summary['phase']=='completed'and summary['cases']==14 and summary['protocol_valid']==14,summary
by={x['category']:x['result']for x in rows};records={x['category']:x for x in rows}
checks={
 'normal_screen':by['normal_screen']['status']=='usable',
 'normal_action':by['normal_candidate']['action']['status']=='supported'and records['normal_candidate']['point_agrees'],
 'normal_result_page':by['empty_evidence_failure']['status']=='usable',
 'localized_book_evidence':all(c['status']=='supported'for c in by['coordinate_failure']['claims']),
 # Both verdicts block the contradictory payload; this gate checks the decision,
 # not a preferred synonym. The original response and rationale remain available.
 'plan_action_conflict':by['candidate_source_failure']['action']['status']in {'contradicted','insufficient'},
 'offscreen_control_not_proven':records['long_history']['point_probe']['kind']=='content'and not records['long_history']['point_agrees'],
 'blank_wait_excluded':by['blank_observation']['pure_wait']and by['blank_observation']['action']['status']=='supported'and all(c['kind']not in {'gui_fact','history_report'}or c['status']=='supported'for c in by['blank_observation']['claims']),
 'missing_not_focused':by['missing_observation']['action']['status']!='supported',
 'stale_not_focused':by['stale_observation']['action']['status']!='supported'or records['stale_observation'].get('focus_agrees')is False,
 'buttons_wait_excluded':by['buttons_observation']['pure_wait']and by['buttons_observation']['action']['status']=='supported'and all(c['kind']in {'hypothesis','intent'}for c in by['buttons_observation']['claims']),
 'stale_transition_rechecked':by['stale_screen']['status']!='usable',
 'blank_transition_rechecked':by['blank_screen']['status']!='usable',
 'normal_transition_usable':by['normal_transition']['status']=='usable',
 'normal_typing_supported':by['normal_typing']['action']['status']=='supported'and records['normal_typing'].get('focus_agrees')is True,
}
acceptance={'checks':checks,'passed':all(checks.values()),'new_model_calls':summary.get('new_model_calls'),'reused_main_results':summary.get('reused_main_results'),'reused_point_results':summary.get('reused_point_results'),'scope':'incremental development regression against delivered images; prior unchanged actual replies retained with provenance; not 14 fresh inferences or test-set accuracy or Mirage-rate estimate','time':time.time()}
(replay/'acceptance.json').write_text(json.dumps(acceptance,indent=2));assert acceptance['passed'],acceptance
req=urllib.request.Request('http://192.0.2.11:18127',headers={'Authorization':'Bearer '+(r/'transport.token').read_text().strip()});health=json.loads(urllib.request.urlopen(req,timeout=10).read());assert health['verifier_grammar']=='lm-format-enforcer-0.11.3'and health['actor_grammar']is False,health
assert not pathlib.Path('/proc/345217').exists(),'Old VWA worker still exists'
diagnostic_checks=None
if not diagnostic:
 launch=json.loads((r/'v2-live-diagnostic-launch.json').read_text());dr=pathlib.Path(launch['root'])
 ds=json.loads((dr/'status.json').read_text());assert ds['phase']=='completed'and ds['diagnostic_only']
 completed=list(dr.glob('runs/*/attempt-*/complete.json'));assert len(completed)==1
 done=json.loads(completed[0].read_text());events=[json.loads(x)for x in(completed[0].parent/'events.jsonl').read_text().splitlines()]
 diagnostic_checks={'injection_fired':done['injection_fired'],'four_real_actions':done['environment_actions']==4,
  'no_blocking':done['outcome']=='diagnostic_step_cap','not_official_result':done['official_reward']is None and done['scoring_status']=='not_run_diagnostic',
  'real_recapture_requested':any(e['kind']=='recapture_requested'for e in events),
  'no_format_failure':not any(e['kind']=='verifier_format_failure'for e in events),
  'same_release':launch['release']==str(release)}
 assert all(diagnostic_checks.values()),diagnostic_checks
 post_launch=json.loads((r/'v2-post-diagnostic-launch.json').read_text());pr=pathlib.Path(post_launch['root'])
 ps=json.loads((pr/'status.json').read_text());assert ps['phase']=='completed'and ps['diagnostic_only']
 pc=list(pr.glob('runs/*/attempt-*/complete.json'));assert len(pc)==1
 pd=json.loads(pc[0].read_text());pe=[json.loads(x)for x in(pc[0].parent/'events.jsonl').read_text().splitlines()]
 post_checks={'stale_injection_fired':pd['injection_fired'],'four_real_actions':pd['environment_actions']==4,
  'no_blocking':pd['outcome']=='diagnostic_step_cap','real_recapture':any(e['kind']=='recapture_requested'for e in pe),
  'state_invalidated_and_redecided':any(e['kind']=='state_invalidated'for e in pe)and any(e['kind']=='decision_accepted'and e['data']['regenerations']>0 for e in pe),
  'no_format_failure':not any(e['kind']=='verifier_format_failure'for e in pe),'same_release':post_launch['release']==str(release)}
 assert all(post_checks.values()),post_checks;diagnostic_checks['post_recovery']=post_checks
if post_diagnostic:
 previous=json.loads((r/'v2-live-diagnostic-launch.json').read_text());assert json.loads((pathlib.Path(previous['root'])/'status.json').read_text())['phase']=='completed','First bounded check must finish before another browser run'
root=r/(('live-diagnostic-v2-'if diagnostic else'vwa-v2-')+str(time.time_ns()));root.mkdir()
env=os.environ.copy();env.update(DATASET='visualwebarena',CLASSIFIEDS='http://192.0.2.10:29980',REDDIT='http://192.0.2.10:29999',SHOPPING='http://127.0.0.1:1',WIKIPEDIA='http://127.0.0.1:1',HOMEPAGE='http://127.0.0.1:1',CLASSIFIEDS_RESET_TOKEN='unused-no-site-reset',REDDIT_RESET_URL='http://127.0.0.1:1/no-reset',PLAYWRIGHT_BROWSERS_PATH='/data/researcher/playwright-browsers',CUDA_VISIBLE_DEVICES='')
with(root/'worker.log').open('xb')as out:
 args=['/data/researcher/vwa100-2026-10-09/venv/bin/python','-u',str(release/'run_vwa_pilot.py'),'--root',str(root),'--plan',str(release/'plan80.json'),'--token-file',str(r/'transport.token')]
 if diagnostic:args+=['--diagnostic-run','vwa--classifieds_112--stale_replace--post_only'if post_diagnostic else'vwa--classifieds_112--blank_replace--joint','--diagnostic-step-cap','4']
 child=subprocess.Popen(args,cwd=release,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
receipt={'pid':child.pid,'root':str(root),'release':str(release),'replay_acceptance':acceptance,'validated_defense_sha256':bindings,'diagnostic_acceptance':diagnostic_checks,'health':health,'time':time.time(),'expected_runs':1 if diagnostic else 20,'diagnostic_only':diagnostic,'plan_sha256':hashlib.sha256((release/'plan80.json').read_bytes()).hexdigest(),'order':'single bounded diagnostic'if diagnostic else'original plan queue','scope':'diagnostic; not a task outcome or part of VWA20'if diagnostic else'new VWA20 version; v1 retained; no periodic automation'}
(r/receipt_name).write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
'''.replace('REPLAYED_RELEASE',repr(replay['release'])).replace('REPLAY',repr(replay['root'])).replace('RELEASE',repr(staged['release'])).replace('POST_DIAGNOSTIC',repr(post_diagnostic)).replace('DIAGNOSTIC',repr(diagnostic)).replace('RECEIPT',repr(receipt_name))
compile(code,'remote-live-launch','exec')
result=json.loads(remote(code,host='4090'));(r/receipt_name).write_text(json.dumps(result,indent=2));print(json.dumps(result))
