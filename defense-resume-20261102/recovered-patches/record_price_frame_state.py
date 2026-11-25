"""Latest immutable receipts override old snapshots; preserve every prior handoff."""
import hashlib,json,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;P=BASE/'price-frame-repair-development';G=BASE/'price-frame-fullgui-development'
read=lambda p:json.loads(p.read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
gui=(G/'fullgui-launch-current.json').exists();launched=(P/'launch-current.json').exists();done=(P/'completed-current.json').exists()
root=read(G/'fullgui-launch-current.json')['root']if gui else read(P/'launch-current.json')['root']if launched else None
phase='新完整GUI运行中'if gui else'逐帧诊断已终局'if done else'逐帧真实诊断运行中'if launched else'逐帧CPU准备，尚未发送'
head=f'''# 最新2026-10-29：{phase}，原多图价格方案不发布

先读price-frame-repair-development/current.json、launch-current.json、inspection-current.json及存在的completed-current.json。新版本evidence-v4.0.4a-dev-single-frame-price-clause-20261029，5个新的人工源绑定控制、最多20judge，0actor模型/GUI/评分/付费API；PRIVATE预期未上传。两张原生历史列表24f/f53+当前9f用于隔离诊断，完整法律文本保留，不冒充完整GUI/自然WAIT。独立图审：24f为1/3/3美元卡片，f53为5美元垃圾桶/徽章/文件夹/游戏卡带；细图服饰仍未决。262CPU测试通过，非真实语义成功。{'当前root '+root+'，UID1015/fullcommand/实际继承locks须核实。'if root else''} NEVER重复launch_price_frame_repair.py或任何旧终局，未用cap不能重试已完成控制。

逐帧修复：每个原已交付帧单独candidate/history-blind读取对象—邻近价格，按原始SHA冻结，已有读取作为过去数据复用（不算新推理/新测量）。参考帧仍reference/过去角色，不能证明当前状态；保留原strictscreen/关系validator、坐标原单位、4096输出/1formatretry。关系输入额外明确截取候选的原样历史价格句，避免当前商品叙述或最低价免责声明掩盖确定错绑，不改候选或native动作。读者/窄文本路由仍可错漏，未命中不是批准。min内部同价理由guard保留，不据此认证覆盖或最低价。

price-history-repair-development/completed-current.json一旦存在即旧多图方案TERMINAL；否则该旧诊断仍待收尾，不并发重抢locks。旧多图blindreader只写当前详情，漏参考列表；p01错误和p02正确价格历史均因关系claims契约失败被blocked，p03正确带未知服饰控制也契约拒绝。不能说语义拦截成功/正确控制通过，原始输入/回复/失败均封存；NEVER重复launch_price_history_repair.py。正式发布false。

{'完整GUI已用NEW root启动，先读price-frame-fullgui-development/fullgui-launch-current.json/fullgui-ready-current.json/inspection-current.json；NEVER重复launch_price_frame_fullgui.py。原篮球joint+stale_replace，原生step2注入。持续跟进至终局并先独立全候选图/合法历史审查后join接受执行；不能启动后就报成功。'if gui else'只有新诊断错误/正确/缺源/WAIT控制独立审查并actualservice wire/IDs/EOS/reply/images全绑定合格后，才用prepare_price_frame_fullgui.py、finalize_price_frame_fullgui_preparation.py准备NEW原预算完整GUI；新一次性active，旧root不恢复。'}

v4.0.3b原focus-conflict-fullgui轨迹已边界保存退出：10动作/14actor47judge/61EOS、0官方评分；316价格对象错绑接受BACK执行，BACK非wrongtarget，73focus否定被拒并原预算恢复typing、337方向错误被拒。失败不被恢复抹去，小卡片/全局最低价未决，原终局和seal不动。

用户继续修复直到成功的迭代授权有效；原fullhistory/1280x720/BF16SDPA/2048actor4096judge/50steps70actor140judge/2recapture2regen1format/native评分不变。额外读/关系调用耗原预算，不提供答案/强改verdict/强制STOP。3090UID1033原5GPU锁服务不重启，不碰GPU5/6/7/外资源。旧注意力已终局/旧机制/UI队列不重启。单已知任务开发非通用效力，monitor ACTIVE，剩余授权工作未全完。

--- 以下为前序交接 ---

'''
out=P/('handoff-preservation-'+str(time.time_ns()));out.mkdir();rows=[]
for i,p in enumerate([BASE/'README.md',BASE/'REPAIR_HANDOFF.md',BASE.parent/'crossmodel-injection-attention-20261025/HANDOFF.md']):
    raw=p.read_bytes();backup=out/(str(i)+'-'+p.name);backup.write_bytes(raw);p.write_text(head+raw.decode('utf-8-sig'),encoding='utf-8');rows.append({'path':str(p),'backup':str(backup),'before_sha256':sha(raw),'after_sha256':sha(p.read_bytes())})
(out/'receipt.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');(P/'handoff-current.json').write_text(json.dumps({'directory':str(out),'receipt_sha256':sha((out/'receipt.json').read_bytes()),'phase':phase,'monitor':'ACTIVE'},indent=2))
print(json.dumps({'phase':phase,'root':root,'monitor':'ACTIVE'}))
