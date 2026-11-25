"""New source-bound placement attempt; retain every prior terminal unchanged."""
import ast
import json
import secrets
import shutil
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
PRIOR = BASE / 'flash-ample-memory-gui-20261114-linked10'
OLD = PRIOR / 'package'
assert not (HERE / 'package').exists()
preservation_file = max(PRIOR.glob('preservation-*.json'), key=lambda p: p.stat().st_mtime_ns)
preserved = json.loads(preservation_file.read_bytes())['result']
assert preserved['postexit_seal_sha256'] == 'd3a02c9982e63b3840ad450c441fb6a20675e6cd1422d629743149d420dc8906'
assert preserved['postexit_files_verified'] == 162
assert all(not v['same_live_process'] for v in preserved['processes'])

for name in ['control.py', 'launch_group.py', 'capture_live_evidence.py',
             'audit_flash_live.py', 'inspect_terminals.py', 'preserve_terminal.py',
             'peek.py', 'wait_capacity.py', 'publish_verified.py', 'capacity_gate.py',
             'memory_lifetime.py', 'torch_chunk_lifetime.py', 'mlp_lifetime.py',
             'inspect_ready.py']:
    text = (PRIOR / name).read_text(encoding='utf8').replace(PRIOR.name, HERE.name)
    if name in ['inspect_ready.py', 'publish_verified.py']:
        text = text.replace('0.85', '0.87')
    if name == 'publish_verified.py':
        # Replace two inherited prose additions with this attempt's actual change.
        text = '\n'.join(line for line in text.split('\n')
                         if not line.startswith("report=report.replace('## 已验证的实际调用'")
                         and not line.startswith("head=head.replace('以下旧头仅历史。'"))
        text = text.replace("name='Flash七卡充裕显存与完整GUI进展-20261114.md'",
            "report=report.replace('## 已验证的实际调用', 'linked10已封存162个postexit文件，50图在GPU0触发85%分配器额度。当前linked11依据同一实际权重元数据，为GPU0额外预留1.5GiB规划激活余量，减少其decoder层，并设原生allocator比例0.87、闲置缓存GC0.8。规划余量不是实测容量，实际EOS与各卡峰值准入见上表；同步和分配器可能增加延迟，双臂同版。\\n\\n## 已验证的实际调用')\nname='Flash七卡充裕显存与完整GUI进展-20261114.md'")
    (HERE / name).write_text(text, encoding='utf8')

from control import save, sha, remote, R3090, R4090, OUT

code = 'ROOT=' + repr('/data/researcher/jev-defense-four-gpu-20261106/' + PRIOR.name) + '\n' + r'''
import hashlib,json,re,time
from pathlib import Path
r=Path(ROOT)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(r/'postexit-seal.json')=='d3a02c9982e63b3840ad450c441fb6a20675e6cd1422d629743149d420dc8906'
sealed=json.loads((r/'postexit-seal.json').read_bytes())
assert sha(r/'primary/actual-state.json')==sealed['primary/actual-state.json']
rows=json.loads((r/'primary/actual-state.json').read_bytes())
layers=[0]*64;base0=0;base6=0;group={};loaded={}
for v in rows:
 name=v['name'];loaded[v['device']]=loaded.get(v['device'],0)+v['bytes']
 match=re.match(r'model\.language_model\.layers\.(\d+)\.',name)
 if match:layers[int(match[1])]+=v['bytes']
 elif name.startswith('model.visual.'):base0+=v['bytes'];group['model.visual']=0
 elif name.startswith('model.language_model.embed_tokens.'):base0+=v['bytes'];group['model.language_model.embed_tokens']=0
 elif name.startswith('model.language_model.norm.'):base6+=v['bytes'];group['model.language_model.norm']=6
 elif name.startswith('lm_head.'):base6+=v['bytes'];group['lm_head']=6
 else:raise ValueError(name)
assert len(rows)==1184 and all(layers)
kv=[0 if i%4!=3 else 53167*2*4*256*2 for i in range(64)]
prefix=[0];pweights=[0]
for w,k in zip(layers,kv):prefix.append(prefix[-1]+w+k);pweights.append(pweights[-1]+w)
margin=1536*1024**2
dp={(0,0):(0,[])}
for stage in range(1,8):
 device=stage-1;base=base0 if device==0 else base6 if device==6 else 0
 extra=margin if device==0 else 0
 for end in range(stage,65):
  candidates=[]
  for begin in range(stage-1,end):
   if(stage-1,begin)not in dp:continue
   previous,path=dp[stage-1,begin]
   score=prefix[end]-prefix[begin]+base+extra
   candidates.append((max(previous,score),path+[(begin,end)]))
  if candidates:dp[stage,end]=min(candidates,key=lambda x:x[0])
objective,parts=dp[7,64]
placement=dict(group);placement['model.language_model.rotary_emb']=0
weights={};estimates={};planning={}
for device,(begin,end)in enumerate(parts):
 for layer in range(begin,end):placement['model.language_model.layers.'+str(layer)]=device
 base=base0 if device==0 else base6 if device==6 else 0
 weights[str(device)]=pweights[end]-pweights[begin]+base
 estimates[str(device)]=prefix[end]-prefix[begin]+base
 planning[str(device)]=estimates[str(device)]+(margin if device==0 else 0)
assert sum(weights.values())==sum(v['bytes']for v in rows)
assert parts[0][1]<=4 and ''not in placement
out={'time':time.time(),'source_root':str(r),'source_actual_state_sha256':sha(r/'primary/actual-state.json'),'source_postexit_seal_sha256':sha(r/'postexit-seal.json'),'source_tensor_count':len(rows),'source_total_weight_bytes':sum(weights.values()),'previous_placed_tensor_bytes':loaded,'device_map':placement,'weight_bytes_by_device':weights,'layer_ranges_inclusive':{str(d):[a,b-1]for d,(a,b)in enumerate(parts)},'estimated_weights_plus_53167_token_full_attention_KV_bytes':estimates,'GPU0_additional_activation_planning_margin_bytes':margin,'planning_objective_bytes_by_device':planning,'planning_margin_is_not_weight_or_measured_fit':True,'KV_estimate_not_runtime_fit_proof':True,'optimizer':'contiguous whole decoder blocks; minimize maximum weights plus estimated KV plus 1.5GiB GPU0 activation planning margin','GPU_or_weights_loaded_by_planner':False,'new_model_GUI_calls':0}
print(json.dumps(out))
'''
raw, op = remote('3090', code, 'CPU-sealed-source-seven-card-GPU0-activation-margin')
placement = json.loads(raw)
save(HERE / ('seven-placement-' + str(time.time_ns()) + '.json'),
     {'result': placement, 'operation': str(op)})

out = HERE / 'package'
out.mkdir()
old_manifest = json.loads((OLD / 'manifest.json').read_bytes())
for name, expected in old_manifest['files'].items():
    assert sha(OLD / name) == expected, name
    target = out / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(OLD / name, target)
shutil.copyfile(HERE / 'launch_group.py', out / 'launch_group.py')
(out / 'explicit-placement.json').write_text(json.dumps(placement, ensure_ascii=False, indent=2), encoding='utf8')
primary = (out / 'primary_server.py').read_text(encoding='utf8')
assert primary.count('0.85') == 3
(out / 'primary_server.py').write_text(primary.replace('0.85', '0.87'), encoding='utf8')
save(out / 'linked10-preservation-binding.json', {
    'postexit_seal_sha256': preserved['postexit_seal_sha256'],
    'postexit_files_verified': preserved['postexit_files_verified'],
    'full_model_three_steps_bitwise_passed': True,
    'capacity_terminal': 'GPU0 allocator85percent budget rejected 50-image prefill',
    'physical_exhaustion_claimed': False, 'formal_GUI_calls': 0})
binding = json.loads((out / 'capacity-source.json').read_bytes())
binding.update({'linked10_postexit_seal_sha256': preserved['postexit_seal_sha256'],
                'native_allocator_limit_fraction': 0.87,
                'GPU0_activation_planning_margin_bytes': 1536 * 1024**2,
                'repair': 'Same validated private dead pointwise buffer reuse and whole-block CUDA mapping; GPU0 activation planning margin and native allocator fraction0.87; no in-forward cache purge, no mathematical/input/precision change.'})
(out / 'capacity-source.json').write_text(json.dumps(binding, ensure_ascii=False, indent=2), encoding='utf8')
plan = json.loads((out / 'plan.json').read_bytes())
plan.update({'version': 'Flash-seven-GPU-activation-aware-ample-memory-linked11',
             'created': time.time(), 'placement': placement,
             'primary_allocator_limit_fraction': 0.87,
             'GPU0_activation_planning_margin_bytes': 1536 * 1024**2,
             'runtime_tradeoff': 'Primary synchronous CUDA retained; native allocator fraction0.87 and GC0.8 may increase latency or reject larger future live sets. Whole-layer mapping accounts separately for GPU0 activation planning margin; measured reserved-peak headroom>=3GiB remains mandatory. Both formal arms identical, no truncation/downscaling/precision change/offload.'})
(out / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf8')
(out / 'private.token').write_text(secrets.token_hex(32), encoding='utf8')
files = {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*')
         if p.is_file() and p.name not in ['manifest.json', 'private.token'] and '__pycache__' not in p.parts}
for name in files:
    if name.endswith('.py'):
        ast.parse((out / name).read_text(encoding='utf8'))
manifest = {**old_manifest, 'version': plan['version'], 'created': time.time(),
            'files': files, 'auth_token_sha256': sha(out / 'private.token'),
            'output3090': OUT, 'package3090': R3090, 'package4090': R4090,
            'source_prior_manifest_sha256': sha(OLD / 'manifest.json'),
            'primary_allocator_memory_fraction': 0.87,
            'GPU0_activation_planning_margin_bytes': 1536 * 1024**2}
save(out / 'manifest.json', manifest)
save(HERE / 'frozen-package.json', {'files': len(files), 'manifest_sha256': sha(out / 'manifest.json'), 'new_model_GUI_calls': 0})
readme = f'''# linked11：激活预算与七卡完整GUI容量修复

linked10已退出，162个postexit文件封存，seal `{preserved['postexit_seal_sha256']}`。原50图在GPU0触发85%原生分配器额度，不能说物理显存耗尽；14真实MLP、9chunk与15图3步全词表logits/IDs比较已通过，0正式GUI。该旧终局不重跑。

本新attempt从其1184个实际state tensor封存元数据规划连续完整decoder blocks，在GPU0目标函数额外计入1.5GiB激活余量；实际权重字节与规划余量分开，均不是适配证明。层范围为 `{placement['layer_ranges_inclusive']}`。视觉+embedding0、norm/lm_head6、rotary0，无根dispatch钩子。全部1187参数/buffer必须CUDA，无模型CPU/disk offload，BF16/SDPA保留。

原生allocator比例0.87，GC0.8、expandable segments；主同步CUDA且forward内不清缓存，数学修复与linked09/10相同。仍须9chunk/14真实MLP输出、15图3步全词表logits/IDs逐位、新50图53167tokens自然EOS全部126IDs等于linked02及每卡reserved峰值余量>=3GiB，经inspect_ready只读核验再一次启动29未开始GUI。3步工程cap不是EOS；压力图为标明合成重复历史，不是50步GUI，不保证任意未来最坏历史。可能增加延迟或提前拒绝更大工作集，双臂同版。

只续29未开始轨迹；原2正常+1OOM和所有旧队列/已完成控制不重跑。主完整图/接受历史/原生提示解析执行评分/2048输出/50决策70actor/原seed保留。Flash每次只一完整图和通用问题，无任务、主历史、候选、前图、累积KV；YES同PNG传主无附文，NO0.5秒持续同环境新复拍至YES或手停。技术失败保全后停，不当NO。网站不重置、私有答案不入输入、不抢外人。目标active、Mirage降低未证明。
'''
(HERE / 'README.md').write_text(readme, encoding='utf8')
print(json.dumps({'files': len(files), 'manifest_sha256': sha(out / 'manifest.json'),
                  'remaining_GUI': 29, 'allocator_memory_fraction': 0.87,
                  'seven_GPU_decoder_placement': placement['layer_ranges_inclusive']}))
