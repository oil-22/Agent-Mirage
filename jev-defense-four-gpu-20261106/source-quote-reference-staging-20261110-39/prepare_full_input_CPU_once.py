"""Prepare the separate original/full proposed input CPU identity check."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'remaining29-full-history-gui-20261110-37'))
from join_source_reviews import verify_seal
from orchestrate import save,sha


def main():
    assert not(HERE/'full-input-CPU-preparation.json').exists()
    original=json.loads((HERE/'native-CPU-failed.json').read_bytes())
    root=Path(original['root']);assert verify_seal(root)==original['seal_sha256']
    launcher=(root/'run_native_CPU_once.py').read_text(encoding='utf8')
    launcher=launcher.replace('native-CPU-submission.json','full-input-CPU-submission.json')
    launcher=launcher.replace('native-reference-CPU-','full-input-reference-CPU-')
    launcher=launcher.replace('native_grammar_check.py','full_input_CPU_check.py')
    launcher=launcher.replace('launch-native-quote-reference-CPU-only-once','launch-complete-input-reference-CPU-only-once')
    target=HERE/'run_full_input_CPU_once.py'
    with target.open('x',encoding='utf8',newline='\n')as stream:stream.write(launcher)
    save(HERE/'full-input-CPU-preparation.json',dict(launcher_sha256=sha(target),checker_sha256=sha(HERE/'full_input_CPU_check.py'),
        scope='Exact original0074 complete native processor input reproduction and proposed table-only delta; no native generation, model weights or GPU',
        condition_not_adopted_by_CPU_preparation=True,new_model_GUI_scorer_calls=0))
    print(json.dumps(dict(prepared=True,new_model_GUI_scorer_calls=0)))


if __name__=='__main__':main()
