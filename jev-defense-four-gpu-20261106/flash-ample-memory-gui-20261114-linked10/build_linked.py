"""Balance decoder blocks on all seven GPUs and bound unused allocator cache."""
import ast,json,secrets,shutil,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;prior=BASE/'flash-ample-memory-gui-20261114-linked09';old=prior/'package'
assert not(HERE/'package').exists()
for n in ['control.py','launch_group.py','capture_live_evidence.py','audit_flash_live.py','inspect_terminals.py','preserve_terminal.py','peek.py','wait_capacity.py','write_current_authority.py','publish_verified.py','capacity_gate.py','memory_lifetime.py','torch_chunk_lifetime.py','mlp_lifetime.py','inspect_ready.py','README.md']:
 text=(prior/n).read_text(encoding='utf8').replace('flash-ample-memory-gui-20261114-linked09','flash-ample-memory-gui-20261114-linked10')
 (HERE/n).write_text(text,encoding='utf8')
from control import save,sha,R3090,R4090,OUT
text=(HERE/'launch_group.py').read_text(encoding='utf8');assert text.count("'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'")==1
text=text.replace("'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'","'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True,garbage_collection_threshold:0.8'");(HERE/'launch_group.py').write_text(text,encoding='utf8')
out=HERE/'package';out.mkdir();m0=json.loads((old/'manifest.json').read_bytes())
for n,h in m0['files'].items():
 assert sha(old/n)==h
 target=out/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,target)
shutil.copyfile(HERE/'launch_group.py',out/'launch_group.py')
placement=json.loads(max(prior.glob('seven-placement-*.json'),key=lambda p:p.stat().st_mtime_ns).read_bytes())['result'];assert ''not in placement['device_map'];save(HERE/'seven-placement-bound.json',placement)
(out/'explicit-placement.json').write_text(json.dumps(placement,ensure_ascii=False,indent=2),encoding='utf8')
text=(out/'primary_server.py').read_text(encoding='utf8');needle="        start=time.time();self.engine=LocalQwen.__new__(LocalQwen);self.engine.torch=torch";assert text.count(needle)==1
allocator="        allocator_began=time.time()\n        for device in range(7):torch.cuda.set_per_process_memory_fraction(0.85,device)\n        save(root/'allocator-budget.json',{'fraction_per_primary_GPU':0.85,'unused_cache_collection_threshold':0.8,'configured_after_owned_resource_admission':True,'before_weight_load':True,'setup_seconds':time.time()-allocator_began,'unused_cache_release_not_numerical_truncation':True})\n"
text=text.replace(needle,allocator+needle)
needle="        save(root/'loaded.json',self.loaded)";assert text.count(needle)==1
text=text.replace(needle,"        self.loaded['primary_allocator_memory_fraction']=0.85\n        self.loaded['allocator_gc_threshold']=0.8\n"+needle);(out/'primary_server.py').write_text(text,encoding='utf8')
preserved=json.loads(max(prior.glob('preservation-*.json'),key=lambda p:p.stat().st_mtime_ns).read_bytes())['result'];save(out/'linked09-preservation-binding.json',{'postexit_seal_sha256':preserved['postexit_seal_sha256'],'postexit_files_verified':preserved['postexit_files_verified'],'full_model_three_steps_bitwise_passed':True,'complete50_EOS_all126_IDs_equal_prior':True,'peak_reserved_headroom_not_ample':True,'formal_GUI_calls':0})
binding=json.loads((out/'capacity-source.json').read_bytes());binding.update({'linked09_postexit_seal_sha256':preserved['postexit_seal_sha256'],'seven_GPU_contiguous_source_bound_placement':True,'native_allocator_limit_fraction':0.85,'automatic_unused_cache_GC_threshold':0.8})
(out/'capacity-source.json').write_text(json.dumps(binding,ensure_ascii=False,indent=2),encoding='utf8')
plan=json.loads((out/'plan.json').read_bytes());plan.update({'version':'Flash-seven-GPU-balanced-blocks-bounded-cache-linked10','created':time.time(),'placement':placement,'primary_allocator_limit_fraction':0.85,'native_unused_cache_GC_threshold':0.8,'capacity':'9 chunk outputs/states,14 actual-weight GPU MLP tests,3 full-vocab cached-step equivalence,50-image naturalEOS all126 IDs equal prior,>=3GiB peak reserved headroom per card','runtime_tradeoff':'Primary synchronous CUDA remains; allocator frees unused cached memory to retain15% physical memory beyond its limit. May increase allocation latency or reject a larger future live working set; no input/history truncation, precision change or model offload. Both formal arms identical.'})
(out/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
(out/'private.token').write_text(secrets.token_hex(32),encoding='utf8')
files={p.relative_to(out).as_posix():sha(p)for p in out.rglob('*')if p.is_file()and p.name not in ['manifest.json','private.token']and '__pycache__'not in p.parts}
for n in files:
 if n.endswith('.py'):ast.parse((out/n).read_text(encoding='utf8'))
m={**m0,'version':plan['version'],'created':time.time(),'files':files,'auth_token_sha256':sha(out/'private.token'),'output3090':OUT,'package3090':R3090,'package4090':R4090,'source_prior_manifest_sha256':sha(old/'manifest.json'),'primary_allocator_memory_fraction':0.85,'allocator_unused_cache_GC_threshold':0.8}
save(out/'manifest.json',m);save(HERE/'frozen-package.json',{'files':len(files),'manifest_sha256':sha(out/'manifest.json'),'new_model_GUI_calls':0})
text=(HERE/'inspect_ready.py').read_text(encoding='utf8');text=text.replace("assert ''not in load(p/'explicit-placement.json')['device_map']","assert ''not in load(p/'explicit-placement.json')['device_map']\nassert loaded['CUDA_LAUNCH_BLOCKING']=='1'and loaded['primary_allocator_memory_fraction']==0.85 and loaded['allocator_gc_threshold']==0.8")
(HERE/'inspect_ready.py').write_text(text,encoding='utf8')
text=(HERE/'README.md').read_text(encoding='utf8');(HERE/'README.md').write_text('''# linked10：七卡均分decoder blocks，限制闲置缓存保留

linked09的9chunk、12真实MLP权重、15图连续3步全词表logits/IDs逐位及完整50图自然EOS全部126IDs均通过，157文件封存、0正式GUI；但峰值reserved余量最小1.62GiB，未达3GiB。实际allocated峰值最多20.15GiB，部分卡reserved多占约2.43GiB，同时GPU0余量10.45GiB。

本linked10在七张主GPU全部分配完整连续decoder blocks，按1184个实际tensor大小及原KV估计CPU规划：GPU0层0–5、1层6–15、2层16–25、3层26–35、4层36–46、5层47–56、6层57–63；视觉/embedding0、norm/lm_head6、rotary0，无根钩子。最大持久权重8.39GB；估计不是显存适配证明。主原生CUDA allocator设物理内存比例0.85、自动未用缓存GC阈值0.8，以释放闲置缓存并保留物理余量；同步CUDA不变、forward不清缓存。该限制可能增加分配延迟或让更大未来live集合提前容量失败，不截断/缩图/降精度/模型offload，两正式臂同版，不保证未来任意最坏历史。实际全部1187参数/buffers仍严格CUDA。

必须新通过9chunk/14实际MLP权重检查、15图3步全词表logits/IDs逐位、50图53167tokens自然EOS且全部126IDs等于linked02、每卡reserved峰值余量>=3GiB以及独立只读ready审计，再一次启动29未开始GUI。旧终局/旧源控制不重跑，原图/接受历史/BF16/SDPA/原生提示解析执行评分/2048输出/50决策70actor/原seed/单图Flash YES原PNG与NO持续复拍条件保留。目标active，尚未证明Mirage降低。以下旧版本头仅作历史。

'''+text,encoding='utf8')
print(json.dumps({'files':len(files),'manifest_sha256':sha(out/'manifest.json'),'remaining_GUI':29,'allocator_memory_fraction':0.85,'seven_GPU_decoder_placement':placement['layer_ranges_inclusive']}))
