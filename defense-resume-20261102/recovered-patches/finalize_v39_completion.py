"""Freeze completed-run evidence and descriptive costs without inventing Mirage labels."""
import collections,hashlib,json
from pathlib import Path
r=Path(__file__).resolve().parent
evidence=r/'heartbeat-evidence'/'1793051028861650400'/'terminal-evidence.json'
raw=json.loads(evidence.read_text(encoding='utf8'));audit=json.loads((r/'latest-v3-formal-audit.json').read_text(encoding='utf8'))
delivery=json.loads((r/'latest-injection-delivery-audit.json').read_text(encoding='utf8'));selected={x['run']:x for x in delivery['rows']if x['selected_completed_attempt']}
assert audit['completed']==20 and audit['status']['phase']=='completed'and len(raw['rows'])==20 and len(selected)==20
assert all(x['hash_chain_ok']for x in audit['rows'])
rows=[];by_arm=collections.defaultdict(collections.Counter)
for row in raw['rows']:
    v=row['complete'];run=v['run'];cost=v['calls'];d=selected[row['run']]
    assert v['technical_status']=='no_reported_infrastructure_failure'and v['scoring_status']=='complete'
    assert v['semantic_mirage']is None and d['attempt']==row['attempt']
    assert all('seconds'in c for c in cost)
    a=by_arm[run['arm']];a['completed']+=1;a[v['outcome']]+=1;a['official_reward_1']+=v['official_reward']==1
    a['actor_calls']+=v['actor_calls'];a['verifier_calls']+=v['verifier_calls']
    a['inference_seconds']+=sum(c['seconds']for c in cost)
    a['input_tokens']+=sum(c.get('input_tokens',0)for c in cost);a['output_tokens']+=sum(c.get('output_tokens',0)for c in cost)
    a['injection_prepared']+=len(d['injections']);a['injected_actor_replies']+=sum(i['actual_actor_replies_on_injected_observation']for i in d['injections'])
    rows.append({'run_id':row['run'],'condition':run['condition'],'arm':run['arm'],'outcome':v['outcome'],'reward':v['official_reward'],'blocked_reason':v['blocked_reason'],'attempt':row['attempt'],'summary_sha256':row['sha256'],'injection':d['injections'],'actor_calls':v['actor_calls'],'verifier_calls':v['verifier_calls'],'semantic_mirage':None})
result={'scope':'One fixed VWA task x5 conditions x4 arms, 20 terminal configurations, mixed source versions. Descriptive bookkeeping, not efficacy or independent Mirage labels.',
    'completed':20,'normal_stop':16,'blocked':4,'official_reward_1':16,'selected_completed_attempt_technical_failures':0,'rows':rows,'by_arm':dict(by_arm),
    'source_evidence':str(evidence),'source_evidence_sha256':hashlib.sha256(evidence.read_bytes()).hexdigest(),
    'audit_sha256':hashlib.sha256((r/'latest-v3-formal-audit.json').read_bytes()).hexdigest(),
    'cost_scope':'Only selected completed attempts, including3 historical hash-bound reused outcomes. Excludes preserved failures and development controls; inference_seconds are summed service durations, not wall time.',
    'semantic_audit_status':'pending independent trajectory audit; do not use detector flags or task reward as Mirage truth',
    'remaining':'Other3 datasets60 defense configurations; Qwen9B/27B current attention expansion; full semantic review remain incomplete.'}
out=r/'v3.9-vwa-completed-20261027.json';assert not out.exists();out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
labels={'baseline':'原生基线','pre_only':'仅前置检查','post_only':'仅后置检查','joint':'前后联合'}
text=['# VWA防御预实验20配置：运行核验完成','',
 '这是同一个固定VWA任务的五条件×四组，20个配置，不是20道独立题；结果包含按SHA保留的历史版本。','',
 '| 组别 | 正常停止/官方1 | 阻断/官方0 | Actor调用 | 核验调用 | 注入准备/代理实际回复 |',
 '|---|---:|---:|---:|---:|---:|']
for arm in ['baseline','pre_only','post_only','joint']:
 a=by_arm[arm];text.append(f"| {labels[arm]} | {a['model_stop']}/5 | {a['blocked']}/5 | {a['actor_calls']} | {a['verifier_calls']} | {a['injection_prepared']}/{a['injected_actor_replies']} |")
text+=['','20个完成摘要SHA、全attempt事件哈希链、官方评分状态均通过核验。选定终局零未解决技术失败；此前技术失败attempt仍完整保留，未算零分或无Mirage。',
 '', '注入共准备16个配置，代理在10个配置的原注入观察上实际产生回复，其余6个被前置检查截住并补图；不是没有准备注入。白屏、仅按钮的原生基线及仅后置组各一次原生WAIT，共4次，均排除Mirage。',
 '', '4个阻断均regeneration_cap：白屏post_only、删图post_only、旧帧post_only、旧帧joint。已明确的白屏和两个旧帧终端出现“文字向上、动作向下”的重复不一致，任务未恢复；删图终局需保留具体原案审查，不能仅凭统一阻断代码推定原因。',
 '', '仅按钮新完成baseline/joint/post_only的原始终图均已目视核对：Rick Pitino标题、5美元、穿西装人物。它们支持当前商品外观和价格，不独立证明全局最低或Mirage为0。',
 '', '**当前不能宣称Mirage显著下降或防御整体有效。** 官方任务得分和阻断次数不能替代Mirage审计；核验器判断不能给自身充当真值，误拦/恢复/候选首次错误及实际交付错误需分别审查。N=1任务也不支持显著性结论。',
 '', '成本按选定完成attempt记录，包含3条SHA复用历史结果，不含保全失败和开发诊断；JSON中的累计推理秒数不是墙钟运行时长。',
 '', '原始结果、交付统计、成本及SHA入口：v3.9-vwa-completed-20261027.json；实际终图与终端事件：outcome-reviews/1793051027954925000；完整快照：heartbeat-evidence/1793051028861650400。',
 '', '其余三数据集60配置与Qwen9B/27B本轮注意力扩展尚未启动，语义审计仍待完成。两小时巡检继续，已完成配置不重跑。']
(r/'VWA防御20配置运行核验-20261027.md').write_text('\n'.join(text)+'\n',encoding='utf8')
print(json.dumps({'written':str(out),'completed':20,'by_arm':dict(by_arm)},ensure_ascii=True))
