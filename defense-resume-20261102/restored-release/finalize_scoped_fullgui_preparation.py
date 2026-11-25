"""Seal a reviewable one-run proposal after actual zero-inference live prerequisites."""
import ast,hashlib,json,re,time
from pathlib import Path
from remote import remote
from launch_scoped_fullgui import validate_decision
BASE=Path(__file__).resolve().parent;PREP=BASE/'scoped-observability-development'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(PREP/'fullgui-ready-current.json').exists()
stage=json.loads((PREP/'fullgui-staging-current.json').read_bytes());out=Path(stage['directory']);release=Path(stage['release'])
assert stage['environment_returncode']==0 and stage['environment_phase']=='environment_preflight_complete'
for n,h in json.loads((out/'release-sha256.json').read_bytes()).items():assert sha((release/n).read_bytes())==h,n
er=json.loads((out/'environment-receipt.json').read_bytes());assert er['child_exited'] and er['model_calls']==0
cpu=json.loads((out/'cpu-results.json').read_bytes());rcpu=json.loads((out/'environment-evidence/remote-cpu-tests.json').read_bytes())
assert [int(re.search(r'Ran (\d+) tests',r['stderr']).group(1))for r in cpu]==[122,40]
assert [int(re.search(r'Ran (\d+) tests',r['stderr']).group(1))for r in rcpu]==[122,40]
assert all(r['returncode']==0 for r in cpu+rcpu)
parent=json.loads((PREP/'live-candidate-current.json').read_bytes());old=Path(parent['directory'])/'original-full-validation'
def defs(p):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(p.read_text(encoding='utf-8')).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
a,b=defs(old/'defense/core.py'),defs(release/'defense/core.py')
assert set(a)==set(b) and [k for k in a if a[k]!=b[k]]==['Controller']
for n in ['run_vwa_pilot.py','plan80.json','native-vwa-request.json','defense/prompts.py','defense/schema.py','defense/http_backend.py','defense/qwen_backend.py']:assert (old/n).read_bytes()==(release/n).read_bytes(),n
# No model call: bind actual native parser/defaults, browser and official evaluator sources.
code=r'''
import hashlib,json,os
from pathlib import Path
assert os.getuid()==1015
b=Path('/data/researcher/vwa100-2026-10-09');u=b/'upstream/visualwebarena-main'
paths=[b/'run_reddit_internvl_smoke.py',b/'selected100-classifieds-reddit/evaluator_configs_v1/classifieds_112.json',u/'browser_env/envs.py',u/'browser_env/actions.py',u/'browser_env/auto_login.py',u/'evaluation_harness/evaluators.py']
out={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
cfg=json.loads(paths[1].read_bytes());assert cfg['require_reset']is False and cfg['eval']['eval_types']==['url_match']
print(json.dumps({'runtime_source_bindings':out,'require_reset':False,'official_eval_types':['url_match'],'expected_answer_transferred':False}))
'''
runtime=json.loads(remote(code,host='4090',timeout=60));(out/'runtime-source-bindings.json').write_text(json.dumps(runtime,indent=2))
oldparser=json.loads((Path(json.loads((PREP/'inspection-current.json').read_bytes())['collected_root'])/'native-parser-binding.json').read_bytes())
assert runtime['runtime_source_bindings'][oldparser['path']]==oldparser['sha256']
# Exercise the decision gate locally without importing/executing remote launch main.
proposal_hash='0'*64;good={'approved':True,'proposal_sha256':proposal_hash,'scope':'one-new-scoped-joint-stale-fullgui','user_authorization_text':'TEST ONLY, not user approval; never persisted as authorization'}
bad=[{},dict(good,approved=False),dict(good,proposal_sha256='1'*64),dict(good,scope='all-old-queues'),dict(good,user_authorization_text='')]
for value in bad:
 try:validate_decision(value,proposal_hash)
 except ValueError:pass
 else:raise AssertionError('Decision guard accepted invalid scope')
assert validate_decision(good,proposal_hash)==good
proposal={'version':'evidence-v4.0-dev-scoped-direction-source-20261028','status':'READY_FOR_USER_CONDITION_DECISION',
 'scope':'Exactly one NEW independent joint/stale fullGUI development validation of known VWA classifieds112, no rerun/resume old terminal, no baseline or other queues',
 'run_selector':'vwa--classifieds_112--stale_replace--joint','release':str(release),'remote_release':stage['remote_preparation_root']+'/release',
 'release_manifest_sha256':stage['release_manifest_sha256'],'original_runner_plan_template_byte_unchanged':True,'strict_validator_and_Limits_AST_unchanged':True,
 'source_review':'Original adf73f7250e7c182 full release compared: only Controller AST changes plus imports/version identification; original prompts.py/schema/backends byte-identical. New separate scoped prompt/helper modules. No old source/terminal rewritten.',
 'condition_changes':['Scene readiness assesses possible next observation instead of target visibility; same candidate-blind projection','Candidate verifier source-atomization appendix and actual image inventory','Narrow affirmative absent image-reference check after strict validators, original1formatretry','Explicit prose/native-scroll direction conflict check with original bounded regeneration, no action edits','Feedback origin separately records original judge reason and selected rule reason'],
 'fixed':{'model':'original27B','precision':'BF16','backend':'SDPA','native_full_history':True,'native_images':[1280,720],'actor_output_tokens':2048,'judge_output_tokens':4096,'seed':20261011,'max_steps':50,'max_actor_calls':70,'max_verifier_calls':140,'max_format_retries':1,'max_regenerations':2,'max_recaptures':2,'same_live_recapture':'env._get_obs','injection':'Original first changed frame after eligible native action, stale previous delivered image','scoring':'original URL-match official scorer, expected URL remains private'},
 'cost':'At most70actor+140verifier calls within original per-trajectory caps, no extra format/recovery budgets, no paidAPI. Existing5GPU deployment counted separately from old7GPU; no currency/energy or bitwise equivalence assumption.',
 'tradeoff':'Accepting a coherent footer can avoid target-visibility false blocks and permit exploratory recovery, but can also admit a coherent wrong destination. All action/history/point/focus/completion checks remain. More source/direction checks can spend existing budgets and cause false blocks. Readiness usable never approves task completion or unseen targets.',
 'residuals':['Real diagnostic still misses blue focus cue','Current unrelated query overextended to no prior basketball search','Some insufficient atomic claims labelled contradicted','Source-reference rejection not naturally exercised online','No new natural actorWAIT or visible-loading positive; authored WAIT is excluded','Full-history/point/completion combined CPU invariants passed, but current new protocol real end-to-end behavior untested'],
 'completed_preparation':{'local_CPU_tests':162,'remote_CPU_tests':162,'decision_guard_cases':6,'logged_in_native_environment_preflight':'completed,0modelcalls','same_live_two_captures':'actually captured1280x720 and independently viewed; My account/Logout visible','official_scorer_transport':'original evaluator loaded; runtime config/source SHA bound, no scoring yet','actual_worker_uid':1015,'actual_full_command_and_inherited_locks_verified':True,'environment_worker_exited':True,'model_calls_in_preparation':0,'GUI_model_actions':0,'site_reset_or_import':False},
 'interpretation':'Single known task development only; success/block/official1 is not efficacy, no first-trigger reduction claim. Label initial/accepted/executed semantic errors independently, keep WAIT excluded and uncertainty. Full task and new failures must be sealed before any diagnosis, no terminal retries.',
 'human_decision_required':'Existing user protocol explicitly requires exact condition/tradeoff decision before new formal actor-feedback condition. This proposal is not authorization.',
 'decision_scope':'one-new-scoped-joint-stale-fullgui','launcher':str(BASE/'launch_scoped_fullgui.py'),'launcher_requires_exact_proposal_SHA_decision':True,
 'remote_active_must_not_exist':'scoped-fullgui-active-20261028.json','formal_release':False,'no_full_trajectory_started':True,'runtime_source_bindings':runtime['runtime_source_bindings']}
(out/'fullgui-proposal.json').write_text(json.dumps(proposal,ensure_ascii=False,indent=2),encoding='utf-8')
report='''# 新防御完整GUI单轮验证：待条件决定

本轮10个场景/候选探针已完成，原始数据和语义限制已封存。下一步建议只做一个新的joint＋stale完整GUI开发验证：VWA classifieds112原篮球任务，独立新根，50步、70actor/140judge、2048/4096输出、2重新生成/2实时回采/1格式重试、原seed/原生解析器/完整历史/1280×720/官方URL评分均保持。没有扩大到60配置，没有重启任何旧终局或27B注意力。

新版本只在Controller加入已完成预检的场景范围提示、事实拆分/图片inventory、显式不存在图片引用检查、文字与原生方向矛盾检查和反馈来源记录。已与原adf73f7250e7c182逐SHA/AST比较：严格validator及Limits不变，原runner/plan/native template/prompts.py/schema/backend字节一致。版本标记单列v4.0-dev，不能混作旧v3.9.9结果。

取舍是：正常但目标屏外的页脚可进入后续探索，能减少这一类可用性误拦；可读的错误目的地也可能进入actor，因此必须继续原逐候选/点/焦点/历史/完成检查。新来源/方向检查也可能耗尽原重试预算并增加误拦。当前蓝框误读、历史过推、insufficient/contradicted强度错误仍保留，不以新提示保证正确。

本地和4090远端分别162项CPU集成/回归通过（122原相关控制＋40方向/来源/场景控制）。旧4项精确断言旧readiness提示的测试原样保留在原目录，由新投影/回采测试覆盖改变的接口；非相关audit/scroll-helper/UI设备测试不计入。另6项决定范围检查通过，不能当语义准确率。

已在新owned根完成原native runner的0推理登录环境预检：UID1015、实际完整命令与5个继承锁核实，1280×720原截图和同一live env._get_obs回采均实际获取并独立查看，My account/Logout可见；原官方evaluator加载通过，任务配置require_reset=false且仅url_match。原生parser/browser/evaluator/任务配置实际源码SHA冻结，预检子进程已正常退出。没有reset/import、模型GUI动作、官方评分或GPU推理新分配。原服务5GPU健康已另核实。

上限为原单轨迹70actor＋140judge调用；现有五卡服务相对历史七卡单列，不假定逐位/成本等价。只用本地模型，无付费API。一个任务的完成或官方1不能证明防御效力，发生后恢复也不抵消最初Mirage。

launch_scoped_fullgui.py已经准备，只有匹配fullgui-proposal.json精确SHA、范围one-new-scoped-joint-stale-fullgui的明确人类决定才能继续；启动前再核实服务、站点ID/owner/端口、原生源码、完整release SHA、任务锁及一次性active。尚未创建fullGUI active或启动轨迹。需要这一次决定来自原实验协议“解释条件改变并等待用户决定”，不是资源授权重问。
'''
rp=BASE/'新防御完整GUI单轮验证条件与取舍-20261028.md';assert not rp.exists();rp.write_text(report,encoding='utf-8')
review={'original_source_reviewed':True,'only_Controller_AST_changed':True,'strict_validator_AST_unchanged':True,'all_original_limits_unchanged':True,'source_guard_not_general_semantic_validator':True,'readiness_old_projection_unchanged':True,'new_modules_sha256':{n:sha((release/n).read_bytes())for n in ['scoped_observability.py','native_direction_consistency.py','native_direction_feedback_origin.py']},'environment_two_images_independently_viewed':True,'no_fullGUI_execution_yet':True,'no_inference_in_preparation':True,'remaining_precondition':'Only explicit human condition decision, then mandatory fresh ownership/source/health check by prepared launcher', 'formal_release':False}
(out/'source-review.json').write_text(json.dumps(review,indent=2))
(out/'preparation-seal.json').write_text(json.dumps({str(p.relative_to(out)).replace('\\','/'):sha(p.read_bytes())for p in out.rglob('*')if p.is_file()and'__pycache__'not in str(p)},ensure_ascii=False,indent=2),encoding='utf-8')
ready={'directory':str(out),'proposal':str(out/'fullgui-proposal.json'),'proposal_sha256':sha((out/'fullgui-proposal.json').read_bytes()),'report':str(rp),'report_sha256':sha(rp.read_bytes()),'release_manifest_sha256':stage['release_manifest_sha256'],'runtime_source_bindings':runtime['runtime_source_bindings'],'preparation_seal_sha256':sha((out/'preparation-seal.json').read_bytes()),'launcher_sha256':sha((BASE/'launch_scoped_fullgui.py').read_bytes()),'status':'READY_FOR_USER_CONDITION_DECISION','fullGUI_started':False,'new_model_calls':0}
(PREP/'fullgui-ready-current.json').write_text(json.dumps(ready,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in ready.items()if k!='runtime_source_bindings'},ensure_ascii=False))
