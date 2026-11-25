"""Remove the root hook; bind only declared static nonpersistent CUDA buffers."""
import ast,json,secrets,shutil,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;prior=BASE/'flash-ample-memory-gui-20261114-linked07';old=prior/'package'
assert not(HERE/'package').exists()
for n in ['control.py','launch_group.py','capture_live_evidence.py','audit_flash_live.py','inspect_terminals.py','preserve_terminal.py','peek.py','wait_capacity.py','publish_progress.py','publish_capacity_state.py','capacity_gate.py','memory_lifetime.py','torch_chunk_lifetime.py','mlp_lifetime.py','inspect_ready.py','README.md']:
 text=(prior/n).read_text(encoding='utf8').replace('flash-ample-memory-gui-20261114-linked07','flash-ample-memory-gui-20261114-linked08')
 (HERE/n).write_text(text,encoding='utf8')
from control import save,sha,R3090,R4090,OUT
out=HERE/'package';out.mkdir();m0=json.loads((old/'manifest.json').read_bytes())
for n,h in m0['files'].items():
 assert sha(old/n)==h
 target=out/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,target)
shutil.copyfile(HERE/'launch_group.py',out/'launch_group.py')
placement=json.loads((out/'explicit-placement.json').read_bytes());assert placement['device_map'].pop('')==0
placement.pop('nonpersistent_buffer_default_device');placement['root_default_hook_prohibited']=True
(out/'explicit-placement.json').write_text(json.dumps(placement,ensure_ascii=False,indent=2),encoding='utf8')
text=(out/'primary_server.py').read_text(encoding='utf8');needle="        inventory=[{'kind':kind";assert text.count(needle)==1
promote='''        # Static nonpersistent buffers can be created after checkpoint dispatch.
        # Place them once at their explicitly declared CUDA module; never move CPU weights or relax the audit.
        placement=json.loads((P/'explicit-placement.json').read_bytes())['device_map'];assert ''not in placement
        placed_buffers=[]
        for name,t in list(self.engine.model.named_buffers()):
            if t.device.type!='cpu':continue
            parent,leaf=name.rsplit('.',1);owner=self.engine.model.get_submodule(parent)
            assert leaf in owner._non_persistent_buffers_set,'CPU persistent model buffer is prohibited'
            matches=[key for key in placement if name==key or name.startswith(key+'.')];assert matches,name
            target='cuda:'+str(placement[max(matches,key=len)])
            before=digest(t.detach().contiguous().view(torch.uint8).numpy().tobytes())
            moved=t.to(target);after=digest(moved.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes());assert before==after and moved.dtype==t.dtype
            owner._buffers[leaf]=moved;placed_buffers.append({'name':name,'shape':list(t.shape),'dtype':str(t.dtype),'source_device':'cpu','declared_target':target,'full_bytes_sha256_before':before,'full_bytes_sha256_after':after,'nonpersistent_static_buffer_only':True})
        save(root/'static-buffer-device-placement.json',placed_buffers)
'''
text=text.replace(needle,promote+needle);(out/'primary_server.py').write_text(text,encoding='utf8')
preserved=json.loads(max(prior.glob('preservation-*.json'),key=lambda p:p.stat().st_mtime_ns).read_bytes())['result'];save(out/'linked07-preservation-binding.json',{'postexit_seal_sha256':preserved['postexit_seal_sha256'],'postexit_files_verified':preserved['postexit_files_verified'],'failure_before_capacity_probes':True,'root_hook_caused_load_OOM_all_evidence_preserved':True,'formal_GUI_calls':0})
binding=json.loads((out/'capacity-source.json').read_bytes());binding['linked07_postexit_seal_sha256']=preserved['postexit_seal_sha256'];binding['root_dispatch_hook_removed']=True
(out/'capacity-source.json').write_text(json.dumps(binding,ensure_ascii=False,indent=2),encoding='utf8')
plan=json.loads((out/'plan.json').read_bytes());plan.update({'version':'Flash-seven-GPU-explicit-leaf-buffer-placement-linked08','created':time.time(),'placement':placement,'nonpersistent_buffer_binding':'No root hook; rotary explicitly on CUDA0. Any CPU-created static nonpersistent buffer must map to an explicit CUDA module and preserve complete dtype/bytes; CPU parameters or persistent buffers stay prohibited. All1187 actual CUDA audit remains.'})
(out/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
(out/'private.token').write_text(secrets.token_hex(32),encoding='utf8')
files={p.relative_to(out).as_posix():sha(p)for p in out.rglob('*')if p.is_file()and p.name not in ['manifest.json','private.token']and '__pycache__'not in p.parts}
for n in files:
 if n.endswith('.py'):ast.parse((out/n).read_text(encoding='utf8'))
m={**m0,'version':plan['version'],'created':time.time(),'files':files,'auth_token_sha256':sha(out/'private.token'),'output3090':OUT,'package3090':R3090,'package4090':R4090,'source_prior_manifest_sha256':sha(old/'manifest.json'),'root_hook_prohibited':True}
save(out/'manifest.json',m);save(HERE/'frozen-package.json',{'files':len(files),'manifest_sha256':sha(out/'manifest.json'),'new_model_GUI_calls':0})
text=(HERE/'README.md').read_text(encoding='utf8');(HERE/'README.md').write_text('''# linked08：移除根钩子，逐模块静态buffer映射

linked07根默认触发accelerate把子模块再搬到GPU0，加载OOM，未进入容量推理/GUI，全部封存。本linked08移除根默认，保留明确language rotary CUDA0及全部持久权重的显式映射。加载后若存在CPU创建的nonpersistent静态buffer，仅按它明确所属模块的CUDA映射一次迁移，完整字节SHA/dtype相同并保存原始清单；CPU参数或persistent buffer仍严格拒绝、meta/disk仍拒绝，不放宽1187真实tensor CUDA检查。没有模型CPU执行/offload。其余数值/显存门槛与29未开始GUI条件沿用，9+12数值/3步全logits/完整50图EOS全部126IDs相同以及每卡峰值reserved余量>=3GiB、独立核验通过后才放GUI。

以下为保留的先前版本说明，版本事实以本头和实际回执为准。

'''+text,encoding='utf8')
print(json.dumps({'files':len(files),'manifest_sha256':sha(out/'manifest.json'),'remaining_GUI':29,'no_root_hook':True,'strict_CUDA_audit_retained':True}))
