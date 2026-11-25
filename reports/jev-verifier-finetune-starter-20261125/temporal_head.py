"""Offline head tuning for the project's native two-frame Flash request."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
REPORTS = HERE.parent
PROMPT = REPORTS / 'jev-temporal-gate-20261122' / 'temporal_request.py'
PROMPT_SHA = 'dc6bcbc9c26f86fad259c3d8a3909648766c16c5bacd955292f3848c2214bbcd'
REV = '9ff7cf9838e59df461c276b7699d56b244d2af58'
RECEIPT = REPORTS.parent / 'jev-defense-four-gpu-20261106/flash-preparation/remote-evidence/download-complete-receipt.json'
REGRESSION = REPORTS / 'jev-verifier-finetune-20261122/known-regression-reference.json'
HISTORY = HERE / 'examples.regression.jsonl'
SPLITS = ('train', 'val', 'test', 'regression')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]


require(sha(PROMPT) == PROMPT_SHA, 'The temporal request builder changed.')
sys.path.insert(0, str(PROMPT.parent))
from temporal_request import action_json, native_request, png_size, QUESTION_ID


def heldout_images():
    data = json.loads(REGRESSION.read_bytes())
    seen = {s for row in data['offline']['requests'] for s in row['ordered_image_sha256']}
    for row in data['live']['unique_input_groups']:
        seen.update(row['binding'][k] for k in ('previous_image_sha256', 'candidate_image_sha256'))
    seen.update(row[k] for row in jsonl(HISTORY) for k in ('before_sha256', 'candidate_sha256'))
    return seen


def read_manifest(path, check_images=False):
    seen_images, by_group, ids, keys = heldout_images(), {}, set(), set()
    rows = jsonl(path)
    require(rows, 'Empty manifest')
    for row in rows:
        sid, split, label = row['sample_id'], row['split'], row['label']
        require(isinstance(sid, str) and sid.strip() and sid not in ids and split in SPLITS, f'Bad ID or split: {sid}')
        ids.add(sid)
        require(label in ('YES', 'NO', None) and (label is None or row['receipt_valid'] is True),
                f'{sid}: supervised rows require a reviewed label and valid receipt')
        require(row['phase'] in ('early', 'settled', 'unrelated', 'no_change', 'unknown'), f'{sid}: bad phase')
        require(all(isinstance(row[k], str) and row[k].strip() for k in
                    ('family_id', 'task_id', 'trajectory_id', 'event_id', 'capture_id', 'reason')),
                f'{sid}: missing grouping or audit metadata')
        pair = row['before_sha256'], row['candidate_sha256']
        require(all(isinstance(s, str) and len(s) == 64 and all(c in '0123456789abcdef' for c in s) for s in pair),
                f'{sid}: invalid image digest')
        require(split == 'regression' or seen_images.isdisjoint(pair), f'{sid}: known regression image')
        key = (*pair, action_json(row['action']))
        require(key not in keys, f'{sid}: duplicate before/action/after; keep repeated observations in the source log')
        keys.add(key)
        groups = [(k, row[k]) for k in ('family_id', 'task_id', 'trajectory_id', 'event_id', 'capture_id')]
        for group in groups + [('image', s) for s in pair]:
            require(by_group.setdefault(group, split) == split, f'{sid}: {group} crosses splits')
        if check_images:
            a, b = image_bytes(path, row)
            require(png_size(a) == png_size(b), f'{sid}: screenshot sizes differ')
    return rows


def image_bytes(manifest, row):
    out = []
    for key in ('before', 'candidate'):
        raw = (manifest.parent / row[key + '_png']).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == row[key + '_sha256'], f"{row['sample_id']}: {key} SHA mismatch")
        out.append(raw)
    return out


def load_engine(folder):
    require(folder.is_dir(), 'Provide the local Flash checkpoint directory.')
    require(sha(RECEIPT) == '6a579d4d91d3b0a2590ecdb54081804ce1a13415607bd87b3efdc5a939cf5f2b', 'Checkpoint receipt changed')
    receipt = json.loads(RECEIPT.read_bytes())
    require(receipt['revision'] == REV, 'Wrong receipt revision')
    for artifact in receipt['files']:
        require(sha(folder / artifact['file']) == artifact['sha256'], f"Wrong checkpoint file: {artifact['file']}")
    sys.path.insert(0, str(folder / 'source/src'))
    from pplx_decider import Decider
    return Decider.from_pretrained(folder.resolve(), device='cuda:0', fast=False)


def features(engine, manifest, rows):
    # The native reference path calls readout(hidden[rows, marker_cols]) once.
    # Capture its exact input; the two logits are from that very same forward.
    h, m = [], []
    handle = engine.readout.register_forward_pre_hook(
        lambda _module, args: h.append(args[0].detach().float().cpu().numpy().copy()))
    try:
        for i, row in enumerate(rows):
            before, cur = image_bytes(manifest, row)
            req = native_request(before, row['action'], cur)
            require(tuple(req['questions'][QUESTION_ID]['criteria']) == ('YES', 'NO'), 'Option order changed')
            logits, = engine.logits([req])
            yes, no = logits[QUESTION_ID]
            require(len(h) == i + 1 and h[-1].shape == (1, engine.readout.in_features), 'Unexpected marker layout')
            m.append((yes - no) / engine.temperature)
    finally:
        handle.remove()
    x, m = np.concatenate(h), np.array(m, dtype=np.float64)
    require(np.isfinite(x).all() and np.isfinite(m).all(), 'Non-finite native features')
    return x, m


def labels(rows):
    return np.array([r['label'] == 'YES' for r in rows]), np.array([r['phase'] == 'early' for r in rows])


def fit_delta(x, m, rows, l2):
    # Equal total training weight per action event. All changes start at zero.
    count = Counter(r['event_id'] for r in rows)
    wt = np.array([1.0 / (len(count) * count[r['event_id']]) for r in rows])
    y, _ = labels(rows)
    scale = max(float(np.sqrt(wt @ np.einsum('ij,ij->i', x, x))), 1e-8)
    h = x.astype(np.float64) / scale
    delta = np.zeros(h.shape[1])
    # Upper bound on the Hessian norm of weighted logistic loss + L2.
    L = 0.25 * (wt @ np.einsum('ij,ij->i', h, h)) + l2
    for _ in range(500):
        p = np.exp(-np.logaddexp(0, -(m + h @ delta)))
        grad = h.T @ (wt * (p - y)) + l2 * delta
        if np.linalg.norm(grad) < 1e-7:
            break
        delta -= grad / L
    return delta / scale


def measures(scores, threshold, rows):
    y, early = labels(rows)
    passed = np.asarray(scores, dtype=np.float64) >= threshold
    def counts(event, subset):
        return [int(np.sum(event & subset)), int(np.sum(subset))]
    return {'false_pass_early': counts(passed, ~y & early), 'false_pass_other_no': counts(passed, ~y & ~early),
            'false_hold_yes': counts(~passed, y)}


def pick_threshold(scores, rows, limits):
    scores = np.asarray(scores, dtype=np.float64)
    candidates = np.unique(np.r_[0., scores, np.nextafter(scores.max(), np.inf)])
    feasible = []
    for t in candidates:
        m = measures(scores, t, rows)
        e, o, h = (v[0] for v in m.values())
        if e <= limits['false_pass_early'][0] and o <= limits['false_pass_other_no'][0]:
            feasible.append((h, e + o, abs(t), t))
    return float(min(feasible)[-1])


def comparison(rows, m, x, head):
    return {'native': measures(m, 0., rows),
            'threshold_only': measures(m, head['native_threshold'], rows),
            'new_head': measures(m + x @ np.asarray(head['delta']), head['threshold'], rows)}


def subset(rows, split):
    selected = [r for r in rows if r['split'] == split and r['label'] is not None]
    require({r['label'] for r in selected} == {'YES', 'NO'}, f'{split}: need new reviewed examples of both classes')
    return selected


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    for cmd in ('check', 'fit', 'test'):
        p = sub.add_parser(cmd)
        p.add_argument('manifest', type=Path)
        if cmd != 'check':
            p.add_argument('--checkpoint', type=Path, required=True)
            p.add_argument('--head', type=Path, required=True, help='new output for fit; frozen input for test')
        if cmd == 'fit':
            p.add_argument('--l2', type=float, default=0.01)
    a = ap.parse_args()
    rows = read_manifest(a.manifest, check_images=a.cmd == 'check')
    if a.cmd == 'check':
        for s in SPLITS:
            group = [r for r in rows if r['split'] == s]
            if group:
                print(s, 'events:', len({r['event_id'] for r in group}), 'labels:', dict(Counter(r['label'] for r in group)))
        return
    meta = {'revision': REV, 'prompt_sha256': PROMPT_SHA, 'manifest_sha256': sha(a.manifest), 'options': ['YES', 'NO']}
    if a.cmd == 'fit':
        train, val = subset(rows, 'train'), subset(rows, 'val')
        require(np.isfinite(a.l2) and a.l2 > 0 and not a.head.exists(), 'Need positive L2 and a new head output path')
        require(all(v[1] for v in measures(np.zeros(len(val)), 0., val).values()),
                'Validation needs visible YES, real early NO and other NO controls')
        engine = load_engine(a.checkpoint)
        x, m = features(engine, a.manifest, train)
        delta = fit_delta(x, m, train, a.l2)
        x, m = features(engine, a.manifest, val)
        limits = measures(m, 0., val)
        head = dict(meta, l2=a.l2, delta=delta.tolist(), native_threshold=pick_threshold(m, val, limits),
                    threshold=pick_threshold(m + x @ delta, val, limits))
        result = head['validation_counts'] = comparison(val, m, x, head)
        with a.head.open('x', encoding='utf-8') as f:
            json.dump(head, f, allow_nan=False)
    else:
        head = json.loads(a.head.read_bytes())
        require(all(head[k] == v for k, v in meta.items()), 'Head, manifest and native protocol must match')
        test = subset(rows, 'test')
        x, m = features(load_engine(a.checkpoint), a.manifest, test)
        result = comparison(test, m, x, head)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
