"""Root-invoked source review finalizer only; no holder submission/HTTP/models."""
import argparse
from pathlib import Path
import sys

from online_gate import read, validate_static, verify_gate
from online_service import save, sha


def main(a):
    draft=read(a.draft);here=Path(__file__).resolve().parent
    if draft['root_reviewed_approval'] is not False or not a.root_reviewed:
        raise RuntimeError('Explicit root source review is required')
    validate_static(draft,here)
    native=Path(draft['preflight_source_root']);sys.path.insert(0,str(native))
    from capacity_gate import verify_manifest,validate_old_terminal,empty_resources,identity,same
    proposed=read(draft['online_launch_gate'])
    if proposed['approved'] is not False:
        raise RuntimeError('Original preparation gate must remain unapproved')
    gate_path=a.draft.parent/'online-launch-gate.reviewed.json'
    save(gate_path,{**proposed,'approved':True,'parent_gate_sha256':draft['online_launch_gate_sha256'],
        'authorization_scope':'root reviewed this independent exact-three service stage; GUI launch remains separately coordinated'})
    reviewed={**draft,'root_reviewed_approval':True,'parent_draft_sha256':sha(a.draft),
        'online_launch_gate':str(gate_path),'online_launch_gate_sha256':sha(gate_path)}
    gate,proof,old=verify_gate(reviewed,verify_manifest,validate_old_terminal,identity,same)
    lease=read('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')
    resources=empty_resources(lease)
    spec=a.draft.parent/'launch-specification.reviewed.json';save(spec,reviewed)
    command={'action':'launch','argv':['/opt/whz/conda-envs/webmall-vlm/bin/python',
        str(here/'launch_online_group.py'),'--root',draft['new_group'],'--spec',str(spec),
        '--spec-sha256',sha(spec)],'script_sha256':sha(here/'launch_online_group.py')}
    target=a.draft.parent/'holder-command.proposed.json';save(target,command)
    save(a.draft.parent/'reviewed-finalization.json',{'root_reviewed_approval':True,
        'old_terminal_preserved':old,'resources':resources,'spec':str(spec),'spec_sha256':sha(spec),
        'holder_command':str(target),'holder_command_sha256':sha(target),'submitted':False,'model_GUI_calls':0})
    print(__import__('json').dumps({'spec':str(spec),'spec_sha256':sha(spec),
        'holder_command':str(target),'holder_command_sha256':sha(target),'submitted':False,'model_GUI_calls':0}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--draft',type=Path,required=True)
    p.add_argument('--root-reviewed',action='store_true');main(p.parse_args())
