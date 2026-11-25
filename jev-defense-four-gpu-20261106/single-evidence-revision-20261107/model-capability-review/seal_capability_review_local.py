"""Local-only source synthesis. Does not import model libraries or use network."""
import hashlib,json,time
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]
D=Path(r'D:\MultiModel')
S=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
A=H/'official-small-source-1794046077389119500'
N=H/'native-small-metadata-linked02-1794046900308884400'
T=D/'jev-defense-validation-20261103/model-research-targeted/1793970598557122600'
F=D/'jev-defense-four-gpu-20261106/flash-preparation'
O=H/('completed-source-review-'+str(time.time_ns()));O.mkdir(exist_ok=False)
for root in [A,N]:
 for name,h in read(root/'seal.json').items():assert S(root/name)==h
q=read(N/'qwen-fixed-api.json');j=read(N/'jev-fixed-api.json')
assert q['sha']=='c202236235762e1c871ad0ccb60c8ee5ba337b9a'
assert j['sha']=='7ac669b8fb476ba926491e3d1c39f9330d68dbed'
qfiles={x['rfilename']:x for x in q['siblings']};jfiles={x['rfilename']:x for x in j['siblings']}
assert 'generation_config.json'not in qfiles
old3090=read(D/'attention-audit-20261031/model-sha256-3090.json')['files']
old4090=read(D/'attention-audit-20261031/model-sha256-4090.json')['files']
shards=[]
for name,item in qfiles.items():
 if name.endswith('.safetensors'):
  old=old3090['Qwen3.5-9B/'+name];other=old4090['Qwen3.5-9B/'+name]
  assert old==other and old['sha256']==item['lfs']['sha256']and old['bytes']==item['lfs']['size']
  shards.append({'path':name,'bytes':item['size'],'sha256':item['lfs']['sha256']})
assert len(shards)==4 and sum(x['bytes']for x in shards)==19306310880
sources={
 'flash-native-model.py':F/'source-fixed/src/pplx_decider/model.py',
 'flash-native-protocol.py':F/'source-fixed/src/pplx_decider/protocol.py',
 'flash-native-types.py':F/'source-fixed/src/pplx_decider/types.py',
 'JEV9B-model-card.md':T/'autotrust--JEV-9B--README.md',
 'JEV9B-native-serve.sh':T/'autotrust--JEV-9B--vl--serve.sh',
 'JEV9B-native-serve_decide.py':A/'autotrust--JEV-9B--vl--serve_decide.py',
 'JEV9B-adapter_config.json':A/'autotrust--JEV-9B--vl--adapter_config.json',
 'JEV9B-decision_head.json':A/'autotrust--JEV-9B--vl--decision_head.json',
 'Qwen9B-config.json':A/'Qwen--Qwen3.5-9B--config.json',
 'Qwen9B-model.safetensors.index.json':A/'Qwen--Qwen3.5-9B--model.safetensors.index.json',
 'Qwen9B-preprocessor_config.json':N/'Qwen--preprocessor_config.json',
 'Qwen9B-tokenizer_config.json':N/'Qwen--tokenizer_config.json',
 'Qwen9B-chat_template.jinja':N/'Qwen--chat_template.jinja',
 'Qwen9B-LICENSE':N/'Qwen--LICENSE',
 'JEV9B-fixed-api.json':N/'jev-fixed-api.json',
 'Qwen9B-fixed-api.json':N/'qwen-fixed-api.json',
}
bindings=[];git_checks=[]
for name,path in sources.items():
 raw=path.read_bytes();(O/name).write_bytes(raw)
 bindings.append({'copy':name,'source':str(path),'sha256':S(path),'bytes':len(raw)})
 mappings={
  'JEV9B-model-card.md':(jfiles,'README.md'),
  'JEV9B-native-serve.sh':(jfiles,'vl/serve.sh'),
  'JEV9B-native-serve_decide.py':(jfiles,'vl/serve_decide.py'),
  'JEV9B-adapter_config.json':(jfiles,'vl/adapter_vllm/adapter_config.json'),
  'JEV9B-decision_head.json':(jfiles,'vl/adapter_vllm/decision_head.json'),
  'Qwen9B-config.json':(qfiles,'config.json'),
  'Qwen9B-model.safetensors.index.json':(qfiles,'model.safetensors.index.json'),
  'Qwen9B-preprocessor_config.json':(qfiles,'preprocessor_config.json'),
  'Qwen9B-tokenizer_config.json':(qfiles,'tokenizer_config.json'),
  'Qwen9B-chat_template.jinja':(qfiles,'chat_template.jinja'),
  'Qwen9B-LICENSE':(qfiles,'LICENSE'),
 }
 if name in mappings:
  inventory,key=mappings[name]
  blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
  assert blob==inventory[key]['blobId'],name
  git_checks.append({'file':name,'expected_git_blob':blob,'fixed_API_bound':True})
pre=read(O/'Qwen9B-preprocessor_config.json');tok=read(O/'Qwen9B-tokenizer_config.json');config=read(O/'Qwen9B-config.json')
assert config['text_config']['eos_token_id']==248044
assert tok['added_tokens_decoder']['248044']['content']=='<|endoftext|>'
assert tok['added_tokens_decoder']['248046']['content']==tok['eos_token']=='<|im_end|>'
assert pre['size']=={'longest_edge':16777216,'shortest_edge':65536}
checkpoint=read(O/'Qwen9B-model.safetensors.index.json')['metadata']['total_size']
assert checkpoint==19306216416
assert config['text_config']['vocab_size']==248320 and config['text_config']['hidden_size']==4096
matrices_min=2*248320*4096*2 # untied input embedding + lm_head at BF16, excluding ALL other tensors.
receipt={
 'status':'source_capability_review_complete_no_new_model_result',
 'selected_single_auxiliary_package':'autotrust/JEV-9B',
 'package_revision':j['sha'],'shared_multimodal_S2_base':'Qwen/Qwen3.5-9B','base_revision':q['sha'],
 'S2_actual_weights':'unmodified base vision-language generation, decision LoRA/head disabled; model alias is not a distinct visual fine-tune',
 'native_original_serving':'vl/serve.sh -> vLLM with one engine, S1 jev-decision LoRA; S2 plain chat/completions selects base served name',
 'typed_decide_system2_only_is_not_freeform_evidence_endpoint':True,
 'flash_freeform_OCR_or_arbitrary_boxes_supported':False,
 'native_files':bindings,'fixed_source_git_blob_checks':git_checks,
 'reuse_existing_base':{'3090':'/home/researcher/models/Qwen3.5-9B','4090':'/data/researcher/models/Qwen3.5-9B','historical_full_identity_3090':str(D/'attention-audit-20261031/model-sha256-3090.json'),'historical_full_identity_4090':str(D/'attention-audit-20261031/model-sha256-4090.json'),'historical_transfer_receipt':str(D/'attention-audit-20261031/model-transfer-verification.json'),'four_official_LFS_match_both_historical_full_SHA_receipts':True,'shards':shards,'currently_present_and_stat_stable_not_asserted_by_this_local_review':True,'new_full_hash_or_attention_worker':False},
 'weights_reference':{'full_checkpoint_file_bytes':sum(x['bytes']for x in shards),'full_checkpoint_tensor_bytes':checkpoint,'checkpoint_contains_MTP':True,'exact_instantiated_native_parameter_bytes_not_measured_here':True,'mandatory_BF16_untied_embedding_and_lm_head_only_lower_bound':matrices_min,'other_layers_vision_buffers_activations_cache_and_workspaces_are_additional':True,'primary27B_prior_native_tensor_bytes':54713457120,'primary27B_plus_full9B_checkpoint_reference_bytes':54713457120+checkpoint,'reference_is_not_exact_simultaneous_GPU_memory_or_fit_proof':True,'current_GPU7_primary_share_cannot_be_reused_as_deployment_proof':True},
 'native_processor':pre,'native_config_dtype':config['text_config']['dtype'],'official_vl_serve_dtype_flag':'not_explicit_vLLM_auto_depends_on_config/runtime','native_chat_template_default':'thinking enabled unless enable_thinking=False explicitly supplied',
 'generation_defaults':{'official_generation_config_file_absent_from_fixed_API':True,'config_EOS':248044,'tokenizer_EOS':248046,'new_auxiliary_experiment_to_explicitly_freeze':{'dtype':'bfloat16','backend':'sdpa','enable_thinking':False,'do_sample':False,'max_new_tokens':2048,'eos_token_id':[248044,248046]},'new_effective_settings_are_not_official_repository_generation_config_defaults':True,'vLLM_S2_plain_endpoint_explicit_EOS_override_in_JEV_source':False,'typed_decide_s2_dist_stops_on_end_think_then_reads_option_distribution':True},
 'license':{'JEV9B':'Apache-2.0 declared in fixed model card/API; no standalone LICENSE in fixed repo inventory','Qwen9B':'Apache-2.0 full LICENSE read and fixed Git blob verified'},
 'independent_evidence_contract':'full original screenshot + frozen generic prompt only; no task, history, actor candidate, cropped/marked inputs or hidden source labels; text/element boxes are model predictions with local unknown, image SHA and original coordinate space; schema-valid is not truthful',
 'minimal_next_step':'native CPU input/default audit and new finite single-image GPU capacity preflight under owned once-only lock contract; no full GUI before source-bound semantic controls and resource admission',
 'Transformers_native_new_S2_vs_published_vLLM':'same fixed base weights, explicitly different engine; no bitwise/parity claim without validation',
 'new_weight_downloads':0,'new_model_GPU_GUI_health_scorer_calls':0,'downloaded_model_repo_code_executed':False,
 'preserved_source_fetch_failures':['official-small-source-1794045369334733000 network sandbox denied','native-small-metadata-linked02-1794046900308884400 unavailable generation_config/NOTICE/standalone JEV LICENSE/calibration reads; fixed API proves first three absent; calibration not required for S2-only generation'],
 'four_image_source_first_labels':'parent separately sealed source-first-four-root-review-01; not reproduced or claimed by this capability review',
}
(O/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
(O/'reuse-base-and-package-manifest.json').write_text(json.dumps({'package':j['id'],'package_revision':j['sha'],'base':q['id'],'base_revision':q['sha'],'base_files':list(qfiles.values()),'JEV_native_VL_files':[x for x in jfiles.values()if x['rfilename']in['vl/serve.sh','vl/serve_decide.py','vl/calibration.json','vl/adapter_vllm/adapter_config.json','vl/adapter_vllm/adapter_model.safetensors','vl/adapter_vllm/decision_head.json']],'S2_uses_no_decision_adapter':True,'no_actual_download_or_loading_by_manifest':True},ensure_ascii=False,indent=2),encoding='utf8')
report='''# 单辅助细粒度视觉证据模型能力审查

建议采用 `autotrust/JEV-9B` 部署包的共享基座 S2 多模态生成路线。它提供所需的自由文本能力入口，比把当前 Flash 固定选项接口当作 OCR 更符合本次需求；尚未证明在本项目读图、框定位或降低 Mirage 上更好，也未证明与主27B同驻四卡能够适配。

JEV包固定 `7ac669b8fb476ba926491e3d1c39f9330d68dbed`；原生 `vl/serve.sh` 明确使用完整多模态 `Qwen/Qwen3.5-9B`，固定 `c202236235762e1c871ad0ccb60c8ee5ba337b9a`。同一引擎 S1 使用 jev-decision LoRA，S2 使用无 adapter 的原基座和 lm_head。S2生成的细读能力实际来自Qwen基座，不能说决策头学会了OCR。模型名是服务别名，不是另一套视觉微调权重。

官方 `vl/serve_decide.py` 的 `/v1/decide` 即便设置 `system2_only`，仍是先 thinking 再读选项概率，不能用作自由证据JSON。应使用原共享基座普通 `/v1/chat/completions`，或明确记录引擎改变的原生 Transformers `Qwen3_5ForConditionalGeneration` 路径；不能未经验证声称 Transformers 与官方vLLM逐位一致。

现有Flash native源码载入 `Qwen3_5Model` 和255类marker readout，没有自由生成路径。choice/noul/score可回答更细的预设问题，也可定义固定区域分类，但不能发现选项外的任意文字或自行输出任意元素框。NeoHorse、Jev-Style和RSI同属此类局限。MiniCPM-OCR-Jev需要候选OCR和渲染图，违反本次仅原图＋固定通用问句的输入约束；WeMM-JEV约52GB级辅助与主27B四卡预算冲突。外榜不作为项目效果证明。

原生processor为Qwen3VLProcessor／Qwen2VLImageProcessorFast，原配置像素预算65536至16777216，patch16／merge2。完整原图传输与内部smart resize不是同一件事，须记录实际pixels/grid。问题不得含任务、目标、历史、actor候选或来源标签；不裁图、不画框。返回的原文、元素框和局部未知仍是预测，引用应绑定原图SHA及原图坐标；schema有效不等于真实。

官方固定filetree没有generation_config.json。config EOS为248044(endoftext)，tokenizer EOS为248046(im_end)。原模板未显式关闭时启用thinking。新的BF16／SDPA、enable_thinking=False、贪心2048与双EOS[248044,248046]必须作为本次辅助的新有效条件冻结，而不是伪称仓库默认。JEV普通S2端点源码没有额外显式EOS覆盖；其typed-decision thinking路径停在end_think再读选项，属于另一接口。

已有完整9B资产可优先复用：3090 `/home/researcher/models/Qwen3.5-9B`，4090 `/data/researcher/models/Qwen3.5-9B`。新的官方固定API四分片LFS身份与20261031两机全SHA回执逐项相同，文件总19,306,310,880字节；本审查没有重新读大权重、重新全hash或恢复attention worker。当前存在性/文件stat由新的独立资源资产核对负责。包内VL adapter为176,647,800字节，S2不启用该决策adapter；如为完整包留存下载需单独按固定LFS校验，不能混进S2推理。

index的checkpoint张量总19,306,216,416字节，含MTP，不能直接叫作实际实例化的GPU参数量。仅必须的BF16 untied输入embedding与lm_head已至少4,068,474,880字节，其余32层、视觉塔、buffers、KV/prefill和workspace另计。按完整checkpoint作保守参数容量参考，与既有主27B native张量54,713,457,120字节合计74,019,673,536字节，仍不能证明四卡fit。旧GPU7上主模型共驻布局不能直接挪用；先有限单辅助capacity gate，再准备新27B＋辅助布局和串行请求，不能把串行推理误当参数无需共驻。

Qwen Apache-2.0完整LICENSE已读并核固定Git blob；JEV固定模型卡/API声明Apache-2.0，该repo未列单独LICENSE文件。已取得源码、配置、模板和API固定对象，11份原始小文件的Git blob校验通过。调研只下载小元数据，不执行模型仓库代码，0权重下载／0模型GPU推理／0GUI／0health／0scorer。失败的小文件读取独立保留；没有把不存在的generation_config当技术修复。

最小可行方案为一个共享9B S2辅助：固定中立问题＋一张原图，返回有局部未知的证据JSON；主框架用独立历史一致性与严格原生动作约束处理历史/坐标，辅助不直接自动allow或block。CPU入口与少量读图容量检查不等于正式防御通过；完整语义正常/负例/WAIT、四注入匹配GUI及效果比较仍须后续有限预检和资源准入。

固定文件下载/复用manifest、逐来源SHA、默认值和未测范围见receipt.json与reuse-base-and-package-manifest.json。本文不重复封存父任务已完成的四张图source-first标签。
'''
(O/'单JEV细粒度证据能力与原生S2边界-20261107.md').write_text(report,encoding='utf8')
(O/'seal.json').write_text(json.dumps({p.name:S(p)for p in O.iterdir()if p.is_file()},indent=2),encoding='utf8')
print(json.dumps({'root':str(O),'receipt_sha256':S(O/'receipt.json'),'report_sha256':S(O/'单JEV细粒度证据能力与原生S2边界-20261107.md'),'manifest_sha256':S(O/'reuse-base-and-package-manifest.json'),'seal_sha256':S(O/'seal.json')},ensure_ascii=False))
