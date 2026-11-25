"""New source-bound repair condition; preserve the interrupted GUI unchanged."""
import copy,hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;P=BASE/'pagination-count-repair-development';P.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(P/'current.json').exists()
parent=read(BASE/'price-frame-fullgui-development/terminal-current.json')
old=Path(read(BASE/'price-frame-fullgui-development/fullgui-staging-current.json')['release'])
terminal=Path(parent['directory']);attempt=next(terminal.glob('runs/*/attempt-*'))
assert sha((terminal/'postexit-terminal-sha256.json').read_bytes())==parent['terminal_sha256']
for n,h in read(terminal/'postexit-terminal-sha256.json').items():
    if (terminal/n).exists():assert sha((terminal/n).read_bytes())==h,n
events=[json.loads(x)for x in(attempt/'events.jsonl').read_text(encoding='utf-8').splitlines()];lookup={e['seq']:e for e in events}
assert lookup[264]['kind']=='candidate'and lookup[280]['kind']=='verdict'
public=next(e['data']['public']for e in reversed(events[:264])if e['kind']=='actor_request')
candidate=lookup[264]['data']['text'];verdict=lookup[280]['data']['verdict']
out=P/('stage-'+str(time.time_ns()));out.mkdir();release=out/'release'
shutil.copytree(old,release,ignore=shutil.ignore_patterns('__pycache__'))
for n in ['pagination_count_reason_scope.py','test_pagination_count_reason_scope.py','test_pagination_count_controller.py']:
    shutil.copy2(BASE/n,release/n)
core=release/'defense/core.py';s=core.read_text(encoding='utf-8')
s=s.replace('from minimum_price_reason_scope import minimum_reason_check','from minimum_price_reason_scope import minimum_reason_check\nfrom pagination_count_reason_scope import pagination_count_reason_check')
needle='                minimum_scope=minimum_reason_check(checked,task_text(view))'
assert s.count(needle)==1
s=s.replace(needle,"""                count_scope=pagination_count_reason_check(checked)
                self.log.append('pagination_count_reason_scope',count_scope)
                if count_scope['reject']:raise ValidationError('Exact page-count source conflict: '+json.dumps(count_scope['errors']))
"""+needle)
needle="                if str(error).startswith('Internal minimum explanation conflict:'):"
assert s.count(needle)==1
s=s.replace(needle,"""                if str(error).startswith('Exact page-count source conflict:'):
                    system+='\\nAn exact remaining-page count was supported by an explanation that leaves extra pages open. Numbered shortcuts plus next/last arrows do not by themselves establish an exact total. Reassess the same full public inputs, retaining uncertainty where the count is not established. No corrected count, page capacity or replacement action is provided. Do not merely remove qualifications from your reason or invent evidence to pass.'
"""+needle)
s=s.replace('evidence-v4.0.4a-dev-single-frame-price-clause-20261029','evidence-v4.0.5-dev-page-count-source-20261029');core.write_text(s,encoding='utf-8')
(out/'inputs').mkdir();(out/'images').mkdir();(out/'PRIVATE').mkdir()
for im in public['images']:
    source=next(p for p in attempt.rglob('*')if p.is_file()and p.suffix in {'.png','.image'}and sha(p.read_bytes())==im['sha256'])
    (out/'images'/(im['sha256']+'.png')).write_bytes(source.read_bytes())
cases=[]
def save(identity,mode,text,origin):
    row={'public':copy.deepcopy(public),'candidate':text,'reference_bank':[],
         'candidate_origin':origin,'source_candidate_event_sha256':lookup[264]['sha256'],
         'source_terminal_sha256':parent['terminal_sha256'],
         'reference_scope':'Full actual legal text and original delivered current screenshot. No private expected count or label provided.'}
    p=out/'inputs'/(identity+'.json');p.write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
    cases.append({'id':identity,'mode':mode,'packet':'inputs/'+p.name,'packet_sha256':sha(p.read_bytes())})
save('c01','controller',candidate,'Actual previously accepted source264, NEW condition with explicit-count reason guard; not another old-condition trial')
save('c02','controller','I cannot establish the exact number of remaining pages from the visible pagination shortcuts. I will inspect page 2 to gather more evidence.\n<action>{"type":"click","x":559,"y":679}</action>','New bounded correct control; no exact count or cheapest claim')
save('c03','verify','Page 1 is highlighted; buttons 2 and 3 are visible, so at least two further page numbers are available. I will inspect page 2.\n<action>{"type":"click","x":559,"y":679}</action>','New lower-bound control; next/last shortcuts are not interpreted as an exact total')
save('c04','verify','The exact remaining-page count is not established by this frame. I will check the visible next page.\n<action>{"type":"click","x":559,"y":679}</action>','New missing exact-count source/abstention control, does not assert a corrected count')
save('c05','routing','There are 3 more pages. I will wait.\n<action>{"type":"wait"}</action>','Authored zero-call native WAIT routing only, not natural or semantic WAIT control')
worker=(BASE/'run_price_history_repair.py').read_text(encoding='utf-8').replace("plan['max_calls']==28","plan['max_calls']==16").replace('Independent28callcap','Independent16callcap')
worker=worker.replace("'scope':'8selected source-bound authored/known-failure NEW-condition probes; not independent tasks, natural actor trajectories or efficacy.'","'scope':'5selected actual/authored NEW-condition source-count controls; 4 model probes plus zero-call WAIT route, no actor model or GUI; same-task nonblind development, not efficacy.'")
(release/'run_pagination_count_repair.py').write_text(worker,encoding='utf-8')
(out/'plan.json').write_text(json.dumps({'cases':cases,'max_calls':16,'formal_release':False,'judge_max_tokens':4096,'max_format_retries':1,'source_terminal_sha256':parent['terminal_sha256']},indent=2))
fixture={'public':public,'candidate':candidate,'verdict':verdict}
(release/'pagination-count-fixture.json').write_text(json.dumps(fixture,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'PRIVATE/review-before-inference.json').write_text(json.dumps({'c01':'Exact3 not established by numbered shortcuts; prior reason explicitly potentially more cannot support exact count. Withhold unless actual source establishes it. No forced verdict.', 'c02':'Uncertain exact count plus correct visible page2 target should not be blocked just for an unknown total.', 'c03':'At least2 further numbers are visibly advertised; no exact total asserted.', 'c04':'No false exact count assertion; bounded navigation.', 'c05':'PureWAIT route excluded, zero calls only, not semantic pass.', 'private_not_transferred':True,'source_original_image_independently_viewed':True},indent=2))
tests=[]
for args in [['-m','unittest','discover','-s','tests'],['-m','unittest','test_native_direction_development','test_native_direction_feedback_origin','test_scoped_observability','test_scoped_controller_integration','test_focus_history_scope','test_current_only_history_scope','test_current_scope_controller','test_focus_history_conflict_scope','test_focus_conflict_typing_flow','test_plan_present_report_source','test_minimum_price_reason_scope','test_price_history_binding','test_price_history_controller','test_price_history_frame_binding','test_price_frame_controller','test_pagination_count_reason_scope','test_pagination_count_controller']]:
    t=subprocess.run([sys.executable]+args,cwd=release,capture_output=True,text=True);tests.append({'args':args,'returncode':t.returncode,'stdout':t.stdout,'stderr':t.stderr})
(out/'local-cpu-tests.json').write_text(json.dumps(tests,indent=2));assert all(t['returncode']==0 for t in tests),tests
manifest={str(p.relative_to(out)).replace('\\','/'):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()and'PRIVATE'not in p.parts and'__pycache__'not in str(p)}
(out/'source-sha256.json').write_text(json.dumps(manifest,indent=2))
row={'directory':str(out),'release':str(release),'cases':5,'max_calls':16,'source_manifest_sha256':sha((out/'source-sha256.json').read_bytes()),'formal_release':False,'original_validators_Limits_native_templates_model_and_budgets_unchanged':True,'parent_terminal_sha256':parent['terminal_sha256']}
(P/'current.json').write_text(json.dumps(row,indent=2));print(json.dumps(row))
