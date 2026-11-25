"""Train native two-image, A/B-readout LoRA adapters on the balanced Jev v3 data."""
import argparse
import json
import os
from collections import Counter
from pathlib import Path

from paired_data import DEFAULT_DATA, Dataset


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="verify both JSONL views and all input images; no torch or GPU")
    train = sub.add_parser("train", help="fit LoRA and evaluate each epoch")
    smoke = sub.add_parser("smoke", help="one training step + native parity + adapter round trip")
    ev = sub.add_parser("eval", help="evaluate a saved adapter on the original validation split")
    predict = sub.add_parser("predict", help="native YES/NO on two PNGs and a dispatched action")
    for p in (check, train, smoke, ev):
        p.add_argument("--data", type=Path, default=DEFAULT_DATA)
    for p in (train, smoke, ev, predict):
        p.add_argument("--checkpoint", type=Path, required=True, help="complete local pplx-decider-flash-v1.2 checkpoint")
        p.add_argument("--device", default="cuda:0")
        p.add_argument("--cpu-threads", type=int, default=8)
    for p in (train, smoke):
        p.add_argument("--output", type=Path, required=True)
        p.add_argument("--rank", type=int, default=8)
        p.add_argument("--alpha", type=float, default=16.)
        p.add_argument("--dropout", type=float, default=.05)
        p.add_argument("--last-full-layers", type=int, default=4, help="last N full-attention text blocks, q_proj and v_proj")
        p.add_argument("--max-pixels", type=int, default=None, help="per image; default: native checkpoint limit")
        p.add_argument("--max-length", type=int, default=8192, help="reject longer requests; never truncate either image")
        p.add_argument("--gradient-checkpointing", action=argparse.BooleanOptionalAction, default=True)
    for p in (train, ev):
        p.add_argument("--batch-size", type=int, default=1, help="microbatch size")
    train.add_argument("--epochs", type=int, default=3)
    train.add_argument("--grad-accum", type=int, default=8)
    train.add_argument("--lr", type=float, default=1e-4)
    train.add_argument("--weight-decay", type=float, default=.01)
    train.add_argument("--warmup", type=float, default=.05, help="fraction of optimizer steps")
    train.add_argument("--seed", type=int, default=42)
    train.add_argument("--log-every", type=int, default=10)
    train.add_argument("--train-per-cell", type=int, help="optional quick run: N train examples per task and label")
    train.add_argument("--val-per-cell", type=int, help="optional quick run: N validation examples per task and label")
    train.add_argument("--resume", action="store_true", help="continue the same output/run config from the last completed epoch")
    for p in (ev, predict):
        p.add_argument("--adapter", type=Path, required=True, help="epoch directory or run directory (picks best epoch)")
    predict.add_argument("--before", type=Path, required=True)
    predict.add_argument("--after", type=Path, required=True)
    predict.add_argument("--action", required=True, help="native action as a JSON object")
    args = cli.parse_args()
    if args.command == "check":
        data = Dataset(args.data)
        report = {"splits": {s: {l: {t: n for t, n in Counter(r.task for r in rows if r.label == l).items()}
                                 for l in ("YES", "NO")} for s, rows in data.splits.items()},
                  "unique_input_PNGs_checked": data.check_images()}
    else:
        if int(os.environ.get("WORLD_SIZE", "1")) != 1:
            cli.error("Use one process on one device; this entry point does not implement DDP.")
        from runner import run_inference, run_smoke, run_train
        report = run_train(args) if args.command == "train" else run_smoke(args) if args.command == "smoke" else run_inference(args)
    print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
