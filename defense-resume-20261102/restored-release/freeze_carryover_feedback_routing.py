"""Freeze supplementary feedback route on the six immutable public inputs; no inference."""
import copy,hashlib,json,subprocess,sys,time
from pathlib import Path
from defense.core import PublicView,VisibleImage,canonical,digest
from carryover_feedback_routing import build_feedback
BASE=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest()
ptr=json.loads((BASE/'history-carryover-development/carryover-current.json').read_bytes());src=Path(ptr['local_root']);summary=json.loads((src/'summary.json').read_bytes())
publics=[json.loads(x)['data']['public']for x in(src/'journal/events.jsonl').read_text(encoding='utf-8').splitlines()if json.loads(x)['kind']=='observation']
out=BASE/'carryover-feedback-routing-development'/str(time.time_ns());out.mkdir(parents=True)
template=json.loads((BASE/'native-vwa-request.json').read_bytes());rows=[]
for obs,case in zip(publics,summary['results']):
 images=tuple(VisibleImage((src/'journal'/(i['sha256']+'.image')).read_bytes(),i['role'])for i in obs['images']);view=PublicView(obs['observation_id'],obs['messages'],images,obs['recent_action'],obs['execution_feedback'],obs['observed_at']);assert canonical(view.data())==canonical(obs)
 before=canonical(case['audit']);r=build_feedback(view,case['source_prior_message_index'],case['audit']);assert before==canonical(case['audit'])
 body={k:copy.deepcopy(v)for k,v in template.items()if k!='messages'};body['messages']=copy.deepcopy(view.messages)+[{'role':'user','content':r['feedback']}]
 assert body['messages'][:-1]==obs['messages']and body['messages'][0]==obs['messages'][0]and body['max_tokens']==2048
 (out/(case['id']+'-routing.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');(out/(case['id']+'-unsent-body.json')).write_text(json.dumps(body,ensure_ascii=False,indent=2),encoding='utf-8')
 rows.append({'id':case['id'],'quarantined':[c['earlier_report_words']for c in r['data']['quarantined_checker_support']],'supported_claims':[c['id']for c in r['data']['supported_current_reuse']],'pending_count':len(r['data']['pending_current_reuse']),'source_image_sha256':r['data']['source_current_image_sha256'],'actor_history_prefix_exact':True,'actor_body_sent':False})
assert [r['id']for r in rows if r['quarantined']]==['h01'];assert rows[2]['supported_claims']==['c1']
test=subprocess.run([sys.executable,'-m','unittest','test_carryover_feedback_routing'],cwd=BASE,capture_output=True,text=True);(out/'tests.txt').write_text(test.stdout+test.stderr,encoding='utf-8');assert test.returncode==0
names=['carryover_feedback_routing.py','test_carryover_feedback_routing.py','freeze_carryover_feedback_routing.py','pagination_derivation_guard.py','defense/core.py','defense/prompts.py','defense/schema.py','native-vwa-request.json']
for n in names:
 p=out/'release'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((BASE/n).read_bytes())
plan={'source_summary_sha256':sha((src/'summary.json').read_bytes()),'source_terminal_manifest_sha256':ptr['seal']['sha256'],'rows':rows,'routing_tests_passed':15,'new_model_calls':0,'new_gui_actions':0,'private_expectations_sent':False,'budgets':{'actor_output':2048,'verifier_output':4096,'actor_calls':70,'verifier_calls':140,'steps':50,'regenerations_per_decision':2,'recaptures_per_decision':2,'format_retries':1,'additional_budget_for_guard':0},'controller_integrated':False,'real_model_feedback_preflight_complete':False,'formal_trial_authorized':False,'formal_release':False,'limits':'Nonblind preparation on previously reviewed development sources. Frozen bodies are unsent. Original verdicts retain their statuses and the strict validator is called unchanged on a copy; quarantine is only a separate pending-feedback route. Does not fix page recognition, intention misclassification, direction, false blocks or establish efficacy. New real controls and original-budget recovery integration must precede a formal-condition decision.'}
(out/'staging.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'report.md').write_text('''# 当前前提反馈路由暂存完成

新增carryover_feedback_routing.py，先对真实上一条assistant报告调用原strict validator，再将内部算术矛盾的supported放入独立quarantine，不发作已确认当前事实。原verdict/status保留作审计；不改原Controller、JSON、图、历史、模型、预算或评分，不给替代页号/方向/目标。

15项路由边界测试通过；6份真实旧开发输入回放仅h01的错误supported被隔离，h03蓝焦点支持保留。6份未发送actor请求保留完整原生历史前缀、原system及2048输出上限。原图/核验输入/旧结果均不改，0模型/GUI/评分调用。原h06的WAIT行为未重生成，不能将CPU路由当作新模型WAIT控制通过。

尚未完成新的真实模型反馈控制、在线原预算恢复集成或正式配对验证。算法只能识别核验器明确写出的局部算术冲突，不验证读图真伪或每页容量的视觉依据；未标结果不能叫语义通过。保持release=false，接下来冻结独立控制后再走正式实验条件决定。
''',encoding='utf-8')
(out/'sha256.json').write_text(json.dumps({str(p.relative_to(out)):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()},indent=2),encoding='utf-8')
receipt={'directory':str(out),'staging_sha256':sha((out/'staging.json').read_bytes()),'manifest_sha256':sha((out/'sha256.json').read_bytes()),'routing_tests':15,'frozen_unsent_requests':6,'new_model_calls':0,'formal_release':False}
(BASE/'carryover-feedback-routing-development/current.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(receipt))
