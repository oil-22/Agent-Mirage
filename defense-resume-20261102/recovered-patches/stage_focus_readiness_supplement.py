"""Distinct readiness/causal-scope probes, within the original aggregate24-call repair cap."""
import copy,hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PARENT=BASE/'focus-history-repair-development';PREP=PARENT/'readiness-supplement';PREP.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
previous=json.loads((PREP/'current.json').read_bytes())if(PREP/'current.json').exists()else None
assert not(PREP/'launch-current.json').exists(),'Never alter or restage a launched attempt'
if previous:
 old=Path(previous['directory'])
 for n,h in json.loads((old/'source-sha256.json').read_bytes()).items():assert sha((old/n).read_bytes())==h,n
 (PREP/('prelaunch-metadata-preservation-'+str(time.time_ns())+'.json')).write_text(json.dumps({'previous_stage':previous,'model_calls':0,'reason':'Bind the replacement current source image to its actual capture timestamp rather than the prior packet timestamp. Prior whole stage and source manifest retained.'},indent=2))
ap=json.loads((PARENT/'service-audit-current.json').read_bytes());audit=json.loads((Path(ap['directory'])/'audit.json').read_bytes())
assert sha((Path(ap['directory'])/'audit.json').read_bytes())==ap['audit_sha256']
assert audit['verified_distinct_requests']+8<=24,'Do not expand aggregate repair budget'
parent=json.loads((PARENT/'current.json').read_bytes());source=Path(parent['directory']);out=PREP/('stage-'+str(time.time_ns()));out.mkdir();release=out/'release'
shutil.copytree(source/'release',release,ignore=shutil.ignore_patterns('__pycache__'))
for n in ['current_only_history_scope.py','test_current_only_history_scope.py','test_current_scope_controller.py']:shutil.copy2(BASE/n,release/n)
p=release/'defense/core.py';before=p.read_text(encoding='utf-8')
after=before.replace('from focus_history_scope import','from current_only_history_scope import check_current_only_history,check_historical_event_sources,RETRY_SCOPE\nfrom focus_history_scope import')
after=after.replace('evidence-v4.0.1-dev-focus-history-scope-20261028','evidence-v4.0.2-dev-current-only-scope-20261028')
needle="                        if source_check['reject']:raise ValidationError('Supplemental explicit image-source reference invalid: '+json.dumps(source_check['errors']))\n                    return checked"
replacement="""                        if source_check['reject']:raise ValidationError('Supplemental explicit image-source reference invalid: '+json.dumps(source_check['errors']))
                        history_scope=check_current_only_history(checked)
                        self.log.append('current_only_execution_history_scope',history_scope)
                        if history_scope['reject']:raise ValidationError('Current-only execution-history assertion: '+json.dumps(history_scope['errors']))
                    return checked"""
assert after.count(needle)==1;after=after.replace(needle,replacement)
needle="                return checked\n            except (ValidationError,json.JSONDecodeError)as error:"
replacement="""                history_sources=check_historical_event_sources(checked,view)
                self.log.append('historical_event_source_scope',history_sources)
                if history_sources['reject']:raise ValidationError('Historical-event source scope: '+json.dumps(history_sources['errors']))
                return checked
            except (ValidationError,json.JSONDecodeError)as error:"""
assert after.count(needle)==1;after=after.replace(needle,replacement)
needle="                if str(error)=='Candidate alone cannot ground a GUI action':"
assert after.count(needle)==1;after=after.replace(needle,"                if str(error).startswith('Current-only execution-history assertion:'):system+='\\n'+RETRY_SCOPE\n"+needle)
p.write_text(after,encoding='utf-8')
tests=subprocess.run([sys.executable,'-m','unittest','test_current_only_history_scope','test_current_scope_controller','test_focus_history_scope'],cwd=release,capture_output=True,text=True)
(out/'new-scope-cpu-tests.json').write_text(json.dumps({'returncode':tests.returncode,'stdout':tests.stdout,'stderr':tests.stderr},indent=2));assert tests.returncode==0,tests.stderr
s=(release/'run_focus_history_repair.py').read_text(encoding='utf-8').replace("plan['max_calls']==24","plan['max_calls']==8").replace("6focus reads,2scene reads and4authored history/candidate probes","2readiness and2historical-source controls under aggregate24call repair cap")
(release/'run_focus_readiness_supplement.py').write_text(s,encoding='utf-8')
(out/'inputs').mkdir();(out/'images').mkdir();(out/'PRIVATE').mkdir();cases=[]
sr=Path(json.loads((PARENT/'source-current.json').read_bytes())['directory']);rows={r['id']:r for r in json.loads((sr/'source-summary.json').read_bytes())['rows']}
for identity,old,name in [('b01','f01','home-cue'),('b02','f05','city-cue')]:
 packet=json.loads((source/'inputs'/(old+'.json')).read_bytes());packet['public']['observation_id']='obs-'+sha((identity+parent['source_manifest_sha256']).encode())[:20]
 packet['public']['recent_action']=json.dumps(rows[name]['attempts'][-1]['payload'])
 packet['public']['execution_feedback']='The source operation returned. This is not confirmation of task completion or of the cause of a visible state.'
 for im in packet['public']['images']:shutil.copy2(source/'images'/(im['sha256']+'.png'),out/'images'/(im['sha256']+'.png'))
 path=out/'inputs'/(identity+'.json');path.write_text(json.dumps(packet,ensure_ascii=False,indent=2),encoding='utf-8');cases.append({'id':identity,'mode':'screen','packet':'inputs/'+path.name,'packet_sha256':sha(path.read_bytes())})
for identity,history in [('b03',False),('b04',True)]:
 packet=json.loads((source/'inputs'/('h01.json'if history else'f06.json')).read_bytes())
 target=json.loads((source/'inputs/f06.json').read_bytes())['public'];packet['public']['observation_id']='obs-'+sha((identity+parent['source_manifest_sha256']).encode())[:20]
 packet['public']['messages'][-1]=target['messages'][-1];packet['public']['images'][0]=target['images'][0];packet['public']['observed_at']=target['observed_at']
 packet['candidate_origin']='authored historical-source diagnostic, not native actor generation'
 sentence='No earlier delivered screenshot contained basketball search results.'if history else'This current copper results page proves no earlier basketball search has ever been performed.'
 packet['candidate']=sentence+' I will click the Your search input.\n<action>{"type":"click","x":178,"y":273}</action>'
 for im in packet['public']['images']:shutil.copy2(source/'images'/(im['sha256']+'.png'),out/'images'/(im['sha256']+'.png'))
 path=out/'inputs'/(identity+'.json');path.write_text(json.dumps(packet,ensure_ascii=False,indent=2),encoding='utf-8');cases.append({'id':identity,'mode':'verify','packet':'inputs/'+path.name,'packet_sha256':sha(path.read_bytes())})
plan={'cases':cases,'max_calls':8,'formal_release':False,'judge_max_tokens':4096,'max_format_retries':1,'aggregate_repair_cap':24,'parent_actual_calls':audit['verified_distinct_requests'],'parent_service_audit_sha256':ap['audit_sha256'],'new_actor_calls':0,'model_GUI_actions':0,
 'scope':'Two previously unsent READINESS+recent-attempt contexts on already captured positive-focus frames. Not repeats of completed focus requests: different phase, projection and source input. Not independent visual replication. No completed control retried.',
 'new_supplemental_guard':'Current-only auxiliary definite execution assertions withheld; determinate past-event claims in main verification require eligible earlier source. Both after original strict validation using original1formatretry, preserving raw/no edits/no opposite facts. Current-screen history logs may be conservatively withheld; no release/general accuracy claim. Known parent s01/h02 failures remain immutable.'}
(out/'plan.json').write_text(json.dumps(plan,indent=2))
(out/'PRIVATE/pre-inference-review.json').write_text(json.dumps({'images_already_independently_viewed':True,'b01':'Current Keyword blue outline remains visually supported despite causal attribution to earlier attempt being unconfirmed. Do not demand unseen target. No historical neversearch inference.','b02':'Current City blue outline visible in a coherent350-result copper query page. This is not intended Keyword focus, basketball completion, or prior neversearch proof. Actual lastclick is attempt only.','b03':'Current copper query results cannot establish never an earlier basketball search; insufficient not opposite-fact proof. Click location current search field assessed separately.','b04':'Actual supplied prior reference shows basketball result screen, contradicting no earlier delivered screenshot; current frame is DIFFERENT copper results page, full public sources preserved. Source eligibility alone never proves semantic truth.','no_private_expectations_transferred':True,'same_visual_sources_not_independent_tasks':True},indent=2))
manifest={str(p.relative_to(out)).replace('\\','/'):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()and'PRIVATE'not in p.parts and'__pycache__'not in str(p)}
(out/'source-sha256.json').write_text(json.dumps(manifest,indent=2))
pointer={'directory':str(out),'release':str(release),'cases':4,'source_manifest_sha256':sha((out/'source-sha256.json').read_bytes()),'private_review_sha256':sha((out/'PRIVATE/pre-inference-review.json').read_bytes()),'parent_actual_calls':audit['verified_distinct_requests'],'max_calls':8,'aggregate_cap':24,'formal_release':False}
if previous:pointer['previous_prelaunch_stage_preserved']=previous['directory']
(PREP/'current.json').write_text(json.dumps(pointer,indent=2))
# Generate separate tools, preserving the earlier12-case source and terminal.
s=(BASE/'launch_focus_history_repair.py').read_text(encoding='utf-8').replace("PREP=BASE/'focus-history-repair-development'","PREP=BASE/'focus-history-repair-development'/'readiness-supplement'")
s=s.replace("b/'focus-history-repair-active-20261028.json'","b/'focus-readiness-supplement-active-20261028.json'").replace("'focus-history-repair-real-preflight-'","'focus-readiness-supplement-real-preflight-'").replace('release/run_focus_history_repair.py','release/run_focus_readiness_supplement.py').replace("'max_calls':24","'max_calls':8")
start=s.index('results=[]\n');end=s.index('env=dict(',start)
s=s[:start]+"""# Original167 tests passed in parent; test the new scope guard/integration only.
tests=subprocess.run([py,'-m','unittest','test_current_only_history_scope','test_current_scope_controller','test_focus_history_scope'],cwd=r/'release',capture_output=True,text=True,timeout=60)
(r/'new-scope-remote-cpu-tests.json').write_text(json.dumps({'returncode':tests.returncode,'stdout':tests.stdout,'stderr':tests.stderr},indent=2));assert tests.returncode==0,tests.stderr
"""+s[end:]
(BASE/'launch_focus_readiness_supplement.py').write_text(s,encoding='utf-8')
for original,target in [('inspect_focus_history_repair.py','inspect_focus_readiness_supplement.py'),('collect_focus_history_receipts.py','collect_focus_readiness_supplement_receipts.py')]:
 s=(BASE/original).read_text(encoding='utf-8').replace("/'focus-history-repair-development'","/'focus-history-repair-development'/'readiness-supplement'")
 (BASE/target).write_text(s,encoding='utf-8')
print(json.dumps(pointer))
