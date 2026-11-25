"""Use the current native Jev starter with this balanced train/validation manifest."""
import os,sys
from pathlib import Path
from verify import canon,check,js
here=Path(__file__).resolve().parent
sys.path.insert(0,os.environ.get('JEV_STARTER_DIR',str(here.parents[1]/'reports/jev-verifier-finetune-starter-20261125')))
import temporal_head
def load_v3(path,check_images=False):
    if path.name!='manifest.jsonl':raise ValueError('Pass the v3 manifest.jsonl.')
    root=path.resolve().parent
    rows,_=check(root);protocol=js(root/'protocol.json')
    if protocol['checkpoint_revision']!=temporal_head.REV or protocol['prompt_builder_sha256']!=temporal_head.PROMPT_SHA:
        raise ValueError('Native checkpoint or prompt builder differs from this release.')
    if any(temporal_head.action_json(r['action'])!=canon(r['action']).decode() for r in rows):
        raise ValueError('Native action serialization differs from the exported prompt.')
    return rows
if __name__=='__main__':
    if sys.argv[1:2]==['test']:raise SystemExit('v3 contains train and validation only. Keep the original frozen test separate.')
    temporal_head.read_manifest=load_v3
    temporal_head.main()
