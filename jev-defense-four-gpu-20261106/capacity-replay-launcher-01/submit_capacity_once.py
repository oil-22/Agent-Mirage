"""Root-invoked atomic holder command submission. No client inference or old queue."""
import argparse
import json
import os
from pathlib import Path
import time
import uuid
from capacity_gate import read,sha,validate_static,validate_old_terminal,empty_resources


def publish_no_clobber(target, raw):
    """Holder never sees an empty/partial *.json; hardlink publication cannot overwrite."""
    temporary=target.parent/('.capacity-publish-'+str(os.getpid())+'-'+uuid.uuid4().hex+'.tmp')
    inode=None
    try:
        with temporary.open('xb')as handle:
            inode=os.fstat(handle.fileno()).st_ino
            handle.write(raw);handle.flush();os.fsync(handle.fileno())
        os.link(temporary,target)
        directory=os.open(str(target.parent),os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        # Only this invocation's O_EXCL file is removed; a published target is
        # never overwritten/removed and the submission claim remains on failure.
        if inode is not None and temporary.exists()and temporary.stat().st_ino==inode:
            temporary.unlink()


def main(a):
    assert sha(a.command)==a.command_sha256
    command=read(a.command);values=command['argv']
    assert command['action']=='launch'and sha(values[1])==command['script_sha256']
    assert Path(values[1]).name=='launch_failed_capacity_once.py'
    index=values.index('--spec');path=Path(values[index+1]);expected=values[values.index('--spec-sha256')+1]
    assert sha(path)==expected
    spec=read(path);assert spec['root_reviewed_approval']is True
    validate_static(spec,Path(__file__).resolve().parent);validate_old_terminal(spec)
    lease=read('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')
    empty_resources(lease)
    assert not Path(spec['new_group']).exists()and not Path(spec['once_only_claim']).exists()
    submission=Path(spec['submission_claim'])
    with submission.open('x')as handle:json.dump({'time':time.time(),'command_sha256':a.command_sha256},handle)
    target=Path('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/commands')/('capacity-layout-'+Path(spec['new_group']).name+'.json')
    publish_no_clobber(target,a.command.read_bytes())
    print(json.dumps({'submitted_once':True,'command':str(target),'spec_sha256':expected,
        'no_client_model_request_sent_by_submitter':True}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--command',type=Path,required=True)
    p.add_argument('--command-sha256',required=True);main(p.parse_args())
