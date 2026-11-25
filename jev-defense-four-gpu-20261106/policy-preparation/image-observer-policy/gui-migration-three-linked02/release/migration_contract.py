"""Exact typed three-run suffix and fixed historical unspent-source evidence."""
import hashlib,json
from pathlib import Path

ORIGINAL_PLAN_SHA='a6e248f730408ab9c5bbaeb72bfa0d392ecf99f247159495273d2b3f5616ef8e'
ORIGINAL_STATE_SHA='967bf98cbb5230a0a87d8151903ea725b8fc355ce3ca7ffda881468d62d26ae9'
ORIGINAL_JOURNAL_SHA='195105c64bbd82d16a7bf4e8209f5bfbee6ea1168fef6c81dfba626691ba1181'
POSTEXIT_RECEIPT_SHA='6cc5f640a3abd9bdeb53a990db14a5386107517846c82933b188e99e83013d36'
STRUCTURAL_RECEIPT_SHA='8017f765b7c68d4014cc848a098769b6348f206a81d8aeb69ca58ab18558e127'
OLD_BATCH_MANIFEST_SHA='826f1bde479c12cb8a63ffdf8fa52af3e085d37a6e188d97489bfdfcf10c88f6'
EXPECTED=[('clean',True),('stale_replace',False),('stale_replace',True)]

def canonical(obj):return json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise RuntimeError(message)
def bound(item,expected=None):
    p=Path(item['path']);require(not p.is_symlink(),'Bound evidence may not be a symlink')
    require(expected is None or item['sha256']==expected,'Unexpected source evidence identity')
    require(sha(p)==item['sha256'],'Bound source bytes changed')
    return json.loads(p.read_bytes())
def original_plan():
    p=Path(__file__).with_name('frozen-original-plan.json')
    require(sha(p)==ORIGINAL_PLAN_SHA,'Original plan bytes differ')
    return json.loads(p.read_bytes())
def validate_three_plan(plan):
    original=original_plan();expected=json.loads(json.dumps(original))
    expected['queue']=expected['queue'][1:];expected['stage']='source_CPU_preparation_launch_not_ready'
    require(canonical(plan)==canonical(expected),'Only the exact untouched original suffix/stage is admitted')
    require([(r['condition'],r['observer_enabled'])for r in plan['queue']]==EXPECTED,'Three-run order differs')
    require(len({r['run_id']for r in plan['queue']})==3,'Duplicate migrated IDs')
    return plan['queue']
def validate_original_state(state):
    original=original_plan();queue=original['queue']
    require(state['phase']=='terminal_failure'and state['active']is None and type(state['next_run_index'])is int and state['next_run_index']==1,'Parent not exact first-run terminal')
    require(set(state['runs'])=={r['run_id']for r in queue},'Parent run inventory differs')
    baseline={'status':'technical_failure','last_decision_index':15,'calls':{'actor':16,'judge':57,'observe':0}}
    require(canonical(state['runs'][queue[0]['run_id']])==canonical(baseline),'Failed baseline may not reset')
    for run in queue[1:]:
        zero={'status':'not_started','last_decision_index':0,'calls':{'actor':0,'judge':0,'observe':0}}
        require(canonical(state['runs'][run['run_id']])==canonical(zero),'Migrated run was started or spent')
def validate_migration_source(proof):
    require(proof.get('classification')=='exact_original_unstarted_suffix_new_three_run_group','Migration classification differs')
    state=bound(proof['original_state'],ORIGINAL_STATE_SHA);validate_original_state(state)
    post=bound(proof['independent_postexit'],POSTEXIT_RECEIPT_SHA)
    require(post['original_exit_json_missing']is True and post['original_terminal_sha256_missing']is True and
        post['worker_exit_codes']=={'primary':None,'pplx_flash':None} and post['actual_holder_launcher_return']['exit_code']==1,
        'Original stop failure metadata must remain explicit')
    audit=bound(proof['original_structural_audit'],STRUCTURAL_RECEIPT_SHA)
    result=audit['audit_result']
    require(result['integrity_audit_passed']is True and result['all_four_trajectories_complete']is False,'Actual old structural audit missing')
    require(len(result['runs'])==4 and all(r.get('status')=='not_attempted'for r in result['runs'][1:]),'Migrated old GUI attempted a run')
    journal=Path(proof['original_journal']['path'])
    require(proof['original_journal']['sha256']==ORIGINAL_JOURNAL_SHA and sha(journal)==ORIGINAL_JOURNAL_SHA,'Original service journal differs')
    previous=None;rows=[]
    for index,line in enumerate(journal.read_bytes().splitlines()):
        row=json.loads(line);body={k:v for k,v in row.items()if k!='sha256'}
        require(row['index']==index and row['previous_sha256']==previous and
            row['sha256']==hashlib.sha256(canonical(body)).hexdigest(),'Original service chain invalid')
        rows.append(row);previous=row['sha256']
    require(len(rows)==150 and previous=='933c224f05a79e180181a4dd9e9e80d616226b08697e3d02e74b06c87f48aaf0','Wrong original service chain')
    old=original_plan();baseline=old['queue'][0]['run_id'];migrated={r['run_id']for r in old['queue'][1:]}
    for row in rows:
        require(row['payload'].get('trajectory_id')not in migrated,'Migrated source has a real service begin or inference')
        if row['event']=='model_request_started':
            require(row['payload']['trajectory_id']==baseline,'Unexpected source model trajectory')
        elif row['event']=='trajectory_transition':
            matches=[p for p in (journal.parent/'transitions').iterdir()if p.is_dir()and
                sha(p/'request.json')==row['payload']['external_wire_sha256']]
            require(len(matches)==1,'Lifecycle source request must match exactly one actual transition')
            receipt=matches[0]
            raw=(receipt/'request.json').read_bytes()
            require(hashlib.sha256(raw).hexdigest()==row['payload']['external_wire_sha256'],'Lifecycle source request wire differs')
            require(canonical(json.loads((receipt/'response.json').read_bytes()))==canonical(row['payload']),'Lifecycle actual response differs')
            envelope=json.loads(raw)
            require(envelope['trajectory_id']==baseline and envelope['trajectory_id']not in migrated,'Migrated source has a real lifecycle begin/end')
    batch=Path(proof['original_batch_root']);manifest=Path(proof['original_batch_manifest']['path'])
    require(proof['original_batch_manifest']['sha256']==OLD_BATCH_MANIFEST_SHA and sha(manifest)==OLD_BATCH_MANIFEST_SHA,'Original GUI manifest differs')
    files=json.loads(manifest.read_bytes())
    require({p.relative_to(batch).as_posix()for p in batch.rglob('*')if p.is_file()}==set(files),'Original GUI terminal inventory differs')
    for name,value in files.items():
        path=(batch/name).resolve();require(path.is_relative_to(batch.resolve())and sha(path)==value,'Original GUI terminal file differs')
    require(all(not list((batch/'runs'/run).glob('attempt-*'))for run in migrated),'Migrated old GUI has an attempt')
    require(proof.get('new_primary_call_cap')==630 and type(proof['new_primary_call_cap'])is int and
        proof.get('new_auxiliary_call_cap')==120 and type(proof['new_auxiliary_call_cap'])is int,'Unspent budget broadened')
    return True
