"""Rebuild the final index from already completed external tail artifacts."""
import json,pathlib,shutil
root=pathlib.Path('/home/researcher/attention-20261031');folder=root/'glm';status=json.loads((folder/'status.json').read_text())
assert status['phase']=='finished' and status['completed']==324 and status['failed']==0
plan=json.loads((root/'campaign/plan.json').read_text());old=json.loads((folder/'results.json').read_text());rows=[]
for case in plan['cases']:
    p=folder/case['id']/'result.json';r=json.loads(p.read_text());assert r['status']=='completed' and r['id']==case['id'];rows.append(r)
assert len({r['id'] for r in rows})==324
if [r['id'] for r in old]!=[r['id'] for r in rows]:
    shutil.copyfile(folder/'results.json',folder/'results-before-tail-reconciliation.json')
    temp=folder/'results.json.tmp';temp.write_text(json.dumps(rows,ensure_ascii=False,indent=2));temp.replace(folder/'results.json')
(root/'glm-tail-reconciliation.json').write_text(json.dumps({'before_index_rows':len(old),'after_index_rows':len(rows),'all_saved_case_results_completed':True,'new_inference_calls':0,'reason':'The sequential runner skipped published tail artifacts without rewriting its global index on trailing cached cases; rebuild index from existing canonical case files.'},indent=2))
print('reconciled',len(old),'->',len(rows))
