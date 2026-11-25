"""Seal linked memory-lifetime-only retry; do not edit previous source or terminals."""
import ast,copy,json,secrets,shutil,time
from pathlib import Path
from control import HERE,BASE,R3090,R4090,OUT,save,sha
prior=BASE/'flash-ample-memory-gui-20261114';old=prior/'package';out=HERE/'package';out.mkdir()
m0=json.loads((old/'manifest.json').read_bytes())
for n,h in m0['files'].items():
 assert sha(old/n)==h
 p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,p)
for n in ['capacity_gate.py','memory_lifetime.py','torch_chunk_lifetime.py','launch_group.py']:shutil.copyfile(HERE/n,out/n)
source=(out/'primary_server.py').read_text(encoding='utf8')
needle="    except BaseException:save(root/'failure.json',{'error':traceback.format_exc(),'no_automatic_retry':True});traceback.print_exc()"
assert source.count(needle)==1
source=source.replace(needle,"    except BaseException:\n        failure={'error':traceback.format_exc(),'no_automatic_retry':True}\n        save(root/'failure.json',failure);state('technical_failure',error=failure)\n        save(root/'failure-memory.json',native.support.memory(native.torch)if 'native'in locals()else {})\n        traceback.print_exc()")
needle="    try:\n        state('loading')"
assert source.count(needle)==1
source=source.replace(needle,"    signal.signal(signal.SIGTERM,lambda *_:stop.set());signal.signal(signal.SIGINT,lambda *_:stop.set())\n    try:\n        state('loading')")
source=source.replace("'capacity_generation_calls':2","'capacity_generation_calls':3")
needle="        capacity_result=capacity_run(native,P,root,save,sha,resource)"
assert source.count(needle)==1
source=source.replace(needle,"        def capacity_admission(loaded):\n            if stop.is_set():raise RuntimeError('Manual stop before next capacity operation')\n            return resource(loaded)\n        capacity_result=capacity_run(native,P,root,save,sha,capacity_admission)")
needle="        state('ready')\n        class Handler"
assert source.count(needle)==1
source=source.replace(needle,"        if stop.is_set():raise RuntimeError('Manual stop during capacity preflight; no GUI starts')\n        state('ready')\n        class Handler")
(out/'primary_server.py').write_text(source,encoding='utf8')
binding=json.loads((out/'capacity-source.json').read_bytes());previous='/data/researcher/jev-defense-four-gpu-20261106/flash-ample-memory-gui-20261114'
op=max((prior/'operations').glob('*actual-capacity-progress-no-new-probe'),key=lambda p:p.stat().st_mtime_ns)
progress=json.loads((op/'stdout.txt').read_bytes())
preserved=json.loads(max(prior.glob('capacity-failure-preservation-*.json'),key=lambda p:p.stat().st_mtime_ns).read_bytes())
# The source result is closed and SHA verified by the preceding preservation audit.
binding.update({'prior_complete15_probe':previous+'/capacity/01-exact-previous-OOM-input','prior_complete15_seal_sha256':None,'linked_prior_output':previous,'prior_seven_GPU_postexit_seal_sha256':preserved['result']['postexit_seal_sha256'],'prior_source_manifest_sha256':sha(old/'manifest.json'),'repair':'Only early deletion of unused local tensors in the original chunk delta fallback; numerical AST must be identical and full logits bitwise verified before release.'})
# Obtain the immutable completed-probe seal hash from its original postexit mapping in a separate read-only receipt.
seal_receipt=json.loads((HERE/'prior-complete15-seal-binding.json').read_bytes());binding['prior_complete15_seal_sha256']=seal_receipt['result']['seal_sha256']
(out/'capacity-source.json').write_text(json.dumps(binding,ensure_ascii=False,indent=2),encoding='utf8')
plan=json.loads((out/'plan.json').read_bytes());plan['version']='Flash-seven-GPU-memory-lifetime-linked02';plan['created']=time.time();plan['memory_lifetime_repair']='dead-local tensor deletions only; identical numerical AST; 9 CPU/GPU kernel tests and full-vocabulary three-step real-input bitwise check required before GUI';plan['capacity']='reuse completed15 EOS; baseline/repair 3-step full-logit invariance; one new linked full50-image stress attempt';plan['contextual_judge']=False
(out/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
auth=json.loads((out/'user-memory-authorization.json').read_bytes());auth['linked_repair_scope']='Process-local early lifetime release, no changed numerical operation/reduction/kernel/precision; independent AST/bitwise validation. Same single-image Flash prompt and all formal budgets.'
(out/'user-memory-authorization.json').write_text(json.dumps(auth,ensure_ascii=False,indent=2),encoding='utf8')
save(out/'prior-capacity-failure-binding.json',{'preservation_receipt':str(max(prior.glob('capacity-failure-preservation-*.json'),key=lambda p:p.stat().st_mtime_ns)),'prior_postexit_seal_sha256':preserved['result']['postexit_seal_sha256'],'prior_failed_stress_images':50,'prior_failed_stress_tokens':53167,'prior_complete15_reused_not_rerun':True,'no_previous_GUI_terminal_retried':True})
(out/'private.token').write_text(secrets.token_hex(32),encoding='utf8')
files={str(p.relative_to(out)).replace('\\','/'):sha(p)for p in out.rglob('*')if p.is_file()and p.name not in ['manifest.json','private.token']and '__pycache__'not in p.parts}
for n in files:
 if n.endswith('.py'):ast.parse((out/n).read_text(encoding='utf8'))
m={**m0,'version':plan['version'],'created':time.time(),'files':files,'auth_token_sha256':sha(out/'private.token'),'output3090':OUT,'package3090':R3090,'package4090':R4090,'source_prior_manifest_sha256':sha(old/'manifest.json'),'native_memory_lifetime_repair':True}
save(out/'manifest.json',m);save(HERE/'frozen-package.json',{'manifest_sha256':sha(out/'manifest.json'),'files':len(files),'new_model_GUI_calls':0,'source_prior_manifest_sha256':sha(old/'manifest.json')})
print(json.dumps({'files':len(files),'manifest_sha256':sha(out/'manifest.json'),'remaining_GUI':29,'native_arithmetic_changes':False}))
