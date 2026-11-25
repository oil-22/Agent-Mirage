"""Linked synchronous CUDA diagnostics, no cache purge during a forward."""
import ast,json,secrets,shutil,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;prior=BASE/'flash-ample-memory-gui-20261114-linked08';old=prior/'package'
assert not(HERE/'package').exists()
for n in ['control.py','launch_group.py','capture_live_evidence.py','audit_flash_live.py','inspect_terminals.py','preserve_terminal.py','peek.py','wait_capacity.py','publish_progress.py','publish_capacity_state.py','capacity_gate.py','memory_lifetime.py','torch_chunk_lifetime.py','mlp_lifetime.py','inspect_ready.py','README.md']:
 text=(prior/n).read_text(encoding='utf8').replace('flash-ample-memory-gui-20261114-linked08','flash-ample-memory-gui-20261114-linked09')
 (HERE/n).write_text(text,encoding='utf8')
from control import save,sha,R3090,R4090,OUT
text=(HERE/'mlp_lifetime.py').read_text(encoding='utf8');needle="    if x.is_cuda and x.shape[-2]>8192:\n        torch.cuda.empty_cache()\n";assert text.count(needle)==1
text=text.replace(needle,'').replace("'allocator_unused_blocks_released_before_long_MLPs':True", "'allocator_unused_blocks_released_before_long_MLPs':False")
(HERE/'mlp_lifetime.py').write_text(text,encoding='utf8')
text=(HERE/'launch_group.py').read_text(encoding='utf8');needle="env.update({'CUDA_VISIBLE_DEVICES':'0,1,2,3,4,5,6',";assert text.count(needle)==1
text=text.replace(needle,"env.update({'CUDA_LAUNCH_BLOCKING':'1','CUDA_VISIBLE_DEVICES':'0,1,2,3,4,5,6',");(HERE/'launch_group.py').write_text(text,encoding='utf8')
out=HERE/'package';out.mkdir();m0=json.loads((old/'manifest.json').read_bytes())
for n,h in m0['files'].items():
 assert sha(old/n)==h
 target=out/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,target)
for n in ['mlp_lifetime.py','launch_group.py']:shutil.copyfile(HERE/n,out/n)
text=(out/'primary_server.py').read_text(encoding='utf8');needle="        save(root/'loaded.json',self.loaded)";assert text.count(needle)==1
text=text.replace(needle,"        self.loaded['CUDA_LAUNCH_BLOCKING']=os.environ.get('CUDA_LAUNCH_BLOCKING')\n"+needle);(out/'primary_server.py').write_text(text,encoding='utf8')
preserved=json.loads(max(prior.glob('preservation-*.json'),key=lambda p:p.stat().st_mtime_ns).read_bytes())['result'];save(out/'linked08-preservation-binding.json',{'postexit_seal_sha256':preserved['postexit_seal_sha256'],'postexit_files_verified':preserved['postexit_files_verified'],'CUDA_illegal_memory_access_before_full_model_equality_pass':True,'formal_GUI_calls':0,'root_cause_not_claimed':True})
binding=json.loads((out/'capacity-source.json').read_bytes());binding['linked08_postexit_seal_sha256']=preserved['postexit_seal_sha256'];binding['synchronous_CUDA_and_no_in_forward_cache_purge']=True
(out/'capacity-source.json').write_text(json.dumps(binding,ensure_ascii=False,indent=2),encoding='utf8')
plan=json.loads((out/'plan.json').read_bytes());plan.update({'version':'Flash-seven-GPU-synchronous-CUDA-no-forward-purge-linked09','created':time.time(),'CUDA_LAUNCH_BLOCKING':'1 for primary only; Flash native scheduling unchanged','in_forward_allocator_cache_purge':False,'runtime_tradeoff':'Synchronous GPU launches can increase latency; both formal arms use this exact scheduling. No original precision/input/history/model prompt/generation budget or semantic gate change. Baseline-versus-memory-repaired full-logit and complete stress-ID checks remain.'})
(out/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
(out/'private.token').write_text(secrets.token_hex(32),encoding='utf8')
files={p.relative_to(out).as_posix():sha(p)for p in out.rglob('*')if p.is_file()and p.name not in ['manifest.json','private.token']and '__pycache__'not in p.parts}
for n in files:
 if n.endswith('.py'):ast.parse((out/n).read_text(encoding='utf8'))
m={**m0,'version':plan['version'],'created':time.time(),'files':files,'auth_token_sha256':sha(out/'private.token'),'output3090':OUT,'package3090':R3090,'package4090':R4090,'source_prior_manifest_sha256':sha(old/'manifest.json'),'primary_CUDA_LAUNCH_BLOCKING':'1','in_forward_allocator_purge':False}
save(out/'manifest.json',m);save(HERE/'frozen-package.json',{'files':len(files),'manifest_sha256':sha(out/'manifest.json'),'new_model_GUI_calls':0})
text=(HERE/'README.md').read_text(encoding='utf8');(HERE/'README.md').write_text('''# linked09：同步CUDA、移除forward内缓存清理

linked08实际1187参数/缓冲均CUDA、9chunk与12实际MLP权重数值通过，原15图baseline三步完整完成；修复后三步遇CUDA非法访存，未通过全模型比较，全部证据已保留，不能称数值修复通过或模型零分。本linked09移除MLP forward中的empty_cache，主模型使用CUDA_LAUNCH_BLOCKING=1同步执行定位，Flash调度保持原状；这会增加延迟，两正式臂一致，不据此声称低成本。尚不能仅凭新尝试断言原非法访存根因。原显式权重/buffer映射、chunk/MLP私有死缓冲复用及严格设备检查保留。完整原图/历史/BF16/SDPA/原生提示解析执行评分/2048输出/50决策70actor/原seed/Flash单图YES原PNG与NO持续复拍条件保持。

必须重新通过9chunk、12实际权重MLP、原15图连续3步全词表logits及IDs逐位、新50图自然EOS全部126IDs等于linked02、各卡reserved峰值余量>=3GiB和独立read-only核验后，才开始29未开始GUI。工程cap不算EOS，50图是合成容量历史、不保证任意未来最坏容量。旧终局/旧队列不得重跑，技术失败保全后停，目标active、Mirage降幅null、未证明防御有效。下面旧头保留历史，冲突以本头和真实新回执为准。

'''+text,encoding='utf8')
print(json.dumps({'files':len(files),'manifest_sha256':sha(out/'manifest.json'),'remaining_GUI':29,'primary_synchronous_CUDA':True,'in_forward_cache_purge':False}))
