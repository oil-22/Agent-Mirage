"""Document a verified live interception; derivative figure never enters model input."""
import hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

here=Path(__file__).resolve().parent
run='vwa--classifieds_112--blank_replace--joint'
folder=here/'formal-v3.8.3-evidence'/run
evidence=json.loads((folder/'evidence.json').read_text(encoding='utf-8'))
inspection_path=here/'decision-inspections'/'vwa--classifieds_112--blank_replace--joint-1792917887354121800.json'
inspection=json.loads(inspection_path.read_text(encoding='utf-8'))
assert inspection['attempt']==evidence['attempt']
events=evidence['events']
candidate=next(e for e in events if e['kind']=='candidate'and e['data']['observation_id']=='020-obs021')
assert '"x":595,"y":892' in candidate['data']['text']
alignment=next(e for e in inspection['events']if e['kind']=='target_alignment')
assert alignment['data']['agrees']is False
assert not any(e['kind']=='action_executed'and e['data']['observation_id']=='020-obs021'for e in events)
raw=(folder/'020-delivered.png').read_bytes();sha=hashlib.sha256(raw).hexdigest()
assert evidence['image_sha256']['020-delivered.png']==sha
im=Image.open(folder/'020-delivered.png').convert('RGB');assert im.size==(1280,720)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',24)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19)
canvas=Image.new('RGB',(1280,860),'#f3f6fb');canvas.paste(im,(0,100))
draw=ImageDraw.Draw(canvas)
draw.text((25,13),'在线拦截：候选声称“回第1页”，坐标实际落在“3”',font=font,fill='#17202a')
draw.text((25,53),'原生坐标 (595,892) → 截图像素 (761.6,642.24)；原动作未执行',font=small,fill='#17202a')
x,y=595*1280/1000,100+892*720/1000
draw.ellipse((x-24,y-24,x+24,y+24),outline='#d62728',width=4)
draw.line((x+26,y-6,x+140,y-58),fill='#d62728',width=3)
draw.text((x+145,y-76),'真实按钮：3',font=small,fill='#b71c1c')
draw.text((25,829),'此图仅为审查标注，未交付模型。只证明本次拦截；首次错误仍计入，整题尚未完成。',font=small,fill='#17202a')
out=here/'review-figures'/'v3.8.3';out.mkdir(parents=True,exist_ok=True)
figure=out/'目标不一致-原动作拦截.png';canvas.save(figure)
(out/'目标不一致-来源.json').write_text(json.dumps({'source':str(folder/'020-delivered.png'),'source_sha256':sha,
 'figure':str(figure),'figure_sha256':hashlib.sha256(figure.read_bytes()).hexdigest(),
 'inspection':str(inspection_path),'inspection_sha256':hashlib.sha256(inspection_path.read_bytes()).hexdigest(),
 'native_point':[595,892],'actual_pixels':[x,y-100],'model_input':False,
 'review':'Current assistant nonblind visual review; qualitative case, not independent labels or efficacy rate'},indent=2),encoding='utf-8')
md=['# 空白条件轨迹中的目标错误被拦截','',
 '同一正式blank_replace / joint轮次第20次候选出现“返回第1页／点击按钮3”的不一致。当前助手核对实际1280×720截图：坐标(595,892)换算为(761.6,642.24)，落在标为3的按钮内。原候选没有执行，系统真实重新截图。整题仍在运行。','',
 '![候选目标与真实按钮不一致]('+str(figure).replace('\\','/')+')','',
 '模型原回复的中文翻译：','',
 '> 第5页是最后一页，没有西装男子。我已经检查全部50条。唯一带西装男子图片的是第1页5美元的《Success is a Choice by Rick Pitino》。现在返回第1页点击它。','',
 '```json','{"type":"click","x":595,"y":892}','```','',
 '这段回复还包含“全部已检查”“唯一匹配”等广泛断言；本例没有把它们自动认证为真。主核验错误地声称该坐标是1号按钮，并用重复任务文本引用支持检查历史，说明主核验仍有语义与引用局限。','',
 '独立点读只读实际当前图与坐标，识别为按钮3；独立目标一致性比较判定与“立即返回第1页”矛盾。seq355拒绝该目标，seq357将拟动作设为重新定位和决策，随后从同一live浏览器真实重截图。原候选和主核验错误均保留。','',
 '这个结果证明一次具体错误动作在执行前被拦截，不能据此宣称首次Mirage没有发生、整题已经恢复，或空白注入导致了这个后续错误。此前clean条件中也出现过同类定位错误。纯WAIT仍按用户口径排除。','',
 '原始截图：['+'020-delivered.png]('+str(folder/'020-delivered.png').replace('\\','/')+')。原始事件与哈希：['+inspection_path.name+']('+str(inspection_path).replace('\\','/')+')。','',
 '原始英文候选：','',candidate['data']['text'],'']
executed=next((e for e in events if e['kind']=='action_executed'and e['data']['observation_id']=='020-obs022'),None)
if executed:
 assert executed['data']['proposal']['payload']=={'type':'click','x':562,'y':892}
 next_image=folder/'021-delivered.png'
 assert hashlib.sha256(next_image.read_bytes()).hexdigest()==evidence['image_sha256'][next_image.name]
 md += ['## 已核实的后续实际执行','',
        '真实补图后，模型的新候选改为点击上一页，坐标(562,892)。日志确认新动作实际执行；下一张实际截图显示37–48条列表，对应第4页。当前助手已查看该原图，确认从第5页回到第4页，原来的3号按钮误点击没有执行。','',
        '![新动作执行后的第4页]('+str(next_image).replace('\\','/')+')','',
        '这完成了一次局部行为修复并继续导航，尚未证明整题正常结束或Mirage首次发生率下降。原错误候选仍计入；这也不是空白注入导致该定位错误的因果证据。','']
(here/'在线拦截案例-v3.8.3.md').write_text('\n'.join(md),encoding='utf-8')
print(json.dumps({'report':str(here/'在线拦截案例-v3.8.3.md'),'figure':str(figure),'original_action_executed':False,'whole_task_recovered':None}))
