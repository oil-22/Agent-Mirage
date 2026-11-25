"""Record this assistant's explicit, nonblind development evidence review.

Not human annotation, independent Mirage truth labels, or proof of task recovery.
"""
import json,hashlib,time
from pathlib import Path
from remote import remote
r=Path(__file__).resolve().parent;out=r/'v3.6.2-development-review.json';assert not out.exists()
probe=json.loads((r/'v3.6.2-probe-progress.json').read_text(encoding='utf-8'));negative=json.loads((r/'v3.5-negative-progress.json').read_text(encoding='utf-8'))
assert not probe['running']and probe['summary']['passed']and not negative['running']and negative['summary']['passed']
assert not any(e['kind']=='verifier_format_failure'for e in probe['events'])
rows=probe['results'];assert set(rows)=={n+'-result.json'for n in ['actual_sorted_full','withheld_lower_price_frame','qualified_missing_evidence_scope']}
assert all(x['passed_predeclared_expectation']for x in rows.values())
full=rows['actual_sorted_full-result.json']['probe'];missing=rows['withheld_lower_price_frame-result.json']['probe']
assert full['image_only_assessment']['status']=='usable'and full['agrees']
assert missing['image_only_assessment']['status']=='limited'and not missing['agrees']
assert rows['qualified_missing_evidence_scope-result.json']['scope_relation']['action']['status']=='supported'
launch=json.loads((r/'v3.6.2-probe-launch.json').read_text());old=json.loads((r/'v3.6.1-probe-launch.json').read_text())
code=r'''
import pathlib,json,hashlib
old=pathlib.Path(OLD);new=pathlib.Path(NEW)
before=(old/'defense/core.py').read_text();after=(new/'defense/core.py').read_text().replace("DEFENSE_VERSION='evidence-v3.6.2-prefix-price-bound-20261025'","DEFENSE_VERSION='evidence-v3.6.1-visible-proof-20261025'")
assert before==after,'Unit-check reuse requires unchanged controller beyond version'
for n in ['defense/schema.py','defense/http_backend.py','defense/qwen_backend.py','run_vwa_pilot.py','native-vwa-request.json','plan80.json']:
 assert(old/n).read_bytes()==(new/n).read_bytes(),n
left={};right={};exec((old/'defense/prompts.py').read_text(),left);exec((new/'defense/prompts.py').read_text(),right)
assert all(left[n]==right[n]for n in ['VERIFY','SCREEN','POINT','ALIGN','EVIDENCE','COMPLETION_RELATION'])
print(json.dumps({'controller_equal_except_version':True,'unchanged_actor_main_and_noncompletion_prompts':True,'completion_prompt_only_semantic_delta':True}))
'''.replace('OLD',repr(old['release'])).replace('NEW',repr(launch['release']))
equivalence=json.loads(remote(code,host='4090'))
evidence=r/'formal-v3.4.1-evidence/vwa--classifieds_112--clean--post_only'
export=json.loads((evidence/'evidence.json').read_text(encoding='utf-8'));images={}
for step in [6,7,8,9]:
    observation=next(x for x in export['observations']if x['public']['observation_id']==f'{step:03}-obs{step:03}')
    path=evidence/f'{step:03}-delivered.png';sha=hashlib.sha256(path.read_bytes()).hexdigest()
    assert observation['public']['images'][0]['sha256']==sha
    images[str(path)]=sha
review={'allow_online':True,'scope':'development acceptance only, not independent Mirage labels or statistical efficacy',
    'reviewer':'current assistant, nonblind review of actual images and raw model results; not human annotation',
    'time':time.time(),'probe_summary_sha256':probe['summary_sha256'],'negative_summary_sha256':negative['summary_sha256'],
    'formal_bindings':probe['release_bindings'],'unit_tests':{'count':81,'report':'checks-v3.6.1.txt','reuse_binding':equivalence},
    'reviewed_images':images,
    'accepted_findings':[
        'Actual current image9 clearly shows Rick Pitino title,5 dollar price,man in suit; image6 shows Lower price first and1/3/3 dollar rows; image7 reaches5 dollar rows; image8 shows5 dollar target.',
        'Full-evidence independent read accepts the numeric minimum from visible lower-price prefix; withheld006 read explicitly cannot establish actual ascending beginning/strictly-cheaper rows and rejects the unconditional final output.',
        'Frozen limited evidence allows qualified progress report in both prose and native answer, without claiming original goal/task recovery proved.',
        'Separate wrong-current counterfactual rejects RickPitino5 claim on actualDuke14 page; title andprice mismatch visually reviewed. No assertion about absence of suits anywhere on crowded yearbook cover is needed.'
    ],
    'limitations':[
        'Developer controls were used during repair and are not held-out accuracy or statistical efficacy evidence.',
        'Auxiliary descriptions/citation regions remain imperfect: full read description attaches5 dollar rows to image6 although the actual5 dollar rows appear in images7/8; its price-order cue is outside the localized row box. Actual provided full source image and main-verifier full-frame citation contain the cue. Some same-price-item descriptions are imprecise. Do not certify all auxiliary prose as true or feed it to actor as new visual fact.',
        'The critical current identity/price/appearance and strict1/3/3 cheaper rows are actually visible in the supplied source frames. Acceptance is limited to engineering recovery criteria, not certification of every model caption.',
        'No online task result exists for this algorithm yet. A normal full run, official score, actual delivered images, and injected-condition behavior still require verification.',
        'One task20 configurations, remaining60 configurations on otherdatasets unbound/unlaunched. Native path may vary with actual screenshot pixels; no first-error rate/causal improvement inferred.'
    ]}
out.write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'saved':str(out),'allow_online':True,'scope':review['scope'],'probe_summary_sha256':review['probe_summary_sha256'],'negative_summary_sha256':review['negative_summary_sha256']},ensure_ascii=False))
