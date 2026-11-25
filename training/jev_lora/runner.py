"""Single-device LoRA training, model selection and an end-to-end diagnostic."""
from __future__ import annotations

import json
import math
import os
import random
import tempfile
import time
from collections import defaultdict
from pathlib import Path

import torch
import torch.nn.functional as F
import transformers

from native_lora import Adapters, LoraSettings, adapter_metadata, encode, load_engine, raw_logits
from paired_data import Dataset, HERE, LABELS, REVISION, TASKS, digest, read_json, require, smoke_examples, subset
from temporal_request import native_request


def write_json(path, obj):
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def labels(rows, engine):
    return torch.tensor([LABELS.index(r.label) for r in rows], dtype=torch.long, device=engine.device)


def score(rows):
    # (truth, prediction, per-example NLL); index 0 = YES.
    n = len(rows)
    yes = sum(y == 0 for y, p, l in rows)
    no = n - yes
    fa = sum(y == 1 and p == 0 for y, p, l in rows)
    fr = sum(y == 0 and p == 1 for y, p, l in rows)
    return dict(n=n, YES=yes, NO=no, accuracy=(n - fa - fr) / n, loss=sum(l for y, p, l in rows) / n,
                balanced_accuracy=1 - (fa / no + fr / yes) / 2 if no and yes else None,
                false_accept_NO_as_YES=fa, false_accept_rate=fa / no if no else None,
                false_reject_YES_as_NO=fr, false_reject_rate=fr / yes if yes else None)


@torch.no_grad()
def evaluate(engine, data, rows, batch_size):
    engine.backbone.eval()
    buckets = defaultdict(list)
    started = time.monotonic()
    next_report = 32
    for start in range(0, len(rows), batch_size):
        part = rows[start:start + batch_size]
        y = labels(part, engine)
        logits = raw_logits(engine, encode(engine, data, part)) / engine.temperature
        losses = F.cross_entropy(logits, y, reduction="none")
        require(torch.isfinite(losses).all(), "Non-finite validation loss")
        for row, yy, pred, loss in zip(part, y.tolist(), logits.argmax(-1).tolist(), losses.tolist(), strict=True):
            for key in ("all", row.task, row.origin):
                buckets[key].append((yy, pred, loss))
        done = start + len(part)
        if len(rows) >= 32 and (start == 0 or done >= next_report or done == len(rows)):
            print(f"validation {done}/{len(rows)} ({time.monotonic()-started:.1f}s)", flush=True)
            next_report = (done // 32 + 1) * 32
    return dict(overall=score(buckets["all"]), by_task={k: score(buckets[k]) for k in TASKS if buckets[k]},
                by_origin={k: score(buckets[k]) for k in ("observed", "constructed") if buckets[k]})


def optimizer_step(engine, adapters, data, window, micro, optimizer):
    """Divide by the actual number of examples, including the last short accumulation window."""
    optimizer.zero_grad(set_to_none=True)
    loss_sum = 0.
    for start in range(0, len(window), micro):
        rows = window[start:start + micro]
        logits = raw_logits(engine, encode(engine, data, rows)) / engine.temperature
        loss = F.cross_entropy(logits, labels(rows, engine), reduction="sum")
        require(torch.isfinite(loss), "Non-finite training loss")
        (loss / len(window)).backward()
        loss_sum += float(loss.detach())
    norm = float(torch.nn.utils.clip_grad_norm_(adapters.parameters(), 1.0, error_if_nonfinite=True))
    optimizer.step()
    return loss_sum / len(window), norm


def checkpoint_gradients(engine, enabled):
    if enabled:
        # Non-reentrant checkpointing works with a frozen embedding/prefix.
        engine.backbone.language_model.gradient_checkpointing_enable(
            gradient_checkpointing_kwargs={"use_reentrant": False})


def lr_at(step, total, base, warmup):
    warm = int(total * warmup)
    if step < warm:
        return base * (step + 1) / warm
    return base * (1. + math.cos(math.pi * (step - warm) / max(total - warm, 1))) / 2.


def completed(run):
    def number(path):
        return path.name.removeprefix("epoch-")
    dirs = sorted((p for p in run.glob("epoch-*") if p.is_dir() and number(p).isdigit()),
                  key=lambda p: int(number(p)))
    require([p.name for p in dirs] == [f"epoch-{i:03d}" for i in range(1, len(dirs) + 1)],
            "Checkpoint sequence has a gap")
    return dirs


def progress(run, dirs):
    def key(p):
        m = read_json(p / "metrics.json")["val"]["overall"]
        return m["balanced_accuracy"], -m["loss"]
    report = dict(completed_epochs=len(dirs), last=dirs[-1].name, best=max(dirs, key=key).name)
    write_json(run / "progress.json", report)
    return report


def run_train(args):
    require(args.epochs > 0 and args.grad_accum > 0 and args.batch_size > 0 and args.log_every > 0
            and math.isfinite(args.lr) and args.lr > 0 and 0 <= args.warmup < 1
            and math.isfinite(args.weight_decay) and args.weight_decay >= 0, "Invalid training options")
    torch.manual_seed(args.seed)
    data = Dataset(args.data)
    train = subset(data.splits["train"], args.train_per_cell, args.seed)
    val = subset(data.splits["val"], args.val_per_cell, args.seed + 1)
    run = args.output.resolve()
    if not args.resume:
        # Accept a new or empty directory, never overwrite a previous run.
        run.mkdir(parents=True, exist_ok=True)
        require(not any(run.iterdir()), f"Output already contains files: {run}; choose a new directory or --resume")
    else:
        require((run / "run.json").is_file(), "--resume needs a completed run configuration")
    cfg = LoraSettings(args.rank, args.alpha, args.dropout, args.last_full_layers)
    engine = load_engine(args.checkpoint, args.device, args.max_pixels, args.max_length, args.cpu_threads)
    adapters = Adapters(engine, cfg)
    checkpoint_gradients(engine, args.gradient_checkpointing)
    params = adapters.parameters()
    optim = torch.optim.AdamW(params, lr=args.lr, weight_decay=args.weight_decay)
    effective = args.batch_size * args.grad_accum
    per_epoch = math.ceil(len(train) / effective)
    config = dict(revision=REVISION, data_sha256=data.hashes, checkpoint_lock_sha256=digest(HERE / "checkpoint-lock.json"),
                  torch=str(torch.__version__), transformers=transformers.__version__, settings=vars(cfg),
                  targets=list(adapters.layers), adapter_parameters=sum(p.numel() for p in params),
                  device_type=engine.device.type, max_pixels=engine.max_pixels, max_length=engine.max_length,
                  seed=args.seed, lr=args.lr, warmup=args.warmup, weight_decay=args.weight_decay,
                  epochs=args.epochs, microbatch=args.batch_size, accumulation=args.grad_accum,
                  checkpoint_gradients=args.gradient_checkpointing, train_per_cell=args.train_per_cell,
                  val_per_cell=args.val_per_cell, train_size=len(train), val_size=len(val))
    if args.resume:
        require(read_json(run / "run.json") == config, "Resume configuration, data or runtime differs")
    else:
        write_json(run / "run.json", config)
    print(f"{len(train)} train / {len(val)} val; {config['adapter_parameters']:,} LoRA parameters, "
          f"{per_epoch} optimizer steps/epoch.", flush=True)
    # Native baseline at unchanged weights; zero-initialized adapters are exactly neutral in eval mode.
    if not (run / "baseline.json").exists():
        baseline = evaluate(engine, data, val, args.batch_size)
        write_json(run / "baseline.json", baseline)
        print("Native validation:", json.dumps(baseline["overall"]), flush=True)
    dirs = completed(run)
    if dirs:
        progress(run, dirs)  # also recover an epoch committed just before an interruption
        adapters.restore(dirs[-1])
        optim.load_state_dict(torch.load(dirs[-1] / "optimizer.pt", map_location="cpu", weights_only=True))
    for epoch in range(len(dirs) + 1, args.epochs + 1):
        torch.manual_seed(args.seed + epoch)
        shuffled = list(train)
        random.Random(args.seed + epoch).shuffle(shuffled)
        adapters.mode(True)
        accumulated = 0.
        started = time.monotonic()
        for j, start in enumerate(range(0, len(shuffled), effective)):
            step = (epoch - 1) * per_epoch + j
            optim.param_groups[0]["lr"] = lr_at(step, args.epochs * per_epoch, args.lr, args.warmup)
            window = shuffled[start:start + effective]
            loss, grad = optimizer_step(engine, adapters, data, window, args.batch_size, optim)
            accumulated += loss * len(window)
            if j == 0 or (j + 1) % args.log_every == 0 or j + 1 == per_epoch:
                print(f"epoch {epoch}/{args.epochs} step {j+1}/{per_epoch} loss={loss:.4f} grad={grad:.4f} "
                      f"({time.monotonic()-started:.1f}s)", flush=True)
        metrics = dict(epoch=epoch, steps=epoch * per_epoch, train_loss=accumulated / len(train),
                       val=evaluate(engine, data, val, args.batch_size))
        tmp = Path(tempfile.mkdtemp(prefix=".saving-", dir=run))
        adapters.save(tmp)
        torch.save(optim.state_dict(), tmp / "optimizer.pt")
        write_json(tmp / "metrics.json", metrics)
        dst = run / f"epoch-{epoch:03d}"
        tmp.rename(dst)
        dirs.append(dst)
        result = progress(run, dirs)
        print("Validation:", json.dumps(metrics["val"]["overall"]), "best:", result["best"], flush=True)
    return read_json(run / "progress.json")


def run_smoke(args):
    """One disposable LoRA update; compare with native logits before training and after reloading."""
    data = Dataset(args.data)
    train, val = smoke_examples(data)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    require(not any(out.iterdir()), "Smoke output must be empty")
    torch.manual_seed(42)
    engine = load_engine(args.checkpoint, args.device, args.max_pixels, args.max_length, args.cpu_threads)
    chunks = encode(engine, data, train)
    require(chunks[0].length != chunks[1].length, "Smoke needs unequal token lengths to test padding")
    def native_raw():
        return torch.tensor([p[0] for p in engine.reference_logits(chunks)], dtype=torch.float32)
    baseline = native_raw()
    adapters = Adapters(engine, LoraSettings(args.rank, args.alpha, args.dropout, args.last_full_layers))
    with torch.no_grad():
        initial = raw_logits(engine, chunks).cpu()
    torch.testing.assert_close(initial, baseline, rtol=1e-5, atol=1e-5)
    checkpoint_gradients(engine, args.gradient_checkpointing)
    adapters.mode(True)
    loss, grad = optimizer_step(engine, adapters, data, train, 1, torch.optim.AdamW(adapters.parameters(), lr=1e-3))
    require(grad > 0 and any(torch.count_nonzero(layer.B) for layer in adapters.layers.values()),
            "LoRA weights did not update")
    require(all(p.grad is None for p in engine.backbone.parameters() if not p.requires_grad)
            and all(p.grad is None for p in engine.readout.parameters()), "Frozen weights received gradients")
    adapters.mode(False)
    updated = native_raw()
    require(not torch.equal(updated, baseline), "Update did not change native A/B logits")
    adapters.save(out / "adapter")
    nparams = sum(p.numel() for p in adapters.parameters())
    adapters.remove()
    restored = Adapters(engine, LoraSettings(**adapter_metadata(out / "adapter")[1]["lora"]))
    restored.restore(out / "adapter")
    reloaded = native_raw()
    torch.testing.assert_close(reloaded, updated, rtol=1e-5, atol=1e-5)
    report = dict(status="passed", revision=REVISION, device=str(engine.device), max_pixels=engine.max_pixels,
                  gradient_checkpointing=args.gradient_checkpointing, train_examples=[r.sid for r in train],
                  val_examples=[r.sid for r in val], tokens=[c.length for c in chunks], lora_parameters=nparams,
                  train_loss=loss, gradient_norm=grad, optimizer_steps=1,
                  native_parity_max_abs=float((initial-baseline).abs().max()),
                  trained_logit_change_max_abs=float((updated-baseline).abs().max()),
                  reload_max_abs=float((reloaded-updated).abs().max()),
                  validation=evaluate(engine, data, val, 1))
    write_json(out / "smoke.json", report)
    return report


def run_inference(args):
    folder, meta = adapter_metadata(args.adapter)
    engine = load_engine(args.checkpoint, args.device, meta["max_pixels"], meta["max_length"], args.cpu_threads)
    adapters = Adapters(engine, LoraSettings(**meta["lora"]))
    adapters.restore(folder)
    if args.command == "predict":
        req = native_request(args.before.read_bytes(), json.loads(args.action), args.after.read_bytes())
        return engine.decide(req)["answers"]["action_outcome_visible"]
    data = Dataset(args.data)
    require(args.batch_size >= 1, "batch-size must be positive")
    return evaluate(engine, data, data.splits["val"], args.batch_size)
