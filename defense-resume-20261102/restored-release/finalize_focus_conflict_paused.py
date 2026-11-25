"""Document and preserve the interrupted failed development trajectory honestly."""
import hashlib,json,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;P=BASE/'focus-conflict-fullgui-development'
read=lambda p:json.loads(p.read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
assert not(P/'paused-finalization-current.json').exists()
t=read(P/'terminal-current.json');a=read(P/'service-audit-current.json');j=read(P/'semantic-join-current.json')
audit=read(Path(a['directory'])/'audit.json');joined=read(Path(j['directory'])/'joined.json')
assert sha((Path(a['directory'])/'audit.json').read_bytes())==a['audit_sha256']
assert joined['candidate_count']==14 and joined['accepted_definite_GUI_errors']==1
result={'root':t['root'],'status':'paused_at_decision_boundary','worker_exited':True,'official_scoring':'not_run_paused','official_reward':None,'terminal':t,'service_audit':a,'semantic_join':j,'formal_release':False,'monitor':'ACTIVE'}
report=f'''# 焦点修复完整GUI中断审查与价格历史新失败

v4.0.3b 在原生决策边界保存退出，10个环境动作，14次actor和47次judge，共61次自然EOS；未运行官方评分，无正常STOP。中断开发轨迹不能算完整试验、官方失败或防御成功，不能恢复旧root。

焦点子问题真实被拦截：蓝框上的否定焦点候选73被86/96拒绝，额外点击未执行；111正确识别后127/128在原预算内实际输入。已发生错误仍保留。

新失败：305核验一面承认升序及较便宜前缀已覆盖，一面以同价5美元未检查为由说还可能更便宜，内部理由矛盾；这不证明真正覆盖或最低价。候选316把实际5美元的垃圾桶、徽章、文件夹、游戏卡带说成1/3美元商品，324错误支持，326接受、327实际BACK。BACK本身为合法导航，错误在被接受并执行的历史子句。337的UP文字/DOWN原生方向矛盾被拦，356恢复UP。

14个候选独立图像/法律历史审查全部覆盖：2个确定GUI错误（1接受并执行）；2个无充分来源断言（均未接受）；5个仍有未决细节（4接受）；1个原生方向错误未接受；0纯WAIT。小卡片服饰/全局最低价仍未决，不能把这些当无Mirage。单审查者、同一已知任务、含法律反馈历史，非完全盲法或效力率。

61次真实服务请求、完整wire/inputIDs/generation/outputIDs/EOS/replies/原图及368事件链已核实。{audit['input_tokens']}输入/{audit['output_tokens']}输出token，{audit['summed_generation_seconds']:.4f}累计生成秒，非墙钟/货币/能耗；0付费API。54远端文件SHA封存（包括未下载的原始pkl/trace）。terminal {t['terminal_sha256']}；service audit {a['audit_sha256']}。

下一版本分开修复内部同价理由和价格—商品原图历史绑定。先做正负/WAIT源绑定预检，不提供正确动作/隐藏答案，不改原严格validator、原生模板、完整历史、图像、模型或预算。旧终局/旧队列/注意力终局不重启，monitor ACTIVE。
'''
(BASE/'焦点修复中断审查与价格历史失败-20261029.md').write_text(report,encoding='utf-8')
head=f'''# 最新2026-10-29：v4.0.3b已原生边界保存退出；新价格历史错误接受执行，继续隔离修复

先读focus-conflict-fullgui-development/paused-finalization-current.json、terminal-current.json、service-audit-current.json、semantic-join-current.json和《焦点修复中断审查与价格历史失败-20261029.md》。root {t['root']} 已退出，NEVER再次launch_focus_conflict_fullgui.py/恢复旧root。真实状态paused_at_decision_boundary，10环境动作14actor47judge=61自然EOS，0官方评分，不能伪装完整终局/official0/技术零。54文件terminal SHA {t['terminal_sha256']}；368事件链和61actualservice fullwire/IDs/EOS/reply/image全绑定，audit {a['audit_sha256']}。14候选独立标签封存后join，2确定错误1接受执行；2无充分来源断言0接受；5未决4接受；1native方向错误未接受；0WAIT。单已知任务非效力率。

焦点73已被86/96拒绝，111后127/128真实typing，旧局部结果不重复。新305同价比较理由内部矛盾；316把实际5美元trashcan/pins/binders/cartridges错绑1/3美元，324支持、326/327接受BACK执行。BACK非wrongtarget。337UP/DOWN矛盾被拦，356恢复UP。不能用后续恢复抹去316。小卡片服饰/全局最低价仍未决。

下一步新隔离版本修复minimum内部理由和非STOP价格—商品历史绑定；candidate/history-blind原图读取→冻结→关系核对，正负/WAIT源绑定预检先行。原strictvalidator/native模板/fullhistory/1280x720/BF16/2048actor4096judge/50steps70actor140judge/2recapture2regen1format不改，不强制STOP/动作、不输隐藏答案、不扩budget。原minimum_price_reason_scope.py14CPU测试仅原型，未真实验证/未发布。用户迭代授权仍有效，无需无谓重问。服务3090UID1033原5GPU锁保持，不碰GPU5/6/7/外资源；旧注意力终局/旧队列不重启。monitor ACTIVE，其余授权工作仍未完。

--- 以下为前序交接 ---

'''
out=P/('paused-handoff-preservation-'+str(time.time_ns()));out.mkdir();rows=[]
for i,p in enumerate([BASE/'README.md',BASE/'REPAIR_HANDOFF.md',BASE.parent/'crossmodel-injection-attention-20261025/HANDOFF.md']):
    raw=p.read_bytes();b=out/(str(i)+'-'+p.name);b.write_bytes(raw);p.write_text(head+raw.decode('utf-8-sig'),encoding='utf-8');rows.append({'path':str(p),'backup':str(b),'before_sha256':sha(raw),'after_sha256':sha(p.read_bytes())})
(out/'receipt.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
result['handoff_backup']=str(out);(P/'paused-finalization-current.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'status':result['status'],'calls':a['calls'],'monitor':'ACTIVE'}))
