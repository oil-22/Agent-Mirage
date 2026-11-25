"""Publish this completed finite development milestone and preserve prior heads."""
import hashlib,json,time
from pathlib import Path
R=Path(__file__).resolve().parent;P=R.parent;O=R/'development-completion-02';O.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def write(p,v):
    with p.open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
refs={
    'first_GPU_terminal_collection':R/'gpu-four-terminal-collection-01/receipt.json',
    'first_GPU_root_audit':R/'first-four-root-technical-audit-02/receipt.json',
    'compact_GPU_terminal_collection':R/'gpu-compact-four-terminal-collection-02/receipt.json',
    'compact_GPU_root_audit':R/'compact-four-root-technical-audit-02/receipt.json',
    'compact_GPU_independent_audit':R/'compact-four-independent-technical-audit-linked03/receipt.json',
    'independent_semantic_review':R/'compact-four-semantic-review-02/receipt.json',
    'CPU_real_reply_actor_insertion':R/'compact-real-reply-actor-wiring-02/receipt.json',
    'compact_contract_peer_review':R/'compact-contract-peer-review-02/receipt.json',
    'report':R/'紧凑单图证据真实预检与边界-20261107.md',
    'first_report':R/'首批单图证据真实预检审查-20261107.md'}
assert all(p.is_file()for p in refs.values())
terminal=read(R/'gpu-compact-four-terminal-collection-02/original/worker/terminal.json')
assert terminal['status']=='completed_four_first_attempts'and terminal['attempted_requests']==4
assert all(x['natural_eos']and x['contract_valid']and not x['retry_performed']for x in terminal['results'])
assert read(R/'gpu-compact-four-terminal-collection-02/original/exit.json')['launcher_exit_code']==0
sem=R/'compact-four-semantic-review-02';seal=read(sem/'seal.json')
rows=seal.get('entries',seal.get('files'))if isinstance(seal,dict)else None
if rows is not None:
    for row in rows:
        name=row.get('path',row.get('file'));assert sha(sem/name)==row['sha256']
else:
    for n,h in seal.items():assert sha(sem/n)==h
for name in ['紧凑单图证据真实预检与边界-20261107.md','首批单图证据真实预检审查-20261107.md']:
    with(O/name).open('xb')as f:f.write((R/name).read_bytes())
receipt={'status':'two_finite_image_only_auxiliary_development_phases_completed_not_formal_defense',
    'created_unix_ns':time.time_ns(),'one_auxiliary':True,
    'actual_model':'Qwen/Qwen3.5-9B@c202236235762e1c871ad0ccb60c8ee5ba337b9a',
    'JEV_relationship':'S2 shared unadapted base; no decision LoRA',
    'phases':[{'actual_calls':4,'natural_EOS':1,'nonEOS_caps':3,'original_contract_valid':0},
        {'actual_calls':4,'natural_EOS':4,'nonEOS_caps':0,'compact_contract_valid':4}],
    'actual_auxiliary_calls_total':8,'automatic_retries_total':0,'parent_auxiliary_cap':24,
    'new_actor_judge_GUI_scorer_paid_calls':0,'CPU_actual_reply_actor_insertion_cases':4,
    'initial_format_failure_or_nonEOS_reclassified':False,'completed_sources_rerun':False,
    'semantic_errors_remain':True,'semantic_pass_rate_established':False,'Mirage_reduction_established':False,
    'formal_GUI_launch_ready':False,'joint_four_card_capacity_proven':False,
    'new_runtime_processes_exited':True,'holder_reservation_released':False,
    'remaining_gates':['critical source-bound negative/normal/WAIT controls',
        'actual main judge complete input and exact candidate origin/history controls',
        'joint main-plus-auxiliary four-GPU capacity',
        'review formal GUI conditions and exact tradeoff before release'],
    'references':{name:{'path':str(p),'sha256':sha(p)}for name,p in refs.items()}}
write(O/'receipt.json',receipt)
backup=O/'heads-before';backup.mkdir()
parent_header='''
## 最新：单图细证据两阶段已终局；紧凑版4 EOS，但不能称防御成功

按用户“按照你的方向进行下去”推进的最新权威为 `single-evidence-revision-20261107/development-completion-02/receipt.json` 和报告 `single-evidence-revision-20261107/紧凑单图证据真实预检与边界-20261107.md`。仅一个辅助：JEV-9B S2共享的固定Qwen3.5-9B原始基座，没有decision LoRA；原生Transformers BF16/SDPA，仅实际完整原图+固定通用提示，无任务/历史/候选/目标/隐藏标签。不是旧Flash三题的改名，也未证明优于Flash。

首批S01/S07/S13/S25四真实调用终局：1EOS因原JSON外壳契约拒绝、3个2048非EOS，0可用包，完整保留、严禁重跑。随后新S04/S10/S16/S19四图采用6文字/6元素/2不确定的紧凑格式与单完整JSON外壳无损解码；完整原图/2048/BF16/SDPA/贪心/EOS不变，4自然EOS/4契约valid/0retry。这是不同图和新提示，不是旧失败同源修复或4语义通过。两批累计8实际辅助调用，计原24cap；0新actor/judge/GUI/scorer/付费调用，不补花旧终局余量。

独立原图优先审查完整覆盖24文字/16元素：S19补全菜单遮挡标题且误标clear、单菜单项框覆盖整菜单；S10的100%框偏移；S16 Donate框含独立Close X。通知/占位区button类型保持不确定。4可读GUI不能替代blank/loading/no-results/footer/WAIT等负例，不计算Mirage率或降幅。原辅助仍是可错、非穷尽的数据，缺失不是不存在，不自动allow/block。

两批各121终局文件与全量实际tensors已镜像；紧凑版CPU/真实首forward/序列/EOS/原始回复/packet、4+25事件链、763CUDA tensors/BF16/SDPA、权重原全SHA+当前stat和官方绑定、两进程exit0/proc消失均经root与独立technical audit。新权重身份复用没有再hash19GB。单批紧凑10,464input/3,240output/143.9702summed generation秒；241.1391秒launcher/964.5565四卡GPU秒仅该窗口，holder仍持原9锁，非总成本。0–3外人任务未动。

4真实回复的actor插入只有CPU回放，供应的导出文本和预算字段保留；不冒充完整历史wire或实际新Controller/GUI。主历史账本/精确引用也仍只有CPU证明；旧absence误拦未修复。formal_GUI_launch_ready=false，联合四卡容量/新主核验真实控制/关键负例与WAIT仍未完成。下一步补这些source-bound控制；完整GUI须待具体条件与代价就绪复核。所有旧终局/旧队列继续禁止恢复，不因本里程碑暂停全局监测。

'''
paths=[(P/'HANDOFF.md','parent-HANDOFF.md'),(P/'README.md','parent-README.md'),(R/'README.md','revision-README.md')]
for p,name in paths:
    raw=p.read_bytes();(backup/name).write_bytes(raw)
    text=raw.decode('utf8');first,sep,rest=text.partition('\n')
    header=parent_header if p.parent==P else parent_header.replace('single-evidence-revision-20261107/','')
    if p.name=='HANDOFF.md':first='# 四张3090：单辅助视觉证据防御开发'
    p.write_text(first+'\n'+header+rest,encoding='utf8',newline='\n')
pointer=P/'single-evidence-development-current.json'
if pointer.exists():(backup/'previous-current.json').write_bytes(pointer.read_bytes())
pointer_value={'status':receipt['status'],'receipt':str(O/'receipt.json'),'receipt_sha256':sha(O/'receipt.json'),
    'report':str(refs['report']),'report_sha256':sha(refs['report']),'formal_GUI_launch_ready':False,
    'actual_aux_calls':8,'critical_controls_and_main_GPU_tests_outstanding':True}
temp=pointer.with_name(pointer.name+'.publishing-02')
write(temp,pointer_value);temp.replace(pointer)
write(O/'publication.json',{'published_heads':[{'path':str(p),'sha256':sha(p)}for p,_ in paths],
    'current_pointer_sha256':sha(pointer),'preexisting_heads_preserved':True,'no_automation_changed':True})
with(O/'publisher-source.py').open('xb')as f:f.write(Path(__file__).read_bytes())
write(O/'seal.json',{str(p.relative_to(O)):sha(p)for p in O.rglob('*')if p.is_file()})
print(json.dumps({'receipt_sha256':sha(O/'receipt.json'),'report_sha256':sha(refs['report']),'completion_seal_sha256':sha(O/'seal.json'),'formal_GUI_ready':False}))
