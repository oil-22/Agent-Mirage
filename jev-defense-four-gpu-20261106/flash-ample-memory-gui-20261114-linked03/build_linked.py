"""Seal a new head-scheduled memory-only variant; prior attempts remain immutable."""
import ast,json,secrets,shutil,time
from control import HERE,BASE,R3090,R4090,OUT,save,sha
prior=BASE/'flash-ample-memory-gui-20261114-linked02';old=prior/'package';out=HERE/'package';out.mkdir()
m0=json.loads((old/'manifest.json').read_bytes())
for n,h in m0['files'].items():
 assert sha(old/n)==h
 p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,p)
for n in ['capacity_gate.py','memory_lifetime.py','torch_chunk_lifetime.py','head_batched_chunk.py','launch_group.py']:shutil.copyfile(HERE/n,out/n)
preserved=json.loads(max(prior.glob('preservation-*.json'),key=lambda p:p.stat().st_mtime_ns).read_bytes())['result']
binding=json.loads((out/'capacity-source.json').read_bytes());previous='/data/researcher/jev-defense-four-gpu-20261106/flash-ample-memory-gui-20261114-linked02'
binding.update({'prior_complete50_probe':previous+'/capacity/50-image-source-bound-stress','prior_complete50_seal_sha256':preserved['stress_seal_sha256'],'linked02_postexit_seal_sha256':preserved['postexit_seal_sha256'],'repair':'Native core arithmetic unchanged; twelve independent heads per serial group; full sequence/images/precision and cache retained; complete stress IDs and three full-vocab cached steps must match before GUI.'})
(out/'capacity-source.json').write_text(json.dumps(binding,ensure_ascii=False,indent=2),encoding='utf8')
plan=json.loads((out/'plan.json').read_bytes());plan.update({'version':'Flash-seven-GPU-head-batched-memory-linked03','created':time.time(),'memory_scheduling':'Twelve independent linear-attention heads per serial batch plus early-dead-local release. Native per-head arithmetic/reduction/precision unchanged; extra launch overhead measured separately. Both formal arms same scheduling.','capacity':'reuse original15 EOS, three-step full-logit original-versus-scheduled check, new scheduled50 full-sequence ID/memory comparison against linked02 EOS','minimum_peak_reserved_headroom_GiB':3})
(out/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
auth=json.loads((out/'user-memory-authorization.json').read_bytes());auth['linked_repair_scope']='GPU memory scheduling only: independent head groups of12; no temporal/context truncation, changed model arithmetic/precision, CPU/disk model offload or semantic-gate change. Exact numerical controls required.'
(out/'user-memory-authorization.json').write_text(json.dumps(auth,ensure_ascii=False,indent=2),encoding='utf8')
save(out/'linked02-capacity-preservation-binding.json',{'postexit_seal_sha256':preserved['postexit_seal_sha256'],'postexit_files_verified':preserved['postexit_files_verified'],'complete50_EOS_and_126_tokens_preserved':True,'minimum_headroom_bytes':min(v['headroom_at_reserved_peak_bytes']for v in preserved['stress_result']['memory']),'readiness_failed_but_not_an_OOM':True,'formal_GUI_calls':0})
(out/'private.token').write_text(secrets.token_hex(32),encoding='utf8')
files={str(p.relative_to(out)).replace('\\','/'):sha(p)for p in out.rglob('*')if p.is_file()and p.name not in ['manifest.json','private.token']and '__pycache__'not in p.parts}
for n in files:
 if n.endswith('.py'):ast.parse((out/n).read_text(encoding='utf8'))
m={**m0,'version':plan['version'],'created':time.time(),'files':files,'auth_token_sha256':sha(out/'private.token'),'output3090':OUT,'package3090':R3090,'package4090':R4090,'source_prior_manifest_sha256':sha(old/'manifest.json'),'native_independent_head_scheduling':12}
save(out/'manifest.json',m);save(HERE/'frozen-package.json',{'files':len(files),'manifest_sha256':sha(out/'manifest.json'),'new_model_GUI_calls':0})
print(json.dumps({'files':len(files),'manifest_sha256':sha(out/'manifest.json'),'remaining_GUI':29,'per_head_arithmetic_changed':False}))
