"""Preserve previous handoffs before recording a meaningful new development phase."""
import hashlib,json,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;P=BASE/'price-history-repair-development'
sha=lambda b:hashlib.sha256(b).hexdigest();read=lambda p:json.loads(p.read_bytes())
launch=read(P/'launch-current.json');done=(P/'completed-current.json').exists()
head=f'''# 最新2026-10-29：价格历史绑定v4.0.4源绑定诊断{'已终局，先读completed-current.json'if done else'运行中，NEVER重复launch'}

先读price-history-repair-development/current.json、launch-current.json、inspection-current.json{'及completed-current.json'if done else''}。root {launch['root']}；UID1015完整命令/6继承任务锁已核实。NEVER再launch_price_history_repair.py；完成控制不花剩余cap重试。8选择性人工/已知失败在新条件下的源绑定控制，最多28judge、0真实actor/GUI/score/付费API，原4096/1formatretry不变。PRIVATE预期未上传，251项完整CPU套件待GUI准备再次绑定；诊断launch已跑245项。不把CPU/静态准备当真实语义成功。

新Controller：原strictvalidator后暂扣“承认升序和较便宜前缀覆盖、却以同价未看完说可能更便宜”的内部矛盾理由，用原1formatretry重核；不改verdict/不认证实际覆盖/最低价。新增非WAIT历史价格路由，原始已交付图candidate/history-blind读取每行对象—邻近价格，冻结SHA后text-only关系检查候选，原actor/main完整历史不删。不是把已有current-only/STOP projection改名，新增对象价格粒度及非STOP关系检查。读者仍可错/细图仍未决，额外调用及误拦耗原140judge预算；无隐藏答案/动作覆盖/强制STOP。

前一v4.0.3b已paused_at_decision_boundary，10动作14actor47judge=61EOS、0官方评分，不是完整试验或official0。focus-conflict-fullgui-development/paused-finalization-current.json与报告权威；14候选全覆盖，316价格对象错绑接受BACK实际执行，73蓝框否定被拦、337UP/DOWN被拦。54文件terminal234068be3daca94ea5e5a88ff2b7a092878bead60d16c5622a43c8bd8fc1d452，service666f8b071839a40deea83a271c4bbe488905c747fa4b62880edeeb67b3a95541。旧root/launch绝不恢复，曾发生错误不消除。下一版完整GUI必须先完成新诊断独立图/source审查/actualservice全绑定、原预算/同一live环境回采准备及新一次性active。

用户“继续修复，直到能防御成功为止”迭代授权有效，不重复无谓确认。原1280x720/fullhistory/BF16/SDPA/2048actor4096judge/50steps70actor140judge/2recapture2regen1format/native评分保留。3090UID1033原5GPU锁服务不动，GPU5/6/7/外资源不碰。旧注意力终局及旧机制/UI队列不重启。其余授权未全完，monitor ACTIVE。未决不是无Mirage，已知单任务开发不构成通用效力。

--- 以下为前序交接 ---

'''
out=P/('handoff-preservation-'+str(time.time_ns()));out.mkdir();rows=[]
for i,p in enumerate([BASE/'README.md',BASE/'REPAIR_HANDOFF.md',BASE.parent/'crossmodel-injection-attention-20261025/HANDOFF.md']):
    raw=p.read_bytes();backup=out/(str(i)+'-'+p.name);backup.write_bytes(raw);p.write_text(head+raw.decode('utf-8-sig'),encoding='utf-8');rows.append({'path':str(p),'backup':str(backup),'before_sha256':sha(raw),'after_sha256':sha(p.read_bytes())})
(out/'receipt.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'handoff-current.json').write_text(json.dumps({'directory':str(out),'receipt_sha256':sha((out/'receipt.json').read_bytes()),'monitor':'ACTIVE'},indent=2))
print(json.dumps({'directory':str(out),'monitor':'ACTIVE'}))
