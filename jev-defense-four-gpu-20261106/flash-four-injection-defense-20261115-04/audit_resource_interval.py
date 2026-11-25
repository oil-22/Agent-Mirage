"""Postexit resource-cost bounds, including launcher final sealing.

The original exit.json is written before final hashing and lock closure. Keep its
recorded interval intact and bind the holder's actual child-exit receipt as an
upper bound for the complete launcher reservation interval. No lock is acquired,
released or modified by this audit.
"""
import json
import time
from pathlib import Path

from control import HERE, manifest, remote, save, sha


CODE = r'''
import hashlib,json,os,time
from pathlib import Path
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
def identity(pid):
 q=Path('/proc',str(pid))
 try:
  s=(q/'stat').read_text().rsplit(')',1)[1].split()
  return {'pid':int(pid),'uid':q.stat().st_uid,'command':(q/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
 except FileNotFoundError:return None
o=Path(O);expanded=json.loads((o/'expanded-lease.json').read_bytes());exited=json.loads((o/'exit.json').read_bytes())
before=o/'resource-before-expansion.json';earliest_start=before.stat().st_mtime_ns/1e9
assert exited['exit_code']==0 and exited['failure']is None
saved=expanded['holder'];actual=identity(saved['pid'])
assert not(actual is not None and actual['state']not in ['Z','X']and all(actual[k]==saved[k]for k in ['pid','uid','command','start_ticks']))
original_path=Path(expanded['original_lease']);assert sha(original_path)==expanded['original_lease_sha256']
original=json.loads(original_path.read_bytes());end_path=original_path.parent/('child-'+str(saved['pid'])+'-exit.json')
end=json.loads(end_path.read_bytes());assert end['pid']==saved['pid']and end['exit_code']==0
assert earliest_start<=expanded['created']<exited['time']<=end['time']
holder=original['holder'];current_holder=identity(holder['pid']);held=[]
holder_same=current_holder is not None and current_holder['state']not in ['Z','X']and all(current_holder[k]==holder[k]for k in ['pid','uid','command','start_ticks'])
if holder_same:
 for row in original['lock_records']:
  q=Path('/proc',str(holder['pid']));fd=q/'fd'/str(row['fd']);info=(q/'fdinfo'/str(row['fd'])).read_text()
  assert fd.stat().st_ino==row['inode']and os.readlink(fd)==row['path']and'WRITE '+str(holder['pid'])in info
  held.append({'path':row['path'],'fd':row['fd'],'inode':row['inode'],'actual_fdinfo':info})
print(json.dumps({'observation_time':time.time(),'expanded_lease_sha256':sha(o/'expanded-lease.json'),
 'resource_before_expansion_sha256':sha(before),'earliest_start_bound_before_extra_lock_acquisition':earliest_start,
 'original_exit_receipt':exited,'original_exit_receipt_sha256':sha(o/'exit.json'),
 'holder_child_exit_receipt':end,'holder_child_exit_path':str(end_path),'holder_child_exit_sha256':sha(end_path),
 'launcher_saved_identity':saved,'launcher_current_identity':actual,
 'final_seal_mtime_ns':(o/'postexit-seal.json').stat().st_mtime_ns,
 'start':expanded['created'],'original_recorded_end_before_final_sealing':exited['time'],
 'actual_launcher_exit_observed_upper_bound':end['time'],
 'eight_GPU_seconds_lower_bound_to_exit_receipt':8*(exited['time']-expanded['created']),
 'eight_GPU_seconds_upper_bound_through_launcher_exit_observation':8*(end['time']-earliest_start),
 'does_not_charge_only_one_GPU':True,'source_parent_four_GPU_holder_still_same':holder_same,
 'source_parent_holder_current_identity':current_holder,'source_parent_current_actual_locks':held,
 'earlier_four_GPU_holder_time_and_later_idle_reservation_not_in_these_bounds':True,
 'no_currency_or_energy_estimate':True,'new_model_GUI_calls':0}))
'''


def main():
    pointer = json.loads((HERE / 'completed-group-audit-current.json').read_bytes())
    group = Path(pointer['root'])
    assert sha(group / 'seal.json') == pointer['seal_sha256']
    for name, expected in json.loads((group / 'seal.json').read_bytes()).items():
        assert sha(group / name) == expected
    admission = json.loads((group / 'admission.json').read_bytes())['result']
    root = HERE / ('resource-interval-audit-' + str(time.time_ns()))
    root.mkdir()
    (root / 'source.py').write_bytes(Path(__file__).read_bytes())
    raw, operation = remote('3090', 'O=' + repr(manifest()['output3090']) + '\n' + CODE,
                            'postexit-actual-holder-child-exit-cost-bounds')
    result = json.loads(raw)
    assert result['expanded_lease_sha256'] == admission['global']['expanded-lease.json']
    assert result['original_exit_receipt_sha256'] == admission['global']['exit.json']
    assert result['resource_before_expansion_sha256'] == admission['global']['resource-before-expansion.json']
    save(root / 'result.json', {'operation': str(operation), 'group_audit': str(group),
                               'group_audit_seal_sha256': pointer['seal_sha256'], **result})
    save(root / 'seal.json', {p.name: sha(p) for p in root.iterdir() if p.is_file()})
    temporary = HERE / ('.resource-interval-' + str(time.time_ns()))
    temporary.write_text(json.dumps({'root': str(root), 'seal_sha256': sha(root / 'seal.json')}), encoding='utf8')
    temporary.replace(HERE / 'resource-interval-audit-current.json')
    print(json.dumps({'root': str(root),
        'eight_GPU_seconds_lower_bound': result['eight_GPU_seconds_lower_bound_to_exit_receipt'],
        'eight_GPU_seconds_upper_bound': result['eight_GPU_seconds_upper_bound_through_launcher_exit_observation'],
        'earlier_holder_and_later_idle_time_excluded': True,'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
