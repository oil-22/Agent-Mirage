"""Root marker-only stop, exact already-preserved terminal group. No model/GUI calls."""
import json,sys,time,hashlib
from pathlib import Path
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote
root=Path(__file__).parent
helper=(root.parent/'progress-preparation/progress_remote.py').read_text(encoding='utf-8')
check=r'''
group=Path('/home/researcher/jev-defense-four-gpu-20261106/online-three-service-group-1793985778592347799')
proof=Path('/home/researcher/jev-defense-four-gpu-20261106/three-terminal-prestop-preservation/1794040105015962100')
assert sha(proof/'receipt.json')=='16fb3e744dcf373932a3ba44c4fc690284049f150e95505816a974758e6be386'
assert sha(proof/'preservation-seal.json')=='47fd5fa7c89ec0193070ec8520378422bf1069142424ad77800bde7ecc35b3a9'
for name,record in read(proof/'preservation-seal.json').items():
 relative=Path(name);assert not relative.is_absolute()and'..'not in relative.parts
 p=proof/relative
 if 'symlink'in record:assert os.readlink(str(p))==record['symlink']
 else:assert sha(p)==record['sha256']and p.stat().st_size==record['bytes']
current=service_snapshot(group)
assert current['all_actual_peer_identities_valid']and not current['foreign_target_compute']
assert current['holder']['identity_matches']and current['holder']['actual']['pid']==2568295 and len(current['holder']['actual_locks'])==9
assert current['launcher']['identity_matches']and len(current['launcher']['actual_locks'])==9
assert current['state_snapshot']['phase']=='terminal_failure'and current['state_snapshot']['active']is None
expected={'primary':(2661955,'1160628036',97),'pplx_flash':(2661956,'1160628040',20)}
for role,(pid,start,count)in expected.items():
 row=current['workers'][role]
 assert row['expected']['pid']==pid and row['expected']['uid']==1033 and str(row['expected']['start_ticks'])==start
 assert row['identity_matches']and len(row['actual_locks'])==9
 assert row['request_counts']=={'completed':count,'failed':0,'pending_unsealed':0}
assert current['workers']['primary']['sealed_native_EOS_count']==97
assert current['journal']['uncommitted_partial_tail_bytes']==0
assert not(group/'stop-requested.json').exists(),'Already marked: never overwrite or duplicate stop'
marker={'reason':'Root marker-only stop of preserved terminal verifier_failure group; complete audit; no automatic retry',
 'time':time.time(),'preservation_root':str(proof),'preservation_receipt_sha256':sha(proof/'receipt.json'),
 'actual_peers':{role:row['actual']for role,row in current['workers'].items()},
 'all9locks_verified':True,'pending_requests':0,'journal_sha256_before_stop':sha(group/'journal.jsonl'),
 'no_signals_sent':True,'holder_to_remain_running':True}
with(group/'stop-requested.json').open('x')as f:json.dump(marker,f,indent=2);f.flush();os.fsync(f.fileno())
print(json.dumps({'marker_written':True,'marker_sha256':sha(group/'stop-requested.json'),'marker':marker,
 'fresh_before_stop':current,'signals_sent':0,'new_model_GUI_health_scorer_calls':0},ensure_ascii=False))
'''
if __name__=='__main__':
 out=root/'service-stop-evidence'/str(time.time_ns());out.mkdir(parents=True,exist_ok=False)
 source="__name__='read_only_helpers'\n"+helper+'\n'+check
 (out/'submitted-source.py').write_text(source,encoding='utf-8')
 try:
  result=remote(source,host='3090',timeout=90)
  (out/'receipt.json').write_text(result,encoding='utf-8');parsed=json.loads(result)
  print(json.dumps({'local':str(out),'marker_sha256':parsed['marker_sha256'],'marker_written':True,'signals_sent':0,'new_model_GUI_calls':0},ensure_ascii=False))
 except Exception as e:
  (out/'failure.txt').write_text(str(e),encoding='utf-8');raise
 finally:
  (out/'seal.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in out.iterdir()if p.is_file()},indent=2)+'\n',encoding='utf-8')
