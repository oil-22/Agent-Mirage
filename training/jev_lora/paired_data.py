"""Read the published two-image views. Only images and the dispatched action reach Jev."""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import temporal_request as native

HERE = Path(__file__).resolve().parent
DEFAULT_DATA = HERE.parents[1] / "datasets" / "jev-trajectory-v3"
TASKS = ("blank_replace", "stale_replace", "buttons_only")
LABELS = ("YES", "NO")  # the native readout uses column A first, B second
PROTOCOL_SHA = "83a8d7014fe7469ab99076b01ab9d58776553e09a2edf7628042627de2ba15bf"
REVISION = "9ff7cf9838e59df461c276b7699d56b244d2af58"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    with Path(path).open("rb") as fp:
        return hashlib.file_digest(fp, "sha256").hexdigest()


def read_json(path):
    return json.loads(Path(path).read_bytes())


def jsonl(path):
    with Path(path).open("rb") as fp:
        return [json.loads(line) for line in fp if line.strip()]


@dataclass(frozen=True)
class Example:
    sid: str
    before: str
    after: str
    action: dict
    prompt: str
    label: str
    task: str
    origin: str


class Dataset:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.protocol = read_json(self.root / "protocol.json")
        stats = read_json(self.root / "stats.json")
        self.hashes = {name: digest(self.root / name) for name in
                       ("manifest.jsonl", "train.jsonl", "val.jsonl", "protocol.json")}
        require(all(stats["sha256"][k] == v for k, v in self.hashes.items()), "Dataset differs from stats.json")
        require(self.hashes["protocol.json"] == PROTOCOL_SHA
                and self.protocol["checkpoint_revision"] == REVISION
                and self.protocol["prompt_builder_sha256"] == digest(HERE / "temporal_request.py"),
                "Expected the published Jev v3 data and native prompt builder")
        meta = jsonl(self.root / "manifest.jsonl")
        require(all(m["split"] in ("train", "val") for m in meta), "Unexpected split")
        self.splits = {}
        ids, owners = set(), {}
        for split in ("train", "val"):
            dataset = []
            metadata = [m for m in meta if m["split"] == split]
            for i, (m, view) in enumerate(zip(metadata, jsonl(self.root / (split + ".jsonl")), strict=True), 1):
                sid, a = m["sample_id"], m["action"]
                b, h = m["before_sha256"], m["candidate_sha256"]
                for key in (b, h):
                    require(len(key) == 64 and all(c in "0123456789abcdef" for c in key), "Invalid PNG digest")
                    require(owners.setdefault(key, split) == split, "PNG shared between train and val")
                pmt = self.protocol["user_text"].replace("{canonical_action_json}", native.action_json(a))
                require(view == {"images": ["images/" + b + ".png", "images/" + h + ".png"],
                                 "prompt": pmt, "label": m["label"]}, "View/manifest mismatch: " + sid)
                require(m["line"] == i and m["task"] in TASKS and m["label"] in LABELS
                        and m["origin"] in ("observed", "constructed") and sid not in ids, "Invalid metadata: " + sid)
                ids.add(sid)
                dataset.append(Example(sid, b, h, a, pmt, m["label"], m["task"], m["origin"]))
            counts = Counter((r.task, r.label) for r in dataset)
            require(set(counts) == {(t, l) for t in TASKS for l in LABELS} and len(set(counts.values())) == 1
                    and all(counts[t, l] == stats["tasks"][split][t][l] for t, l in counts),
                    "Expected six balanced cells: " + split)
            self.splits[split] = dataset

    def image(self, key):
        raw = (self.root / "images" / (key + ".png")).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == key, "PNG digest mismatch: " + key)
        return raw

    def request(self, row):
        return native.native_request(self.image(row.before), row.action, self.image(row.after))

    def check_images(self):
        sizes = {}
        for split in self.splits.values():
            for r in split:
                for h in (r.before, r.after):
                    if h not in sizes:
                        sizes[h] = native.png_size(self.image(h))
                require(sizes[r.before] == sizes[r.after], "Viewport mismatch: " + r.sid)
        return len(sizes)


def subset(rows, per_cell, seed):
    if per_cell is None:
        return list(rows)
    require(per_cell >= 1, "per-cell must be positive")
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    picked, counts = [], Counter()
    for r in shuffled:
        key = (r.task, r.label)
        if counts[key] < per_cell:
            counts[key] += 1
            picked.append(r)
    require(len(picked) == 6 * per_cell, "Not enough rows for this per-cell limit")
    return picked


def smoke_examples(data):
    train = data.splits["train"]
    # Two different prompt lengths exercise the left-padding offset, with both labels present.
    yes = next(r for r in train if r.label == "YES" and r.action["type"] == "scroll")
    no = next(r for r in train if r.label == "NO" and r.action["type"] == "click")
    return [yes, no], subset(data.splits["val"], 1, 43)
