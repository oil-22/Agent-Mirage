"""NEW isolated strict-comparison/compact-reader condition; old terminals immutable."""
import copy,hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
B=Path(__file__).resolve().parent;P=B/'strict-price-repair-development';P.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(P/'current.json').exists()
parent=read(B/'pagination-count-fullgui-development/terminal-current.json')
old=Path(read(B/'pagination-count-fullgui-development/fullgui-staging-current.json')['release'])
terminal=Path(parent['directory']);attempt=next(terminal.glob('runs/*/attempt-*'))
assert sha((terminal/'postexit-terminal-sha256.json').read_bytes())==parent['terminal_sha256']
for n,h in read(terminal/'postexit-terminal-sha256.json').items():
    if(terminal/n).exists():assert sha((terminal/n).read_bytes())==h,n
events=[json.loads(x)for x in(attempt/'events.jsonl').read_text(encoding='utf-8').splitlines()]
assert events[330]['kind']=='candidate'and events[340]['kind']=='verdict'
public=lambda n:next(e['data']['public']for e in reversed(events[:n])if e['kind']=='actor_request')
pub=public(330);candidate=events[330]['data']['text']
out=P/('stage-'+str(time.time_ns()));out.mkdir();release=out/'release'
shutil.copytree(old,release,ignore=shutil.ignore_patterns('__pycache__'))
for n in ['strict_price_comparison.py','test_strict_price_comparison.py','test_strict_price_controller.py','compact_price_frame_binding.py','run_strict_price_repair.py']:
    shutil.copy2(B/n,release/n)
core=release/'defense/core.py';s=core.read_text(encoding='utf-8')
needle='from price_history_frame_binding import FRAME_READ as PRICE_FACT_READ'
assert s.count(needle)==1;s=s.replace(needle,'from compact_price_frame_binding import FRAME_READ as PRICE_FACT_READ')
s=s.replace('from native_direction_feedback_origin import attribute_direction_feedback','from native_direction_feedback_origin import attribute_direction_feedback\nfrom strict_price_comparison import check_strict_price_comparison')
needle='            price_history_reason=None\n            if self.limits.probe_history_reports and needs_price_history(candidate,proposal):'
assert s.count(needle)==1
s=s.replace(needle,"""            comparison_check=check_strict_price_comparison(candidate,proposal)
            self.log.append('strict_price_comparison',comparison_check)
            comparison_reason=comparison_check['conflicts'][0]['reason']if comparison_check['reject']else None
            price_history_reason=None
            # An already-rejected internal comparison cannot reach acceptance.
            # Skip only the auxiliary history-price branch until a NEW proposal;
            # the original full actor/main-checker contexts remain unchanged.
            if comparison_reason:
                self.log.append('price_history_auxiliary_deferred',{'reason':'internal_comparison_already_rejected','no_price_fact_certified':True})
            if self.limits.probe_history_reports and comparison_reason is None and needs_price_history(candidate,proposal):""")
s=s.replace('point_needs_evidence=price_history_reason is not None','point_needs_evidence=price_history_reason is not None or comparison_reason is not None')
s=s.replace('or price_history_reason is not None\n','or price_history_reason is not None or comparison_reason is not None\n')
s=s.replace('completion_reason or direction_reason or price_history_reason or point_reason','completion_reason or direction_reason or comparison_reason or price_history_reason or point_reason')
needle='                if direction_reason:patch=attribute_direction_feedback(patch,verdict[\'action\'],direction_check)'
assert s.count(needle)==1
s=s.replace(needle,needle+"""
                elif comparison_reason:
                    patch.update(feedback_reason_source='strict_price_comparison',
                                 original_verifier_assessment=verdict['action']['status'],
                                 feedback_supplies_corrected_price_or_action=False)
""")
s=s.replace('evidence-v4.0.5-dev-page-count-source-20261029','evidence-v4.0.6-dev-strict-price-compact-frame-20261029');core.write_text(s,encoding='utf-8')
(release/'strict-price-source-fixture.json').write_text(json.dumps({'public':pub,'candidate':candidate,'verdict':events[340]['data']['verdict']},ensure_ascii=False,indent=2),encoding='utf-8')
for name in ['inputs','images','PRIVATE']:(out/name).mkdir()
cases=[]
def save(identity,mode,p,text,refs,origin):
    for im in list(p['images'])+[{'sha256':r['image_sha256']}for r in refs]:
        h=im['sha256'];dest=out/'images'/(h+'.png')
        if not dest.exists():
            source=next(f for f in attempt.rglob('*')if f.is_file()and f.suffix in {'.png','.image'}and sha(f.read_bytes())==h)
            dest.write_bytes(source.read_bytes())
    row={'public':copy.deepcopy(p),'candidate':text,'reference_bank':refs,'candidate_origin':origin,
         'source_terminal_sha256':parent['terminal_sha256'],'source_candidate_event_sha256':events[330]['sha256'],
         'scope':'Selected same-task source-bound NEW development condition; no private label/answer supplied.'}
    f=out/'inputs'/(identity+'.json');f.write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
    cases.append({'id':identity,'mode':mode,'packet':'inputs/'+f.name,'packet_sha256':sha(f.read_bytes())})
save('s01','controller',pub,candidate,[],'Actual330 negative in NEW internally inconsistent strict-comparison condition')
save('s02','controller',pub,candidate.replace('cheaper items','earlier items'),[],'Authored earlier/equal-price wording control; actual full legal prefix unchanged')
save('s03','controller',pub,candidate.replace(', and the earlier $5.00 trash cans/pins',''),[],'Authored strictly-lower1/3 control, no full coverage or minimum assertion')
save('s04','controller',pub,'I cannot establish the price ordering of uninspected items from this view. I will scroll up to gather evidence.\n<action>{"type":"scroll","direction":"up"}</action>',[],'Authored unknown-comparison control')
save('s05','raw_reference',pub,'',[],'Original failed8b5 single reference frame; NEW compact prompt, original4096/EOS/schema')
ref=[{'observation_id':pub['observation_id'],'image_sha256':pub['images'][0]['sha256'],'candidate':candidate}]
save('s06','price_binding',public(376),'Earlier I saw "Success is a Choice by Rick Pitino" priced at $5.00.\n<action>{"type":"scroll","direction":"down"}</action>',ref,'Authored correct historical price-only relation; cached NEW raw reading, no clothing/minimum claim')
save('s07','price_binding',public(376),'Earlier I saw "Success is a Choice by Rick Pitino" priced at $3.00.\n<action>{"type":"scroll","direction":"down"}</action>',ref,'Authored incorrect historical price-only relation, no supplied expected verdict')
save('s08','routing',pub,'Current candidate is $5.00. The cheaper items ($1.00,$5.00) remain uninspected.\n<action>{"type":"wait"}</action>',[],'Authored zero-call native WAIT routing only; not natural semantic pass')
(out/'plan.json').write_text(json.dumps({'cases':cases,'max_calls':24,'formal_release':False,'judge_max_tokens':4096,'max_format_retries':1,'parent_terminal_sha256':parent['terminal_sha256']},indent=2))
(out/'PRIVATE/review-before-inference.json').write_text(json.dumps({'s01':'Must withhold internally false strict5vs5 comparison even if main checker misses it; UP is lawful.', 's02':'Earlier items wording alone is not strict lower; preserve uncertainty.', 's03':'1/3 lower than5 internally consistent; not GUI truth or coverage certification.', 's04':'Unknown comparison is not false comparison.', 's05':'Original8b5 has cropped Kentucky5, Rick5 book with suit man, SNES5, SportsIllustrated5, cropped rocks price unknown; require naturalEOS and accurate bindings, no repeated row.', 's06':'Rick5 historical association supported by8b5 only, not global minimum.', 's07':'Rick3 contradicts readable8b5 price.', 's08':'0-call authored native WAIT routing, not semantic result.', 'private_not_transferred':True},ensure_ascii=False,indent=2),encoding='utf-8')
modules=['test_native_direction_development','test_native_direction_feedback_origin','test_scoped_observability','test_scoped_controller_integration','test_focus_history_scope','test_current_only_history_scope','test_current_scope_controller','test_focus_history_conflict_scope','test_focus_conflict_typing_flow','test_plan_present_report_source','test_minimum_price_reason_scope','test_price_history_binding','test_price_history_controller','test_price_history_frame_binding','test_price_frame_controller','test_pagination_count_reason_scope','test_pagination_count_controller','test_strict_price_comparison','test_strict_price_controller']
tests=[]
for args in [['-m','unittest','discover','-s','tests'],['-m','unittest']+modules]:
    t=subprocess.run([sys.executable]+args,cwd=release,capture_output=True,text=True);tests.append({'args':args,'returncode':t.returncode,'stdout':t.stdout,'stderr':t.stderr})
(out/'local-cpu-tests.json').write_text(json.dumps(tests,indent=2));assert all(t['returncode']==0 for t in tests),tests
manifest={str(p.relative_to(out)).replace('\\','/'):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()and'PRIVATE'not in p.parts and'__pycache__'not in str(p)}
(out/'source-sha256.json').write_text(json.dumps(manifest,indent=2))
row={'directory':str(out),'release':str(release),'cases':8,'max_calls':24,'source_manifest_sha256':sha((out/'source-sha256.json').read_bytes()),'formal_release':False,'parent_terminal_sha256':parent['terminal_sha256'],'condition_changes':['Explicit candidate-internal strict price conflict withholding, original neutral feedback/recovery budgets','Compact image-only single-frame auxiliary prompt; no image/history/token/schema truncation','Price auxiliary deferred for already-rejected internal comparison; main checker still sees original full inputs'],'original_validator_native_templates_model_and_budgets_unchanged':True}
(P/'current.json').write_text(json.dumps(row,indent=2));print(json.dumps(row))
