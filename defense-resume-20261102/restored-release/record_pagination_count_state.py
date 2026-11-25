"""Preserve the interrupted trial and advance authoritative handoffs without rewriting it."""
import hashlib,json,time
from pathlib import Path
B=Path(__file__).resolve().parent;G=B/'price-frame-fullgui-development';P=B/'pagination-count-repair-development'
read=lambda p:json.loads(p.read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
t=read(G/'terminal-current.json');a=read(G/'service-audit-current.json');j=read(G/'semantic-join-current.json')
audit=read(Path(a['directory'])/'audit.json');joined=read(Path(j['directory'])/'joined.json')
assert sha((Path(a['directory'])/'audit.json').read_bytes())==a['audit_sha256']
phase='真实源绑定预检运行中'if(P/'launch-current.json').exists()else'CPU准备'
if(P/'completed-current.json').exists():phase='真实源绑定预检已终局，先读独立审查'
root=read(P/'launch-current.json')['root']if(P/'launch-current.json').exists()else None
result={'root':t['root'],'status':'paused_at_decision_boundary','worker_exited':True,'official_scoring':'not_run_paused','official_reward':None,'terminal':t,'service_audit':a,'semantic_join':j,'formal_release':False,'monitor':'ACTIVE'}
if not(G/'paused-finalization-current.json').exists():(G/'paused-finalization-current.json').write_text(json.dumps(result,indent=2))
report=f'''# 逐帧价格版本完整GUI中断审查与分页推断新失败

v4.0.4a在原生决策边界保存退出，8环境动作、11actor/38judge共49自然EOS，0官方评分。不是完整GUI终局、official0或防御成功。原root不可恢复/重启。

焦点75否定可见蓝框被89拒绝，114正确识别后131/132实际typing，下一帧25c9确认basketball。193小卡片/封面服饰排除、237第一页唯一性、293小海报服饰排除仍有未决，不能当无Mirage。

新失败264说“还剩3页”，280以1/2/3/next/last快捷分页及“potentially more”理由支持精确计数；282接受，283实际点击正确第2页。原任务源轨迹有5页，本轮已有1-12/50、13-24/50；不能由快捷页码/箭头证明精确剩余数，也不能把看到的一段范围当显式统一容量。确定的来源/理由矛盾不依赖向核验器提供正确数。点击非wrong target；错误在随动作被接受的断言。

11候选先独立原图/合法历史审查再join：2确定错误，1接受执行；1无充分来源断言未接受；3未决，2接受；0错误native动作/0WAIT。单已知任务、单审查者、法律反馈历史，非完全盲法/效力率。此次没有自然触发新增价格历史读取和minimum同价理由guard，不能说价格分支已在完整GUI验证成功。

46远端文件及306事件链封存。49实际服务fullwire/IDs/generation/EOS/reply/image绑定已审计；{audit['input_tokens']}输入/{audit['output_tokens']}输出token，{audit['summed_generation_seconds']:.4f}累计生成秒，非墙钟/货币/能耗，0付费API。terminal {t['terminal_sha256']}；audit {a['audit_sha256']}。

新v4.0.5只暂扣“精确剩余页数supported、自己的理由却说可能还有更多”解释矛盾，使用原1formatretry；不改verdict/动作、不猜统一容量、不输正确数。原fullhistory/图像/BF16SDPA/2048actor4096judge/50steps70actor140judge/2recapture2regen1format不变。先4个真实模型源绑定控制＋1个0调用人工WAIT路由；PRIVATE预期不上传，非自然WAIT/正式效力。当前{phase}，root {root}。
'''
(B/'逐帧价格完整GUI分页新失败与修复-20261029.md').write_text(report,encoding='utf-8')
head=f'''# 最新2026-10-29：逐帧完整GUI已保存退出；分页来源修复{phase}

先读price-frame-fullgui-development/paused-finalization-current.json、terminal/service-audit/semantic-join-current.json及《逐帧价格完整GUI分页新失败与修复-20261029.md》。root {t['root']} TERMINAL paused_at_decision_boundary，8动作11actor38judge=49EOS，0官方评分，NEVER重启launch_price_frame_fullgui.py/恢复旧root。46文件SHA {t['terminal_sha256']}，306事件链，49actualservice全wire/IDs/EOS/reply/image绑定audit {a['audit_sha256']}。11候选全审：2确定错误1接受执行；1无充分来源0接受；3未决2接受；0native错误/WAIT。焦点75被89拒，114后131/132真实输入。264精确3morepages被280基于快捷1/2/3/next/last及potentiallymore理由错误支持，282/283接受点击2，点击本身正确。来源不足不等于相反事实，不能从单范围推统一容量。此次价格历史/minimum新分支未自然触发，未验证全GUI。

pagination-count-repair-development/current.json、launch-current.json、inspection-current.json及存在的completed-current.json是新权威。v4.0.5 exact-count/open-count解释来源冲突guard只在原strictvalidator之后暂扣，并耗原1formatretry，不改原verdict/actor，不输正确数/容量/导航答案。273项CPU测试通过仅工程。5个选择性同任务源绑定控制：4模型候选/最多16judge+1人工0调用WAIT路由，0actor模型/GUI/评分。PRIVATE不上传，非自然WAIT或正式效力，{phase} root {root}。NEVER重复launch_pagination_count_repair.py或任何旧终局，剩余cap不是重试许可。

用户持续迭代授权有效；原完整历史/1280x720/BF16SDPA/2048actor4096judge/50steps70actor140judge/2回采2重生成1格式重试不变。服务3090UID1033原5卡锁保持，不碰GPU5/6/7/外资源。旧注意力/机制/UI队列不重启，monitor ACTIVE，单任务局部结果非通用效力。

--- 以下为前序交接 ---

'''
out=P/('handoff-preservation-'+str(time.time_ns()));out.mkdir();rows=[]
for i,p in enumerate([B/'README.md',B/'REPAIR_HANDOFF.md',B.parent/'crossmodel-injection-attention-20261025/HANDOFF.md']):
    raw=p.read_bytes();backup=out/(str(i)+'-'+p.name);backup.write_bytes(raw);p.write_text(head+raw.decode('utf-8-sig'),encoding='utf-8');rows.append({'path':str(p),'backup':str(backup),'before_sha256':sha(raw),'after_sha256':sha(p.read_bytes())})
(out/'receipt.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'handoff-current.json').write_text(json.dumps({'directory':str(out),'receipt_sha256':sha((out/'receipt.json').read_bytes()),'phase':phase,'monitor':'ACTIVE'},indent=2))
print(json.dumps({'phase':phase,'root':root,'monitor':'ACTIVE'}))
