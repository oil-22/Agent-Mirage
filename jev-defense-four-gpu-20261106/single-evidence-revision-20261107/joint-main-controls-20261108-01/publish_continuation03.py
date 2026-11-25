"""Publish an actually observed attempt03 without replacing immutable receipts."""
from pathlib import Path
import hashlib
import json
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
snap = next(p for p in sorted((HERE/'progress-evidence').glob('*/stdout.json'),reverse=True)
    if json.loads(p.read_bytes()).get('root','').endswith('-03'))
d=json.loads(snap.read_bytes())
assert not d.get('worker/terminal.json') and not d.get('exit.json')
for key in ['launcher-process.json','worker/process.json']:
    a=d[key]['value']['actual']
    assert a['uid']==1033 and 'joint-main-controls-20261108-03' in a['command']
    assert len(a['locks'])==9 and all(v['matches'] for v in a['locks'])
assert not d['journal']['errors']
history=HERE/'pointer-history'/str(time.time_ns());history.mkdir(parents=True)
pointer=PROJECT/'single-evidence-development-current.json'
(history/pointer.name).write_bytes(pointer.read_bytes())
launch=HERE/'technical-continuation-03/launch.json'
value={'status':'attempt03_unfinished_controls_actually_running',
    'remote_root':d['root'],'launch':str(launch),'launch_sha256':sha(launch),
    'latest_evidence':str(snap),'latest_evidence_sha256':sha(snap),
    'actual_launcher_pid_locator':d['launcher-process.json']['value']['actual']['pid'],
    'actual_worker_pid_locator':d['worker/process.json']['value']['actual']['pid'],
    'PIDs_require_full_identity_recheck':True,'loaded':bool(d.get('worker/loaded.json')),
    'journal_events':d['journal']['verified_events'],'journal_head':d['journal']['head'],
    'journal_kind_counts':d['journal']['kind_counts'],
    'primary_layer_counts':[19,24,21],'physical_GPUs':[4,5,6,7],
    'only_remaining_controls':['C05','C06','C07','C08'],'new_auxiliary_calls':0,
    'maximum_new_judge_calls':8,'prior_judge_calls_including_OOM':6,'original_judge_cap':16,
    'prior_completed_controls_not_replayed':['C01','C02','C03','C04','N13','N14','N15','N16'],
    'parent02_immutable_terminal_manifest_sha256':'f8a6eecf9bdb9e7a5bcbd99751a7b4cd9285f6e1ea78121ff88682f761baa48c',
    'formal_GUI_launch_ready':False,'actor_GUI_scorer_paid_calls':0,
    'Mirage_reduction_established':False,'last_observed_unix':d['time_unix']}
pointer.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
head='''## 最新：2026-11-08 新03技术延续已真实运行，仅C05–08，旧02不重启

`single-evidence-revision-20261107/joint-main-controls-20261108-01/technical-continuation-03/launch.json` 与最新 `progress-evidence` 为实际权威。新launcher3637267/worker3637463 UID1033/完整命令/start_ticks/九锁已重核；只作定位。原18/24/22层改为19/24/21以分散原物理6卡压力，同4–7卡、同27B+单9B/BF16/SDPA，0–3外人任务不动。预测显存只用于选择新放置，是否fit须看实际完整输入推理，跨放置bitwise输出不作保证。

仅继续原17,113token/4image、0生成的C05技术失败和未开始C06–08，旧4辅助/C01–04不重跑。C05完整request SHA、全部processor输入与原失败prepared的shape/dtype/bytes/SHA在真实生成前强制一致；原prompt、validator、full history/images、4096及1格式retry保留。新最多8judge+此前6（含OOM）<=原16cap，0新辅助/actor/GUI/scorer/付费。两模型仍联合驻留，但这批没有新的辅助答复输入actor，不能称完整辅助防御或降低Mirage。旧02终局259文件及失败日志/实际forward保全，其他旧队列禁启。

'''
handoff=PROJECT/'HANDOFF.md'
(history/'HANDOFF-before.md').write_bytes(handoff.read_bytes())
handoff.write_text(head+handoff.read_text(encoding='utf8'),encoding='utf8')
(history/'seal.json').write_text(json.dumps({p.name:sha(p) for p in history.iterdir() if p.is_file()},indent=2),encoding='utf8')
print(json.dumps({'published':str(pointer),'loaded':value['loaded'],'based_on':str(snap)},ensure_ascii=False))
