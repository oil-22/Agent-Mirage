import json,hashlib
from pathlib import Path
root=Path(__file__).parent;base=root.parent
j=base/'structure-three-audit01/service-audit-public-1794040226300580000/service-journal.jsonl'
e=base/'three-terminal-postexit-public/1794040388947724400/public/exit.json'
rows=[json.loads(l)for l in j.read_text(encoding='utf-8').splitlines()]
loaded={r['payload']['role']:r['time']for r in rows if r['event']=='worker_loaded'}
ready=max(loaded.values());terminal=rows[-1]['time'];exit_time=json.loads(e.read_bytes())['time']
assert rows[-1]['event']=='trajectory_transition'and rows[-1]['payload']['body']['status']=='technical_failure'
out={'type':'observed_service_loaded_to_real_exit_window_not_full_task_reservation',
 'service_journal_sha256':hashlib.sha256(j.read_bytes()).hexdigest(),'original_exit_sha256':hashlib.sha256(e.read_bytes()).hexdigest(),
 'worker_loaded_times':loaded,'both_loaded_epoch':ready,'original_trajectory_terminal_epoch':terminal,'real_launcher_exit_epoch':exit_time,
 'both_loaded_to_exit_seconds':exit_time-ready,'both_loaded_to_exit_hours':(exit_time-ready)/3600,
 'four_card_equivalent_hours_for_this_observed_window':4*(exit_time-ready)/3600,
 'terminal_to_exit_idle_seconds':exit_time-terminal,'terminal_to_exit_idle_hours':(exit_time-terminal)/3600,
 'terminal_to_exit_idle_four_card_equivalent_hours':4*(exit_time-terminal)/3600,
 'full_task_reservation_closed':False,'holder9locks_remain':True,
 'scope':'Server wall-clock window after both workers loaded through actual group exit, includes waiting/audit idle. Excludes earlier loading/preparation/old attempts; holder reservation continues after group exit. Not model generation seconds, currency or energy.'}
dest=root/'observed-service-residency.json';assert not dest.exists();dest.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,indent=2))
