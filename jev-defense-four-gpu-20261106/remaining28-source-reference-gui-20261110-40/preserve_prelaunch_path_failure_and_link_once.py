"""Seal the failed read-only legacy-path check; link a corrected collector."""
import hashlib
import json
from pathlib import Path
import shutil
import time

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf8')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')

def main():
    old=HERE/'prelaunch_resources_once.py'
    linked=HERE/'prelaunch_resources_linked02.py'
    assert not linked.exists()
    operation=HERE.parent/'full-history-gui-development-20261109-23/operations/1794312959049973800-remaining28-approved-prelaunch-resources-3090'
    assert json.loads((operation/'receipt.json').read_bytes())['returncode']==1
    out=HERE/('prelaunch-path-failure-preservation-'+str(time.time_ns()));out.mkdir()
    shutil.copyfile(old,out/old.name)
    for p in operation.iterdir():
        if p.is_file():shutil.copyfile(p,out/p.name)
    save(out/'failure.json',dict(kind='read_only_collector_legacy_output_path_mismatch',
        operation=str(operation), wrong_assumption='R32 service output under /data',
        authority='R32 original manifest outputs=/home/researcher/jev-defense-four-gpu-20261106/prefill-scheduled-full-history-gui-20261109-32',
        new_model_GPU_GUI_scorer_paid_calls=0, experimental_runtime_or_terminal_changed=False))
    save(out/'seal.json',{p.name:sha(p)for p in out.iterdir()if p.is_file()})
    code=old.read_text(encoding='utf8')
    before=' old=storage/name'
    assert code.count(before)==1
    code=code.replace(before," old=(base if name=='prefill-scheduled-full-history-gui-20261109-32'else storage)/name")
    code=code.replace("'prelaunch-'+host+", "'prelaunch-linked02-'+host+")
    code=code.replace("'remaining28-approved-prelaunch-resources-'+host", "'remaining28-approved-prelaunch-resources-linked02-'+host")
    code=code.replace("remote_evidence_sha256=sha(out/'evidence.json'),", "remote_evidence_sha256=sha(out/'evidence.json'), prior_read_only_failure_preservation="+repr(str(out))+", prior_failure_seal_sha256="+repr(sha(out/'seal.json'))+",")
    compile(code,str(linked),'exec')
    with linked.open('x',encoding='utf8',newline='\n')as f:f.write(code)
    save(HERE/'prelaunch-path-repair-linked02.json',dict(preservation=str(out),seal_sha256=sha(out/'seal.json'),
        original_collector_sha256=sha(old),linked_collector_sha256=sha(linked),
        only_legacy_service_root_and_attempt_provenance_changed=True,new_model_GPU_GUI_scorer_paid_calls=0))
    print(json.dumps(dict(preserved=str(out),linked_collector=str(linked))))

if __name__=='__main__':main()
