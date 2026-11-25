"""Run the published Jev LoRA trainer on one explicitly selected GPU (Linux)."""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def card(uuid):
    def query(fields):
        return subprocess.check_output(
            ["nvidia-smi", "-i", uuid, "--format=csv,noheader,nounits", fields],
            text=True, timeout=20,
        ).strip()
    index, actual, total, free = query("--query-gpu=index,uuid,memory.total,memory.free").split(", ")
    if actual != uuid:
        raise RuntimeError("Selected GPU identity changed")
    apps = query("--query-compute-apps=pid,used_gpu_memory")
    return dict(index=int(index), uuid=actual, total_mib=int(total), free_mib=int(free),
                apps=apps.splitlines(), at=now())


def require_idle(uuid):
    state = card(uuid)
    if state["apps"] or state["free_mib"] < 23000:
        raise RuntimeError(f"GPU is no longer available: {state}")
    return state


def preflight(root, checkpoint, cap):
    import torch
    from PIL import Image
    sys.path.insert(0, str(root / "jev_lora"))
    from native_lora import Adapters, LoraSettings, encode, load_engine
    from paired_data import Dataset
    from runner import checkpoint_gradients, evaluate, optimizer_step

    if torch.cuda.device_count() != 1 or not torch.cuda.is_bf16_supported():
        raise RuntimeError("Expected exactly one visible BF16 CUDA device")
    path = root / f"preflight-{cap}.json"
    report = dict(started=now(), device=torch.cuda.get_device_name(0),
                  visible=os.environ["CUDA_VISIBLE_DEVICES"], requested_pixels=cap)
    stage = "load"
    try:
        torch.manual_seed(42)
        ds = Dataset(root / "jev-trajectory-v3")
        engine = load_engine(checkpoint, "cuda:0", cap, 8192, 8)
        adapters = Adapters(engine, LoraSettings())
        checkpoint_gradients(engine, True)
        opt = torch.optim.AdamW(adapters.parameters(), lr=1e-4, weight_decay=.01)
        sizes = {}

        def size(key):
            if key not in sizes:
                with Image.open(ds.root / "images" / (key + ".png")) as image:
                    sizes[key] = image.size
            return sizes[key]

        def priority(row):
            w, h = size(row.before)
            return (w * h, len(row.prompt.encode("utf-8")), row.before != row.after)

        for stage in ("val", "train"):
            row = max(ds.splits[stage], key=priority)
            encoded, = encode(engine, ds, [row])
            probe = dict(sample_id=row.sid, width_height=size(row.before),
                         tokens=encoded.length, image_grid=encoded.image_grid_thw.tolist())
            del encoded
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
            start = time.monotonic()
            if stage == "val":
                probe["loss"] = evaluate(engine, ds, [row], 1)["overall"]["loss"]
            else:
                adapters.mode(True)
                loss, grad = optimizer_step(engine, adapters, ds, [row], 1, opt)
                if grad <= 0 or not any(torch.count_nonzero(m.B).item() for m in adapters.layers.values()):
                    raise RuntimeError("No LoRA weight changed during preflight")
                probe.update(loss=loss, grad=grad)
            torch.cuda.synchronize()
            probe.update(seconds=time.monotonic() - start,
                         peak_allocated_mib=round(torch.cuda.max_memory_allocated() / 2**20),
                         peak_reserved_mib=round(torch.cuda.max_memory_reserved() / 2**20))
            report[stage] = probe
            print(stage, json.dumps(probe), flush=True)
        report.update(status="passed", effective_max_pixels=engine.max_pixels,
                      trainable_parameters=sum(p.numel() for p in adapters.parameters()))
    except torch.cuda.OutOfMemoryError as e:
        report.update(status="cuda_oom", stage=stage, error=str(e))
    write(path, report | {"finished": now()})
    return 0 if report["status"] == "passed" else 42


def launch(root, checkpoint, uuid):
    home = Path.home()
    locks = [home / ".mirage-resource-locks" / (uuid + ".lock"),
             home / "defense-resume-20261102-retry2/resource-locks" / (uuid + ".lock"),
             home / "jev-defense-four-gpu-20261106/inference.lock"]
    env = os.environ | dict(CUDA_VISIBLE_DEVICES=uuid, CUDA_DEVICE_ORDER="PCI_BUS_ID",
                            HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                            TOKENIZERS_PARALLELISM="false", PYTHONUNBUFFERED="1",
                            OMP_NUM_THREADS="8", MKL_NUM_THREADS="8",
                            PYTORCH_ALLOC_CONF="expandable_segments:True")
    record = dict(launch_time=now(), supervisor_pid=os.getpid(), gpu_uuid=uuid, run=str(root))
    with (root / "job.started").open("x") as fp:
        fp.write(now() + "\n")
    with contextlib.ExitStack() as stack:
        try:
            record["before_lock"] = require_idle(uuid)
            fds = []
            for path in sorted(locks):
                fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
                stack.callback(os.close, fd)
                st = os.fstat(fd)
                if st.st_uid != os.getuid() or not stat.S_ISREG(st.st_mode):
                    raise RuntimeError(f"Unexpected lock file: {path}")
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fds.append(fd)
            record.update(after_lock=require_idle(uuid), locks=list(map(str, locks)))

            def child(stage, args, log):
                with (root / log).open("x", buffering=1) as fp:
                    worker = subprocess.Popen([sys.executable, "-u", *map(str, args)], stdout=fp,
                                              stderr=subprocess.STDOUT, cwd=root, env=env,
                                              pass_fds=tuple(fds))
                    record.update(stage=stage, worker_pid=worker.pid, log=log, updated=now())
                    write(root / "job.json", record)
                    print(now(), stage, worker.pid, log, flush=True)
                    return worker.wait()

            for cap in (1638400, 1048576, 786432, 524288, 262144):
                require_idle(uuid)
                rc = child("preflight", [Path(__file__).resolve(), "--probe", cap, "--root", root,
                                         "--checkpoint", checkpoint], f"preflight-{cap}.log")
                if rc == 0:
                    break
                if rc != 42:
                    raise RuntimeError(f"Preflight failed (exit {rc}); see {record['log']}")
            else:
                raise RuntimeError("No tested image limit fits")
            record["preflight"] = f"preflight-{cap}.json"
            record["max_pixels"] = cap
            record["before_training"] = require_idle(uuid)
            rc = child("training", [root / "jev_lora/train_lora.py", "train",
                       "--data", root / "jev-trajectory-v3", "--checkpoint", checkpoint,
                       "--output", root / "model", "--max-pixels", cap, "--log-every", 5], "train.log")
            if rc:
                raise RuntimeError(f"Trainer exited with code {rc}; see train.log")
            progress = json.loads((root / "model/progress.json").read_text())
            if progress["completed_epochs"] != 3:
                raise RuntimeError(f"Incomplete run: {progress}")
            record.update(stage="completed", progress=progress)
        except BaseException as e:
            record.update(stage="failed", error=repr(e))
            raise
        finally:
            write(root / "job.json", record | {"finished": now()})
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--gpu", help="full physical GPU UUID")
    mode.add_argument("--probe", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    base = args.root.resolve(strict=True)
    raise SystemExit(preflight(base, args.checkpoint, args.probe) if args.probe is not None
                     else launch(base, args.checkpoint, args.gpu))
