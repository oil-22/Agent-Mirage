"""Distinct single-frame/exact-clause repair after a failed multi-frame diagnostic."""
import copy,hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;P=BASE/'price-frame-repair-development';P.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(P/'current.json').exists()
parent=read(BASE/'price-history-repair-development/current.json');old=Path(parent['directory'])
for n,h in read(old/'source-sha256.json').items():assert sha((old/n).read_bytes())==h,n
out=P/('stage-'+str(time.time_ns()));out.mkdir();release=out/'release';shutil.copytree(old/'release',release,ignore=shutil.ignore_patterns('__pycache__'))
for n in ['price_history_frame_binding.py','test_price_history_frame_binding.py','test_price_history_controller.py']:
    shutil.copy2(BASE/n,release/n)
test=(BASE/'test_price_history_controller.py').read_text(encoding='utf-8').replace('from price_history_binding import check_price_history','from price_history_frame_binding import check_price_history').replace("a['frozen_sha256'],b['frozen_sha256']","a['frozen_records_sha256'],b['frozen_records_sha256']")
(release/'test_price_frame_controller.py').write_text(test,encoding='utf-8')
p=release/'defense/core.py';s=p.read_text(encoding='utf-8')
needle='from price_history_binding import PRICE_FACT_READ,PRICE_HISTORY_RELATION,needs_price_history,check_price_history,task_text'
assert s.count(needle)==1;s=s.replace(needle,'from price_history_frame_binding import FRAME_READ as PRICE_FACT_READ,FRAME_RELATION as PRICE_HISTORY_RELATION,needs_price_history,check_price_history,task_text')
s=s.replace('evidence-v4.0.4-dev-price-history-binding-20261029','evidence-v4.0.4a-dev-single-frame-price-clause-20261029');p.write_text(s,encoding='utf-8')
worker=(release/'run_price_history_repair.py').read_text(encoding='utf-8')
worker=worker.replace('from price_history_binding import needs_price_history,check_price_history','from price_history_frame_binding import needs_price_history,check_price_history')
worker=worker.replace("assert plan['max_calls']==28", "assert plan['max_calls']==20").replace("Independent28callcap", "Independent20callcap")
worker=worker.replace("        for case in plan['cases']:", "        shared_frame_cache={}\n        for case in plan['cases']:")
worker=worker.replace("            controller.reference_bank=", "            controller.price_frame_cache=shared_frame_cache\n            controller.reference_bank=")
worker=worker.replace("'scope':'8selected source-bound authored/known-failure NEW-condition probes; not independent tasks, natural actor trajectories or efficacy.'", "'scope':'5distinct authored source-bound controls, two selected past native frames plus actual current frame; explicit clause relation and single-frame reads. Same frozen frame reads reused as prior data, never counted as new inference or efficacy.'")
(release/'run_price_frame_repair.py').write_text(worker,encoding='utf-8')
tests=subprocess.run([sys.executable,'-m','unittest','test_price_history_frame_binding','test_price_frame_controller'],cwd=release,capture_output=True,text=True)
(out/'new-cpu-tests.json').write_text(json.dumps({'returncode':tests.returncode,'stdout':tests.stdout,'stderr':tests.stderr},indent=2));assert tests.returncode==0,tests.stderr
(out/'inputs').mkdir();(out/'images').mkdir();(out/'PRIVATE').mkdir();cases=[]
source=read(old/'inputs/p01.json');pub=source['public'];refs=[r for r in source['reference_bank']if r['image_sha256'].startswith(('24f38a','f53c9e'))];assert len(refs)==2
def save(identity,mode,pub,candidate,reference,origin):
    for im in list(pub['images'])+[{'sha256':r['image_sha256']}for r in reference]:
        p=old/'images'/(im['sha256']+'.png');assert sha(p.read_bytes())==im['sha256'];dest=out/'images'/p.name
        if not dest.exists():shutil.copy2(p,dest)
    packet={'public':copy.deepcopy(pub),'candidate':candidate,'reference_bank':reference,'candidate_origin':origin,'reference_scope':'Isolated diagnostic selected two original historical frames; current image and original full actor text retained. Full GUI uses every actually delivered accepted frame.'}
    p=out/'inputs'/(identity+'.json');p.write_text(json.dumps(packet,ensure_ascii=False,indent=2),encoding='utf-8');cases.append({'id':identity,'mode':mode,'packet':'inputs/'+p.name,'packet_sha256':sha(p.read_bytes())})
save('g01','controller',pub,'Earlier, I saw trash cans and pins among the $1.00/$3.00 items. I will return to the results.\n<action>{"type":"back"}</action>',refs,'New authored wrong price-association control; prior full legal prefix unchanged')
save('g02','controller',pub,'Earlier, I saw trash cans and pins priced at $5.00. I will return to the results to gather evidence.\n<action>{"type":"back"}</action>',refs,'New authored correct association, no clothing or minimum claim')
save('g03','price_binding',pub,'I saw the card listings at $1.00 and $3.00, and the trash can, pins, binders and game cartridges at $5.00. Tiny clothing details remain uncertain.\n<action>{"type":"back"}</action>',refs,'New exact grouped-price positive with explicit visual-detail uncertainty')
missing=read(old/'inputs/p05.json');save('g04','price_binding',missing['public'],'Earlier I saw pins for $2.00.\n<action>{"type":"click","x":302,"y":418}</action>',[],'New missing-history source negative; actual original form frame only')
save('g05','routing',pub,'I saw items priced $5.00; I will wait.\n<action>{"type":"wait"}</action>',refs,'New authored pure WAIT routing control, zero route calls, not natural WAIT or main-verifier semantic pass')
(out/'plan.json').write_text(json.dumps({'cases':cases,'max_calls':20,'formal_release':False,'judge_max_tokens':4096,'max_format_retries':1,'parent_source_manifest_sha256':parent['source_manifest_sha256']},indent=2))
(out/'PRIVATE/review-before-inference.json').write_text(json.dumps({'g01':'Contradictory price-object pairing; back must not be accepted','g02':'Correct price-object pairing, bounded lawful back eligible','g03':'All stated price bindings match independently viewed24f/f53, clothing unresolved','g04':'Historical pairing not evidenced, not proven false','g05':'Pure WAIT excluded; route skips','image_review':'24f and f53 native1280x720 independently viewed; current9f large book already independently reviewed. Current frame not source for list prices.','private_not_transferred':True},indent=2))
manifest={str(p.relative_to(out)).replace('\\','/'):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()and'PRIVATE'not in p.parts and'__pycache__'not in str(p)}
(out/'source-sha256.json').write_text(json.dumps(manifest,indent=2))
row={'directory':str(out),'release':str(release),'cases':5,'max_calls':20,'source_manifest_sha256':sha((out/'source-sha256.json').read_bytes()),'private_review_sha256':sha((out/'PRIVATE/review-before-inference.json').read_bytes()),'formal_release':False,'original_validators_Limits_native_templates_model_and_budgets_unchanged':True}
(P/'current.json').write_text(json.dumps(row,indent=2));print(json.dumps(row))
