"""Freeze memory-only buffer reuse and a smaller GPU0 weight budget."""
import ast,json,secrets,shutil,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;prior=BASE/'flash-ample-memory-gui-20261114-linked04';old=prior/'package'
assert not(HERE/'package').exists()
for n in ['control.py','launch_group.py','capture_live_evidence.py','audit_flash_live.py','inspect_terminals.py','preserve_terminal.py','peek.py','publish_progress.py']:
 text=(prior/n).read_text(encoding='utf8').replace('flash-ample-memory-gui-20261114-linked04','flash-ample-memory-gui-20261114-linked05')
 (HERE/n).write_text(text,encoding='utf8')
from control import save,sha,R3090,R4090,OUT
for n in ['capacity_gate.py','memory_lifetime.py','torch_chunk_lifetime.py','inspect_ready.py']:(HERE/n).write_bytes((prior/n).read_bytes())
text=(HERE/'memory_lifetime.py').read_text(encoding='utf8')
text=text.replace('def capture_three(engine,body,root,expected,code,torch,save):','def capture_three(engine,body,root,expected,code,torch,save,mlp_code=None):')
text=text.replace("counts={'patched_or_baseline_kernel_calls':0}","counts={'patched_or_baseline_kernel_calls':0,'actual_MLP_calls':0}")
text=text.replace("if event=='call'and frame.f_code is code:counts['patched_or_baseline_kernel_calls']+=1","if event=='call'and frame.f_code is code:counts['patched_or_baseline_kernel_calls']+=1\n        if event=='call'and frame.f_code is mlp_code:counts['actual_MLP_calls']+=1")
text=text.replace("    save(root/'invariance-record.json',", "    assert counts['actual_MLP_calls']==192\n    save(root/'invariance-record.json',")
text=text.replace("'input_tokens':prepared['input_ids']['shape'][-1]}","'input_tokens':prepared['input_ids']['shape'][-1],'actual_MLP_calls':counts['actual_MLP_calls']}")
text=text.replace("    save(root/'source-proof.json',proof)","    from mlp_lifetime import prepare\n    mlp,mlp_original_code,mlp_candidate_code,mlp_proof=prepare(torch,module,engine.model,root,save,sha)\n    proof['arithmetic_AST_scope']='chunk delta core only; MLP buffer reuse separately source-bound and bitwise tested'\n    proof['MLP_memory_proof']=mlp_proof\n    save(root/'source-proof.json',proof)")
text=text.replace("expected,original_code,torch,save)","expected,original_code,torch,save,mlp_original_code)")
text=text.replace("    raw.__code__=candidate.__code__","    raw.__code__=candidate.__code__\n    mlp.__code__=mlp_candidate_code")
text=text.replace("expected,candidate.__code__,torch,save)","expected,candidate.__code__,torch,save,mlp_candidate_code)")
text=text.replace("'actual_chunk_calls_per_pass':48,","'actual_chunk_calls_per_pass':48,'actual_MLP_calls_per_pass':192,")
text=text.replace("        raw.__code__=original_code","        raw.__code__=original_code\n        mlp.__code__=mlp_original_code")
(HERE/'memory_lifetime.py').write_text(text,encoding='utf8')
text=(HERE/'inspect_ready.py').read_text(encoding='utf8').replace("assert proof['only_dead_local_deletions_added']and proof['kernel_tests']==9", "assert proof['only_dead_local_deletions_added']and proof['MLP_memory_proof']['all_tests_passed']and proof['actual_MLP_calls_per_pass']==192 and proof['kernel_tests']==9")
(HERE/'inspect_ready.py').write_text(text,encoding='utf8')
out=HERE/'package';out.mkdir();m0=json.loads((old/'manifest.json').read_bytes())
for n,h in m0['files'].items():
 assert sha(old/n)==h
 target=out/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,target)
for n in ['capacity_gate.py','memory_lifetime.py','torch_chunk_lifetime.py','mlp_lifetime.py','launch_group.py']:shutil.copyfile(HERE/n,out/n)
text=(out/'primary_server.py').read_text(encoding='utf8');needle="max_memory={i:'20GiB'for i in range(7)}";assert text.count(needle)==1
text=text.replace(needle,"max_memory={0:'3500MiB',**{i:'20GiB'for i in range(1,7)}}")
(out/'primary_server.py').write_text(text,encoding='utf8')
preserved=json.loads(max(prior.glob('preservation-*.json'),key=lambda p:p.stat().st_mtime_ns).read_bytes())['result']
binding=json.loads((out/'capacity-source.json').read_bytes());binding.update({'linked04_postexit_seal_sha256':preserved['postexit_seal_sha256'],'repair':'Original per-head numerical chunk AST plus unaliased MLP elementwise product buffer reuse; native balanced GPU0 weight budget3500MiB reserves vision headroom. Full stress IDs and 3 full-logit cached steps required.'})
(out/'capacity-source.json').write_text(json.dumps(binding,ensure_ascii=False,indent=2),encoding='utf8')
plan=json.loads((out/'plan.json').read_bytes());plan.update({'version':'Flash-seven-GPU-MLP-buffer-vision-headroom-linked05','created':time.time(),'memory_scheduling':'Original chunk-head shape/core arithmetic retained; reuse dead SiLU MLP output buffer for the identical elementwise product; GPU0 weight budget3500MiB, others20GiB with native balanced placement. Full inputs/BF16 unchanged, both arms same deployment.','capacity':'9 original chunk controls plus actual-weights MLP controls; original versus repaired three-step full logits; new50 EOS IDs identical to preserved linked02; >=3GiB peak reserved headroom on every GPU','minimum_peak_reserved_headroom_GiB':3})
(out/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
auth=json.loads((out/'user-memory-authorization.json').read_bytes());auth['linked_repair_scope']=plan['memory_scheduling']+' No input/prompt/semantic gate change, no CPU/disk model offload; exact numerical validation required.'
(out/'user-memory-authorization.json').write_text(json.dumps(auth,ensure_ascii=False,indent=2),encoding='utf8')
save(out/'linked04-preservation-binding.json',{'postexit_seal_sha256':preserved['postexit_seal_sha256'],'postexit_files_verified':preserved['postexit_files_verified'],'complete50_preserved':True,'readiness_failed_not_OOM':True,'formal_GUI_calls':0})
(out/'private.token').write_text(secrets.token_hex(32),encoding='utf8')
files={p.relative_to(out).as_posix():sha(p)for p in out.rglob('*')if p.is_file()and p.name not in ['manifest.json','private.token']and '__pycache__'not in p.parts}
for n in files:
 if n.endswith('.py'):ast.parse((out/n).read_text(encoding='utf8'))
m={**m0,'version':plan['version'],'created':time.time(),'files':files,'auth_token_sha256':sha(out/'private.token'),'output3090':OUT,'package3090':R3090,'package4090':R4090,'source_prior_manifest_sha256':sha(old/'manifest.json'),'head_batching':False,'GPU0_weight_budget':'3500MiB','other_primary_weight_budget':'20GiB','MLP_product_buffer_reuse':True}
save(out/'manifest.json',m);save(HERE/'frozen-package.json',{'files':len(files),'manifest_sha256':sha(out/'manifest.json'),'new_model_GUI_calls':0})
(HERE/'README.md').write_text('''# 七卡主27B与独立Flash，linked05显存续跑

用户明确充裕显存继续至可复核降低Mirage。3090主物理0–6、Flash7；原UID/命令/start/UUID、主17锁/Flash9锁与全部compute逐次核验，不抢占外人。仅续29未开始，原2正常+1OOM终局不重跑；新七任务14完整匹配对，T000旧帧门控单列诊断。

Flash完整单图+固定通用问题、无任务/主上下文/候选/前图/累积KV，YES同PNG给主模型、无附加文字概率，NO等待0.5秒同环境持续新复拍至YES或手停；技术失败不当NO。全部原图、接受历史、BF16/SDPA、2048输出、50决策/70actor和原生提示/解析/执行/评分/seed保持。无旧上下文语义judge，不恢复旧队列。

原七卡50图OOM，linked02完整50图EOS但最小余量0.84GiB，linked03head分组逐位失败拒绝，linked04再删死value/attn后全词表逐位和完整50图126IDs相同，但最小reserved余量1.41GiB，仍未通过3GiB。全部独立封存，不重跑旧启动器。

本linked05保留原chunk head形状和数值AST，仅加入既有dead-local删除；另让MLP的未再使用SiLU输出缓冲承接相同逐元素乘法，避免另分配整个中间张量。MLP仍执行原gate/up/down线性与SiLU，权重/输入不改；不声称该MLP的AST相同，必须实际逐字节检查。主GPU0仅给权重3500MiB、其他20GiB并保持native balanced，为图像编码腾出余量；无CPU/disk模型offload。两正式臂一致。9个原chunk检查、每实际MLP GPU真实权重的1/65token完整输出和输入未改检查、真实15图连续3步全词表logits/IDs一致，以及新完整50图自然EOS全部IDs与linked02相同且每卡reserved峰值余量>=3GiB，全部通过后才开放GUI。

容量压力是标明合成重复历史，不是GUI50步，也不证明任意未来历史/每步2048输出最坏容量。3token工程cap不算正式EOS。旧15图完整EOS复用。原始wire/tensor/有效配置/输出IDs,EOS/回复/日志/seals/事件链保留；相同原tensor完整字节SHA相同后可硬链接，不以摘要替代证据。

新技术失败保全后停，修复用新关联attempt；不热改冻结源、不重刷终局、不缩图/截史/降精度/扩预算。手停4090根目录STOP。效果仍待完整配对、逐候选语义与误拦/等待/官方完成审查；纠正不抹去Mirage，pureWAIT排除，未知不当无Mirage，单图不保证清晰旧帧新鲜。目标active，降幅null，不能靠一直等/少动作/分数或挑阳性称有效。
''',encoding='utf8')
print(json.dumps({'files':len(files),'manifest_sha256':sha(out/'manifest.json'),'remaining_GUI':29,'buffer_reuse_and_vision_headroom':True}))
