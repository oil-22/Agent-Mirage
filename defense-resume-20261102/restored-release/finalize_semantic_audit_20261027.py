"""Write the audit report, append-only handoff snapshots and automation payload."""
import hashlib
import json
import tomllib
from pathlib import Path

BASE=Path(__file__).resolve().parent
ATT=BASE.parent/'crossmodel-injection-attention-20261025'
ptr=json.loads((BASE/'semantic-review-complete-current.json').read_bytes())
out=Path(ptr['directory'])
review_raw=(out/'review.json').read_bytes()
assert hashlib.sha256(review_raw).hexdigest()==ptr['review_sha256']
d=json.loads(review_raw)
assert d['counts']['reviewed_candidates']==542
assert not (out/'handoff-before').exists()
sha=lambda raw:hashlib.sha256(raw).hexdigest()
save=lambda p,obj:p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
rr=d['rows'];counts=d['counts']
supplement={
 'accepted_semantic_positive_candidates':sum(r['accepted']for r in rr if r['candidate_semantic_mirage']is True),
 'rejected_semantic_positive_candidates':sum(not r['accepted']for r in rr if r['candidate_semantic_mirage']is True),
 'accepted_semantic_positive_without_environment_action':sum(r['accepted']and not r['environment_action_executed']for r in rr if r['candidate_semantic_mirage']is True),
 'candidates_with_any_unresolved_subclaim':sum(bool(r.get('unresolved_subclaims'))for r in rr),
 'positive_candidates_also_containing_unresolved_subclaims':sum(r['candidate_semantic_mirage']is True and bool(r.get('unresolved_subclaims'))for r in rr),
 'source_event_chains_verified':20,
 'source_candidate_event_public_bindings_verified':542,
 'current_review_sha256':ptr['review_sha256'],
 'label_seal_sha256':d['semantic_labels_precede_execution_join_sha256'],
 'model_calls':0,'gui_actions':0,'official_evaluations':0,
}
save(out/'supplementary-statistics.json',supplement)
table='\n'.join('|'+ '|'.join(map(str,[r['run_id'].replace('vwa--classifieds_112--','').replace('--',' / '),r['candidate_count'],r['positive_candidates'],r['accepted_executed_positive_candidates'],r['native_action_error_candidates'],r['accepted_executed_native_action_errors']]))+'|'for r in d['trajectories'])
report=f'''# 原VWA20逐候选语义审查：542个候选覆盖完成（2026-10-27）

原20配置的542个实际候选均已审阅。按用户“边界计入、发生后即计入、后续纠正不抵消、纯native WAIT排除”的口径，确认139个候选含至少一个无依据或被实际视觉证据反驳的断言。20个配置均有至少一次阳性；它们是**同一个固定任务的20个逻辑配置**，不是20个独立任务，且版本混用，不能据此比较防御效力。

审查与原核验器判定独立：先看实际交付原图、候选及合法历史，封存语义标签，再关联PRIVATE执行索引。单一审查者，历史包含防御反馈，非全盲，也没有多评审一致性结果。

## 计数与边界

|指标|候选数|解释|
|---|---:|---|
|已逐项审阅|542|未审0；原图和合法输入绑定逐一校验|
|确定含语义Mirage|139|一个候选多种错误仍只计一个候选；包括再生成中的重复发生|
|阳性中接受且实际执行后续动作|120|不等于120次错误原生动作|
|阳性被接受|123|其中3个STOP没有环境动作；16个被拒绝|
|无确定阳性、但有未决子断言|54|不标成无Mirage；小图衣着及全局最低价等保留不确定|
|纯native WAIT排除|4|显式识别空白/加载仍单独记录|
|明确原生动作目标/方向错误|81|独立计数，不把坐标或prose/JSON冲突自动当感知Mirage|
|上述动作错误被接受并执行|65|后续可能局部恢复，原发生不抹去|

共有62个候选仍有至少一个未决子断言，其中8个同时具有另一项确定错误。139与54的区分是“是否已有确定阳性”，并不意味着其余子断言全部已解决。未发现确定错误的候选仅有范围受限的判断，不代表所有隐含细节为真。审阅覆盖完成不等于所有子断言均得到确定真值。

## 新的实质发现

1. **视觉漏认和错误唯一性。** 原图3e254f50…的30美元Victor Wembanyama球员卡清楚显示绿色西装男（原像素402—497、81—160）。16个当前视口否定、17个历史page2否定、29个全局唯一断言含这一反证；类别多标签有重叠。它推翻“只有Rick Pitino书符合”，并不推翻5美元是最低价。不能把30美元反例误写成发现了更便宜的商品。
2. **把点击意图当成已翻页。** 多条当前图显示25—36/50或选中3，候选仍说第4页；累计65个当前页身份错误。某些“点击第1页”的坐标实际位于商品文字，随后确实打开Duke年鉴详情。后续back/正确分页返回第1页只是局部恢复。
3. **文字UP、native DOWN。** 33个候选发生此冲突，作为动作一致性错误单列。四条最终block轨迹的末尾冲突没有在原预算内恢复；其它执行过错误方向的轨迹后来恢复不抵消原错误。
4. **核验器自身也会误读。** 对原图5ca10255…重新直接核对：page4按钮原像素792—831、470—510；native628/629/630,679分别映射803.84/805.12/806.4,488.88，均在按钮内部。原post_only第019候选曾被point reader称作按钮间隙，独立审查不采用该结论；第020实际被接受执行后到第4页。原018的拒绝还涉及page3衣着未决断言，不能把所有拒绝都归因于坐标。这里仅修正离线标签，没有改模型输出、框、validator、预算或重跑终局。
5. **页数与来源记忆。** 滑动分页显示1/2/3或1/2/3/4不代表总共3或4页；两条确定总页数断言错误。另两条候选提及未在此前实际交付图或合法文本中出现的4美元商品，按无依据具体来源状态计入；不据此断言隐藏站点绝不存在4美元商品。

“only I observed/identified”并明确保留不确定的主观识别范围，没有自动等同为对全体商品的唯一性保证。小JMU球队合照中的服装细节不强行造真值；笼统“expensive”也不擅自解释成所有物品都高于5美元。

## 逐配置描述（不可作因果排名）

|条件 / arm|候选|确定语义阳性|阳性接受且执行|动作错误候选|动作错误接受且执行|
|---|---:|---:|---:|---:|---:|
{table}

每配置首个错误候选、原图/包SHA、接受执行状态、原终局SHA及局部恢复链均见review.json。官方任务得分、候选语义、动作错误分别保留；官方1不等于无Mirage，block也不证明防御成功。不可将不同版本与重复历史结果做显著性/总体Mirage率/公平arm比较。

## 封存与验证

- 权威指针：`semantic-review-complete-current.json`；旧partial-current已转向同一新结果，旧40/160封存目录均保留。
- 完整审查：`semantic-review-complete/1793111865686362200/review.json`，SHA `{ptr['review_sha256']}`。
- 本轮382标签封存（早于执行关联）：SHA `{d['semantic_labels_precede_execution_join_sha256']}`。
- 全20远端events与终局SHA、全部event链及542个候选事件/actor public输入绑定复核通过。实际交付图base64与原PNG逐字节验证，没有替换原图。
- 关联脚本一次元数据断言失败被保全在`join-metadata-failure-preservation`：导出字段实际是candidate事件哈希，不能当作候选纯文本哈希。修正后分别核验事件封套SHA、原文本SHA和public输入SHA。0模型/GUI/评分调用，语义标签未改。
- 本轮只读健康证据`heartbeat-evidence/1793111971146570900`：服务UID1033/whz、完整release命令、实际持锁PID、最近请求/回复及日志SHA、站点HTTP200；4090无匹配旧实验worker。未启停任何服务/终局队列。

原27B注意力扩展、其它60原生配置完整在线预检及joint正常页脚readiness误拦的独立诊断仍待办；UI双GPU条件选择仍待答复，不重问、不默认批准。总体两小时monitor继续ACTIVE，旧机制队列保持暂停。此次没有推理、GUI操作、评分或付费调用。
'''
report_path=BASE/'原VWA20语义审查完成-542候选-20261027.md'
assert not report_path.exists()
report_path.write_text(report,encoding='utf-8')
header=f'''# 最新2026-10-27：原20的542个候选全部审阅，语义阳性与动作错误独立计数

权威`semantic-review-complete-current.json`（旧partial-current也指向新结果），完整`semantic-review-complete/1793111865686362200/review.json`，SHA{ptr['review_sha256']}；中文`原VWA20语义审查完成-542候选-20261027.md`。全542候选审阅覆盖完成、0未审；139候选含确定边界口径语义Mirage，123接受（含3STOP无环境动作）、120接受且执行；另54无确定阳性但含未决子断言，不标成无Mirage；4纯nativeWAIT排除。共62候选有未决子断言，其中8同时有另一确定错误。独立动作错误81、其中65接受且执行，不能把120阳性候选都叫错误原生动作。20配置均至少一次阳性，但为一个固定任务×5条件×4arms，混版本/3历史封存，不是20独立任务/显著效力或公平排名。

本轮382标签先于PRIVATE执行索引关联封存，SHA{d['semantic_labels_precede_execution_join_sha256']}。全20远端events/终局SHA与完整event链、542候选事件/合法public输入/实际图绑定复核通过。新确定反证：30美元Victor卡3e254…清楚绿色西装男，推翻“无西装/全局唯一”，不推翻5美元最低；65当前页身份错误，多次page3误称page4；33文字up/nativeDOWN单列动作冲突。JMU小图、微小卡片及最低价未决不造真值；明确only-I-observed/identified+不确定范围不自动当全局唯一。后续局部回到page1/详情不抵消原发生；single-reviewer/历史含反馈，非全盲。

关键离线纠正：5ca1原图page4按钮792..831,470..510，native628/629/630,679均在其内；原post_only019 reader称gap不能作真值，020接受执行后确到page4。018另有衣着未决断言，不能把所有拒绝都归因于坐标。没改框/JSON/validator/预算或重跑。关联脚本一次字段语义断言失败已封存：source_candidate_sha256是完整事件SHA而非文本SHA；修正后分别核事件/文本/public绑定，0模型调用，标签未变。

只读健康`heartbeat-evidence/1793111971146570900`：27B UID1033/whz、完整命令、service.lock实际PID持锁、最近请求回复/日志SHA、站点HTTP200；4090无匹配旧worker。原20、新版两终局、UI完成控制与Qwen9/GLM终局全部封存不重启。UI双GPU选择仍待答复，不重问或默认同意。其余60原生完整在线预检、原27B注意力及joint页脚readiness诊断仍待办，整体monitor保持ACTIVE、旧队列暂停。不要重复播报旧完成结果；语义覆盖已完，未来不要把它仍列为382未审或重跑标签脚本。

--- 以下为历史交接 ---

'''
backup=out/'handoff-before';backup.mkdir()
for p in [BASE/'README.md',BASE/'REPAIR_HANDOFF.md',ATT/'HANDOFF.md']:
    raw=p.read_bytes();name=('attention-'if p.parent==ATT else 'defense-')+p.name
    (backup/name).write_bytes(raw)
    p.write_bytes(header.encode('utf-8')+raw)
auto_path=Path('C:/Users/researcher/.codex/automations/mirage/automation.toml')
auto_raw=auto_path.read_bytes();(backup/'automation.toml').write_bytes(auto_raw)
auto=tomllib.loads(auto_raw.decode('utf-8'))
prompt=auto['prompt']
start=prompt.index('Partial original20 semantic audit ')
end=prompt.index('\n\nAttention remains finished:',start)
new='''Original20 semantic review now has COMPLETE CANDIDATE COVERAGE542/542,0unreviewed. Prefer semantic-review-complete-current.json (partial-current also points here), review semantic-review-complete/1793111865686362200/review.json SHAb7df2711eb9edd8d96dd3c700a824bed416199d59fa06a36ad48cdda5a9b1c4d, Chinese report 原VWA20语义审查完成-542候选-20261027.md.139definite boundary-inclusive candidate semanticMirage,123accepted (3STOP without environment action),120accepted+executed;54additional candidates have unresolved subclaims and no definite positive, not noMirage.62candidates have any unresolved subclaim,8also a definite other error.4pure nativeWAIT excluded.81separate native-action target/direction errors,65accepted+executed;120positive candidates are NOT120wrongnativeactions. All20logical configs have at least1positive, but ONEfixed task/mixed versions/3historical preserved results, not20independenttasks or fair efficacy/ranking.16current-suit absence+17historicalpage2absence+29globaluniqueness+65pageidentity categories overlap. Actual30dollar green-suit Victorcard3e254 refutes no-suit/uniqueness, NOT5dollar minimum.33up-prose/nativeDOWN errors separate. JMU small images/globalminimum retain uncertainty; qualified only-I-observed/identified not automatically global uniqueness. Local recovery to page1/detail does not erase occurrence. Single reviewer, legal feedback histories, not fullyblind. Full coverage does not resolve all subclaims. New382labels sealed BEFORE PRIVATEexecutionjoin SHA4ae8cba2fe54682da8f260649427a6531a2bd3b8bda29f15f9fb02ad3a255c37; all20remote event/terminal SHA+eventchains and542event/text/public/image bindings verified. Join-only metadata assertion failure preserved: source_candidate_sha256 is EVENT hash not raw text hash; corrected verification checks both plus public,0modelcalls,labels unchanged. Never rerun old label scripts or say382unreviewed.

Important independent correction: on ORIGINAL5ca1 page3 bottom, page4 button pixels792..831,470..510; native628/629/630,679 map803.84/805.12/806.4,488.88 INSIDE4, NOT gap. Originalpost_only019 point-reading gap verdict is false evidence,020executed then actualpage4.018also had unresolved page3 suit claim; do not attribute every block to coordinates. This is offline audit only: no box/actionJSON/validator/budget edits or terminal reruns. Preserve originals. Native-source-only progress remaining-native-source-freeze-current.json still6WebMall/Android files provenanceSHA9c4c5877e32143536041221fe35ea3460c26fe56c6628ad090f11c9ac82cca07, ASTread/noGUI/noinference. Android native dialect not original27Brequestbinding; full prompts/parser/effective defaults/same-live recapture/isolatedownership/scorer unresolved. Do not start60formal configurations/oldlaunchers.'''
prompt=prompt[:start]+new+prompt[end:]
prompt=prompt.replace('Other authorized work: original20 independent semantic review and other3datasets60defense native adapters/complete live preflights.',
                      'Other authorized work: other3datasets60defense native adapters/complete live preflights, original27Battention preflight/expansion, and separate source-bound jointreadiness diagnosis. Original20candidate review coverage is complete; uncertain subclaims stay uncertain.')
prompt=prompt.replace('Keep overall monitorACTIVE for outstanding semantic audit/60native configurations/original27Battention,',
                      'Keep overall monitorACTIVE for outstanding60native configurations/original27Battention/jointreadiness diagnosis,')
prompt=prompt.replace('Lasthealthheartbeat-evidence/1793104369217431100 servicealive andsiteHTTP200.',
                      'Lasthealthheartbeat-evidence/1793111971146570900 verifies serviceUID1033/fullcommand/heldservice.lock/recentrequestresponseandlogSHA/siteHTTP200;4090no matching oldworkers. Read-only, no resourceallocation.')
payload={'mode':'update','id':auto['id'],'kind':auto['kind'],'name':auto['name'],
         'prompt':prompt,'rrule':auto['rrule'],'status':auto['status'],
         'targetThreadId':auto['target_thread_id']}
if 'notification_policy'in auto:payload['notificationPolicy']=auto['notification_policy']
save(BASE/'automation-update-semantic542-20261027.json',payload)
save(out/'finalization-artifacts.json',{
 'report':str(report_path),'report_sha256':sha(report_path.read_bytes()),
 'review_sha256':ptr['review_sha256'],
 'files':{str(p):sha(p.read_bytes())for p in [report_path,BASE/'README.md',BASE/'REPAIR_HANDOFF.md',ATT/'HANDOFF.md',BASE/'automation-update-semantic542-20261027.json',out/'supplementary-statistics.json']},
 'backup_files':{p.name:sha(p.read_bytes())for p in backup.iterdir()},
 'automation_update_still_pending':True})
print(json.dumps({'report':str(report_path),'review_sha256':ptr['review_sha256'],'supplement':supplement,'automation_payload':str(BASE/'automation-update-semantic542-20261027.json')}))
