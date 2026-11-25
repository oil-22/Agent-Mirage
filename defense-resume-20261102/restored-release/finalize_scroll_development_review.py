"""Finalize only with independently recorded before/after image review."""
import hashlib,json,subprocess,time
from pathlib import Path
from defense.core import canonical,digest
r=Path(__file__).resolve().parent;out=r/'v3.9.7-development-review.json';assert not out.exists()
launch=json.loads((r/'v3.9.7-controller-live-launch.json').read_bytes())
progress=json.loads((r/'v3.9.7-development-progress.json').read_bytes());assert progress['summary']['passed']
live=r/'scroll-live-evidence'/Path(launch['live']['root']).name
summary=json.loads((live/'summary.json').read_bytes());assert summary['passed']
visual=json.loads((r/'v3.9.7-live-visual-review.json').read_bytes());assert visual['returned_to_earlier_content']
for name,field in [('before-repair.png','before_sha256'),('after-repair.png','after_sha256')]:
    assert digest((live/name).read_bytes())==summary[field]==visual[field]
chains=[]
for path in [live/'events/events.jsonl']:
    prev='0'*64;events=[json.loads(x)for x in path.read_text(encoding='utf8').splitlines()]
    for e in events:
        value=dict(e);h=value.pop('sha256');assert value['previous']==prev and digest(canonical(value))==h;prev=h
    chains.append({'path':str(path),'events':len(events),'last_sha256':prev,'file_sha256':digest(path.read_bytes())})
candidate=summary['result']['candidate'];payload=json.loads(candidate.split('<action>')[1].split('</action>')[0]);assert payload=={'type':'scroll','direction':'up'}==summary['result']['proposal']['payload']
record={'time':time.time(),'allow_full_validation':True,'defense_version':'evidence-v3.9.7-native-action-feedback-20261027','engineering_tests':122,'development_summary_sha256':progress['summary_sha256'],'development_cases':[{'case':x['case'],'passed':x['passed']}for x in progress['summary']['results']],'development_new_calls':progress['summary']['new_model_calls'],'live_summary_sha256':digest((live/'summary.json').read_bytes()),'live_visual_review':visual,'live_final_candidate':candidate,'live_original_json_unchanged':True,'live_result':{k:summary['result'].get(k)for k in ['status','regenerations','recaptures','observation_id']},'live_chain_checks':chains,'live_scope':summary['scope'],'original20_preserved':True,'conditions_and_all_validators_unchanged':True,'limitations':['Nonblind development on two archived traces; source-initialized live single decision, not two complete natural trajectories.','One initial regeneration may still repeat the unsupported conclusion; this diagnostic checks recovery within the original two-regeneration cap.','Main-checker labels are not independent semantic truth; output claims need separate review.','Combined feedback and direction clarification have not been individually ablated.','No efficacy, generalization, significant Mirage reduction or full-task recovery claim.'],'full_validation_scope':'New separate root with stale/joint and stale/post_only only; old20 completion pointers and terminal attempts unchanged.'}
out.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({'allow_full_validation':True,'live_summary_sha256':record['live_summary_sha256'],'live_result':record['live_result']}))
