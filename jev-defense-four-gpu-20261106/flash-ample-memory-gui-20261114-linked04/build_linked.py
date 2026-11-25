"""New linked dead-lifetime attempt; never modify the three preserved terminals."""
import ast,hashlib,json,secrets,shutil,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
old2=BASE/'flash-ample-memory-gui-20261114-linked02';old3=BASE/'flash-ample-memory-gui-20261114-linked03'
assert not(HERE/'package').exists()
for n in ['control.py','launch_group.py','capture_live_evidence.py','audit_flash_live.py','inspect_terminals.py','preserve_terminal.py']:
 text=(old3/n).read_text(encoding='utf8').replace('flash-ample-memory-gui-20261114-linked03','flash-ample-memory-gui-20261114-linked04')
 if n=='preserve_terminal.py':text=text.replace("'failure_before_full_model_invariance':True,",'').replace("'source_proof':load(r/'capacity/lifetime-validation/source-proof.json'),","'source_proof':load(r/'capacity/lifetime-validation/source-proof.json'),")
 (HERE/n).write_text(text,encoding='utf8')
for n in ['memory_lifetime.py','torch_chunk_lifetime.py']:(HERE/n).write_bytes((old2/n).read_bytes())
text=(HERE/'torch_chunk_lifetime.py').read_text(encoding='utf8')
needle='    g = g.reshape(g.shape[0], g.shape[1], -1, chunk_size)'
assert text.count(needle)==1
text=text.replace(needle,'    del value\n'+needle).replace('    del k_beta\n','    del k_beta, attn\n')
(HERE/'torch_chunk_lifetime.py').write_text(text,encoding='utf8')
(HERE/'capacity_gate.py').write_bytes((old3/'capacity_gate.py').read_bytes())
text=(old3/'inspect_ready.py').read_text(encoding='utf8').replace("proof['independent_heads_per_batch']==12 and ","proof['only_dead_local_deletions_added']and ")
(HERE/'inspect_ready.py').write_text(text,encoding='utf8')
from control import save,sha,R3090,R4090,OUT
out=HERE/'package';out.mkdir();m0=json.loads((old2/'package/manifest.json').read_bytes())
for n,h in m0['files'].items():
 assert sha(old2/'package'/n)==h
 target=out/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old2/'package'/n,target)
for n in ['capacity_gate.py','memory_lifetime.py','torch_chunk_lifetime.py','launch_group.py']:shutil.copyfile(HERE/n,out/n)
preserved2=json.loads(max(old2.glob('preservation-*.json'),key=lambda p:p.stat().st_mtime_ns).read_bytes())['result']
preserved3=json.loads(max(old3.glob('preservation-*.json'),key=lambda p:p.stat().st_mtime_ns).read_bytes())['result']
binding=json.loads((out/'capacity-source.json').read_bytes());previous='/data/researcher/jev-defense-four-gpu-20261106/flash-ample-memory-gui-20261114-linked02'
binding.update({'prior_complete50_probe':previous+'/capacity/50-image-source-bound-stress','prior_complete50_seal_sha256':preserved2['stress_seal_sha256'],'linked02_postexit_seal_sha256':preserved2['postexit_seal_sha256'],'rejected_head_batch_postexit_seal_sha256':preserved3['postexit_seal_sha256'],'repair':'Only additional del for dead pre-beta value and full attn after its last use. Original head shape/kernel/math retained; complete stress IDs and three full-vocab cached steps must match.'})
(out/'capacity-source.json').write_text(json.dumps(binding,ensure_ascii=False,indent=2),encoding='utf8')
plan=json.loads((out/'plan.json').read_bytes());plan.update({'version':'Flash-seven-GPU-extended-dead-lifetime-linked04','created':time.time(),'memory_scheduling':'Additional release of dead original value view and full triangular attention tensor; no head batching, changed numerical AST/kernel/precision, or history truncation. Both arms use identical deployment.','capacity':'reuse completed original15 EOS; compare native versus additional-deletion three full-logit cached steps; new complete50 IDs must equal preserved linked02 EOS','minimum_peak_reserved_headroom_GiB':3})
(out/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
auth=json.loads((out/'user-memory-authorization.json').read_bytes());auth['linked_repair_scope']='Delete already-dead local references only; original numerical AST, head shapes, operation order, full sequence/images/history and BF16 unchanged; no CPU/disk model offload or semantic-gate changes. Strict output and memory gates remain.'
(out/'user-memory-authorization.json').write_text(json.dumps(auth,ensure_ascii=False,indent=2),encoding='utf8')
save(out/'linked-prior-preservation-binding.json',{'linked02_postexit_seal_sha256':preserved2['postexit_seal_sha256'],'linked02_postexit_files_verified':preserved2['postexit_files_verified'],'linked02_complete50_EOS_126_tokens_preserved':True,'linked02_readiness_failed_but_not_OOM':True,'linked03_postexit_seal_sha256':preserved3['postexit_seal_sha256'],'linked03_files_verified':preserved3['postexit_files_verified'],'linked03_head_batch_rejected_before_full_model_invariance':True,'prior_formal_GUI_calls':0})
(out/'private.token').write_text(secrets.token_hex(32),encoding='utf8')
files={p.relative_to(out).as_posix():sha(p)for p in out.rglob('*')if p.is_file()and p.name not in ['manifest.json','private.token']and '__pycache__'not in p.parts}
for n in files:
 if n.endswith('.py'):ast.parse((out/n).read_text(encoding='utf8'))
m={**m0,'version':plan['version'],'created':time.time(),'files':files,'auth_token_sha256':sha(out/'private.token'),'output3090':OUT,'package3090':R3090,'package4090':R4090,'source_prior_manifest_sha256':sha(old2/'package/manifest.json'),'head_batching':False}
save(out/'manifest.json',m);save(HERE/'frozen-package.json',{'files':len(files),'manifest_sha256':sha(out/'manifest.json'),'new_model_GUI_calls':0})
(HERE/'README.md').write_text('''# 七卡主27B与独立Flash的完整GUI续跑：linked04

主模型使用3090物理0–6，Flash独占7；实际UID/完整命令/start/UUID/17与9继承锁及全部compute逐次核验，禁止外人抢占。完整原图、接受历史、BF16/SDPA、原生提示/解析/执行/评分及2048输出、50决策/70actor与原seed保持。只运行29未开始轨迹；三条旧终局不重跑，新七任务14个完整配对与T000旧帧门控诊断单列。

Flash每次独立完整单图+固定通用问题，无任务/主上下文/候选/前图/累积KV。YES原PNG转交，不附加文字或概率；NO等待0.5秒持续同环境新复拍至YES或手停，无辅助或复拍总上限；技术失败不是NO。可读旧帧不能靠单图保证新鲜，YES不是动作正确证明，无旧上下文语义judge。

前七卡原实现15图EOS但50图OOM；linked02仅提前释放死局部引用，9核检查与15图连续3步全词表logits和IDs逐位相同，50图自然EOS126tokens，但峰值reserved余量最小0.84GiB，未达3GiB。linked03把独立head分组后未通过核逐位检查，已拒绝、退出并封存32文件，0正式GUI；不采用分组、不降低校验门槛。旧attempt和原失败日志/输入/代码/完整原张量不改。

本linked04仍只加入del，再提前释放已经不参与后续计算的原value视图和完整attn；去掉del后必须与原数值AST逐节点相同，保留原head数/内核/运算顺序/精度、不动pinned源码文件。须新通过9个CPU/GPU完整输出及最终状态逐位核验、真实15图连续3步全词表logits及IDs逐位核验，并让新50图完整输出与linked02全部126个IDs相同、每卡reserved峰值余量至少3GiB，再开放GUI。3步工程cap不算EOS；15图完整旧EOS复用。50图压力历史为明确合成，不是实跑50步，不保证所有未来历史/每步2048token的最坏情况容量或普遍逐位。

完整wire/实际forward IDs,pixels,grid/有效默认/输出IDs,EOS/replies/日志与seal和事件链保留。完整字节SHA核对后可硬链接相同原tensor，未以摘要替代证据。新源码包冻结不热改；任何技术失败保全后停队列，新条件需新关联attempt。手动在4090运行根写STOP即可于在途调用结束后停止后续调用/动作。

目标保持active，按边界包含Mirage、正常操作误拦/复拍等待、官方完成与技术故障分别审查；纠正不抹去发生，纯nativeWAIT排除，未知不当无Mirage。完整配对效果尚未证明，相对降幅null，不通过挑选结果/一直等待/评分替代语义来追求效果。不恢复任何旧队列。
''',encoding='utf8')
print(json.dumps({'files':len(files),'manifest_sha256':sha(out/'manifest.json'),'remaining_GUI':29,'only_dead_local_deletions':True}))
