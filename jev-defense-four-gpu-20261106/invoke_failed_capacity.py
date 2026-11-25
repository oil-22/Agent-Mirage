"""Explicit root stage commands for the frozen single-capacity repair; no automatic follow-on."""
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,r'D:\MultiModel\defense-resume-20261102\restored-release')
from remote import remote

STAMP='1793984469336572715'
PREP='/home/researcher/jev-defense-four-gpu-20261106/failed-capacity-source-preparation/'+STAMP
SOURCE='/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/failed-layout-capacity-'+STAMP
POST='/home/researcher/jev-defense-four-gpu-20261106/independent-service-postexit/1793983761231132390'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['check','finalize','submit','inspect','one-judge'])
    args=parser.parse_args()
    setup='PREP='+repr(PREP)+'\nSOURCE='+repr(SOURCE)+'\nPOST='+repr(POST)+'\nMODE='+repr(args.mode)+'\n'
    code=r'''
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
prep=Path(PREP);source=Path(SOURCE);post=Path(POST)
python='/opt/whz/conda-envs/webmall-vlm/bin/python'
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
if MODE=='check':
 script="""import json,sys,time
from pathlib import Path
sys.path.insert(0,SOURCE)
from capacity_gate import read,sha,validate_static,validate_old_terminal,empty_resources
spec=read(Path(PREP)/'launch-specification.draft.json')
spec.update(old_terminal_manifest=str(Path(POST)/'service-original-sha256.json'),old_terminal_manifest_sha256='eedd00633edb80b9f57ed81d1e899e564e38b0c5c2efbd6c44531c99a372e624',old_postexit_audit={'path':str(Path(POST)/'receipt.json'),'sha256':'6cc5f640a3abd9bdeb53a990db14a5386107517846c82933b188e99e83013d36'})
validate_static(spec,SOURCE);old=validate_old_terminal(spec)
resources=empty_resources(read('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json'))
root=Path('/home/researcher/jev-defense-four-gpu-20261106/capacity-prelaunch-CPU-gates')/str(time.time_ns());root.mkdir(parents=True)
receipt={'status':'passed','spec_draft_sha256':sha(Path(PREP)/'launch-specification.draft.json'),'old_postexit_audit_sha256':spec['old_postexit_audit']['sha256'],'old_terminal_manifest_sha256':spec['old_terminal_manifest_sha256'],'source_sha256':spec['source_sha256'],'old_terminal_gate':old,'resources':resources,'root_reviewed_approval':False,'actual_model_GPU_GUI_calls':0}
(root/'receipt.json').write_text(json.dumps(receipt,indent=2));(root/'seal.json').write_text(json.dumps({'receipt.json':sha(root/'receipt.json')}))
print(json.dumps({'gate_receipt':str(root/'receipt.json'),'sha256':sha(root/'receipt.json'),'all_gates_passed':True,'resources':resources,'old_stage':old,'actual_model_GPU_GUI_calls':0}))
"""
 script='SOURCE='+repr(SOURCE)+'\nPREP='+repr(PREP)+'\nPOST='+repr(POST)+'\n'+script
 command=[python,'-c',script]
elif MODE=='finalize':
 command=[python,str(source/'finalize_reviewed_spec.py'),'--draft',str(prep/'launch-specification.draft.json'),
 '--old-manifest',str(post/'service-original-sha256.json'),'--old-manifest-sha256','eedd00633edb80b9f57ed81d1e899e564e38b0c5c2efbd6c44531c99a372e624',
 '--old-postexit-audit',str(post/'receipt.json'),'--old-postexit-audit-sha256','6cc5f640a3abd9bdeb53a990db14a5386107517846c82933b188e99e83013d36']
elif MODE=='submit':
 command=[python,str(source/'submit_capacity_once.py'),'--command',str(prep/'holder-command.proposed.json'),
 '--command-sha256',sha(prep/'holder-command.proposed.json')]
elif MODE=='inspect':
 spec=prep/'launch-specification.reviewed.json'
 if not spec.exists():spec=prep/'launch-specification.draft.json'
 command=[python,str(source/'inspect_capacity_once.py'),'--spec',str(spec)]
elif MODE=='one-judge':
 spec=prep/'launch-specification.reviewed.json'
 command=[python,str(source/'run_one_frozen_judge.py'),'--spec',str(spec),'--spec-sha256',sha(spec)]
result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),cwd=str(source))
print(json.dumps({'mode':MODE,'exit_code':result.returncode,'stdout':result.stdout.decode(),'stderr':result.stderr.decode()}))
'''
    timeout=7500 if args.mode=='one-judge'else 120
    print(remote(setup+code,timeout=timeout))


if __name__=='__main__':main()
