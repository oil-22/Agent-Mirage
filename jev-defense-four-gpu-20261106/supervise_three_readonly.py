"""Current-turn60-second read-only supervision; no health, POST or run changes."""
import hashlib,json,subprocess,sys,time
from pathlib import Path
# Linked root script retains the parent's read-only monitoring logic.
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'supervision-evidence'/str(time.time_ns());OUT.mkdir(parents=True,exist_ok=False)
COMMAND=[sys.executable,'-B',str(ROOT/'inspect_gui_progress.py'),'--service-group','/home/researcher/jev-defense-four-gpu-20261106/online-three-service-group-1793985778592347799',
    '--batch-root','/data/researcher/jev-defense-four-gpu-20261106/gui-batch-image-observer-three-01',
    '--control-root','/data/researcher/jev-defense-four-gpu-20261106/gui-outer-control-three-01',
    '--background-root','/data/researcher/jev-defense-four-gpu-20261106/gui-outer-background-three-01']
seen=set();previous='0'*64;seq=0


def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def record(value):
    global previous,seq
    body={'seq':seq,'previous':previous,'time':time.time(),**value};digest=hashlib.sha256(canonical(body)).hexdigest()
    with(OUT/'supervision.jsonl').open('ab')as handle:handle.write(canonical({**body,'sha256':digest})+b'\n')
    previous=digest;seq+=1
def report(value):print(json.dumps(value,ensure_ascii=False),flush=True)


report({'stage':'read_only_monitor_started','local_root':str(OUT),'interval_seconds':60,
    'new_model_GUI_health_or_POST_requests':0})
time.sleep(60)
while True:
    started=time.monotonic()
    run=subprocess.run(COMMAND,capture_output=True,text=True,timeout=120)
    if run.returncode:
        record({'stage':'inspection_process_failure','exit_code':run.returncode,
            'stderr':run.stderr,'stdout':run.stdout,'new_model_GUI_health_or_POST_requests':0})
        report({'stage':'inspection_process_failure','local_root':str(OUT),'automatic_model_or_GUI_retry':False});break
    brief=json.loads(run.stdout);receipt=Path(brief['receipt']);raw=receipt.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==brief['sha256']
    data=json.loads(raw);errors=[]
    for host,row in data['results'].items():
        if row.get('inspection_failed'):errors.append({'host':host,'error':row.get('error')})
    if errors:
        record({'stage':'inspection_failed','receipt':str(receipt),'receipt_sha256':brief['sha256'],'errors':errors})
        report({'stage':'inspection_failed','receipt':str(receipt),'receipt_sha256':brief['sha256'],'errors':errors});break
    service=data['results']['3090']['evidence'];controller=data['results']['4090']['evidence']
    state=service['state_snapshot'];chains=controller['eventchains']
    counts={role:row['request_counts']for role,row in service['workers'].items()}
    snapshot={'stage':'snapshot','receipt':str(receipt),'receipt_sha256':brief['sha256'],
        'service_state':state,'actual_request_counts':counts,
        'service_journal_chain_head':service['journal']['chain_head'],
        'service_journal_event_count':service['journal']['event_count'],
        'controller_chains':[{'path':row['path'],'event_count':row['event_count'],
            'chain_head':row['chain_head'],'terminal':row.get('terminal')}for row in chains],
        'failure_markers':controller['failure_markers'],
        'outer_postexit_seal_present':controller['outer_postexit_seal_present'],
        'new_model_GUI_health_or_POST_requests':0,'semantic_labels_inferred':False}
    record(snapshot)
    for row in chains:
        if row.get('terminal') and row['path']not in seen:
            seen.add(row['path'])
            report({'stage':'new_trajectory_terminal','receipt':str(receipt),'receipt_sha256':brief['sha256'],
                'terminal':row['terminal'],'controller_chain':{'path':row['path'],'head':row['chain_head'],
                    'event_count':row['event_count']},'actual_request_counts':counts,'semantic_labels_inferred':False})
    danger=service['foreign_target_compute']or controller['failure_markers']or service['launcher_failure_present']or\
        not service['all_actual_peer_identities_valid']or any(v['failed']for v in counts.values())
    if danger:
        report({'stage':'failure_or_resource_conflict','receipt':str(receipt),'receipt_sha256':brief['sha256'],
            'foreign_target_compute':service['foreign_target_compute'],'failure_markers':controller['failure_markers'],
            'actual_request_counts':counts,'automatic_stop_or_restart_performed':False});break
    if state['phase']in('terminal_failure',):
        report({'stage':'service_terminal_failure','receipt':str(receipt),'receipt_sha256':brief['sha256'],
            'state':state,'automatic_retry_performed':False});break
    if len(chains)==3 and all(row.get('terminal',{}).get('filename')=='complete.json'for row in chains)and\
        state['phase']=='complete'and state['active']is None and controller['outer_postexit_seal_present']:
        report({'stage':'all_three_actual_terminals_and_outer_postexit_present','receipt':str(receipt),
            'receipt_sha256':brief['sha256'],'actual_request_counts':counts,'semantic_labels_inferred':False,
            'service_stop_not_performed':True});break
    time.sleep(max(1,60-(time.monotonic()-started)))
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in OUT.iterdir()if p.is_file()}
with(OUT/'seal.json').open('x',encoding='utf8')as handle:json.dump(manifest,handle,indent=2)
