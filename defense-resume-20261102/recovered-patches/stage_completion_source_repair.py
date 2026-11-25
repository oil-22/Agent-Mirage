"""Prepare a NEW completion-source condition; ambiguous322 is NOT a strict-price negative."""
import copy,hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
B=Path(__file__).resolve().parent;P=B/'completion-source-repair-development';P.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(P/'current.json').exists()
parent=read(B/'strict-price-fullgui-retry1-development/terminal-current.json');adj=read(B/'strict-price-fullgui-retry1-development/semantic-adjudication-current.json')
assert sha((Path(adj['directory'])/'adjudicated-joined.json').read_bytes())==adj['adjudicated_join_sha256']
terminal=Path(parent['directory']);assert sha((terminal/'postexit-terminal-sha256.json').read_bytes())==parent['terminal_sha256']
for n,h in read(terminal/'postexit-terminal-sha256.json').items():
    if(terminal/n).exists():assert sha((terminal/n).read_bytes())==h,n
a=next(terminal.glob('runs/*/attempt-*'));events=[json.loads(x)for x in(a/'events.jsonl').read_text(encoding='utf-8').splitlines()]
request=next(e for e in events if e['kind']=='verifier_request'and e['data']['phase']=='completion')
reading=next(e['data']['image_only_assessment']for e in events if e['kind']=='completion_crosscheck')
pub=request['data']['public'];text=pub['messages'][0]['content'];provenance=json.loads(text.split('Image provenance only: ',1)[1]);origins={p['image_index']:p['source_observation_id']for p in provenance}
old=Path(read(B/'strict-price-fullgui-retry1-development/fullgui-staging-current.json')['release'])
out=P/('stage-'+str(time.time_ns()));out.mkdir();release=out/'release';shutil.copytree(old,release,ignore=shutil.ignore_patterns('__pycache__'))
for n in ['completion_frame_price_source.py','test_completion_frame_price_source.py','test_completion_source_retry.py','run_completion_source_repair.py']:shutil.copy2(B/n,release/n)
core=release/'defense/core.py';s=core.read_text(encoding='utf-8')
s=s.replace('from strict_price_comparison import check_strict_price_comparison','from strict_price_comparison import check_strict_price_comparison\nfrom completion_frame_price_source import RELATION as COMPLETION_SOURCE_RELATION,check_completion_frame_prices')
s=s.replace("'price_read','price_relation'}", "'price_read','price_relation','completion_source_relation'}")
s=s.replace("        if phase=='price_relation':system=PRICE_HISTORY_RELATION", "        if phase=='price_relation':system=PRICE_HISTORY_RELATION\n        if phase=='completion_source_relation':system=COMPLETION_SOURCE_RELATION")
s=s.replace("if phase in {'alignment','completion_relation','price_relation'}:return validate_alignment(value,view,candidate,allow_acknowledgment=phase in {'completion_relation','price_relation'})", "if phase in {'alignment','completion_relation','price_relation','completion_source_relation'}:return validate_alignment(value,view,candidate,allow_acknowledgment=phase in {'completion_relation','price_relation','completion_source_relation'})")
needle='                    checked=validate_screen(value,view)';assert s.count(needle)==1
s=s.replace(needle,needle+"""
                    if phase=='completion':
                        attribution=check_completion_frame_prices(self,view,checked)
                        if attribution['reject']:
                            raise ValidationError('Completion numerical image-source binding not established')
""")
needle="                if str(error).startswith('Exact page-count source conflict:'):";assert s.count(needle)==1
s=s.replace(needle,"""                if str(error)=='Completion numerical image-source binding not established':
                    system+='\\nAn independent same-frame reading did not establish every concrete price/count attributed to a numbered image in your previous completion reading. Re-evaluate the SAME full original images and exact frame indices. Preserve cropped or unreadable fields as unknown; another older image does not make a field readable in the cited frame. No corrected price, count, GUI target or action is supplied. This diagnostic does not certify global minimum or task success, and is not an instruction to force a status.'
"""+needle)
s=s.replace('evidence-v4.0.6-dev-strict-price-compact-frame-20261029','evidence-v4.0.7-dev-completion-frame-source-20261029');core.write_text(s,encoding='utf-8')
for n in ['inputs','images','PRIVATE']:(out/n).mkdir()
for im in pub['images']:
    h=im['sha256'];f=next(f for f in a.rglob('*')if f.is_file()and f.suffix in {'.image','.png'}and sha(f.read_bytes())==h);(out/'images'/(h+'.png')).write_bytes(f.read_bytes())
bank=[{'observation_id':origins[i],'image_sha256':im['sha256'],'candidate':''}for i,im in enumerate(pub['images'])if im['role']=='reference']
prior=Path(read(B/'strict-price-repair-development/inspection-current.json')['collected_root']);es=[json.loads(x)for x in(prior/'journal/s05/events.jsonl').read_text(encoding='utf-8').splitlines()];frozen=next(e['data']for e in es if e['kind']=='price_history_single_frame_frozen');assert frozen['original_source_frame']['sha256'].startswith('8b5bc')
raw_clause=next(x for x in reading['visible']if 'Reference image 8 (index 8)'in x);assert '7.00' in raw_clause
cases=[]
def save(identity,mode,payload):
    f=out/'inputs'/(identity+'.json');f.write_text(json.dumps({'public':copy.deepcopy(pub),'reference_bank':bank,'parent_terminal_sha256':parent['terminal_sha256'],'source_completion_request_sha256':request['sha256'],**payload},ensure_ascii=False,indent=2),encoding='utf-8');cases.append({'id':identity,'mode':mode,'packet':'inputs/'+f.name,'packet_sha256':sha(f.read_bytes())})
record={'original_completion_image_index':8,'source_image_sha256':frozen['original_source_frame']['sha256'],'independent_single_frame':frozen}
save('u01','relation',{'completion_reading':{'visible':[raw_clause],'scope':'Exact actual source-attributed visible clause selected, not an edited full reading or a whole-completion test'},'source_records':[record],'origin':'Actual original completion8b5 price-source error; NEW relation condition, previously frozen737token raw read reused as data, not new inference'})
save('u02','relation',{'completion_reading':{'visible':['Reference image8 shows the Rick Pitino book at5.00 $, with the bottom Rocks/Boulders row price unknown.']},'source_records':[record],'origin':'Authored correct source binding, no minimum or clothing claim'})
save('u03','relation',{'completion_reading':{'visible':['Reference image8 does not establish the Rocks/Boulders listing price; it could be7.00 $ but that is unconfirmed.']},'source_records':[record],'origin':'Authored explicit uncertainty; no definite7-dollar source claim'})
save('u04','completion',{'candidate':None,'origin':'Exact original full image-only completion public input, NEW post-validation source audit/original one format retry; zero actor/GUI, no prefrozen cache seeded'})
save('u05','routing',{'candidate':'I will wait.\n<action>{"type":"wait"}</action>','origin':'Authored zero-call WAIT route only'})
save('u06','routing',{'candidate':events[322]['data']['text'],'origin':'Actual322 retained as AMBIGUOUS, not a definite strict-price negative; zero-call route, no model semantic result'})
(out/'plan.json').write_text(json.dumps({'cases':cases,'max_calls':16,'formal_release':False,'judge_max_tokens':4096,'max_format_retries':1,'parent_terminal_sha256':parent['terminal_sha256'],'semantic_adjudication_sha256':adj['correction_sha256']},indent=2))
(out/'PRIVATE/review-before-inference.json').write_text(json.dumps({'u01':'Original8b5 Rocks price cropped unknown; actual clause attributes7 to that frame, should not be source-supported.7 in older1029 does not fix attribution.', 'u02':'Rick5 and bottom unknown match independently viewed8b5.', 'u03':'Explicit conditional7 unconfirmed is not a definite source assertion; preserve uncertainty.', 'u04':'Source-audited full original completion; no promise of correction or minimum. Read all actual replies/frames independently; one original retry only, no outcome or label edits.', 'u05':'Pure authored WAIT0 calls only, excluded.', 'u06':'Ambiguous coordinate categories cheaper1/3 AND other5; guard must abstain, do not tune to false negative label.', 'private_not_transferred':True},indent=2))
modules=['test_native_direction_development','test_native_direction_feedback_origin','test_scoped_observability','test_scoped_controller_integration','test_focus_history_scope','test_current_only_history_scope','test_current_scope_controller','test_focus_history_conflict_scope','test_focus_conflict_typing_flow','test_plan_present_report_source','test_minimum_price_reason_scope','test_price_history_binding','test_price_history_controller','test_price_history_frame_binding','test_price_frame_controller','test_pagination_count_reason_scope','test_pagination_count_controller','test_strict_price_comparison','test_strict_price_controller','test_completion_frame_price_source','test_completion_source_retry']
tests=[]
for args in [['-m','unittest','discover','-s','tests'],['-m','unittest']+modules]:
    t=subprocess.run([sys.executable]+args,cwd=release,capture_output=True,text=True);tests.append({'args':args,'returncode':t.returncode,'stdout':t.stdout,'stderr':t.stderr})
(out/'local-cpu-tests.json').write_text(json.dumps(tests,indent=2));assert all(t['returncode']==0 for t in tests),tests
manifest={str(p.relative_to(out)).replace('\\','/'):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()and'PRIVATE'not in p.parts and'__pycache__'not in str(p)};(out/'source-sha256.json').write_text(json.dumps(manifest,indent=2))
row={'directory':str(out),'release':str(release),'cases':6,'max_calls':16,'source_manifest_sha256':sha((out/'source-sha256.json').read_bytes()),'formal_release':False,'parent_terminal_sha256':parent['terminal_sha256'],'semantic_adjudication_sha256':adj['correction_sha256'],'condition_changes':['Independent numbered-frame price attribution audit of completion reading; original one-format-retry only','Raw same-frame records frozen/cached without actor/task/candidate; numerical relation does not certify clothing/minimum','Ambiguous322 preserved, original strict price guard unchanged'],'original_full_inputs_native_runner_validator_model_and_budgets_unchanged':True}
(P/'current.json').write_text(json.dumps(row,indent=2));print(json.dumps(row))
