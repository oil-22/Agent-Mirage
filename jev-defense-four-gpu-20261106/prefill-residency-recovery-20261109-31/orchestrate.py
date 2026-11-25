"""Original-budget NEW31 wrapper around the reviewed once-only owned launcher."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE / 'full-history-gui-development-20261109-23'))
source = (BASE / 'memory-scheduled-capacity-20261109-26/orchestrate.py').read_text(encoding='utf8')
source = source.replace('memory-scheduled-capacity-20261109-26', HERE.name)
source = source.replace('full-history-gui-development-20261109-23', 'memory-scheduled-full-history-gui-20261109-29')
source = source.replace("'actor_spent':11,'actor_cap':70,'judge_spent':33,'judge_cap':140,'pending_actor_candidate_index':11,'actions_executed':10", "'actor_spent':17,'actor_cap':70,'judge_spent':49,'judge_cap':140,'pending_actor_candidate_index':17,'actions_executed':16")
source = source.replace("m['one_linked_judge_attempt_index']==34 and m['remaining_judge_after_attempt']==106", "m['one_linked_judge_attempt_index']==50 and m['remaining_judge_after_attempt']==90")
source = source.replace('original0044', 'original0021').replace('requests/0044', 'requests/0021')
source = source.replace("len(payload['view']['images'])==11", "len(payload['view']['images'])==17")
source = source.replace('[1,22596]', '[1,32184]')
source = source.replace("'linked_judge_attempt':34", "'linked_judge_attempt':50")
source = source.replace("'original_judge_attempt_index': 34", "'original_judge_attempt_index': 50")
source = source.replace("{'actor':11,'evidence':0,'judge':33}", "{'actor':17,'evidence':0,'judge':49}")
# Submission/admission reference the previously frozen NEW29 sources whose
# primary device map and complete strict release are unchanged in NEW31.
source = source.replace("old=p.parent/'memory-scheduled-full-history-gui-20261109-29'", "old=p.parent/'memory-scheduled-full-history-gui-20261109-29'")
source = source.replace('stage-new-memory-scheduled26-once','stage-new-prefill31-once')
source = source.replace('CPU-source-budget-and-placement26-admission','CPU-source-budget-and-prefill31-admission')
source = source.replace('submit-linked26-judge34-once-no-GUI','submit-linked31-judge50-once-no-GUI')
source = source.replace('inspect-existing-linked26-actual-handle','inspect-existing-linked31-actual-handle')
source = source.replace("out['residency_transitions']=", "out['prefill_residency']=[{k:v for k,v in json.loads(q.read_bytes()).items() if k not in ['moves']} for q in sorted((r/'worker').glob('prefill-residency-*.json'))]\nout['residency_transitions']=")
exec(compile(source, str(Path(__file__).resolve()), 'exec'), {'__name__':'__main__','__file__':str(Path(__file__).resolve())})
