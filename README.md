# Agent-Mirage

**Agent-Mirage: From Visual Evidence Failures to Error Propagation in Multimodal Agents**

We define **Agent-Mirage** as a multimodal agent failing to recognize visual evidence failure and continuing to act confidently.

This project studies how errors persist and propagate through interaction trajectories, how current visual evidence and historical judgments affect subsequent actions, and how early diagnosis and targeted repair can reduce downstream consequences. GUI interaction serves as an experimental domain.

## Reproduce the reported measurements

The [offline review package](review/README.md) contains the measured counts, matched attention observations, gate outcomes, and a small browser fixture. With Python 3.11 or newer:

```sh
cd review
python -m pip install -r requirements.txt
python reproduce.py benchmark
python reproduce.py attention
python reproduce.py defense
```

These commands recompute the reported statistics from recorded measurements. The live experiment runners and the fine-tuning implementation are also included in this repository.

## Experiment code

| Study | Entry points |
| --- | --- |
| Attention and history dependence | [First collection](attention-audit-20261031/run_attention.py), [expanded collection](attention-audit-20261102/run_attention.py), [matched analysis](attention-audit-20261102/analyze_expansion.py) |
| Context length and visual failure | [Pilot](context-length-pilot-20261117/run_pilot.py), [natural trajectories and length bins](context-length-natural-20261117/scale100-resume01/run_scale100.py), [trajectory token accounting](reports/trajectory-token-audit-20261117/analyze_tokens.py) |
| Visual detail and cropping | [Crop replay](reports/crop-visual-replay-20261120/worker.py), [visual-token probe](reports/crop-visual-token-probe-20261120/crop_token_probe.py) |
| Evidence checks, recovery, and full GUI episodes | [Early controller](defense-resume-20261102/verified-release), [Jev integration](jev-defense-validation-20261103/release), [multi-GPU experiments](jev-defense-four-gpu-20261106), [paired full-GUI protocol and runtimes](reports/jev-gui-paired-20261122/PROTOCOL.md) |
| Single-frame and temporal verifier comparisons | [Temporal panel](reports/jev-temporal-gate-20261122/live_run.py), [scale panel](reports/jev-defense-scale-20261122/live_run.py), [toggle controls](reports/jev-toggle-guard-20261122/toggle_protocol.py), [outcome study](reports/jev-toggle-outcome-20261122/launch_study.py) |
| Dataset construction and verifier training | [Dataset builders](datasets/README.md), [two-frame LoRA](training/jev_lora/README.md), [single-GPU launcher](training/jev_lora_ops/launch_single_gpu.py), [frozen-backbone head baseline](reports/jev-verifier-finetune-starter-20261125/README.md) |

The dated directories preserve each experiment's relative imports, scripts, and separate protocol versions. For a live run, provision the relevant benchmark, local model/processor, and source observations first. Historical launchers also refer to job-specific mounts, SSH aliases, service tokens, GPU placement, and sealed run manifests. Configure those for your own environment; the published network and hardware identifiers are examples. The review commands above do not depend on these services.

## Fine-tune the two-frame verifier

The [LoRA trainer](training/jev_lora/train_lora.py) uses the ordered before/after screenshots and the dispatched action to predict YES or NO. The v3 split contains 3,312 training samples and 318 validation samples. Obtain the full v3 data bundle separately and use the [base model](https://huggingface.co/perplexity-ai/pplx-decider-flash-v1.2/tree/9ff7cf9838e59df461c276b7699d56b244d2af58) at the revision pinned in the [checkpoint lock](training/jev_lora/checkpoint-lock.json).

```sh
# From the repository root, in the native Jev environment:
python training/jev_lora/train_lora.py check --data /path/to/jev-trajectory-v3
python training/jev_lora/train_lora.py train --data /path/to/jev-trajectory-v3 --checkpoint /path/to/pplx-decider-flash-v1.2 --output runs/jev-lora-v3
```

See the [training guide](training/jev_lora/README.md) for dependencies, adapter loading, evaluation, prediction, and resuming from a completed epoch. This is a source release: the full screenshot corpus, private evaluator state, model weights, and run logs are separate artifacts.
