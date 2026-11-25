import hashlib,json,pathlib,shutil,subprocess,sys,tarfile,time
B=pathlib.Path(__file__).parent;P=B/'package';P.mkdir(exist_ok=True)
M=json.loads((B/'appearance-absence-repair-development/stage-1793275195957987900/source-sha256.json').read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in (B/'verified-release').rglob('*.py'):
 rel=p.relative_to(B/'verified-release');out=P/'release'/rel;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(p.read_bytes())
for name in ['resume_service.py','run_remaining_preflight.py','orchestrate_preflight.py','original-runtime.json','prompt-string-service-binding.json']:
 shutil.copy2(B/name,P/name)
shutil.copytree(B/'restored-inputs',P/'restored-inputs',dirs_exist_ok=True)
input_checks=[]
for p in (P/'restored-inputs/inputs').glob('*.json'):
 assert sha(p)==M['inputs/'+p.name],p
 input_checks.append({'name':p.name,'sha256':sha(p),'original_exact':True})
for p in(P/'restored-inputs/images').glob('*.png'):assert sha(p)==p.stem
cases=[]
for i in range(1,9):
 identity='w%02d'%i;mode='verify'if i==8 else 'routing'if i==7 else'relation-after-w01'if i in [3,4]else'check'
 cases.append({'id':identity,'mode':mode,'packet':'inputs/'+identity+'.json','packet_sha256':M['inputs/'+identity+'.json']})
original_plan={'cases':cases,'max_calls':24,'formal_release':False,'max_format_retries':1}
assert hashlib.sha256(json.dumps(original_plan,indent=2).replace('\n','\r\n').encode()).hexdigest()==M['plan.json']
plan={'created':time.time(),'parent_root':'appearance-absence-repair-preflight-1793275223685095909','prior_submitted_model_calls':1,'max_new_calls':23,'prior_terminal':{'service_request':'1793275238049158233','input_tokens':1598,'output_tokens':4096,'hit_output_cap':True,'natural_EOS':False},'remaining_cases':cases[2:],'excluded_cases':[{'id':'w01','status':'prior_completed_technical_output_cap','reason':'Keep original4096 cap; no same-source retry'},{'id':'w02','status':'blocked_on_failed_shared_person_read','reason':'Complete original history contains the same3e254 source; no repeated capped read or partial-response reuse'}],'new_GUIs':0,'formal_release':False}
(P/'resume-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
sealed={str(p.relative_to(P/'restored-inputs')).replace('\\','/'):sha(p)for p in(P/'restored-inputs').rglob('*')if p.is_file()and p.suffix in ['.png','.json']}
(P/'sealed-inputs.json').write_text(json.dumps(sealed,indent=2),encoding='utf-8')
source_checks=[]
runtime_names=['defense/'+n for n in ['__init__.py','core.py','prompts.py','schema.py','qwen_backend.py','http_backend.py']]+['appearance_absence_source.py','compact_price_frame_binding.py','price_history_frame_binding.py','minimum_price_reason_scope.py','pagination_count_reason_scope.py','focus_history_conflict_scope.py','scene_only_readiness.py','current_only_history_scope.py','focus_history_scope.py','native_direction_consistency.py','scoped_observability.py','native_direction_feedback_origin.py','strict_price_comparison.py','completion_frame_price_source.py']
for n in runtime_names:
 actual=sha(P/'release'/n);expected=M['release/'+n];source_checks.append({'path':n,'expected_sha256':expected,'restored_sha256':actual,'byte_exact':actual==expected})
 assert actual==expected or n=='defense/prompts.py',n
ns={};exec((P/'release/defense/prompts.py').read_text(encoding='utf-8'),ns);bindings=json.loads((P/'prompt-string-service-binding.json').read_bytes())
for k,v in bindings.items():assert hashlib.sha256(ns[k].encode()).hexdigest()==v['exact_string_sha256'] and v['present_exactly']
admission={'user_instruction':'2026-11-02 防御的实验继续启动','full_GUI_authorized_by_this_launch':False,'original_122_passed':'Ran 122 tests'in(B/'restored-original-tests.txt').read_text(encoding='utf-8')and'\nOK'in(B/'restored-original-tests.txt').read_text(encoding='utf-8'),'available_supplemental_191_passed':'Ran 191 tests'in(B/'restored-available-supplemental-tests.txt').read_text(encoding='utf-8')and'\nOK'in(B/'restored-available-supplemental-tests.txt').read_text(encoding='utf-8'),'six_historical_tests_unrunnable_missing_archived_fixtures':True,'original_input_packets_exact':len(input_checks),'input_checks':input_checks,'source_checks':source_checks,'source_restoration_limit':'prompts.py whole-file SHA remains different; VERIFY, FACTUAL_SOURCE_ROUTING and HISTORY_REPORT exact strings bound to actual archived service requests. The new single-frame/absence/epistemic prompts and core/schema/backends are byte-exact to archived manifest. No claim of full source-tree restoration. Only the scoped remaining controls admitted.','max_new_calls':23,'original_total_cap':24,'original_full_inputs_BF16_SDPA':True,'four_GPU_deployment':'New balanced physical1,2,3,4; no bitwise/cost equivalence to prior five GPUs','formal_release':False}
assert admission['original_122_passed'] and admission['available_supplemental_191_passed']
(P/'admission.json').write_text(json.dumps(admission,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'package-sha256.json').write_text(json.dumps({str(p.relative_to(P)).replace('\\','/'):sha(p)for p in P.rglob('*')if p.is_file()and'__pycache__'not in str(p)and p.name!='package-sha256.json'},indent=2),encoding='utf-8')
for n in ['orchestrate_preflight.py','resume_service.py','run_remaining_preflight.py']:compile((P/n).read_text(encoding='utf-8'),n,'exec')
with tarfile.open(B/'resume-package.tar.gz','w:gz')as tar:
 for p in P.rglob('*'):
  if p.is_file():tar.add(p,arcname=str(p.relative_to(P)).replace('\\','/'))
print(json.dumps({'package':str(P),'inputs_exact':len(input_checks),'runtime_exact':sum(x['byte_exact']for x in source_checks),'runtime_total':len(source_checks),'size':(B/'resume-package.tar.gz').stat().st_size}))
