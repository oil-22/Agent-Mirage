"""Differentiable counterpart of Decider.reference_logits and text-attention LoRA."""
from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import torch
import torch.nn.functional as F
from safetensors.torch import load_file, save_file
from torch import nn

from paired_data import HERE, LABELS, PROTOCOL_SHA, REVISION, digest, read_json, require
from temporal_request import QUESTION_ID

FORMAT = "jev-native-lora-v1"


@dataclass(frozen=True)
class LoraSettings:
    rank: int = 8
    alpha: float = 16.0
    dropout: float = 0.05
    last_full_layers: int = 4


class LowRankLinear(nn.Module):
    def __init__(self, base, cfg):
        super().__init__()
        self.base = base
        args = {"device": base.weight.device, "dtype": torch.float32}
        self.A = nn.Parameter(torch.empty(cfg.rank, base.in_features, **args))
        self.B = nn.Parameter(torch.zeros(base.out_features, cfg.rank, **args))
        nn.init.kaiming_uniform_(self.A, a=math.sqrt(5))
        self.scale = cfg.alpha / cfg.rank
        self.drop = nn.Dropout(cfg.dropout)

    def forward(self, x):
        y = self.base(x)
        # FP32 master adapter/optimizer weights; use the activation dtype for matmuls.
        delta = F.linear(F.linear(self.drop(x), self.A.to(x.dtype)), self.B.to(x.dtype))
        return y + (self.scale * delta).to(y.dtype)


class Adapters:
    def __init__(self, engine, cfg):
        require(cfg.rank > 0 and math.isfinite(cfg.alpha) and cfg.alpha > 0
                and 0 <= cfg.dropout < 1, "Invalid LoRA rank, alpha or dropout")
        self.engine, self.cfg, self.layers = engine, cfg, {}
        engine.backbone.requires_grad_(False).eval()
        engine.readout.requires_grad_(False).eval()
        kinds = engine.backbone.config.text_config.layer_types
        full = [i for i, t in enumerate(kinds) if t == "full_attention"]
        require(0 < cfg.last_full_layers <= len(full), f"Checkpoint has {len(full)} full-attention layers")
        for i in full[-cfg.last_full_layers:]:
            parent = engine.backbone.language_model.layers[i].self_attn
            for proj in ("q_proj", "v_proj"):
                linear = getattr(parent, proj)
                require(isinstance(linear, nn.Linear), "Expected an unwrapped native " + proj)
                layer = LowRankLinear(linear, cfg)
                setattr(parent, proj, layer)
                self.layers[f"language_model.layers.{i}.self_attn.{proj}"] = layer
        trainable = {id(p) for p in engine.backbone.parameters() if p.requires_grad}
        require(trainable == {id(p) for p in self.parameters()} and len(trainable) == 2 * len(self.layers),
                "Only LoRA tensors may be trainable")
        self.mode(False)

    def parameters(self):
        return [p for layer in self.layers.values() for p in (layer.A, layer.B)]

    def mode(self, training):
        # Leave the image tower and readout in eval mode; allow text-layer checkpointing/dropout.
        self.engine.backbone.language_model.train(training)

    def remove(self):
        self.mode(False)
        for name, layer in self.layers.items():
            parent, field = name.rsplit(".", 1)
            setattr(self.engine.backbone.get_submodule(parent), field, layer.base)
        self.layers.clear()

    def state(self):
        return {f"{name}.lora_{field}": getattr(layer, field)
                for name, layer in self.layers.items() for field in ("A", "B")}

    def save(self, folder):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        dst = folder / "adapter.safetensors"
        save_file({k: v.detach().cpu().contiguous() for k, v in self.state().items()}, str(dst))
        meta = dict(format=FORMAT, revision=REVISION, protocol_sha256=PROTOCOL_SHA,
                    checkpoint_lock_sha256=digest(HERE / "checkpoint-lock.json"),
                    lora=asdict(self.cfg), targets=list(self.layers),
                    answer_order=list(LABELS), max_pixels=self.engine.max_pixels,
                    max_length=self.engine.max_length, weights_sha256=digest(dst))
        (folder / "adapter.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    @torch.no_grad()
    def restore(self, folder):
        folder, meta = adapter_metadata(folder)
        require(self.cfg == LoraSettings(**meta["lora"]) and list(self.layers) == meta["targets"]
                and self.engine.max_pixels == meta["max_pixels"] and self.engine.max_length == meta["max_length"],
                "Loaded adapter configuration does not match this model")
        params = self.state()
        saved = load_file(str(folder / "adapter.safetensors"), device="cpu")
        require(set(saved) == set(params), "Adapter keys differ")
        for name, param in params.items():
            value = saved[name]
            require(value.shape == param.shape and value.dtype == torch.float32 and torch.isfinite(value).all(),
                    "Invalid adapter tensor: " + name)
            param.copy_(value)


def adapter_metadata(folder):
    folder = Path(folder).resolve()
    if not (folder / "adapter.json").exists() and (folder / "progress.json").exists():
        sub = read_json(folder / "progress.json")["best"]
        require(Path(sub).name == sub and sub.startswith("epoch-"), "Invalid best checkpoint pointer")
        folder = folder / sub
    meta = read_json(folder / "adapter.json")
    require(meta["format"] == FORMAT and meta["revision"] == REVISION and meta["answer_order"] == list(LABELS)
            and meta["protocol_sha256"] == PROTOCOL_SHA and meta["checkpoint_lock_sha256"] == digest(HERE / "checkpoint-lock.json")
            and meta["weights_sha256"] == digest(folder / "adapter.safetensors"), "Incompatible or damaged adapter")
    return folder, meta


def load_engine(checkpoint, device, max_pixels=None, max_length=8192, cpu_threads=8):
    checkpoint = Path(checkpoint).resolve()
    lock = read_json(HERE / "checkpoint-lock.json")
    require(checkpoint.is_dir() and lock["revision"] == REVISION, "Pass the full local Jev Flash v1.2 checkpoint directory")
    require(cpu_threads >= 1 and max_length > 0 and (max_pixels is None or max_pixels >= 65536),
            "Invalid CPU threads, token limit or image pixel limit")
    dev = torch.device(device)
    require(dev.type in ("cpu", "cuda"), "Use cpu or a CUDA device")
    if dev.type == "cuda":
        require(torch.cuda.is_available(), "CUDA unavailable; install the checkpoint's CUDA PyTorch environment")
        torch.cuda.set_device(dev.index if dev.index is not None else 0)
        require(torch.cuda.is_bf16_supported(), "The Jev native CUDA path requires BF16 support")
    print(f"Verifying {lock['repository']} at {REVISION} ...", flush=True)
    for name, wanted in lock["files"].items():
        require(digest(checkpoint / name) == wanted, "Checkpoint file differs from pinned revision: " + name)
    pkg = checkpoint / "source" / "src"
    sys.path.insert(0, str(pkg))
    import pplx_decider
    require(Path(pplx_decider.__file__).resolve().parent == (pkg / "pplx_decider").resolve(),
            "An unrelated pplx_decider was already imported")
    engine = pplx_decider.Decider.from_pretrained(checkpoint, device=str(dev), fast=False,
                                                   max_pixels=max_pixels, max_length=max_length, cpu_threads=cpu_threads)
    require(engine.codes[:2] == ["A", "B"] and engine.fast is None, "Expected the reference A/B decider")
    return engine


def encode(engine, data, entries):
    chunks = []
    for row in entries:
        req = data.request(row)
        sysmsg, user = engine.encoder.messages(req)
        require(sysmsg["content"] == data.protocol["system_prompt"]
                and user["content"] == [{"type": "image"}, {"type": "image"}, {"type": "text", "text": row.prompt}]
                and tuple(req["questions"][QUESTION_ID]["criteria"]) == LABELS, "Prompt drift: " + row.sid)
        (c,) = engine.encoder.plan(req, engine.max_length)
        require(c.keys == (QUESTION_ID,) and c.counts == (2,) and c.markers.numel() == 1
                and c.image_grid_thw is not None and tuple(c.image_grid_thw.shape) == (2, 3)
                and c.pixel_values is not None, "Missing images or binary readout: " + row.sid)
        chunks.append(c)
    return chunks


def raw_logits(engine, chunks):
    """Same marker, noncausal mask hook, left padding and A/B columns as native inference, WITH autograd."""
    from pplx_decider.protocol import left_pad
    inputs = {k: v.to(engine.device) for k, v in left_pad(chunks, engine.encoder.pad_id).items()}
    hidden = engine.backbone(**inputs, use_cache=False).last_hidden_state
    width = inputs["input_ids"].size(1)
    cols = torch.tensor([width - c.length + int(c.markers[0]) for c in chunks], device=engine.device)
    rows = torch.arange(len(chunks), device=engine.device)
    return engine.readout(hidden[rows, cols])[:, :2].float()
