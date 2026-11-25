"""Create a separate linked source package; retain every old terminal and source."""
import ast,copy,json,secrets,shutil,time
from pathlib import Path
from control import HERE,BASE,OLD,R3090,R4090,OUT,save,sha

old=OLD/'package-linked02';out=HERE/'package';assert not out.exists();out.mkdir()
manifest=json.loads((old/'manifest.json').read_bytes())
for n,h in manifest['files'].items():
 assert sha(old/n)==h,n
 p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,p)

def change(text,a,b):
 assert text.count(a)==1,(a,text.count(a))
 return text.replace(a,b)

text=(old/'primary_server.py').read_text(encoding='utf8')
start=text.index('def resource(loaded):');end=text.index('\nclass NativeActor:',start)
text=text[:start]+"def resource(loaded):\n    from expanded_guard import resource as expanded_resource\n    return expanded_resource(P,loaded)\n"+text[end:]
text=change(text,"max_memory={i:'22GiB'for i in range(3)}","max_memory={i:'20GiB'for i in range(7)}")
text=change(text,"['cuda:0','cuda:1','cuda:2']","['cuda:'+str(i)for i in range(7)]")
text=change(text,"'physical_gpus':[4,5,6]","'physical_gpus':list(range(7))")
text=change(text,"with p.open('xb')as f:f.write(data)","from evidence_store import store\n            source=folder/prepared[name.removeprefix('first_forward_')]['file']if name.startswith('first_forward_')and name.removeprefix('first_forward_')in prepared else None\n            storage=store(p,data,source)")
text=change(text,"'sha256':digest(data),'file':p.name}","'sha256':digest(data),'file':p.name,'storage':storage}")
text=change(text,"state('loading');native=NativeActor(root);journal.emit('loaded',{'loaded_sha256':sha(root/'loaded.json')});state('ready')","state('loading');native=NativeActor(root);journal.emit('loaded',{'loaded_sha256':sha(root/'loaded.json')})\n        state('capacity_preflight')\n        from capacity_gate import run as capacity_run\n        capacity_result=capacity_run(native,P,root,save,sha,resource)\n        journal.emit('capacity_passed',{'terminal_sha256':sha(root.parent/'capacity/terminal.json'),'capacity_generation_calls':2})\n        state('ready')")
text=change(text,"http://127.0.0.1:18341/decision","http://127.0.0.1:18342/decision")
text=text.replace("('192.0.2.11',19201)","('192.0.2.11',19202)").replace("http://192.0.2.11:19201","http://192.0.2.11:19202")
(out/'primary_server.py').write_text(text,encoding='utf8')

gui=(old/'gui_experiment.py').read_text(encoding='utf8').replace('32 new complete native GUI trajectories','29 unstarted linked native GUI trajectories').replace('http://192.0.2.11:19201','http://192.0.2.11:19202')
gui=change(gui,"            transport.request('/end',{'run_id':item['run_id'],'terminal_sha256':sha(attempt/'terminal.json'),'infrastructure_failure':infrastructure})","            try:transport.request('/end',{'run_id':item['run_id'],'terminal_sha256':sha(attempt/'terminal.json'),'infrastructure_failure':infrastructure})\n            except Exception:\n                infrastructure=True\n                save(attempt/'end-notification-failure.json',{'error':traceback.format_exc(),'not_a_semantic_failure':True,'original_terminal_preserved':True,'no_automatic_retry':True})\n                log.emit('end_notification_failure',{'terminal_sha256':sha(attempt/'terminal.json'),'preserved':True})")
(out/'gui_experiment.py').write_text(gui,encoding='utf8')
for n in ['expanded_guard.py','evidence_store.py','capacity_gate.py','launch_group.py']:shutil.copyfile(HERE/n,out/n)
cfg=json.loads((out/'flash/service-config.json').read_bytes());cfg['port']=18342
(out/'flash/service-config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')

evidence=json.loads((OLD/'experiment-current.json').read_bytes());s=json.loads(Path(evidence['status']).read_bytes());e=Path(s['evidence']);audited=json.loads((e/'summary.json').read_bytes())
excluded={t['run']['run_id']for t in audited['normal_results']}|{q['run_id']for q in audited['failed_requests']}
assert len(excluded)==3
prior=json.loads((old/'plan.json').read_bytes());plan=copy.deepcopy(prior)
queue=[]
for row in prior['queue']:
 if row['run_id']in excluded:continue
 new=copy.deepcopy(row);new['prior_unstarted_run_id']=new['run_id'];new['run_id']=new['run_id'].replace('flash13-','flash14-');queue.append(new)
assert len(queue)==29
plan.update({'version':'Flash-single-image-seven-GPU-primary-continuation-v2','created':time.time(),'queue':queue,'expected_trajectories':29,'matched_pairs':14,'unmatched_additional_trajectory':'T000 stale gate; prior baseline technical failure excluded from semantic comparison','main_gpu_physical':list(range(7)),'Flash_gpu_physical':7,'excluded_prior_terminals':sorted(excluded),'new_deployment_condition':'User-authorized seven-card primary balanced BF16/SDPA, independent Flash GPU7; allocator expandable_segments; both continuation arms identical. Old three-card terminals remain a separate stratum. No bitwise identity promised.','capacity':'One exact unfinished source input replay plus explicit synthetic 50-image stress input; separate capacity calls, not formal semantic outcomes.','main_memory_limit':'20GiB placement ceiling per primary GPU, seven devices; measured peak headroom must be >=3GiB in capacity probes.'})
(out/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
failed=audited['failed_requests'][0]
save(out/'capacity-source.json',{'source_request':failed['directory'],'wire_sha256':failed['wire_sha256'],'seal_sha256':failed['seal_sha256'],'prior_input_tokens':15367,'prior_images':15,'purpose':'new independent capacity validation after explicitly authorized deployment expansion; no GUI replay or semantic/control relabel'})
save(out/'continuation-provenance.json',{'prior_manifest_sha256':sha(old/'manifest.json'),'postexit_status_sha256':evidence['status_sha256'],'excluded_terminals':sorted(excluded),'remaining':queue,'old_complete_or_failed_trajectories_reexecuted':False,'source_generation_AST_unchanged':True,'Flash_model_prompt_interface_unchanged':True,'native_parser_executor_scorer_and_main_template_unchanged':True})
save(out/'user-memory-authorization.json',{'date':'2026-11-14 Asia/Shanghai','request':'按照充裕的显存预算跑起来，目标是跑出效果为止','prior_resource_inspection':'User was shown eight empty GPUs immediately before instruction.','authorized_interpretation':'Use all eight free and exclusively lockable 3090 GPUs: seven original27B, one Flash; preserve BF16, full histories/images, native prompts and per-trajectory budgets.','NO_policy':'持续复拍，直到 YES 或手动停止','no_foreign_preemption':True,'no_paid_API':True,'no_old_queues_resumed':True})
# Original launch-authorization is immutable history, new authority is above.
save(out/'analysis-plan.json',{'primary_metric':'within each condition, paired complete trajectories with at least one definite boundary-inclusive Mirage; pure native WAIT excluded','secondary_metrics':['definite positive candidates and accepted/executed positives','normal-operation false blocks and NO duration/recaptures','official success and technical failure counts separately','eight reserved-GPU seconds and per-device memory; no invented currency/energy'], 'planned_full_pairs':14,'independent_tasks_in_new_paired_stratum':7,'unpaired_T000_stale_gate':'diagnostic, excluded from paired effect denominator','old_three_card_T000_clean':'separate historical stratum, not pooled as seven-card outcome','effects_not_assumed':True,'claim_policy':'Report complete coverage, uncertainty and paired effect estimates; no significance claim merely from startup/YES/official score; do not erase an occurrence after recovery or quietly change labels/stopping criteria to seek success','raw_review_before_execution_join':True,'Mirage_reduction':None})
(out/'private.token').write_text(secrets.token_hex(32),encoding='utf8')
files={str(p.relative_to(out)).replace('\\','/'):sha(p)for p in out.rglob('*')if p.is_file()and p.name not in ['manifest.json','private.token']and '__pycache__'not in p.parts}
for n in files:
 if n.endswith('.py'):ast.parse((out/n).read_text(encoding='utf8'))
m={'version':plan['version'],'created':time.time(),'files':files,'auth_token_sha256':sha(out/'private.token'),'output3090':OUT,'package3090':R3090,'package4090':R4090,'trajectories':29,'remaining_queue':queue,'main_url':'http://192.0.2.11:19202','source_prior_manifest_sha256':sha(old/'manifest.json'),'Flash_contract_sha256':sha(out/'flash/gate-contract.json'),'native_actor_template_sha256':sha(out/'actor-template.json'),'ample_memory_authorized':True,'user_memory_authorization':'按照充裕的显存预算跑起来，目标是跑出效果为止','main_physical_gpus':list(range(7)),'Flash_physical_gpu':7,'no_old_terminal_rerun':True}
save(out/'manifest.json',m)
save(HERE/'frozen-package.json',{'manifest_sha256':sha(out/'manifest.json'),'files':len(files),'new_model_GUI_calls':0,'source_prior_manifest_sha256':sha(old/'manifest.json')})
print(json.dumps({'manifest_sha256':sha(out/'manifest.json'),'files':len(files),'remaining_trajectories':len(queue),'paired_tasks':7,'full_pairs':14}))
