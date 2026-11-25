# Jev 双截图判定集 v3

用两张有序截图和一次实际分发的动作，判断候选图是否足以看出结果。正式文件为 [train.jsonl](train.jsonl) 和 [val.jsonl](val.jsonl)，共 **3,630 条独立输入**。两个文件各自满足 YES:NO = 1:1；在每个标签内，三个场景各占 1/3。v3 替代 v2.1 用于本轮微调，不要拼接两个版本。

| 划分 | 白屏 YES / NO | 旧帧 YES / NO | 仅按钮 YES / NO | YES 合计 | NO 合计 | 总数 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 训练 | 552 / 552 | 552 / 552 | 552 / 552 | 1656 | 1656 | 3312 |
| 验证 | 53 / 53 | 53 / 53 | 53 / 53 | 159 | 159 | 318 |

**场景与标签分别记录。** 白屏组的正常对照是该组的 YES；全白候选不标 YES。旧帧与仅按钮组也以动作的可见结果判定。仅按钮的实收图有时足以看出结果：例如 [val.jsonl 第 164 行 的前图](images/69ee60c8324d2f899ddd3d7e4788be56fca5347425a39497903490069d735ebb.png) 是启动器，[第二张图](images/c376ce0da4c6760763992e5a3e085313d2ee6d95f45c5b91f8680ec08dc0ed2a.png) 仍能看出滚动打开了快捷设置，故为 YES。训练中有 3 条、验证中有 6 条这样“实际收到仅按钮图仍判 YES”的样本。

| 负例的来源 | 白屏：实收 / 构造 | 旧帧：实收 / 构造 | 仅按钮：实收 / 构造 |
| --- | ---: | ---: | ---: |
| 训练 | 117 / 435 | 110 / 442 | 21 / 531 |
| 验证 | 42 / 11 | 11 / 42 | 15 / 38 |

负例优先采用历史实验实际送入模型的截图。其余负例是离线对照：保留同一轨迹的真实前图和动作，替换第二张图；每条都能在同一划分找到前图和 prompt 完全相同的实收 YES。白屏使用同分辨率的历史全白 PNG；旧帧使用动作前原图或日志可定位的更早一帧；仅按钮使用实验记录的整组控件矩形，逐像素核实保留区在前图和正常结果图中相同，区外全白，且保留区不包含点击目标。全白不计入仅按钮。没有缺图、静默丢图或用文字占位的输入。

每条 YES 都是归档中的实收输入。训练有 1,491 组、验证有 91 组正负对共享同一前图和动作，两条都在正式数据内。其余正常对照优先附同一前图和动作的可复核替换图，只用于审计，不另计行数。还有训练 5 条、验证 9 条凭原实验场景及独立正常交付记录归组，没有声称有同动作的反例。详见 [manifest.jsonl](manifest.jsonl) 的 task、role、origin、contrast_sample_id 字段；[audit.jsonl](audit.jsonl) 与 [source-receipts.jsonl](source-receipts.jsonl) 按 ID 查证据。

三个来自 train.jsonl 的对照例子（同一行内前图和 prompt 均相同）：

| 场景 | 动作前 | 能判定动作结果 | 不能判定动作结果 |
| --- | --- | --- | --- |
| 白屏注入 | [click 的前图](images/450320dd48abe29cf5426ddf8fcef9d04491700095ab12a6fe32ba8b5e88817f.png) | [YES，第 2174 行](images/2baaaae72fb314ed6dd3dda165f9ac40aaac46c17dba50f5f39b32e5b46a5211.png) | [NO，第 86 行](images/e52ae68d052db9f6f16fb6b5d2498e83b09545c9daaf4579e6c406a5713ad11f.png) |
| 旧帧替换 | [click 的前图](images/3e372dc35e7d3674816d4b5eccecb1a5393f8713eb99963969fb1795b93f37ab.png) | [YES，第 194 行](images/7985dfed99be87d4b7f28a9927ec055b8572fe6c7123270be57a36871f292a1b.png) | [NO，第 11 行](images/9746a25cba90bf2fb13bea70e34994239de7748f1fe935b8a61c1e5e8f9cb569.png) |
| 仅按钮 | [click 的前图](images/ec5aa021ef6093dcca70223e99de9bcc1180400c8b008a3a67ed693dc7db4afc.png) | [YES，第 839 行](images/e922dfe522dcb605627bcbb2e4cfaa46a78f123e0767888238a937ca593a4190.png) | [NO，第 58 行](images/57e82e16054e1a0eb26507a17092097323dbf25b69177847ad25bd9c23dde224.png) |

**读入。** 每行仅含 images = [前图, 候选图]、prompt、label；图片路径相对于 JSONL 所在目录。沿用 [protocol.json](protocol.json) 中的原生英文问题、全局 system prompt 和 A→YES / B→NO 映射。不要把 task、role、审核理由或第三张参考图喂给模型。训练判定头和 LoRA 都可以读这一划分。项目原生判定头已有入口：在原工作区运行 `python native_head_v3.py check manifest.jsonl`；单独解压时，JEV_STARTER_DIR 可指向原项目的 starter 目录。

**评估。** 验证集的 NO 从 v2.1 的 76 条增加到 159 条；本版重新取样，并非旧验证集追加。建议按场景分别报告 NO→YES 误放与 YES→NO 误拦，并将实收与离线构造的 NO 分开报告。仅按钮 NO 使用的不同候选画面是训练 10 种、验证 13 种；它们与不同的前图或动作组成独立输入，不能当成同等数量的独立按钮样式或线上发生率。旧版独立测试集未重采样，仍在 v2.1/test.jsonl，本包不将其计入三类平衡规模。

**核验。** 解压后运行 `python verify.py`（Python 3.11+、Pillow）。[stats.json](stats.json) 来自于重新读取导出文件：逐条核验数据比例、原生 prompt、PNG 内容、来源、对照关系和跨集合隔离；手机去除系统栏、OSWorld 去除顶部时钟栏后也检查了相同画面。已评定的旧数据沿用原标签；新增部分由像素/日志规则或助手看图复核，没有把 Jev 的预测当真值。这不是双人盲标集。
