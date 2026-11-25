"""Root-invoked one POST after actual ready/identity/locks. No retry, health or GUI."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import traceback
import urllib.error
import urllib.request
from capacity_gate import read,sha,same,identity,validate_static
from preflight_service import save


def seal_client_root(root):
    inventory={p.name:sha(p)for p in root.iterdir()if p.is_file()and p.name!='seal.json'}
    save(root/'seal.json',inventory)


def main(a):
    assert sha(a.spec)==a.spec_sha256
    spec=read(a.spec);assert spec['root_reviewed_approval']is True
    validate_static(spec,Path(__file__).resolve().parent)
    group=Path(spec['new_group']);config=read(group/'runtime-config.json')
    lease=read('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')
    assert same(identity(lease['holder']['pid']),lease['holder'])
    allowed=set()
    for role in('primary','pplx_flash'):
        process=read(group/'processes'/(role+'.json'))['identity'];actual=identity(process['pid'])
        assert same(actual,process)and actual['uid']==1033
        assert actual['command']==' '.join(config['commands'][role])
        allowed.add(actual['pid'])
        for row in lease['lock_records']:
            fd=Path('/proc',str(actual['pid']),'fd',str(row['fd']))
            assert os.readlink(fd)==row['path']and fd.stat().st_ino==row['inode']
            assert'lock:'in Path('/proc',str(actual['pid']),'fdinfo',str(row['fd'])).read_text()
        assert len(lease['lock_records'])==9
        assert read(group/role/'ready.json')['loaded_sha256']==sha(group/role/'loaded.json')
        assert not list((group/role/'requests').iterdir()),'Attempt already spent/pending; no resend'
    target={row['uuid']for row in lease['gpu']}
    raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
    assert all(int(line.split(',')[1])in allowed for line in raw.splitlines()
               if line.strip()and line.split(',')[0].strip()in target)
    root=Path(spec['client_receipt_root']);root.mkdir(parents=True,exist_ok=False)
    wire=Path(spec['frozen_wire']).read_bytes();(root/'request-wire.json').write_bytes(wire)
    with(root/'once-only-client-claim.json').open('x')as handle:json.dump({'time':time.time(),
        'spec_sha256':a.spec_sha256,'wire_sha256':sha(spec['frozen_wire']),'automatic_retry':False},handle)
    token=Path(spec['token_file']).read_text().strip()
    request=urllib.request.Request('http://127.0.0.1:'+str(spec['roles']['primary']['port'])+'/',data=wire,
        headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},method='POST')
    try:
        try:
            with urllib.request.urlopen(request,timeout=7200)as response:status=response.status;content=response.read()
        except urllib.error.HTTPError as error:status=error.code;content=error.read()
        (root/'response.raw').write_bytes(content)
        with(root/'response-metadata.json').open('x')as handle:json.dump({'HTTP_status':status,
            'response_sha256':sha(root/'response.raw'),'automatic_retry':False,'model_calls_submitted':1},handle)
    except BaseException:
        with(root/'transport-failure.json').open('x')as handle:json.dump({'error':traceback.format_exc(),
            'automatic_retry':False,'request_may_have_completed_or_pending_check_actual_service':True},handle)
        raise
    finally:
        seal_client_root(root)
    print(json.dumps({'client_receipt':str(root),'HTTP_status':status,'single_POST_submitted':True,
        'helper_actor_GUI_scorer_calls':0,'automatic_retry':False,'semantic_success_not_inferred':True}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True)
    p.add_argument('--spec-sha256',required=True);main(p.parse_args())
