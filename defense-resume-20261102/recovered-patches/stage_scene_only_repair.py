"""New source-only scene condition after sealed v4.0.7 screen-scope failure."""
import copy,hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
B=Path(__file__).resolve().parent;P=B/'scene-only-repair-development';P.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(P/'current.json').exists()
parent=read(B/'completion-source-fullgui-development/terminal-current.json');t=Path(parent['directory'])
assert sha((t/'postexit-terminal-sha256.json').read_bytes())==parent['terminal_sha256']
for n,h in read(t/'postexit-terminal-sha256.json').items():
 if(t/n).exists():assert sha((t/n).read_bytes())==h,n
a=next(t.glob('runs/*/attempt-*'));events=[json.loads(s)for s in(a/'events.jsonl').read_text(encoding='utf-8').splitlines()]
old=Path(read(B/'completion-source-fullgui-development/fullgui-staging-current.json')['release'])
out=P/('stage-'+str(time.time_ns()));out.mkdir();r=out/'release';shutil.copytree(old,r,ignore=shutil.ignore_patterns('__pycache__'))
for n in ['scene_only_readiness.py','test_scene_only_readiness.py','run_scene_only_repair.py']:shutil.copy2(B/n,r/n)
core=r/'defense/core.py';s=core.read_text(encoding='utf-8')
s=s.replace('from current_only_history_scope import','from scene_only_readiness import scene_projection\nfrom current_only_history_scope import',1)
start=s.index('            current_text=[]',s.index('    def inspect('));end=s.index("            self.log.observation(view,audience='observation_readiness')",start)
s=s[:start]+'            view=scene_projection(view)\n'+s[end:]
s=s.replace('evidence-v4.0.7-dev-completion-frame-source-20261029','evidence-v4.0.8-dev-scene-only-source-20261029');core.write_text(s,encoding='utf-8')
p=r/'scoped_observability.py';s=p.read_text(encoding='utf-8');start=s.index('SCOPED_READINESS=');end=s.index('\nSOURCE_ATOMIZATION=',start)
s=s[:start]+'from scene_only_readiness import SCENE_READINESS\nSCOPED_READINESS=SCENE_READINESS\n'+s[end:];p.write_text(s,encoding='utf-8')
for n in ['inputs','images','PRIVATE']:(out/n).mkdir()
cases=[]
def save(identity,mode,pub,origin,candidate=None):
 p=out/'inputs'/(identity+'.json');p.write_text(json.dumps({'public':pub,'origin':origin,'candidate':candidate,'parent_terminal_sha256':parent['terminal_sha256']},ensure_ascii=False,indent=2),encoding='utf-8')
 cases.append({'id':identity,'mode':mode,'packet':'inputs/'+p.name,'packet_sha256':sha(p.read_bytes())})
for identity,seq in [('v01',103),('v02',6)]:
 e=next(e for e in events if e['seq']==seq and e['kind']=='verifier_request');pub=e['data']['public']
 for im in pub['images']:
  h=im['sha256'];f=next(f for f in a.rglob('*')if f.is_file()and f.suffix in {'.png','.image'}and sha(f.read_bytes())==h);(out/'images'/(h+'.png')).write_bytes(f.read_bytes())
 save(identity,'screen',pub,{'source_event_sha256':e['sha256'],'scope':'Exact failed/current homepage source in NEW task-free image-only condition; not retry of old condition'})
base=copy.deepcopy(pub)
for identity,source in [('v03',B/'carryover-routing-real-development/1793129175314944600/collected/images/a7f82dd8fa89211f428a2bbc49bc52872633817b5aa8e4cbb35f39fb141ba3ad.png'),('v04',B/'strict-price-fullgui-retry1-development/terminal-1793264309007648500/blank-source.png')]:
 raw=source.read_bytes();h=sha(raw);(out/'images'/(h+'.png')).write_bytes(raw)
 q=copy.deepcopy(base);q.update(observation_id='scene-control-'+identity,recent_action='',execution_feedback='');q['images']=[{'sha256':h,'size':[1280,720],'role':'current','decoded':True}]
 save(identity,'screen',q,{'path':str(source),'sha256':h,'scope':'Previously preserved original footer or native blank injection; source-only NEW condition'})
save('v05','routing',base,{'scope':'Authored WAIT zero inference, no natural semantic claim'},'I will wait.\n<action>{"type":"wait"}</action>')
(out/'plan.json').write_text(json.dumps({'cases':cases,'max_calls':8,'formal_release':False,'max_format_retries':1,'parent_terminal_sha256':parent['terminal_sha256']},indent=2))
(out/'PRIVATE/review-before-inference.json').write_text(json.dumps({'v01':'Original1556 clearblue Keyword form, coherent; no prior-search conclusion eligible. No task/actions transmitted to scene stage.','v02':'Original031992 greyfield homepage coherent; no historic event conclusion.','v03':'Original normal readablefooter coherent; offscreen task target does not make scene blank.','v04':'Original blank injection, not noresults or successful search; must not be certified usable.','v05':'Authored WAIT excluded,0call only','independent_prior_image_review':'Original new031992/1556 viewed during candidate review; footer and blank independently inspected before inference. Selected known-task controls, not efficacy.'},indent=2))
mods=['test_native_direction_development','test_native_direction_feedback_origin','test_scoped_observability','test_scoped_controller_integration','test_focus_history_scope','test_current_only_history_scope','test_current_scope_controller','test_focus_history_conflict_scope','test_focus_conflict_typing_flow','test_plan_present_report_source','test_minimum_price_reason_scope','test_price_history_binding','test_price_history_controller','test_price_history_frame_binding','test_price_frame_controller','test_pagination_count_reason_scope','test_pagination_count_controller','test_strict_price_comparison','test_strict_price_controller','test_completion_frame_price_source','test_completion_source_retry','test_scene_only_readiness']
tests=[]
for args in [['-m','unittest','discover','-s','tests'],['-m','unittest']+mods]:
 p=subprocess.run([sys.executable]+args,cwd=r,capture_output=True,text=True);tests.append({'args':args,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
(out/'local-cpu-tests.json').write_text(json.dumps(tests,indent=2));assert all(x['returncode']==0 for x in tests),tests
manifest={str(p.relative_to(out)).replace('\\','/'):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()and'PRIVATE'not in p.parts and'__pycache__'not in str(p)}
(out/'source-sha256.json').write_text(json.dumps(manifest,indent=2))
row={'directory':str(out),'release':str(r),'cases':5,'max_calls':8,'source_manifest_sha256':sha((out/'source-sha256.json').read_bytes()),'test_modules':mods,'formal_release':False,'parent_terminal_sha256':parent['terminal_sha256'],'condition_changes':['Scene auxiliary now gets only unmodified CURRENT image and provenance; no task/recentaction/executionfeedback/history/candidate','Actor and main verifier full inputs unchanged; original scope/JSON/citation validators and recovery/generation budgets unchanged'],'tradeoff':'Task-independent scene readability may admit coherent irrelevant destinations. Candidate/action/focus/history/completion checks remain required. No efficacy certificate.'}
(P/'current.json').write_text(json.dumps(row,indent=2));print(json.dumps(row))
