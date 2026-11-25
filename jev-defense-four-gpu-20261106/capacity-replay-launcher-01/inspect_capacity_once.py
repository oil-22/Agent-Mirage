"""Read-only capacity readiness/terminal snapshot, no HTTP and no model imports."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from capacity_gate import read,sha,same,identity,verify_manifest


def main(a):
    spec=read(a.spec);group=Path(spec['new_group'])
    if not group.exists():
        print(json.dumps({'group':str(group),'stage':'not_started','HTTP_model_GUI_calls':0}));return
    lease=read('/home/researcher/jev-defense-four-gpu-20261106/resource-attempt-20261106-01/lease.json')
    config=read(group/'runtime-config.json');rows={}
    for role in('primary','pplx_flash'):
        launch=group/(role+'-launch.json')
        if not launch.exists():rows[role]={'stage':'not_launched'};continue
        value=read(launch);expected=value['identity'];actual=identity(expected['pid'])
        valid=same(actual,expected)
        row={'pid':expected['pid'],'actual_identity_matches':valid,'actual_process_absent':actual is None,
            'loaded':(group/role/'loaded.json').exists(),'ready':(group/role/'ready.json').exists(),
            'actual_locks':0,'requests':[],'allocator':value.get('PYTORCH_CUDA_ALLOC_CONF')}
        if valid:
            assert actual['uid']==1033 and actual['command']==' '.join(config['commands'][role])
            for record in lease['lock_records']:
                fd=Path('/proc',str(actual['pid']),'fd',str(record['fd']))
                assert os.readlink(fd)==record['path']and fd.stat().st_ino==record['inode']
                assert'lock:'in Path('/proc',str(actual['pid']),'fdinfo',str(record['fd'])).read_text()
            row['actual_locks']=len(lease['lock_records'])
        for request in sorted((group/role/'requests').glob('*')):
            item={'path':str(request),'stage':'pending_unsealed'}
            if(request/'seal.json').exists():
                for name,expected_sha in read(request/'seal.json').items():assert sha(request/name)==expected_sha
                item.update(stage='failed'if(request/'failure.json').exists()else'completed',
                    seal_sha256=sha(request/'seal.json'))
                if(request/'generation.json').exists():
                    generation=read(request/'generation.json');ids=generation['generated_ids']
                    eos=generation['generation_config']['eos_token_id'];eos=eos if isinstance(eos,list)else[eos]
                    item['generation']={'input_tokens':len(generation['input_ids']),'output_tokens':len(ids),
                        'native_EOS':bool(ids)and ids[-1]in eos,'hit_output_cap':generation['hit_output_cap']}
                if(request/'failure.json').exists():item['exception_last_line']=read(request/'failure.json')['error'].splitlines()[-1]
            row['requests'].append(item)
        rows[role]=row
    allowed={row['pid']for row in rows.values()if row.get('actual_identity_matches')}
    target={row['uuid']for row in lease['gpu']}
    raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
    foreign=[line for line in raw.splitlines()if line.strip()and line.split(',')[0].strip()in target
             and int(line.split(',')[1])not in allowed]
    terminal=group/'terminal-manifest.json'
    sealed=False
    if terminal.exists():verify_manifest(group,terminal,sha(terminal));sealed=True
    print(json.dumps({'group':str(group),'workers':rows,'foreign_target_compute':foreign,
        'terminal_manifest_verified':sealed,'terminal_manifest_sha256':sha(terminal)if sealed else None,
        'capacity_attempt':read(group/'capacity-attempt-terminal.json')if(group/'capacity-attempt-terminal.json').exists()else None,
        'actual_exit':read(group/'exit.json')if(group/'exit.json').exists()else None,
        'HTTP_model_GUI_calls':0,'semantic_or_GUI_success_not_inferred':True}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);main(p.parse_args())
