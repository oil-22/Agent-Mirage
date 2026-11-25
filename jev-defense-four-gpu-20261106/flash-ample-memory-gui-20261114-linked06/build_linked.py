"""Freeze explicit CPU-planned placement and pointwise buffer lifetimes."""
import ast,json,secrets,shutil,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;prior=BASE/'flash-ample-memory-gui-20261114-linked05';old=prior/'package'
assert not(HERE/'package').exists()
for n in ['control.py','launch_group.py','capture_live_evidence.py','audit_flash_live.py','inspect_terminals.py','preserve_terminal.py','peek.py','wait_capacity.py','publish_progress.py']:
 text=(prior/n).read_text(encoding='utf8').replace('flash-ample-memory-gui-20261114-linked05','flash-ample-memory-gui-20261114-linked06')
 (HERE/n).write_text(text,encoding='utf8')
from control import save,sha,R3090,R4090,OUT
for n in ['capacity_gate.py','memory_lifetime.py','torch_chunk_lifetime.py','mlp_lifetime.py','inspect_ready.py']:(HERE/n).write_bytes((prior/n).read_bytes())
text=(HERE/'torch_chunk_lifetime.py').read_text(encoding='utf8')
for before,after in [('    query = query * scale','    query.mul_(scale)'),('        attn[..., i, :i] = row + (row.unsqueeze(-1) * sub).sum(-2)','        torch.mul(row.unsqueeze(-1), sub, out=sub)\n        attn[..., i, :i] = row + sub.sum(-2)'),('    k_cumdecay = attn @ (k_beta * g.exp().unsqueeze(-1))','    k_beta.mul_(g.exp().unsqueeze(-1))\n    k_cumdecay = attn @ k_beta')]:
 assert text.count(before)==1; text=text.replace(before,after)
(HERE/'torch_chunk_lifetime.py').write_text(text,encoding='utf8')
normalizer='''def normalize_buffer_destinations(source):
    pairs=[('    query.mul_(scale)','    query = query * scale'),('        torch.mul(row.unsqueeze(-1), sub, out=sub)\\n        attn[..., i, :i] = row + sub.sum(-2)','        attn[..., i, :i] = row + (row.unsqueeze(-1) * sub).sum(-2)'),('    k_beta.mul_(g.exp().unsqueeze(-1))\\n    k_cumdecay = attn @ k_beta','    k_cumdecay = attn @ (k_beta * g.exp().unsqueeze(-1))')]
    if 'query.mul_(scale)'in source:
        for changed,original in pairs:
            assert source.count(changed)==1
            source=source.replace(changed,original)
    return source

'''
text=(HERE/'memory_lifetime.py').read_text(encoding='utf8');text=text.replace('def arithmetic_ast(source):',normalizer+'def arithmetic_ast(source):\n    source=normalize_buffer_destinations(source)')
text=text.replace("'all_numerical_AST_nodes_unchanged':True,'only_dead_local_deletions_added':True,'weights_precision_attention_kernel_and_reduction_order_unchanged':True", "'all_numerical_AST_nodes_unchanged':False,'only_dead_local_deletions_added':False,'normalized_arithmetic_AST_equal_after_restoring_product_destinations':True,'only_private_dead_pointwise_output_buffers_reused':True,'original_matmul_reduction_and_elementwise_operand_order_preserved':True")
text=text.replace("'chunk delta core only; MLP buffer reuse separately source-bound and bitwise tested'", "'chunk scalar, row-product and k_beta-product destination rewrites normalized explicitly back to original expressions before AST equality; MLP separately source-bound and bitwise tested'")
(HERE/'memory_lifetime.py').write_text(text,encoding='utf8')
text=(HERE/'mlp_lifetime.py').read_text(encoding='utf8').replace('def forward(self,x):\n','def forward(self,x):\n    if x.is_cuda and x.shape[-2]>8192:\n        torch.cuda.empty_cache()\n')
text=text.replace("'input_or_weights_not_modified':True,", "'input_or_weights_not_modified':True,'allocator_unused_blocks_released_before_long_MLPs':True,")
(HERE/'mlp_lifetime.py').write_text(text,encoding='utf8')
text=(HERE/'inspect_ready.py').read_text(encoding='utf8').replace("proof['all_numerical_AST_nodes_unchanged']", "proof['normalized_arithmetic_AST_equal_after_restoring_product_destinations']").replace("proof['only_dead_local_deletions_added']", "proof['only_private_dead_pointwise_output_buffers_reused']")
text=text.replace("assert loaded['CUDA']['devices']==['cuda:'+str(i)for i in range(7)]", "assert loaded['CUDA']['devices']==['cuda:'+str(i)for i in range(7)]\nassert loaded['device_map']=={k:str(v)for k,v in load(p/'explicit-placement.json')['device_map'].items()}")
(HERE/'inspect_ready.py').write_text(text,encoding='utf8')
out=HERE/'package';out.mkdir();m0=json.loads((old/'manifest.json').read_bytes())
for n,h in m0['files'].items():
 assert sha(old/n)==h
 target=out/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,target)
for n in ['capacity_gate.py','memory_lifetime.py','torch_chunk_lifetime.py','mlp_lifetime.py','launch_group.py']:shutil.copyfile(HERE/n,out/n)
placement=json.loads(max(prior.glob('explicit-placement-*.json'),key=lambda p:p.stat().st_mtime_ns).read_bytes())['result'];save(out/'explicit-placement.json',placement)
text=(out/'primary_server.py').read_text(encoding='utf8');needle="device_map='balanced',max_memory={0:'3500MiB',**{i:'20GiB'for i in range(1,7)}}";assert text.count(needle)==1
text=text.replace(needle,"device_map=json.loads((P/'explicit-placement.json').read_bytes())['device_map'],max_memory={i:'20GiB'for i in range(7)}")
(out/'primary_server.py').write_text(text,encoding='utf8')
preserved=json.loads(max(prior.glob('preservation-*.json'),key=lambda p:p.stat().st_mtime_ns).read_bytes())['result']
binding=json.loads((out/'capacity-source.json').read_bytes());binding.update({'linked05_postexit_seal_sha256':preserved['postexit_seal_sha256'],'repair':'CPU source-bound explicit contiguous placement; original pointwise expressions with private dead output-buffer reuse; MLP buffer reuse and unused allocator-block purge. Original full sequence/precision/matmul/reduction order retained. Exact controls required.'})
(out/'capacity-source.json').write_text(json.dumps(binding,ensure_ascii=False,indent=2),encoding='utf8')
plan=json.loads((out/'plan.json').read_bytes());plan.update({'version':'Flash-seven-GPU-explicit-placement-buffer-lifetimes-linked06','created':time.time(),'memory_scheduling':binding['repair'],'placement':placement,'capacity':'9 original chunk complete output/state controls, 12 actual-weights MLP tests, 3 full-vocab model cached-step equality, full50 EOS IDs identical to linked02; >=3GiB peak reserved headroom on every GPU','minimum_peak_reserved_headroom_GiB':3})
(out/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
auth=json.loads((out/'user-memory-authorization.json').read_bytes());auth['linked_repair_scope']=plan['memory_scheduling']+' No input/prompt/semantic gate change or CPU/disk model offload; both formal arms same deployment.'
(out/'user-memory-authorization.json').write_text(json.dumps(auth,ensure_ascii=False,indent=2),encoding='utf8')
save(out/'linked05-preservation-binding.json',{'postexit_seal_sha256':preserved['postexit_seal_sha256'],'postexit_files_verified':preserved['postexit_files_verified'],'full50_OOM_failed_request_preserved':True,'formal_GUI_calls':0})
(out/'private.token').write_text(secrets.token_hex(32),encoding='utf8')
files={p.relative_to(out).as_posix():sha(p)for p in out.rglob('*')if p.is_file()and p.name not in ['manifest.json','private.token']and '__pycache__'not in p.parts}
for n in files:
 if n.endswith('.py'):ast.parse((out/n).read_text(encoding='utf8'))
m={**m0,'version':plan['version'],'created':time.time(),'files':files,'auth_token_sha256':sha(out/'private.token'),'output3090':OUT,'package3090':R3090,'package4090':R4090,'source_prior_manifest_sha256':sha(old/'manifest.json'),'head_batching':False,'explicit_source_bound_placement':True,'pointwise_dead_output_buffer_reuse':True}
save(out/'manifest.json',m);save(HERE/'frozen-package.json',{'files':len(files),'manifest_sha256':sha(out/'manifest.json'),'new_model_GUI_calls':0})
(HERE/'README.md').write_text('''# 七卡主27B与独立Flash，linked06完整GUI续跑

用户已要求充裕显存继续至可复核降低Mirage。主3090物理0–6、Flash7；实际UID/命令/start/UUID、主17锁/Flash9锁与全部compute逐次核验，不抢占外人。仅续29未开始，原2正常+1OOM终局不重跑；新七任务14完整匹配对，T000旧帧门控单列。Flash完整单图+固定通用问题，无任务/主上下文/候选/前图/累积KV；YES同PNG给主模型，无文字概率；NO等待0.5秒持续同环境新复拍至YES或手停；技术失败不是NO。原图、接受历史、BF16/SDPA、2048输出、50决策/70actor与原生提示/解析/执行/评分/seed保持。

原七卡50图OOM；linked02自然EOS126tokens但余量0.84GiB；linked03head分组逐位失败拒绝；linked04全部IDs相同但余量1.41GiB；linked05 MLP缓冲逐位通过，但自动低GPU0预算使尾卡11.68GB权重，50图OOM。各目录及完整失败输入、原tensor/日志/源码和postexit seals不可重跑或覆盖。

本linked06按封存1184个state tensor实际大小、连续完整decoder block及full-attention KV估计，在CPU确定显式映射：视觉+embedding0，64层分到1–6，norm/lm_head6。估计不是容量证明，真实所有CUDA/权重bytes与映射核验后仍需完整压力测试。保留原chunk head形状/内核数学，原query标量乘法、row广播乘法与k_beta广播乘法使用其各自已死私有缓冲，避免再分配全尺寸结果。逐项恢复原输出目的表达式并去掉dead-local del后AST必须与原式完全相等；不称未修改AST。所有matmul、规约、元素操作数顺序和精度保留，原始源码文件未改。MLP保留原gate/up/down和SiLU，复用死SiLU输出缓冲承接相同乘法，并在长MLP前释放allocator未用缓存块；这些资源调度开销单列。

9项CPU/GPU完整chunk输出及状态、各实际GPU真实MLP权重1/65token的全部输出字节与输入未改、真实15图连续3个cached steps全词表logits/IDs逐位一致，每遍192MLP与48chunk实际调用，以及新50图自然EOS全部126IDs等于linked02、每卡reserved峰值余量>=3GiB，全部通过后才开放GUI。3token工程cap不是EOS，旧15图完整EOS复用；50图为标明合成重复历史，不是50步GUI，不保证任意未来历史最坏容量或普遍逐位。

wire/完整历史/实际first-forward IDs,pixels,grid/有效配置/输出IDs,EOS/原回复/日志/seals/链保留，相同tensor完整字节SHA相同后硬链接不替代原字节。新技术失败完整保留后停，修复须新关联attempt，禁止热改冻结源码/重刷终局/缩图/截史/降精度/扩预算。手停4090根STOP。主模型不接辅助概率/解释，无旧上下文语义judge，网站不重置，私有答案不入模型。目标active，Mirage降幅null，效果尚未证明；需完整配对语义/误拦/等待/官方完成审查，发生后纠正仍计，纯nativeWAIT排除，未知不当无Mirage。单图不能证明清晰旧帧新鲜或动作正确，不能靠少动作/一直等待/评分/挑阳性称有效。所有旧队列不恢复。
''',encoding='utf8')
print(json.dumps({'files':len(files),'manifest_sha256':sha(out/'manifest.json'),'remaining_GUI':29,'explicit_weight_bytes_by_GPU':placement['weight_bytes_by_device']}))
