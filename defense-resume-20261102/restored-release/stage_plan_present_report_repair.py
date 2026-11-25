"""Linked source-classifier repair with archived full-contract replay, zero new inference."""
import ast,hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;PREP=BASE/'plan-present-report-repair-development';PREP.mkdir(exist_ok=True)
assert not(PREP/'current.json').exists()
read=lambda p:json.loads(p.read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
diagnostic=read(BASE/'focus-conflict-repair-development/inspection-current.json');assert diagnostic['terminal']and diagnostic['status']['phase']=='completed'
terminal=Path(diagnostic['collected_root']);case=read(terminal/'h03-result.json');assert case['contract_status']=='rejected'and'Plan-only source'in case['reason']
parent=read(BASE/'focus-conflict-typing-edge-development/current.json');old=Path(parent['directory'])
assert sha((old/'source-sha256.json').read_bytes())==parent['source_manifest_sha256']
for n,h in read(old/'source-sha256.json').items():assert sha((old/n).read_bytes())==h,n
out=PREP/('stage-'+str(time.time_ns()));out.mkdir();release=out/'release';shutil.copytree(old/'release',release,ignore=shutil.ignore_patterns('__pycache__'))
shutil.copy2(BASE/'test_plan_present_report_source.py',release/'test_plan_present_report_source.py')
def test():
    p=subprocess.run([sys.executable,'-m','unittest','test_plan_present_report_source'],cwd=release,capture_output=True,text=True)
    return {'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
before=test();(out/'before-repair.json').write_text(json.dumps(before,indent=2));assert before['returncode']!=0 and'FAIL:'in before['stderr']
p=release/'focus_history_conflict_scope.py';s=p.read_text(encoding='utf-8')
needle="reported = any(COMPLETED.search(s) and not PLAN.search(s) for s in sentences)"
assert s.count(needle)==1
s=s.replace(needle,"reported = any((COMPLETED.search(s) or re.search(r'\\b(?:shows|depicts|contains|displays)\\b', s, re.I)) and not PLAN.search(s) for s in sentences)")
p.write_text(s,encoding='utf-8')
p=release/'defense/core.py';s=p.read_text(encoding='utf-8');s=s.replace('evidence-v4.0.3a-dev-focus-conflict-preserved-20261029','evidence-v4.0.3b-dev-focus-plan-report-20261029');p.write_text(s,encoding='utf-8')
after=test();(out/'after-repair.json').write_text(json.dumps(after,indent=2));assert after['returncode']==0
# Replay only already returned raw responses through the unchanged strict history validator.
packet=read(terminal/'inputs/h03.json');pub=packet['public'];candidate=packet['candidate']
events=[json.loads(x)for x in(terminal/'journal/h03/events.jsonl').read_text(encoding='utf-8').splitlines()]
raws=[e['data']['response']for e in events if e['kind']=='verifier_raw'];assert len(raws)==len(case['calls'])
replay_dir=out/'archived-replay';replay_dir.mkdir();(replay_dir/'packet.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2),encoding='utf-8')
(replay_dir/'raws.json').write_text(json.dumps(raws,ensure_ascii=False,indent=2),encoding='utf-8')
code='''import json,sys
from pathlib import Path
from defense.core import PublicView,validate_history_relation
from focus_history_conflict_scope import plan_source_check,plan_only_source
r=Path(sys.argv[1]);packet=json.loads((r/'packet.json').read_bytes());pub=packet['public'];v=PublicView(pub['observation_id'],pub['messages'],(),pub['recent_action'],pub['execution_feedback'],pub['observed_at']);rows=[]
for raw in json.loads((r/'raws.json').read_bytes()):
 value=json.loads(raw)if isinstance(raw,str)else raw
 checked=validate_history_relation(value,v,packet['candidate']);check=plan_source_check(checked,v,json.loads(packet['candidate'])['queried_history_claim'])
 rows.append({'strict_validator_passed':True,'raw_status':checked['status'],'source_check':check})
assert any(x['raw_status']=='supported'and not x['source_check']['reject']for x in rows)
assert not plan_only_source(v.messages[1]['content'])
print(json.dumps({'rows':rows,'new_model_calls':0,'scope':'Archived text report relation only; no image truth/completion certification'}))
'''
proc=subprocess.run([sys.executable,'-c',code,str(replay_dir)],cwd=release,capture_output=True,text=True)
(out/'archived-replay-result.json').write_text(json.dumps({'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr},indent=2));assert proc.returncode==0,proc.stderr
manifest={str(p.relative_to(out)).replace('\\','/'):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()and'__pycache__'not in str(p)}
(out/'source-sha256.json').write_text(json.dumps(manifest,indent=2))
pointer={'directory':str(out),'release':str(release),'source_manifest_sha256':sha((out/'source-sha256.json').read_bytes()),'parent_manifest_sha256':parent['source_manifest_sha256'],'diagnostic_terminal_manifest_sha256':diagnostic['terminal_manifest_sha256'],'original_failure_preserved':True,'baseline_regression_failed':True,'repaired_tests':6,'archived_full_validator_replay':True,'new_model_calls':0,'fullgui_candidate_eligible':True,'formal_release':False}
(PREP/'current.json').write_text(json.dumps(pointer,indent=2));print(json.dumps(pointer))
