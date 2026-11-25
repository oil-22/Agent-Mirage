"""Root-only atomic new holder submission. No HTTP/client request."""
import argparse
from pathlib import Path
import sys
import time

from online_gate import read,validate_static,verify_gate
from online_service import save,sha


def main(a):
    if sha(a.command)!=a.command_sha256:raise RuntimeError('Command bytes differ')
    command=read(a.command);argv=command['argv'];here=Path(__file__).resolve().parent
    if command['action']!='launch' or Path(argv[1])!=here/'launch_online_group.py' or sha(argv[1])!=command['script_sha256']:
        raise RuntimeError('Only this new exact-three launcher is admissible')
    path=Path(argv[argv.index('--spec')+1]);expected=argv[argv.index('--spec-sha256')+1]
    if sha(path)!=expected:raise RuntimeError('Reviewed spec differs')
    spec=read(path)
    if spec['root_reviewed_approval']is not True:raise RuntimeError('Root review required')
    validate_static(spec,here);sys.path.insert(0,spec['preflight_source_root'])
    from capacity_gate import verify_manifest,validate_old_terminal,empty_resources,identity,same
    from submit_capacity_once import publish_no_clobber
    verify_gate(spec,verify_manifest,validate_old_terminal,identity,same)
    lease=read('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json');empty_resources(lease)
    if Path(spec['new_group']).exists()or Path(spec['once_only_claim']).exists():
        raise RuntimeError('Existing online group/claim forbids duplicate submission')
    save(Path(spec['submission_claim']),{'time':time.time(),'command_sha256':a.command_sha256,'no_automatic_retry':True})
    target=Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/commands')/('online-three-'+Path(spec['new_group']).name+'.json')
    publish_no_clobber(target,a.command.read_bytes())
    print(__import__('json').dumps({'submitted_once':True,'command':str(target),'spec_sha256':expected,
        'client_model_GUI_requests_sent':0}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--command',type=Path,required=True)
    p.add_argument('--command-sha256',required=True);main(p.parse_args())
