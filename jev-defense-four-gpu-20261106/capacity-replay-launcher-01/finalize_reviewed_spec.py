"""Root explicitly runs this after source review; prepare spec/command only, never launch."""
import argparse
import json
from pathlib import Path
import sys
from capacity_gate import read,sha,validate_static,validate_old_terminal,empty_resources


def main(a):
    draft=read(a.draft);assert draft['root_reviewed_approval']is False
    here=Path(__file__).resolve().parent
    validate_static(draft,here)
    draft.update(root_reviewed_approval=True,parent_draft_sha256=sha(a.draft),
        old_terminal_manifest=str(a.old_manifest),old_terminal_manifest_sha256=a.old_manifest_sha256)
    if a.old_control_exit_audit:
        assert a.old_control_exit_audit_sha256
        draft['old_control_exit_audit']={'path':str(a.old_control_exit_audit),'sha256':a.old_control_exit_audit_sha256}
    if a.old_postexit_audit:
        assert a.old_postexit_audit_sha256
        draft['old_terminal_mode']='postexit_copy_original_metadata_missing'
        draft['old_postexit_audit']={'path':str(a.old_postexit_audit),'sha256':a.old_postexit_audit_sha256}
    old=validate_old_terminal(draft)
    lease=read('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')
    resources=empty_resources(lease)
    root=a.draft.parent
    reviewed=root/'launch-specification.reviewed.json'
    with reviewed.open('x')as handle:json.dump(draft,handle,indent=2)
    command={'action':'launch','argv':['/opt/whz/conda-envs/webmall-vlm/bin/python',
        str(here/'launch_failed_capacity_once.py'),'--root',draft['new_group'],'--spec',str(reviewed),
        '--spec-sha256',sha(reviewed)],'script_sha256':sha(here/'launch_failed_capacity_once.py')}
    target=root/'holder-command.proposed.json'
    with target.open('x')as handle:json.dump(command,handle,indent=2)
    proof=root/'reviewed-finalization.json'
    with proof.open('x')as handle:json.dump({'root_reviewed_approval':True,'old_terminal_gate':old,
        'actual_resource_gate':resources,'reviewed_spec_sha256':sha(reviewed),
        'holder_command_sha256':sha(target),'submitted_to_holder':False,'model_GPU_calls':0},handle,indent=2)
    print(json.dumps({'spec':str(reviewed),'spec_sha256':sha(reviewed),'holder_command':str(target),
        'holder_command_sha256':sha(target),'submitted':False,'model_GPU_calls':0}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--draft',type=Path,required=True)
    p.add_argument('--old-manifest',type=Path,required=True);p.add_argument('--old-manifest-sha256',required=True)
    p.add_argument('--old-control-exit-audit',type=Path);p.add_argument('--old-control-exit-audit-sha256')
    p.add_argument('--old-postexit-audit',type=Path);p.add_argument('--old-postexit-audit-sha256')
    main(p.parse_args())
