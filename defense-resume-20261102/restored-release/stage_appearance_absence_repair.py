"""Build a distinct source-bound appearance/absence repair after the full GUI terminal."""
import copy,hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
B=Path(__file__).resolve().parent;P=B/'appearance-absence-repair-development';P.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_bytes());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not(P/'current.json').exists()
parent=read(B/'scene-only-fullgui-development/terminal-current.json');terminal=Path(parent['directory']);assert sha(terminal/'postexit-terminal-sha256.json')==parent['terminal_sha256']
for n,h in read(terminal/'postexit-terminal-sha256.json').items():
 if(terminal/n).exists():assert sha(terminal/n)==h,n
a=next(terminal.glob('runs/*/attempt-*'));events=[json.loads(x)for x in(a/'events.jsonl').read_text(encoding='utf-8').splitlines()]
old=Path(read(B/'scene-only-fullgui-development/fullgui-staging-current.json')['release']);out=P/('stage-'+str(time.time_ns()));out.mkdir();r=out/'release';shutil.copytree(old,r,ignore=shutil.ignore_patterns('__pycache__'))
for n in ['appearance_absence_source.py','test_appearance_absence_source.py','test_appearance_absence_controller.py','run_appearance_absence_repair.py']:shutil.copy2(B/n,r/n)
core=r/'defense/core.py';s=core.read_text(encoding='utf-8');s=s.replace('from scene_only_readiness import scene_projection','from scene_only_readiness import scene_projection\nfrom appearance_absence_source import PERSON_READ,ABSENCE_RELATION,EPISTEMIC_SCOPE,check_appearance_absence')
s=s.replace("system+='\\n'+FACTUAL_SOURCE_ROUTING", "system+='\\n'+FACTUAL_SOURCE_ROUTING+'\\n'+EPISTEMIC_SCOPE")
s=s.replace("'completion_source_relation'}","'completion_source_relation','person_read','absence_relation'}")
s=s.replace("        if phase=='completion_source_relation':system=COMPLETION_SOURCE_RELATION","        if phase=='completion_source_relation':system=COMPLETION_SOURCE_RELATION\n        if phase=='person_read':system=PERSON_READ\n        if phase=='absence_relation':system=ABSENCE_RELATION")
s=s.replace("{'screen','focus','completion','price_read'}","{'screen','focus','completion','price_read','person_read'}")
s=s.replace("if readiness or phase=='focus':","if readiness or phase in {'focus','person_read'}:")
needle='            point_reason=None;point_needs_evidence=price_history_reason is not None or comparison_reason is not None;focus_reason=None';assert s.count(needle)==1
s=s.replace(needle,"""            appearance_absence_reason=None
            if self.limits.probe_history_reports and not checked_wait(proposal) and comparison_reason is None and verdict['action']['status']=='supported' and all(c['status']=='supported' for c in verdict['claims'] if c['kind']in {'gui_fact','history_report'}):
                try:appearance_source=check_appearance_absence(self,candidate_view,candidate,proposal)
                except (ValidationError,BudgetExhausted)as e:return blocked('appearance_absence_verifier_error:'+str(e))
                appearance_absence_reason=appearance_source['reason']
            point_reason=None;point_needs_evidence=price_history_reason is not None or comparison_reason is not None or appearance_absence_reason is not None;focus_reason=None""")
s=s.replace("or comparison_reason is not None\n            completion_reason=None","or comparison_reason is not None or appearance_absence_reason is not None\n            completion_reason=None")
s=s.replace('completion_reason or direction_reason or comparison_reason or price_history_reason or point_reason or focus_reason','completion_reason or direction_reason or comparison_reason or price_history_reason or appearance_absence_reason or point_reason or focus_reason')
needle="                corrections.append(patch)";assert s.count(needle)==1
s=s.replace(needle,"""                if appearance_absence_reason:
                    patch.update(feedback_reason_source='appearance_absence_source',original_verifier_assessment=verdict['action']['status'],feedback_supplies_corrected_GUI_fact_or_action=False)
"""+needle)
s=s.replace('evidence-v4.0.8-dev-scene-only-source-20261029','evidence-v4.0.9-dev-appearance-absence-source-20261029');core.write_text(s,encoding='utf-8')
for n in ['inputs','images','PRIVATE']:(out/n).mkdir()
packets=read(Path(read(B/'scene-only-fullgui-development/public-candidates-current.json')['directory'])/'packets.json');byseq={x['candidate_seq']:x for x in packets}
accepted=[e for e in events if e['kind']=='decision_accepted'];cases=[]
def save(identity,mode,pub,candidate,bank,origin):
 for im in pub['images']+bank:
  h=im['sha256'];f=next(p for p in a.rglob('*')if p.is_file()and p.suffix in {'.png','.image'}and sha(p)==h);(out/'images'/(h+'.png')).write_bytes(f.read_bytes())
 p=out/'inputs'/(identity+'.json');p.write_text(json.dumps({'public':pub,'candidate':candidate,'reference_bank':bank,'origin':origin,'parent_terminal_sha256':parent['terminal_sha256']},ensure_ascii=False,indent=2),encoding='utf-8');cases.append({'id':identity,'mode':mode,'packet':'inputs/'+p.name,'packet_sha256':sha(p)})
x=byseq[293];save('w01','check',x['public'],x['candidate'],[],{'source_candidate_event_sha256':x['candidate_event_sha256'],'new_condition':'Actual clear-person-negative prefix, independent blind reading and source relation; not old main-checker rerun'})
x=byseq[341];bank=[]
for accepted_event in accepted:
 if accepted_event['seq']>=341:break
 q=next(p for p in packets if p['candidate']==accepted_event['data']['candidate']and p['public']['observation_id']==accepted_event['data']['observation_id'])
 for im in q['public']['images']:bank.append({**im,'observation_id':q['public']['observation_id'],'candidate':q['candidate']})
save('w02','check',x['public'],x['candidate'],bank,{'source_candidate_event_sha256':x['candidate_event_sha256'],'scope':'Complete actual accepted-observation bank before341, source-only; not evaluator answers'})
x=byseq[293];save('w03','relation-after-w01',x['public'],'I cannot confirm that no man in a suit is shown.',[],{'scope':'Authored uncertainty control using frozen w01 record, no extra image inference'})
save('w04','relation-after-w01',x['public'],'The only item I identified with a man in a suit was the book.',[],{'scope':'Qualified identified report must not be silently strengthened into global uniqueness; authored bounded control'})
save('w05','check',byseq[12]['public'],'No person in a suit is visible in this current screenshot.',[],{'scope':'Authored current home-scene negative control, no instructed expected outcome'})
blank=Path(read(B/'scene-only-repair-development/current.json')['directory'])/'images';blankpacket=read(Path(read(B/'scene-only-repair-development/current.json')['directory'])/'inputs/v04.json');pub=blankpacket['public'];im=pub['images'][0];shutil.copy2(blank/(im['sha256']+'.png'),out/'images'/(im['sha256']+'.png'))
p=out/'inputs/w06.json';p.write_text(json.dumps({'public':pub,'candidate':'No man in a suit exists on this page.','reference_bank':[],'origin':'Actual original blank injection; blank is not proof of task absence','parent_terminal_sha256':parent['terminal_sha256']},indent=2));cases.append({'id':'w06','mode':'check','packet':'inputs/w06.json','packet_sha256':sha(p)})
save('w07','routing',byseq[12]['public'],'I will wait.\n<action>{"type":"wait"}</action>',[],{'scope':'ArtificialWAIT0call, not natural semantic pass'})
q=next(e for e in events if e['kind']=='verifier_request'and e['seq']>656)
save('w08','verify',q['data']['public'],byseq[656]['candidate'],[],{'source_request_event_sha256':q['sha256'],'source_candidate_event_sha256':byseq[656]['candidate_event_sha256'],'scope':'Original full verify request, all actual images/history; NEW explicit epistemic atomization prompt, unchanged validator'})
p=out/'inputs/w08.json';v=read(p);v['proposal']=q['data']['proposal'];p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8');cases[-1]['packet_sha256']=sha(p)
(out/'plan.json').write_text(json.dumps({'cases':cases,'max_calls':24,'formal_release':False,'max_format_retries':1},indent=2))
(out/'PRIVATE/review-before-inference.json').write_text(json.dumps({'w01':'Original3e254 cleargreensuitedVictor30. Definite localabsence false, independent reader should see actualperson. No expectedfact sent.','w02':'Original341 wholepage2absence contradicted by earlierdelivered3e254. Fullnative source history, not privateanswers.','w03':'Explicit inability to confirmabsence is not definiteabsence.','w04':'OnlyIidentified is boundedselfreport, not globaluniqueness; actual actor missedVictor.','w05':'Currenthome has no clearpeople, must read allactualpixels, not force support; falseblock/unreadable retained.','w06':'Blank limited/unknown, no globalpageabsencecertificate.','w07':'ArtificialWAIT0call route only','reviewer_scope':'Single known-task development, full original images already independently viewed before this NEW condition. Not fullyblind/general efficacy.'},indent=2))
mods=read(B/'scene-only-repair-development/current.json')['test_modules']+['test_appearance_absence_source','test_appearance_absence_controller'];tests=[]
for args in [['-m','unittest','discover','-s','tests'],['-m','unittest']+mods]:
 p=subprocess.run([sys.executable]+args,cwd=r,capture_output=True,text=True);tests.append({'args':args,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
(out/'local-cpu-tests.json').write_text(json.dumps(tests,indent=2));assert all(x['returncode']==0 for x in tests),tests
manifest={str(p.relative_to(out)).replace('\\','/'):sha(p)for p in out.rglob('*')if p.is_file()and'PRIVATE'not in p.parts and'__pycache__'not in str(p)};(out/'source-sha256.json').write_text(json.dumps(manifest,indent=2))
(P/'current.json').write_text(json.dumps({'directory':str(out),'release':str(r),'source_manifest_sha256':sha(out/'source-sha256.json'),'test_modules':mods,'max_calls':24,'cases':len(cases),'parent_terminal_sha256':parent['terminal_sha256'],'formal_release':False,'tradeoff':'Extra per-frame and relation calls consume original140judge budget in GUI. Readers/negative routing can miss/falseblock; small/cropped figures stayunknown. No suppliedcorrectperson/item/price/action or minimumcertificate. Main verify prompt adds explicit epistemic atomization; full actor/main inputs and validators unchanged.'},indent=2));print(json.dumps({'directory':str(out),'cases':len(cases),'max_calls':24}))
