"""Read local exported request proofs; never invoke models or experiment runners."""
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

BASE = Path(r'D:\MultiModel\jev-defense-four-gpu-20261106')
OUT = Path(__file__).resolve().parent

def quantile(xs, p):
    xs = sorted(xs)
    a = (len(xs)-1)*p
    i = int(a)
    return xs[i] + (xs[min(i+1, len(xs)-1)]-xs[i])*(a-i)

def stats(xs):
    return dict(n=len(xs), min=min(xs), median=statistics.median(xs),
                mean=statistics.mean(xs), p25=quantile(xs,.25), p75=quantile(xs,.75),
                p90=quantile(xs,.9), p95=quantile(xs,.95), max=max(xs), sum=sum(xs))

records = {}
duplicates = 0
conflicts = []
sources = sorted(BASE.rglob('request-results.json'))
for p in sources:
    data = json.loads(p.read_text(encoding='utf-8-sig'))
    for role, rows in data.items():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('input_tokens'), int):
                continue
            identity = row.get('folder') or row.get('root') or row.get('request_id')
            key = (role, identity)
            r = {k: row.get(k) for k in ['request_id', 'run_id', 'decision', 'input_tokens',
                 'output_tokens', 'history_messages', 'exact_full_history_preserved',
                 'actual_tensor_files_verified']}
            r.update(role=role, campaign=p.relative_to(BASE).parts[0], source=str(p),
                     remote_folder=identity, retained_image_count=len(row.get('all_image_sha256s', [])))
            if key in records:
                duplicates += 1
                if records[key]['input_tokens'] != r['input_tokens']:
                    conflicts.append(identity)
            records[key] = r
rows = list(records.values())
primary = [r for r in rows if r['role'] == 'primary']
runs = defaultdict(list)
for r in primary:
    runs[(r['campaign'], r['run_id'])].append(r)
run_rows = []
for (campaign, run_id), rs in sorted(runs.items()):
    rs.sort(key=lambda r: r['decision'])
    run_rows.append(dict(campaign=campaign, run_id=run_id, calls=len(rs),
        first_input=rs[0]['input_tokens'], max_input=max(r['input_tokens'] for r in rs),
        cumulative_input=sum(r['input_tokens'] for r in rs),
        cumulative_output=sum(r['output_tokens'] or 0 for r in rs),
        max_retained_images=max(r['retained_image_count'] for r in rs),
        max_history_messages=max(r['history_messages'] or 0 for r in rs)))
edges = [0, 1000, 2000, 5000, 10000, 20000, 30000, 50000, float('inf')]
hist = [{'lower':a, 'upper':b if b != float('inf') else None,
         'calls':sum(a <= r['input_tokens'] < b for r in primary)} for a,b in zip(edges,edges[1:])]
coverage = []
for target in [1000,2000,5000,10000,20000,30000,40000,50000]:
    coverage.append(dict(target=target,
        runs_reaching=sum(r['max_input']>=target for r in run_rows),
        runs_within_10_percent=sum(any(abs(r['input_tokens']-target)<=.1*target for r in rs) for rs in runs.values())))
campaigns = {}
for campaign in sorted(set(r['campaign'] for r in primary)):
    rs=[r for r in primary if r['campaign']==campaign]
    campaigns[campaign]=dict(runs=len(set(r['run_id'] for r in rs)), input=stats([r['input_tokens'] for r in rs]))
summary = dict(scope='Local Nov15-17 defense trajectory audit exports; primary model path Qwen3.8-27B. Not the complete 11-model benchmark.',
    count_source='Actual generate input_ids.shape[-1], multimodal full input, not history-only tokens.',
    source_files=len(sources), duplicate_rows=duplicates, conflicts=conflicts,
    primary_delivered=stats([r['input_tokens'] for r in primary]),
    primary_output=stats([r['output_tokens'] for r in primary]),
    trajectories=len(run_rows), per_trajectory_input=stats([r['cumulative_input'] for r in run_rows]),
    per_trajectory_output=stats([r['cumulative_output'] for r in run_rows]),
    per_trajectory_calls=stats([r['calls'] for r in run_rows]),
    input_histogram=hist, threshold_coverage=coverage, campaigns=campaigns,
    undelivered=[r for r in rows if r['role']=='undelivered'],
    auxiliary_input=stats([r['input_tokens'] for r in rows if r['role']=='Flash']),
    all_primary_full_history_verified=all(r['exact_full_history_preserved'] is True for r in primary),
    all_primary_tensor_files_verified=all(r['actual_tensor_files_verified'] is True for r in primary))
OUT.mkdir(exist_ok=True, parents=True)
(OUT/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
for name, data in [('requests.csv',rows),('trajectories.csv',run_rows)]:
    with (OUT/name).open('w', encoding='utf-8-sig', newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
print(json.dumps(summary, ensure_ascii=True, indent=2))
print('LONGEST_RUNS', json.dumps(sorted(run_rows,key=lambda r:r['max_input'],reverse=True)[:6]))
