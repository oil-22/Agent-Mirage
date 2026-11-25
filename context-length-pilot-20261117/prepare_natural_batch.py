"""Freeze the next unused task batch without modifying the completed pilot."""
from pathlib import Path
import json,shutil,secrets,hashlib,ast
from datetime import datetime,timezone,timedelta

SRC=Path(r'D:\MultiModel\context-length-pilot-20261117\quant-nf4-02')
DST=Path(r'D:\MultiModel\context-length-natural-20261117\batch01')
DST.mkdir(parents=True,exist_ok=False)
for name in ['actor-template.json','native_environment.py','native-bindings-public.json','native-parser-source.py','tasks.json']:
    shutil.copy2(SRC/name,DST/name)
cfg=json.loads((SRC/'config.json').read_text(encoding='utf8'))
cfg.update(task_ids=[3,58,94,112,131],stage='natural context-length stratification; all clean trajectories and probes before branch continuations',
    attempt='natural-batch01',prior_attempt='completed quant-nf4-02 pilot preserved separately',capacity_probe_before_gui=False,
    capacity_evidence='prior same-model NF4 setup completed a 52,134-token continuation; this is not a natural 40k checkpoint',
    max_model_calls=6000,service_port=19318,history_policy='all actually retained text and images; no padding, duplication, trimming, or forcing continuation after model stop',
    checkpoint_policy='first actual normal input inside each configured window; semantic eligibility audited separately',
    schedule='all clean trajectories with isolated probes, then all independent matched-prefix continuation branches',
    task_selection='all five previously preselected read-only tasks not run in the completed NF4 pilot; fixed ascending ID order',
    selected_at=datetime.now(timezone(timedelta(hours=8))).isoformat())
(DST/'config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
(DST/'service.token').write_text(secrets.token_hex(32),encoding='ascii')
service=(SRC/'model_service.py').read_text(encoding='utf8').replace("ThreadingHTTPServer(('192.0.2.11',19317),Handler)","ThreadingHTTPServer(('192.0.2.11',config['service_port']),Handler)")
service=service.replace("url='http://192.0.2.11:19317'","url='http://192.0.2.11:'+str(config['service_port'])")
assert '19317' not in service
(DST/'model_service.py').write_text(service,encoding='utf8')
runner=(SRC/'run_pilot.py').read_text(encoding='utf8')
runner=runner.replace("URL='http://192.0.2.11:19317'","URL='http://192.0.2.11:'+str(CFG['service_port'])")
runner=runner.replace("if CALLS>=2000:raise RuntimeError('Pilot call budget reached')","if CALLS>=CFG['max_model_calls']:raise RuntimeError('Natural batch call budget reached')")
runner=runner.replace("        for tid in CFG['task_ids']:\n", "        continuation_queue=[]\n        for tid in CFG['task_ids']:\n")
old="""            checkpoints=collect_clean(task,private,private.parent/'clean')
            for cp in checkpoints:
                for condition in CFG['conditions'][1:]:
                    continue_branch(task,private,cp,condition,private.parent/'branches'/cp.name/condition)
        state(phase='completed',semantic_labels='pending_audit')"""
new="""            checkpoints=collect_clean(task,private,private.parent/'clean')
            for cp in checkpoints:
                for condition in CFG['conditions'][1:]:
                    continuation_queue.append(dict(task_id=tid,private=str(private),checkpoint=str(cp),condition=condition,
                        folder=str(private.parent/'branches'/cp.name/condition)))
            save(R/'continuation-queue.json',continuation_queue)
        save(R/'initial-phase-completed.json',dict(time=time.time(),model_calls=CALLS,task_ids=CFG['task_ids'],
            planned_continuations=len(continuation_queue),history_policy=CFG['history_policy'],semantic_labels='pending_audit'))
        for job in continuation_queue:
            continue_branch(tasks[job['task_id']],Path(job['private']),Path(job['checkpoint']),job['condition'],Path(job['folder']))
        state(phase='completed',semantic_labels='pending_audit')"""
assert old in runner
runner=runner.replace(old,new)
assert runner.count('continuation_queue=[]')==1
assert '19317' not in runner
(DST/'run_natural.py').write_text(runner,encoding='utf8')
for name in ['model_service.py','run_natural.py','native_environment.py']:
    ast.parse((DST/name).read_text(encoding='utf8'),filename=name)
tasks={r['task_id']:r for r in json.loads((DST/'tasks.json').read_text(encoding='utf8'))}
bindings={r['task_id']:r for r in json.loads((DST/'native-bindings-public.json').read_text(encoding='utf8'))['tasks']}
for tid in cfg['task_ids']:
    assert bindings[tid]['eligible'] and not tasks[tid]['require_reset'] and not tasks[tid]['image']
plan=dict(task_ids=cfg['task_ids'],tasks=[tasks[tid] for tid in cfg['task_ids']],bins=cfg['bins'],tolerance=cfg['tolerance'],
    normal_prefix='untouched natural trajectory; independent injected branches do not feed back into the clean trajectory',
    outcomes_not_used_for_task_selection=True,no_history_retention_diagnostic_in_this_batch=True,
    semantic_eligibility='pending independent review; typing/focus checkpoints are not automatically negative or positive',
    covered_windows_not_guaranteed=True,created_at=cfg['selected_at'])
(DST/'prospective-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
manifest={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(DST.iterdir()) if f.is_file() and f.name!='service.token'}
(DST/'source-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print(json.dumps({'directory':str(DST),'task_ids':cfg['task_ids'],'bins':cfg['bins'],'syntax_checked':True,'plan_sha256':manifest['prospective-plan.json']}))
