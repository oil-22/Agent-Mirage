# 从历史轨迹重建 v2

成品直接读取上一层的 JSONL。只有要重做提取和定标才需要这里的脚本。它们按原工作区布局使用同级 v1 的提取工具、冻结的 Jev prompt 和原生 Encoder 源码、历史归档与索引，以及 OpenCV、NumPy、Pillow、RapidOCR。已有轨迹只读，本次未更改 v1、远端实验或模型。

在本目录下按次序执行：

1. `python collect_natural.py`：只读历史 4090 上 Classifieds 实验的 clean 目录。从原始 Playwright trace 核对动作顺序、原语和参数；从模型收图记录核对图片摘要。仅保存必要的原图和事实索引到原工作区的 `.tmp/jev-trajectory-v2-review/natural/`。不同类型的 probe 要与该步正常帧共享前缀图像及最后一个图像槽位；跳过已记录漂移的检查点和静默丢图。
2. `python qualify.py`：对自然轨迹和原归档中实际交付的异常帧定标。页面变化、滚动、OCR 和焦点各有自己的可见证据。未证实的候选不因一条成功执行回执就成为正例。
3. `python assemble.py`：保留 v1，优先实收输入；在训练来源中寻找配对反例。按父正例、候选来源、实际动作和解码后图像做隔离检查及去重。
4. `python review_sample.py`：生成固定抽样的看图材料到原工作区临时目录。标记点击坐标和放大的局部只供审核。已有版本的看图记录在上层 spot-check.json；若改变数据或抽样，需重新审核再发布。
5. `python finalize.py views`、`python finalize.py report`、`python finalize.py zip`：生成平衡子集、复核原生编码与来源，最后核验 ZIP 的 CRC、成员和逐文件 SHA-256。

归档可用范围可能随历史存储变动；该版的自然轨迹索引摘要、历史别名索引摘要和构建数字固定在 validation.json。日常复核请用上层的 `verify.py`，不需要 SSH、OCR 或原工程的临时文件。
