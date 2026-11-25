"""Write a data card and package only the verified inventory. The sibling archive is portable."""
from pathlib import Path
from collections import Counter
import hashlib,json,zipfile

P=Path(__file__).resolve().parents[1]
def read(name):return json.loads((P/name).read_bytes())
def lines(name):return [json.loads(s) for s in (P/name).read_bytes().splitlines()]
def digest(f):
    with f.open('rb') as src:return hashlib.file_digest(src,'sha256').hexdigest()
def main():
    st=read('stats.json');m=lines('manifest.jsonl');by={r['sample_id']:r for r in m}
    for n,h in st['sha256'].items():
        if digest(P/n)!=h:raise ValueError('Rerun verify.py --write-stats first: '+n)
    tasks={'blank_replace':'白屏注入','stale_replace':'旧帧替换','buttons_only':'仅按钮'}
    counts=st['splits'];orig=st['by_task_and_origin']
    tbl=['| 划分 | 白屏 YES / NO | 旧帧 YES / NO | 仅按钮 YES / NO | YES 合计 | NO 合计 | 总数 |',
         '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    nt=['| 负例的来源 | 白屏：实收 / 构造 | 旧帧：实收 / 构造 | 仅按钮：实收 / 构造 |',
        '| --- | ---: | ---: | ---: |']
    for s,title in [('train','训练'),('val','验证')]:
        v=counts[s];cells=st['tasks'][s]
        tbl.append('| '+title+' | '+' | '.join(f"{cells[t]['YES']} / {cells[t]['NO']}" for t in tasks)+f" | {v['YES']} | {v['NO']} | {v['total']} |")
        nt.append('| '+title+' | '+' | '.join(f"{orig[s][t]['NO'].get('observed_injection',0)} / {orig[s][t]['NO'].get('constructed_injection',0)}" for t in tasks)+' |')
    def example(row):return f"{row['split']}.jsonl 第 {row['line']} 行"
    butyes=next(r for r in m if r['evidence_kind']=='archived_android_buttons_only' and r['label']=='YES')
    ex=[]
    for g in tasks:
        a=next(r for r in m if r['split']=='train' and r['task']==g and r['label']=='NO' and r['contrast_sample_id'] and
               (r['evidence_kind']=='documented_earlier' if g=='stale_replace' else r['role']=='observed_injection'))
        b=by[a['contrast_sample_id']]
        ex.append(f"| {tasks[g]} | [{a['action']['type']} 的前图]({a['before_png']}) | [YES，第 {b['line']} 行]({b['candidate_png']}) | [NO，第 {a['line']} 行]({a['candidate_png']}) |")
    c0,c1=st['unique_buttons_only_NO_candidates']['train'],st['unique_buttons_only_NO_candidates']['val']
    d0,d1=st['roles']['train'].get('scenario_control',0),st['roles']['val'].get('scenario_control',0)
    n0,n1=st['matched_pairs']['train'],st['matched_pairs']['val']
    doc=f"""# Jev 双截图判定集 v3

用两张有序截图和一次实际分发的动作，判断候选图是否足以看出结果。正式文件为 [train.jsonl](train.jsonl) 和 [val.jsonl](val.jsonl)，共 **{st['total_rows']:,} 条独立输入**。两个文件各自满足 YES:NO = 1:1；在每个标签内，三个场景各占 1/3。v3 替代 v2.1 用于本轮微调，不要拼接两个版本。

{chr(10).join(tbl)}

**场景与标签分别记录。** 白屏组的正常对照是该组的 YES；全白候选不标 YES。旧帧与仅按钮组也以动作的可见结果判定。仅按钮的实收图有时足以看出结果：例如 [{example(butyes)} 的前图]({butyes['before_png']}) 是启动器，[第二张图]({butyes['candidate_png']}) 仍能看出滚动打开了快捷设置，故为 YES。训练中有 {orig['train']['buttons_only']['YES'].get('observed_injection',0)} 条、验证中有 {orig['val']['buttons_only']['YES'].get('observed_injection',0)} 条这样“实际收到仅按钮图仍判 YES”的样本。

{chr(10).join(nt)}

负例优先采用历史实验实际送入模型的截图。其余负例是离线对照：保留同一轨迹的真实前图和动作，替换第二张图；每条都能在同一划分找到前图和 prompt 完全相同的实收 YES。白屏使用同分辨率的历史全白 PNG；旧帧使用动作前原图或日志可定位的更早一帧；仅按钮使用实验记录的整组控件矩形，逐像素核实保留区在前图和正常结果图中相同，区外全白，且保留区不包含点击目标。全白不计入仅按钮。没有缺图、静默丢图或用文字占位的输入。

每条 YES 都是归档中的实收输入。训练有 {n0:,} 组、验证有 {n1:,} 组正负对共享同一前图和动作，两条都在正式数据内。其余正常对照优先附同一前图和动作的可复核替换图，只用于审计，不另计行数。还有训练 {d0} 条、验证 {d1} 条凭原实验场景及独立正常交付记录归组，没有声称有同动作的反例。详见 [manifest.jsonl](manifest.jsonl) 的 task、role、origin、contrast_sample_id 字段；[audit.jsonl](audit.jsonl) 与 [source-receipts.jsonl](source-receipts.jsonl) 按 ID 查证据。

三个来自 train.jsonl 的对照例子（同一行内前图和 prompt 均相同）：

| 场景 | 动作前 | 能判定动作结果 | 不能判定动作结果 |
| --- | --- | --- | --- |
{chr(10).join(ex)}

**读入。** 每行仅含 images = [前图, 候选图]、prompt、label；图片路径相对于 JSONL 所在目录。沿用 [protocol.json](protocol.json) 中的原生英文问题、全局 system prompt 和 A→YES / B→NO 映射。不要把 task、role、审核理由或第三张参考图喂给模型。训练判定头和 LoRA 都可以读这一划分。项目原生判定头已有入口：在原工作区运行 {chr(96)}python native_head_v3.py check manifest.jsonl{chr(96)}；单独解压时，JEV_STARTER_DIR 可指向原项目的 starter 目录。

**评估。** 验证集的 NO 从 v2.1 的 76 条增加到 {counts['val']['NO']} 条；本版重新取样，并非旧验证集追加。建议按场景分别报告 NO→YES 误放与 YES→NO 误拦，并将实收与离线构造的 NO 分开报告。仅按钮 NO 使用的不同候选画面是训练 {c0} 种、验证 {c1} 种；它们与不同的前图或动作组成独立输入，不能当成同等数量的独立按钮样式或线上发生率。旧版独立测试集未重采样，仍在 v2.1/test.jsonl，本包不将其计入三类平衡规模。

**核验。** 解压后运行 {chr(96)}python verify.py{chr(96)}（Python 3.11+、Pillow）。[stats.json](stats.json) 来自于重新读取导出文件：逐条核验数据比例、原生 prompt、PNG 内容、来源、对照关系和跨集合隔离；手机去除系统栏、OSWorld 去除顶部时钟栏后也检查了相同画面。已评定的旧数据沿用原标签；新增部分由像素/日志规则或助手看图复核，没有把 Jev 的预测当真值。这不是双人盲标集。
"""
    (P/'README.md').write_text(doc,encoding='utf-8')
    images=[P/'images'/(h+'.png') for h in read('image-index.json')]
    mainfiles=[P/n for n in ['train.jsonl','val.jsonl','manifest.jsonl','audit.jsonl','source-receipts.jsonl','image-index.json','mask-templates.json','protocol.json','split-guards.json','stats.json','README.md','verify.py','native_head_v3.py']]
    files=sorted([*mainfiles,*images,*(P/'build').glob('*.py')],key=lambda f:f.relative_to(P).as_posix())
    (P/'checksums.sha256').write_text(''.join(digest(f)+'  '+f.relative_to(P).as_posix()+'\n' for f in files),encoding='utf-8')
    files.append(P/'checksums.sha256');out=P.with_suffix('.zip');tmp=out.with_suffix('.zip.tmp')
    with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=5,allowZip64=True) as z:
        for f in files:
            z.write(f,str(P.name+'/'+f.relative_to(P).as_posix()),compress_type=zipfile.ZIP_STORED if f.suffix=='.png' else zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(tmp) as z:
        if len(z.namelist())!=len(files) or z.testzip() is not None:raise ValueError('Invalid release archive')
    tmp.replace(out)
    (P/'bundle.sha256').write_text(digest(out)+'  '+out.name+'\n',encoding='utf-8')
    print('Verified archive:',out,out.stat().st_size,'bytes;',len(files),'members.',flush=True)
if __name__=='__main__':main()
