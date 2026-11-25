"""Export actor-visible outputs and public receipts, never private scoring answers."""
from pathlib import Path
import json
from deploy_scale100 import remote

P=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,hashlib,time
p=Path(ROOT);o=p/'gui-output';cfg=json.loads((p/'config.json').read_text())
ledger=json.loads((p/'reuse-ledger.json').read_text())
sources={x['task_id']:Path(x['clean_path']) for x in ledger['completed_natural_trajectories']}
sources.update({int(f.parent.name[1:]):f for f in o.glob('T*/clean')})
rows=[];probes=[];index=[]
for tid,folder in sorted(sources.items()):
    terminal=json.loads((folder/'terminal.json').read_text()) if (folder/'terminal.json').exists() else None
    index.append(dict(task_id=tid,source=str(folder),terminal=terminal,reused=not str(folder).startswith(ROOT+'/')))
    for f in sorted(folder.glob('*-response.json')):
        step=int(f.name[:3]);v=json.loads(f.read_text());a=folder/f'{step:03}-action.json';manifest=folder/f'{step:03}-input-manifest.json'
        rows.append(dict(task_id=tid,step=step,input_tokens=v['input_tokens'],visual_tokens=v['visual_tokens'],non_image_token_count=v['non_image_token_count'],output_tokens=v['output_tokens'],text=v['text'],natural_EOS=v['natural_EOS'],receipt=v['receipt'],response_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),action=json.loads(a.read_text())['payload'] if a.exists() else None,input_manifest=json.loads(manifest.read_text()) if manifest.exists() else None))
    for f in sorted(folder.glob('checkpoint-*/checkpoint.json')):
        cp=f.parent;c=json.loads(f.read_text())
        for decision in sorted(cp.glob('*-decision.json')):
            v=json.loads(decision.read_text());probes.append(dict(task_id=tid,step=c['step'],bin=c['bin'],normal_input_tokens=c['normal_input']['input_tokens'],condition=decision.name.replace('-decision.json',''),delivered_input_tokens=v['input_tokens'],text=v['text'],parsed_action=v.get('parsed_action'),parse_error=v.get('parse_error'),receipt=v['receipt'],state_drift=(cp/'original-state-drift.json').exists(),semantic_label='pending_audit'))
print(json.dumps(dict(export_time=time.time(),planned_unique=100,completed_unique=sum(x['terminal'] is not None for x in index),index=index,normal_steps=rows,initial_probes=probes)))
'''
if __name__=='__main__':
    d=remote('4090',code,timeout=90);out=P/'results';out.mkdir(exist_ok=True)
    for name,key in [('normal-steps.jsonl','normal_steps'),('initial-probes.jsonl','initial_probes')]:
        (out/name).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in d[key]),encoding='utf8')
    (out/'trajectory-index.json').write_text(json.dumps({k:v for k,v in d.items() if k not in ['normal_steps','initial_probes']},ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(completed_unique=d['completed_unique'],normal_steps=len(d['normal_steps']),initial_probes=len(d['initial_probes']),local_directory=str(out))))
