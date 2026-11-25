"""Record verified operational facts; never infer semantic Mirage labels."""
import json,time
from pathlib import Path

here=Path(__file__).resolve().parent
watch=json.loads((here/'v3-foreground-watch-latest.json').read_text(encoding='utf-8'))
inventory=json.loads((here/'adapter-source-inventory.json').read_text(encoding='utf-8'))
contract=json.loads((here/'osworld-native-contract.json').read_text(encoding='utf-8'))
cost=json.loads((here/'latest-runtime-cost.json').read_text(encoding='utf-8'))
receipt=json.loads((here/'v3.8.3-vwa-resume.json').read_text(encoding='utf-8'))
summary={'recorded_at':time.time(),'source_snapshot_time':watch['time'],
 'formal':{'worker':receipt['pid'],'release':receipt['release'],'attempt':watch['attempt'],
           'phase':watch['batch_phase'],'counts':watch['counts'],'done':watch['done'],
           'reported_technical_failure':watch['technical_failure']},
 'resources':{'gpus':receipt['service']['gpus'],'model_replicas':1,
              'gpu_5':'Excluded: unrelated / ownership-unconfirmed process',
              'linear_speedup_claim':False},
 'scheduling':{'formal_priority':receipt['priority_runs'],'new_development_inference_calls_this_continuation':0,
               'hourly_automation_restored':False},
 'other_dataset_preparation':{'osworld_native_contract':contract['native_system_matches_actual_archive'],
                             'osworld_online_started':False,'other_three_datasets_formal_started':False},
 'semantic_mirage_rate':None,'statistically_significant_reduction':None,
 'scope':'Operational status and native-adapter preparation only. WAIT excluded. One task x twenty configurations; no efficacy claim.'}
(here/'execution-acceleration-latest.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
c=watch['counts'];done=watch['done'];md=[
 '# 3090防御实验：执行核实', '',
 f'本快照来自在线事件时间戳 {watch["time"]}。正式轮次仍在运行时，以下计数会继续变化。', '',
 f'- 模型服务使用物理卡0、1、2、3、4、6、7，共7张3090，承载同一份BF16/SDPA的27B模型。第5卡避开归属未确认的进程。多卡解决容量限制，尚未测得线性提速。',
 f'- 在线空白joint轮次：{c.get("candidate",0)}条候选，{c.get("action_executed",0)}次实际动作，{c.get("verifier_raw",0)}/{c.get("verifier_request",0)}次核验回复，{c.get("recapture_requested",0)}次真实重截图，{c.get("verifier_format_failure",0)}次格式故障。',
 '- 优先顺序仍为完整空白joint、完整空白baseline，再继续原队列；本次接续没有新增开发推理或重复启动正式轮次。',
 '- 空白截图被交付给截图检查器，随后真实重截图，输入及搜索得到下一观察确认。这证明补图流程可用，不能单凭它证明Mirage降低。',
 '- 独立4步baseline诊断在同一空白上明确指出空白并选择原生WAIT，按用户口径不计Mirage。该诊断不算正式完成数，不运行官方评分。',
 '- 当前正式范围仍为一个任务的20配置。其余三个数据集60配置尚未在线启动。OSWorld已对齐实际27B历史请求的提示、解析和归一化坐标换算；仍需环境和完整actor/评分绑定。', '',
 '当前没有可报告的统计降率结果。首次候选错误与过滤后执行错误分别审查，后来纠正不抵消首次发生；未审查轨迹不标记为阴性。', '',
 '[真实补图及阴性对照](空白注入在线补图案例-v3.8.3.md) · [此前误点击被拦案例](在线修复案例-v3.6.2.md)', '',
 '模型服务的汇总耗时包含开发和正式调用，不能当整题成本或提速对照。最新均值：'+', '.join(f'{k} {v["mean_seconds"]}秒' for k,v in cost['groups'].items()if k in {'screen','verify','actor'})+'。',
 ]
(here/'加速执行状态-20261025.md').write_text('\n'.join(md),encoding='utf-8')
print(json.dumps({'written':'execution-acceleration-latest.json','candidate':c.get('candidate'),'actions':c.get('action_executed'),'formal_done':done is not None}))
