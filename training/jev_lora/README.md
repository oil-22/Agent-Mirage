# Jev 双截图 LoRA 微调

训练入口是 `train_lora.py train`。输入为 v3 的前图、候选图、含实际动作的原生 prompt；监督为 YES 或 NO。默认使用全部 3,312 条训练数据，原有 318 条验证数据只用于评估和选择 epoch。

### 在训练机运行

将训练代码与解压后的 `jev-trajectory-v3/` 放在训练机上。使用原生 Jev Flash Python 环境和完整的 `perplexity-ai/pplx-decider-flash-v1.2` checkpoint（包括 `source/src/pplx_decider` 和原生 readout）。脚本会检查固定版本的权重、处理器和源码。新建环境时使用 Python 3.12+ 和 [requirements.txt](requirements.txt)，PyTorch / torchvision 选择与训练机 CUDA 驱动匹配的构建。LoRA 用 PyTorch 实现，无需额外安装 PEFT。

以下从项目根目录执行。将 `DATA` 和 `CKPT` 指向自己机器上的完整数据包和固定版本的原生 checkpoint；`PY` 是已安装依赖的 Python。

```bash
DATA="/path/to/jev-trajectory-v3"
CKPT="/path/to/pplx-decider-flash-v1.2"
PY=python
CODE="$PWD/training/jev_lora/train_lora.py"

"$PY" "$CODE" check --data "$DATA"
"$PY" "$CODE" train --data "$DATA" --checkpoint "$CKPT" --output runs/jev-lora-v3
```

默认单进程、单卡 BF16，微批 1，累积 8，各样本每轮使用一次，3 个 epoch；每个完整 epoch 有 414 次优化器更新。峰值学习率 `1e-4`，5% warmup 后按余弦衰减，梯度范数裁剪为 1。默认沿用 checkpoint 的每图像素上限 1,638,400，启用文本层的梯度检查点。显存较紧时可以试 `--last-full-layers 2` 或 `--max-pixels 262144`；减小像素上限会改变实际输入分辨率，要重新评估小按钮、焦点环等细节。8 GB 显存装不下这个版本 BF16 的完整基础权重。

默认使用第一个可见 CUDA 设备，遵循训练机的 `CUDA_VISIBLE_DEVICES` 设置。先验证本机前向、反向和保存/加载，可单独运行：

```bash
"$PY" "$CODE" smoke --data "$DATA" --checkpoint "$CKPT" --output runs/jev-lora-smoke
```

`smoke` 用 2 条真实训练输入做 1 次更新，随后重新加载适配器，并用验证集每格 1 条、共 6 条跑通指标。它比较未更新时与原生 A/B 分数是否一致、更新是否改变分数、重新载入是否复现。它的 6 条验证结果不能当作模型效果。

### 更新哪些权重

默认只在文本骨干最后 4 个 **full-attention** 层（层号 19、23、27、31，从 0 起）给 `q_proj`、`v_proj` 加 LoRA：rank 8、alpha 16、dropout 0.05，共 458,752 个可训练参数，B 从零开始。视觉编码器、其余骨干及 255 类原生判定头均冻结。

双图顺序、原生编码器、非因果全注意力、左侧补齐和 `<|fim_suffix|>` 决策位置保持一致。训练在该位置取原生判定头 A、B 两列，按 checkpoint 的温度缩放，对 YES=0、NO=1 做交叉熵。场景名、来源、标签理由都不会进入模型输入。

### 输出、续训与使用

- `baseline.json`：训练前原模型在同一验证集上的结果。每个 `epoch-NNN/metrics.json` 包含损失、准确率、平衡准确率，以及总体、三个场景和实收／构造两种来源各自的 NO→YES 误放和 YES→NO 误拦（含分母，无该类时比率为 null）。
- `epoch-NNN/adapter.safetensors` 与 `adapter.json`：该轮的 LoRA 权重及加载配置，不包含基础模型。`progress.json` 指向最后和最佳已训练 epoch；最佳按验证集平衡准确率选择，并列时取更低的验证损失。对照 `baseline.json` 判断是否值得使用新权重。
- 中断后用原命令和相同参数，加 `--resume` 从最后一个完整 epoch 的适配器和优化器状态继续；未结束的 epoch 会重跑。正式训练使用新输出目录，以免混入烟测输出。

传入整个训练输出目录会自动加载最佳 epoch，也可直接传 `epoch-001/` 等指定目录：

```bash
"$PY" "$CODE" eval --data "$DATA" --checkpoint "$CKPT" --adapter runs/jev-lora-v3
"$PY" "$CODE" predict --checkpoint "$CKPT" --adapter runs/jev-lora-v3 --before before.png --after after.png --action '{"type":"scroll","direction":"down"}'
```

适配器使用本目录的原生加载器 `native_lora.py`。预测经过 Jev 自己的 `decide()`，返回 YES/NO 及概率。若要先试一个配平的小训练，可以在一个新目录运行 `train --epochs 1 --train-per-cell 1 --val-per-cell 1` 并加上上述数据、权重和输出参数；不影响完整数据。

本次在真实 4B checkpoint 上使用 CPU 和每图 65,536 像素上限做了短测。[原生分数和适配器重载记录](validation/native-cpu-smoke.json)中，更新前与原生 logits 的最大差值为 0，更新后最大变化为 0.25128，重新加载后的最大差值为 0。[小规模训练记录](validation/small-cpu-train.json)使用 6 条训练、6 条验证，覆盖最后一个不足累积步数的批次。这些记录用于验证代码；没有据此估计完整数据的准确率或 GPU 显存。
