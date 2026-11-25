"""Reproduce the benchmark, attention contrasts and observation-level defense rates."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from statistics import median

DATA = Path(__file__).resolve().parent / "data"


def read(name):
    return json.loads((DATA / (name + ".json")).read_text(encoding="utf-8"))


def pct(k, n):
    return None if n == 0 else 100 * k / n


def benchmark():
    groups = defaultdict(list)
    for row in read("benchmark"):
        for dimension in ("condition", "platform", "model"):
            groups[f"{dimension}: {row[dimension]}"].append(row)
        groups["all"].append(row)
    result = {}
    for label, rows in groups.items():
        n = sum(r["n"] for r in rows)
        result[label] = {"runs": n, **{k + "_pct": pct(sum(r[k] for r in rows), n)
                         for k in ("flags", "failures", "repair_flags", "repair_failures")}}
    return result


def attention():
    import numpy as np
    rows = read("attention")
    index = {(r["model"], r["task"], r["stage"], r["history"], r["condition"]): r for r in rows}
    if len(index) != len(rows):
        raise ValueError("Duplicate task/position/condition")
    tasks = sorted({r["task"] for r in rows})
    def metric(r, name):
        if name == "first_image":
            return r["image"]
        return (r["history_prose"] + r["history_action"]) / (1-r["image"])
    result = {}
    for model in sorted({r["model"] for r in rows}):
        for history in ("last2", "full"):
            for cond in ("silent_drop", "blank_replace", "stale_replace", "buttons_only"):
                for name in ("first_image", "first_history_nonimage"):
                    vals = {}
                    for t in tasks:
                        diffs = []
                        for s in ("early", "middle", "late"):
                            stem = (model, t, s, history)
                            diffs.append(metric(index[stem+(cond,)], name)-metric(index[stem+("current_control",)], name))
                        vals[t] = float(np.mean(diffs))
                    seed = int(hashlib.sha256(json.dumps(vals, sort_keys=True).encode()).hexdigest()[:8], 16)
                    arr = np.array(list(vals.values()))
                    rng = np.random.default_rng(seed)
                    draws = arr[rng.integers(0,len(arr),(10000,len(arr)))].mean(1)
                    q = np.quantile(draws,[.025,.975])
                    result["/".join((model,history,cond,name))] = {
                        "tasks":len(arr), "delta_pp":float(arr.mean()*100), "ci95_pp":(q*100).tolist()}
    return result


def defense():
    rows, pairs, controls = (read(n) for n in ("full_task_exposures","temporal_pairs","temporal_normal_controls"))
    result = {}
    for condition in ["all", *sorted({r["condition"] for r in rows})]:
        for arm in ("off", "on"):
            selected = [r for r in rows if (condition=="all" or r["condition"]==condition) and r["arm"]==arm]
            n = len(selected)
            result[f"full/{condition}/{arm}"] = {
                "exposed": n, "bad_forward_pct":pct(sum(r["bad_forward"] for r in selected), n),
                "withheld_by_gate_pct":pct(sum(r["rejection_stage"] is not None for r in selected), n),
                "usable_same_decision_forward_pct":pct(sum(r["recovery_forward"] for r in selected), n)}
    confirmed = [r for r in pairs if r["both_first_early_confirmed"]]
    recovered = [r for r in confirmed if r["defense_loop_recovered"]]
    ready = [r for r in controls if r["first_truth"] in ("ready","boundary")]
    result["temporal"] = {
        "assigned_delayed_pairs":len(pairs), "confirmed_pairs":len(confirmed),
        "original_bad_delivery_pct":pct(sum(r["original_fault_delivery"] for r in confirmed),len(confirmed)),
        "temporal_bad_delivery_pct":pct(sum(r["defense_fault_delivery"] for r in confirmed),len(confirmed)),
        "recovered_among_confirmed_pct":pct(len(recovered),len(confirmed)),
        "confirmed_recovery_among_assigned_pct":pct(len(recovered),len(pairs)),
        "false_first_hold_on_usable_controls_pct":pct(sum(r["first_ready_false_hold"] for r in ready),len(ready)),
        "extra_time_recovered_median_s":median(r["gate_seconds_defense"]-r["gate_seconds_original"] for r in recovered)}
    return result


if __name__ == "__main__":
    studies = {"benchmark":benchmark, "attention":attention, "defense":defense}
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("study", choices=[*studies, "all"], default="all", nargs="?")
    opt = p.parse_args().study
    print(json.dumps({k:f() for k,f in studies.items() if opt in ("all",k)},indent=2,allow_nan=False))
