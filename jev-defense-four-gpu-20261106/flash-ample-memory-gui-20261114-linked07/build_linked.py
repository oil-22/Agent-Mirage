"""Bind nonpersistent rotary buffers too; keep the strict CUDA tensor audit."""
import ast,json,secrets,shutil,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;prior=BASE/'flash-ample-memory-gui-20261114-linked06';old=prior/'package'
assert not(HERE/'package').exists()
for n in ['control.py','launch_group.py','capture_live_evidence.py','audit_flash_live.py','inspect_terminals.py','preserve_terminal.py','peek.py','wait_capacity.py','publish_progress.py','publish_capacity_state.py','capacity_gate.py','memory_lifetime.py','torch_chunk_lifetime.py','mlp_lifetime.py','inspect_ready.py','README.md']:
 text=(prior/n).read_text(encoding='utf8').replace('flash-ample-memory-gui-20261114-linked06','flash-ample-memory-gui-20261114-linked07')
 (HERE/n).write_text(text,encoding='utf8')
from control import save,sha,R3090,R4090,OUT
out=HERE/'package';out.mkdir();m0=json.loads((old/'manifest.json').read_bytes())
for n,h in m0['files'].items():
 assert sha(old/n)==h
 target=out/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,target)
for n in ['launch_group.py']:shutil.copyfile(HERE/n,out/n)
placement=json.loads((out/'explicit-placement.json').read_bytes());placement['device_map']['']=0;placement['device_map']['model.language_model.rotary_emb']=0
placement['nonpersistent_buffer_default_device']=0;placement['rotary_explicit_device']=0;placement['persistent_weight_placement_unchanged_from_linked06']=True
(out/'explicit-placement.json').write_text(json.dumps(placement,ensure_ascii=False,indent=2),encoding='utf8')
text=(out/'primary_server.py').read_text(encoding='utf8');needle="        tensors=support.audit_tensors(torch,[('primary',self.engine.model)],['cuda:'+str(i)for i in range(7)])";assert text.count(needle)==1
record="        inventory=[{'kind':kind,'name':name,'shape':list(t.shape),'dtype':str(t.dtype),'device':str(t.device),'bytes':t.numel()*t.element_size()}for kind,items in [('parameter',self.engine.model.named_parameters()),('buffer',self.engine.model.named_buffers())]for name,t in items]\n        save(root/'all-parameters-and-buffers-before-device-audit.json',inventory)\n"
text=text.replace(needle,record+needle);(out/'primary_server.py').write_text(text,encoding='utf8')
preserved=json.loads(max(prior.glob('preservation-*.json'),key=lambda p:p.stat().st_mtime_ns).read_bytes())['result'];save(out/'linked06-preservation-binding.json',{'postexit_seal_sha256':preserved['postexit_seal_sha256'],'postexit_files_verified':preserved['postexit_files_verified'],'failure_before_capacity_probes':True,'strict_CUDA_check_rejected_CPU_nonpersistent_buffer':True,'formal_GUI_calls':0})
binding=json.loads((out/'capacity-source.json').read_bytes());binding['linked06_postexit_seal_sha256']=preserved['postexit_seal_sha256'];binding['nonpersistent_rotary_buffers_explicitly_placed_on_CUDA0']=True
(out/'capacity-source.json').write_text(json.dumps(binding,ensure_ascii=False,indent=2),encoding='utf8')
plan=json.loads((out/'plan.json').read_bytes());plan.update({'version':'Flash-seven-GPU-explicit-placement-all-buffers-linked07','created':time.time(),'placement':placement,'nonpersistent_buffer_binding':'Root default CUDA0 and explicit language rotary CUDA0; all1187 real parameters and buffers must pass unchanged strict CUDA audit. All persistent weight mapping and numerical memory repairs same as linked06.'})
(out/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
(out/'private.token').write_text(secrets.token_hex(32),encoding='utf8')
files={p.relative_to(out).as_posix():sha(p)for p in out.rglob('*')if p.is_file()and p.name not in ['manifest.json','private.token']and '__pycache__'not in p.parts}
for n in files:
 if n.endswith('.py'):ast.parse((out/n).read_text(encoding='utf8'))
m={**m0,'version':plan['version'],'created':time.time(),'files':files,'auth_token_sha256':sha(out/'private.token'),'output3090':OUT,'package3090':R3090,'package4090':R4090,'source_prior_manifest_sha256':sha(old/'manifest.json'),'all_model_parameters_and_buffers_required_on_CUDA':True}
save(out/'manifest.json',m);save(HERE/'frozen-package.json',{'files':len(files),'manifest_sha256':sha(out/'manifest.json'),'new_model_GUI_calls':0})
text=(HERE/'README.md').read_text(encoding='utf8');(HERE/'README.md').write_text('''# linked07：完整显式映射与全部真实CUDA缓冲核验

linked06加载实际权重后被严格CUDA检查拦下：nonpersistent位置编码缓冲未被持久1184 tensor表覆盖。失败早于容量/模型generate，全部postexit保留。本linked07将根默认与language rotary显式映射CUDA0，1187个真实parameters/buffers仍必须全部CUDA，不放宽设备检查；先完整记录实际清单再审核。持久权重映射、数学/缓冲修复及全部模型输入和正式条件沿用linked06。需9chunk＋12真实权重MLP检查、连续3步全词表logits/IDs逐位及完整50图EOS126IDs相同、每卡reserved峰值余量至少3GiB，独立核验后才启动29未开始GUI。原终局不重跑、旧队列不恢复，目标active、效果尚未证明。

'''+text,encoding='utf8')
print(json.dumps({'files':len(files),'manifest_sha256':sha(out/'manifest.json'),'remaining_GUI':29,'strict_CUDA_tensor_audit_retained':True}))
