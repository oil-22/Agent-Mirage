"""Record submission and the preceding sealed terminal without inferring fit."""
import json
import time
from control import HERE, BASE, OUT, R3090, R4090, save, sha

ts = time.time_ns()
pub = HERE / ('capacity-authority-' + str(ts))
pub.mkdir()
frozen = json.loads((HERE / 'frozen-package.json').read_bytes())
plan = json.loads((HERE / 'package/plan.json').read_bytes())
value = {'time': ts / 1e9, 'goal': 'active', 'attempt': HERE.name,
         'submission': json.loads((HERE / 'service-submission.json').read_bytes()),
         'frozen': frozen, 'placement': plan['placement'],
         'native_allocator_memory_fraction': 0.87, 'unused_cache_GC_threshold': 0.8,
         'GPU0_additional_activation_planning_margin_bytes': 1536 * 1024**2,
         'prior_attempt': 'linked10 terminal, 162 postexit files preserved',
         'prior_postexit_seal_sha256': 'd3a02c9982e63b3840ad450c441fb6a20675e6cd1422d629743149d420dc8906',
         'status': 'submitted; inspect actual process/locks/evidence/terminal',
         'formal_GUI_started': False, 'formal_GUI_trajectories_consumed': 0,
         'remaining_GUI': 29, 'older_terminals_reexecuted': False,
         'main_gpu': list(range(7)), 'Flash_gpu': 7,
         'primary_synchronous_CUDA': '1', 'in_forward_allocator_purge': False,
         'runtime_root3090': R3090, 'output3090': OUT, 'GUI_root4090': R4090,
         'GUI_requires_independent_ready_audit': True, 'Mirage_reduction': None}
save(pub / 'status.json', value)
head = f'''## 最新：2026-11-14 linked11已一次提交容量验证；linked10已封存，GUI尚未开始

权威 `{HERE.name}/{pub.name}/status.json` 及实际输出。74源文件manifest `{frozen['manifest_sha256']}` 已双机逐文件核验；主3090物理0–6、Flash7，须实际UID/fullcmd/start/17与9继承锁/UUID/compute核对。禁止重复stage/service/gui。只续29未开始GUI，原2正常+1OOM和旧队列不重跑；七任务14完整新配对，T000旧帧门控单列诊断，旧三卡配对不池化。目标active，Mirage降幅null、尚未证明有效。

linked10已退出，162个postexit文件SHA核验，seal `d3a02c9982e63b3840ad450c441fb6a20675e6cd1422d629743149d420dc8906`；9chunk/14真实MLP及15图3步全词表logits/IDs通过，50图在GPU0触发85% allocator额度，非物理显存耗尽，0正式GUI。旧终局不重跑。linked11从其1184实际tensor封存元数据规划：GPU0层0–3，1层4–13，2层14–23，3层24–34，4层35–45，5层46–56，6层57–63；视觉+embedding0、norm/lm_head6、rotary0，无根钩子。目标函数额外计GPU0激活1.5GiB，实际权重和规划余量分开，非容量证明。

原生allocator0.87、GC0.8、expandable segments；主CUDA同步、forward无清缓存，数学缓冲复用同linked09/10。仍须9chunk/14真实MLP、15图3步全词表logits/IDs逐位、新50图53167tokens自然EOS全126IDs等于linked02、每卡reserved峰值余量>=3GiB和inspect_ready核验，再一次启动GUI。3步工程cap非EOS，50图为合成重复历史，非50GUI步，不保证未来任意最坏历史。同步/allocator可能增加延迟或拒绝更大集合，两正式臂同版。1187实际参数/buffer严格CUDA，BF16/SDPA、原图/完整历史/原生提示解析执行评分/2048输出/50决策70actor/原seed不变。无CPU/disk模型offload。

Flash固定revision，每次只完整单图+通用问题，无任务/主历史/候选/前图/累积KV；YES同PNG转主无附文，NO0.5秒持续同环境新复拍至YES或手停。技术失败保全后停，不当NO；单图不证明清晰旧帧新鲜或动作正确。网站不重置、私有答案不入模型、不抢外人。所有旧内存attempt终局保留。以下旧头仅历史。

'''
for name in ['HANDOFF.md', 'README.md']:
    p = BASE / name
    old = p.read_bytes()
    (pub / ('prior-' + name)).write_bytes(old)
    assert p.read_bytes() == old
    p.write_bytes(head.encode('utf8') + old)
save(pub / 'seal.json', {p.name: sha(p) for p in pub.iterdir() if p.is_file()})
print(json.dumps({'authority': str(pub / 'status.json'), 'goal': 'active', 'formal_GUI_started': False}))
