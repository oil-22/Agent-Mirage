"""Complete CPU audit of the SAME one actual calls, without model loading."""
import ast
import json
import time
from pathlib import Path

from control_offline import prepared
from remote_util import HERE, remote, save, sha


ADMISSION = r'''
p=Path(P);o=Path(O)
assert os.getuid()==1033 and sha(p/'manifest.json')==MANIFEST
m=json.loads((p/'manifest.json').read_bytes())
for name,h in m['files'].items():assert sha(p/name)==h,name
exit=json.loads((o/'exit.json').read_bytes());released=json.loads((o/'released.json').read_bytes())
assert exit['exit_code']==exit['child_exit_code']==0 and exit['failure']is None
assert released['fresh_locks_closed']==3 and released['no_broker_left_running']
identities=[identity(json.loads(q.read_bytes()))for q in[o/'launcher-process.json',o/'service/process.json']]
terminal=json.loads((o/'service/terminal.json').read_bytes())
assert terminal['status']=='completed'and terminal['attempted_calls']==terminal['complete_replies']==1
assert terminal['new_primary_calls']==terminal['GUI_actions']==terminal['paid_API_calls']==terminal['automatic_retries']==0
global_map=json.loads((o/'postexit-seal.json').read_bytes())
assert {q.relative_to(o).as_posix()for q in o.rglob('*')if q.is_file()and q!=o/'postexit-seal.json'}==set(global_map)
chain_info,events=chain(o/'service/journal/events.jsonl')
assert chain_info['head']==terminal['journal_head']and chain_info['events']==terminal['journal_events']
names=sorted(q.name for q in(o/'service/requests').iterdir())
assert set(names)=={v['request_id']for v in m['cases']}and len(names)==1
assert len([v for v in events if v['kind']=='native_call_started'])==1
assert {v['data']['request_id']for v in events if v['kind']=='native_call_started'}==set(names)
assert {v['data']['request_id']:v['data']['image_sha256']for v in events if v['kind']=='request_received'}=={v['request_id']:v['sha256']for v in m['cases']}
assert {v['data']['request_id']:v['data']['seal_sha256']for v in events if v['kind']=='request_sealed'}=={name:sha(o/'service/requests'/name/'seal.json')for name in names}
loaded=json.loads((o/'service/loaded.json').read_bytes())
assert loaded['revision']=='9ff7cf9838e59df461c276b7699d56b244d2af58'and loaded['single_image']and loaded['no_cross_request_KV']and loaded['fast']is False
assert json.loads((o/'service/checkpoint-before.json').read_bytes())==json.loads((o/'service/checkpoint-after-load.json').read_bytes())==json.loads((o/'service/checkpoint-final.json').read_bytes())
lease=json.loads((o/'lease.json').read_bytes());locks_raw=Path('/proc/locks').read_text().splitlines();lock_rows=[]
for record in lease['lock_records']:
 q=Path(record['path']);st=q.stat();assert st.st_ino==record['inode']
 key=(os.major(st.st_dev),os.minor(st.st_dev),st.st_ino);matches=[]
 for line in locks_raw:
  for item in line.split():
   parts=item.split(':')
   if len(parts)!=3:continue
   try:value=(int(parts[0],16),int(parts[1],16),int(parts[2]))
   except ValueError:continue
   if value==key:matches.append(line)
 lock_rows.append({'path':str(q),'inode':st.st_ino,'kernel_locks':matches})
assert not any(v['kernel_locks']for v in lock_rows)
before=(o/'resource-before-locks.json').stat().st_mtime_ns/1e9
assert before<=lease['created']<=exit['time']<=released['time']
print(json.dumps({'global':global_map,'global_seal_sha256':sha(o/'postexit-seal.json'),'names':names,'identities':identities,'terminal':terminal,'chain':chain_info,'events':events,'loaded':loaded,'kernel_lock_release':lock_rows,'all_three_locks_released':True,'resource_cost':{'reserved_GPUs':1,'GPU_seconds_lower':exit['time']-lease['created'],'GPU_seconds_upper':released['time']-before,'includes_load_and_idle':True,'excludes_postexit_auditing':True},'lease':lease,'new_model_GUI_calls':0}))
'''


def main():
    assert not (HERE / 'completed-audit-current.json').exists()
    pointer, package, manifest = prepared()
    original = HERE.parent / 'flash-injection-first-defense-20261115-01/audit_completed_group.py'
    values = {v.targets[0].id: v.value.value for v in ast.parse(original.read_text('utf8')).body
              if isinstance(v, ast.Assign) and len(v.targets) == 1 and isinstance(v.targets[0], ast.Name) and isinstance(v.value, ast.Constant) and isinstance(v.value.value, str)}
    common = values['COMMON'].replace('key=(str(p),s.st_size,s.st_mtime_ns)', 'key=(str(p),s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)').replace('assert p.stat()==s,str(p)', 'after=p.stat();assert (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)==(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns),str(p)')
    old = "d=root/'service/requests'/name;proof=verify(d,global_map=GLOBAL,prefix='flash/service/requests/'+name+'/')"
    assert values['FLASH'].count(old) == 1
    flash = values['FLASH'].replace(old, "d=Path(O)/'service/requests'/name;proof=verify(d,global_map=GLOBAL,prefix='service/requests/'+name+'/')")
    anchor = " assert len(trace)==1 and trace[0]['past_key_values']is None and trace[0]['use_cache']is False"
    assert flash.count(anchor) == 1
    flash = flash.replace(anchor, anchor + "\n text=(d/'actual-input-text.txt').read_text();assert contract['question']in text and contract['state']in text and all(v in text for v in contract['options'].values())")
    anchor = "  assert list(v.shape)==t['shape']and str(v.dtype)==t['dtype']and hashlib.sha256(v.view(torch.uint8).numpy().tobytes()).hexdigest()==t['sha256']"
    assert flash.count(anchor) == 1
    flash = flash.replace(anchor, anchor + "\n  if 'values'in t:assert v.tolist()==t['values']")
    root = HERE / ('completed-audit-' + str(time.time_ns())); root.mkdir()
    (root / 'source.py').write_bytes(Path(__file__).read_bytes()); (root / 'original-reader-source.py').write_bytes(original.read_bytes())
    (root / 'actual-CPU-reader.py').write_text(common + '\n' + flash, encoding='utf8')
    prefix = 'P=' + repr(manifest['remote_package']) + '\nO=' + repr(manifest['output']) + '\nMANIFEST=' + repr(pointer['manifest_sha256']) + '\n' + common + '\n'
    def call(name, source):
        raw, operation = remote('3090', prefix + source, 'one-normal-offline-postexit-' + name, timeout=180)
        value = json.loads(raw)
        save(root / (name + '.json'), {'operation': str(operation), 'result': value})
        return value
    print(json.dumps({'audit_root': str(root)}), flush=True)
    admission = call('admission', ADMISSION)
    global_map = admission['global']; requests = []
    for i, name in enumerate(admission['names']):
        value = call('Flash-%02d' % i, 'GLOBAL=' + repr(global_map) + '\nNAMES=' + repr([name]) + '\n' + flash)
        requests.extend(value['requests'])
        print(json.dumps({'verified_actual_requests': len(requests)}), flush=True)
    nonrequest = {n: h for n, h in global_map.items() if not n.startswith('service/requests/')}
    call('other-raw-members', 'ROWS=' + repr(nonrequest) + '\nfor name,h in ROWS.items():assert sha(Path(O)/name)==h,name\nprint(json.dumps({"members":len(ROWS)}))')
    final = call('final-identities', ADMISSION)
    assert final['global_seal_sha256'] == admission['global_seal_sha256'] and final['chain'] == admission['chain']
    by_id = {v['request_id']: v for v in requests}; assert len(by_id) == len(requests) == 1
    cases = []
    for case in manifest['cases']:
        row = by_id[case['request_id']]; assert row['image_sha256'] == case['sha256']
        assert row['contract_sha256'] == manifest['contract_sha256']
        cases.append({**row, 'case_id': case['id']})
    result = {'status': 'passed', 'actual_Flash_requests': 1, 'wire_tensors_probabilities_and_no_KV_verified': True,
              'all_original_identities_exited': True, 'all_three_kernel_locks_released': True,
              'request_rows': cases, 'input_tokens': sum(v['input_tokens'] for v in cases), 'native_seconds_sum': sum(v['elapsed_seconds_with_input_capture'] for v in cases),
              'resource_cost': admission['resource_cost'], 'group_seal_sha256': admission['global_seal_sha256'],
              'new_model_GPU_GUI_calls_from_audit': 0, 'not_a_new_GUI_release': True}
    save(root / 'summary.json', result)
    save(root / 'seal.json', {q.relative_to(root).as_posix(): sha(q) for q in root.rglob('*') if q.is_file()})
    save(HERE / 'completed-audit-current.json', {'root': str(root), 'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps({'audit_completed': str(root), 'actual_Flash_requests': 1, 'new_primary_GUI_calls': 0}), flush=True)


if __name__ == '__main__':
    main()
