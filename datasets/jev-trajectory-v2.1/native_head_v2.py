"""Use the existing native Jev head with the verified v2.1 manifest.

Example in the original checkout: python native_head_v2.py check manifest.jsonl
JEV_STARTER_DIR can point to the original starter if you unpacked elsewhere.
"""
import os,sys
from pathlib import Path
from verify import check
here=Path(__file__).resolve().parent
sys.path.insert(0,os.environ.get('JEV_STARTER_DIR',str(here.parents[1]/'reports/jev-verifier-finetune-starter-20261125')))
import temporal_head
def read_v2(path,check_images=False):
    if path.name!='manifest.jsonl':raise ValueError('Use the v2.1 manifest.jsonl.')
    rows,_=check(path.resolve().parent,report=False)
    return rows
if __name__=='__main__':
    temporal_head.read_manifest=read_v2
    temporal_head.main()
