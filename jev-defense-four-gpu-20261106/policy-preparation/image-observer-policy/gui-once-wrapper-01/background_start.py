"""Explicit root-invoked background start of one sealed GUI wrapper, no shell."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
sys.path.insert(0,'/data/researcher/jev-defense-four-gpu-20261106/gui-once-wrapper-01')
import gui_once as g

BASE=Path('/data/researcher/jev-defense-four-gpu-20261106')


def validate(a):
    g.require(os.getuid()==1015,'Expected owned4090 GUI UID1015')
    spec=g.bound(a.spec,a.spec_sha256)
    g.require(a.spec.resolve()==BASE/'gui-final-readiness-01/launch-spec.json', 'Wrong new linked specification')
    g.require(Path(spec['batch_root'])==BASE/'gui-batch-image-observer-01' and
        Path(spec['linked_root'])==BASE/'gui-final-readiness-01','Wrong new once-only experiment')
    wrapper=BASE/'gui-once-wrapper-01/gui_once.py'
    g.require(g.sha(wrapper)==spec['wrapper_source_sha256'] and
        spec['wrapper_source_sha256']=='a2bc6313b807cd800d245428d77f50dd7449e970e2201c2d1a926dd7b230429f',
        'Actual wrapper source changed')
    owner=g.bound(spec['ownership_evidence']['path'],spec['ownership_evidence']['sha256'])
    g.ownership(owner,time.time())
    return spec,wrapper


def main(a):
    spec,wrapper=validate(a)
    root=BASE/'gui-outer-background-01'
    g.require(not root.exists(),'Background launch already attempted; no retry')
    root.mkdir(exist_ok=False)
    command=[g.PYTHON,'-B',str(wrapper),'run','--spec',str(a.spec.resolve()),
        '--spec-sha256',a.spec_sha256,'--control-root',str(BASE/'gui-outer-control-01')]
    g.write(root/'once-only-launch.json',{'argv':command,'spec_sha256':a.spec_sha256,
        'launcher_source_sha256':g.sha(Path(__file__)),'time':time.time(),
        'automatic_retry':False,'parent_process':g.identity(os.getpid())})
    try:
        with(root/'wrapper.log').open('xb')as log:
            child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,
                stderr=subprocess.STDOUT,start_new_session=True,cwd=str(BASE),
                env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        actual=g.identity(child.pid)
        g.write(root/'actualprocess.json',{'identity':actual,'argv':command,'started_time':time.time(),
            'wrapper_sha256':g.sha(wrapper),'spec_sha256':a.spec_sha256,
            'no_models_GUI_called_by_launcher_before_spawn':True})
    except BaseException:
        g.write(root/'launch-failure.json',{'traceback':traceback.format_exc(),'automatic_retry':False})
        raise
    print(json.dumps({'background_root':str(root),'actual_wrapper_process':actual,
        'spec_sha256':a.spec_sha256,'gui_completion_or_health_not_inferred':True,
        'new_model_GUI_calls_count_requires_actual_receipts':True}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--spec',type=Path,required=True)
    parser.add_argument('--spec-sha256',required=True);main(parser.parse_args())
