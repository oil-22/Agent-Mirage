"""Root-invoked marker-only stop of this exact preserved failed model group."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
BASE=Path(__file__).resolve().parent
CHECK='''
group=Path('/home/researcher/jev-defense-four-gpu-20261106/online-service-group-1793978182501156243')
proof=Path('/home/researcher/jev-defense-four-gpu-20261106/failed-gui-service-preservation/1793982653388639508')
assert sha(proof/'receipt.json')=='d78feb1d58d452c5218663bd41afe155e35825efddff0300ef0f5ff2c9c7e976'
assert sha(proof/'seal.json')=='51ffb22c4dcc2b81fab5499d9ae4a88eaf3a7bbcac9123399bde2fb476cae1af'
for name,expected in read(proof/'seal.json').items():assert sha(proof/name)==expected
current=service_snapshot(group)
assert current['all_actual_peer_identities_valid']and not current['foreign_target_compute']
assert current['holder']['identity_matches']and len(current['holder']['actual_locks'])==9
assert current['launcher']['identity_matches']and len(current['launcher']['actual_locks'])==9
assert current['state_snapshot']['phase']=='terminal_failure'and current['state_snapshot']['active']is None
assert current['workers']['primary']['expected']['pid']==2610487
assert current['workers']['pplx_flash']['expected']['pid']==2610488
assert all(row['expected']['uid']==1033 and row['expected']['start_ticks']=='1159792893'and
    row['identity_matches']and len(row['actual_locks'])==9 for row in current['workers'].values())
assert current['workers']['primary']['request_counts']=={'completed':72,'failed':1,'pending_unsealed':0}
assert current['workers']['pplx_flash']['request_counts']=={'completed':0,'failed':0,'pending_unsealed':0}
assert current['journal']['uncommitted_partial_tail_bytes']==0
assert not(group/'stop-requested.json').exists(),'Stop marker already present; do not overwrite'
marker={'reason':'root-requested marker-only stop after preserved terminal prefill OOM; no retry',
    'time':time.time(),'preservation_receipt_sha256':sha(proof/'receipt.json'),
    'preservation_root':str(proof),'actual_peers':{role:row['actual']for role,row in current['workers'].items()},
    'all9locks_verified':True,'pending_requests':0,'current_journal_sha256':sha(group/'journal.jsonl'),
    'no_signals_sent':True,'holder_to_remain_running':True}
if EXECUTE:
    with(group/'stop-requested.json').open('x')as handle:
        json.dump(marker,handle,indent=2);handle.flush();os.fsync(handle.fileno())
print(json.dumps({'gate_passed':True,'marker_written':EXECUTE,'group':str(group),
    'actual_peer_PIDs':[2610487,2610488],'all9locks_verified':True,'pending_requests':0,
    'primary_completed':72,'primary_failed':1,'model_HTTP_GUI_calls':0,'signals_sent':0,
    'holder_untouched':True}))
'''


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    source=(BASE/'progress-preparation/progress_remote.py').read_text(encoding='utf8')
    code="__name__='audit_helpers'\nEXECUTE="+repr(args.execute)+'\n'+source+'\n'+CHECK
    print(remote(code,timeout=90))


if __name__=='__main__':main()
