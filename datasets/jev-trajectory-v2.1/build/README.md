# 构建与证据说明

成品只需要 Python 3.11+ 和 Pillow 即可离线核验。以下重建步骤另外依赖原项目的 Jev 提示构建器、编码器、旧版数据、AndroidWorld 历史归档缓存，以及 NumPy/OpenCV。单独解压的数据包没有完整原始实验日志。归档路径均为来源索引，不会作为动作重放。

1. 在原仓库运行 `python datasets/jev-trajectory-v2.1/build/validation_sources.py`，对齐同一轨迹连续两步的交付、原生动作和实际干预记录，必要时只读取回原始 PNG。未分发的动作、缺图、缺回执、不支持的手势不参与。
2. `validation_review.py` 和 `matched_controls.py` 用于生成供看图的候选、控件放大图和实际对照。没有把无标注、相同画面、极小像素变化或某种干预名称直接当作监督标签。去除了白屏配同一个桌面滚动、只有时钟或指针不同等近重复；有明确失败提示、滚动边界和可辨认结果的不作为补充 NO。
3. [review-decisions.jsonl](review-decisions.jsonl) 是实际入选决定，绑定完整的动作前图 SHA-256、规范动作 JSON、实际交付图 SHA-256 三元组的哈希，以及原轨迹路径与步骤。对照另绑自己的三元组、轨迹和步骤；缩略图编号只是定位标签。
4. `python datasets/jev-trajectory-v2.1/build/extend_validation.py` 从冻结的 v2 复制基础部分，从原 `agent_trace.jsonl` 与 `model_delivery.jsonl` 再读取每条选定事件，对有干预的事件加读 `intervention/events.jsonl`。逐条核对真实派发、归一化坐标、截图字节、请求回执、原生双图顺序与编码器消息。除模型输入外，证据还含源日志摘要、回执的完整记录摘要和派发字段。为避免夹带历史模型推理文本，派发记录只导出必要字段；要独立复核完整的派发行，应对照原日志。可用的未替换原图和匹配对照图片均随包提供。
5. `python datasets/jev-trajectory-v2.1/build/finalize.py check` 重新校验并生成统计，`python datasets/jev-trajectory-v2.1/build/finalize.py zip` 打包，逐成员检查 CRC 和 SHA-256。目录内的 `checksums.sha256` 校验成员；目录外同名 ZIP 的摘要在 `bundle.sha256`。旧数据包未改写。

原 4,459 行元数据和审核记录是保留字节前缀。离线验证器检查冻结的训练、测试及旧验证文件摘要，所有模型输入/辅助图片在不同划分间按字节摘要及解码画面隔离，任务族、轨迹、事件与采集 ID 也不跨划分。新增部分还与历史已定标 Android 输入及已选新增输入做更严的近似画面、相邻点击去重（阈值见 [extension-checks.json](extension-checks.json)）。25 份对照回执不计入验证集行数。
