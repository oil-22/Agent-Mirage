"""Preserve invalid self-seals and bind immutable evidence with linked postseals.

Read/copy only. No source/model-input edits, CPU-control reruns, loaders, GPU
leases, inference, or automatic terminal retry. Original bad seals remain.
"""
import hashlib
import json
import sys
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent.parent))
from control import remote


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path,value):
    with path.open('xb')as stream:
        stream.write(json.dumps(value,ensure_ascii=False,indent=2).encode('utf8'))


def main():
    assert not(HERE/'postseal-repair-current.json').exists()
    names=['CPU-stage-current.json','CPU-stage-linked03-current.json','generation-bindings-current.json']
    roots=[];stages=[]
    for name in names:
        pointer=json.loads((HERE/name).read_bytes());root=Path(pointer['root'])
        assert sha(root/'seal.json')==pointer['seal_sha256']
        bad=json.loads((root/'seal.json').read_bytes())
        assert bad['seal.json']==hashlib.sha256(b'').hexdigest()
        for member,h in bad.items():
            if member!='seal.json':assert sha(root/member)==h,member
        if name.startswith('CPU-stage'):
            value=json.loads((root/'result.json').read_bytes());operation=Path(value['operation'])
            original=json.loads((operation/'stdout.txt').read_bytes())
            assert {k:v for k,v in value.items()if k!='operation'}==original
            stages.append({'name':name,'root':str(root),'remote_evidence':value['remote_evidence'],
                           'remote_seal_sha256':value['remote_seal_sha256']})
        roots.append((name,root))
    code='ROWS='+repr(stages)+'\n'+r'''
import hashlib,json,time
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for row in ROWS:
 original=Path(row['remote_evidence']);bad=json.loads((original/'seal.json').read_bytes())
 assert sha(original/'seal.json')==row['remote_seal_sha256']
 assert bad['seal.json']==hashlib.sha256(b'').hexdigest()
 assert {p.name for p in original.iterdir()if p.is_file()}==set(bad)
 for name,h in bad.items():
  if name!='seal.json':assert sha(original/name)==h,name
 target=original.parent/('CPU-evidence-linked-postseal-'+str(time.time_ns()));target.mkdir()
 for path in original.iterdir():
  if path.is_file():
   name='original-invalid-seal.json'if path.name=='seal.json'else path.name
   with(target/name).open('xb')as f:f.write(path.read_bytes())
 proof={'original':str(original),'original_invalid_seal_sha256':sha(original/'seal.json'),
  'original_all_nonseal_bytes_unchanged_and_verified':True,'no_CPU_control_reruns':True,
  'new_model_GPU_GUI_calls':0,'repair':'new full-member snapshot includes original invalid seal; seal excluded from its own hash'}
 with(target/'postseal-repair.json').open('x')as f:json.dump(proof,f,indent=2)
 members={p.name:sha(p)for p in target.iterdir()if p.is_file()}
 with(target/'seal.json').open('x')as f:json.dump(members,f,indent=2)
 assert all(sha(target/name)==h for name,h in members.items())
 rows.append({'name':row['name'],'remote_postseal':str(target),'remote_postseal_sha256':sha(target/'seal.json'),**proof})
print(json.dumps({'rows':rows,'new_model_GPU_GUI_calls':0}))
'''
    raw,operation=remote('3090',code,'linked-postseal-CPU-evidence-preserve-original-self-seal-no-rerun',timeout=55)
    remote_proof=json.loads(raw)
    repair=HERE/('postseal-repair-'+str(time.time_ns()));repair.mkdir()
    (repair/'source.py').write_bytes(Path(__file__).read_bytes())
    for name in ['publish_execution_preparation.py','stage_cpu_only.py','stage_cpu_only_linked03.py']:
        (repair/name).write_bytes((HERE/name).read_bytes())
    save(repair/'remote-postseals.json',{'operation':str(operation),**remote_proof})
    rows=[]
    for name,original in roots:
        target=repair/name.replace('-current.json','');target.mkdir()
        for path in original.iterdir():
            if path.is_file():
                dest=target/('original-invalid-seal.json'if path.name=='seal.json'else path.name)
                with dest.open('xb')as f:f.write(path.read_bytes())
        proof={'original':str(original),'original_invalid_seal_sha256':sha(original/'seal.json'),
               'source_files_and_outputs_preserved_byte_identically':True,
               'new_model_GPU_GUI_calls':0,'no_original_control_or_tensor_checks_rerun':True}
        if name.startswith('CPU-stage'):
            proof['remote_postseal']=next(x for x in remote_proof['rows']if x['name']==name)
        save(target/'postseal-repair.json',proof)
        members={p.name:sha(p)for p in target.iterdir()if p.is_file()}
        save(target/'seal.json',members)
        assert all(sha(target/n)==h for n,h in members.items())
        pointer_name=name.replace('-current.json','-postseal-current.json')
        save(HERE/pointer_name,{'root':str(target),'seal_sha256':sha(target/'seal.json')})
        rows.append({'pointer':pointer_name,**proof,'linked_postseal':str(target)})
    save(repair/'summary.json',{'time':time.time(),'rows':rows,'new_model_GPU_GUI_calls':0,
         'old_self_reference_seals_preserved':True,'actual_study_source_or_prompts_or_input_or_budget_changed':False,
         'old_report_publish_failed_before_creating_its_publication_or_mutating_handoffs':True,
         'old_report_error':'AssertionError: seal.json (self-seal included the hash of its newly opened empty file)'})
    members={str(p.relative_to(repair)).replace('\\','/'):sha(p)for p in repair.rglob('*')if p.is_file()}
    save(repair/'seal.json',members)
    save(HERE/'postseal-repair-current.json',{'root':str(repair),'seal_sha256':sha(repair/'seal.json')})
    old=(HERE/'publish_execution_preparation.py').read_text(encoding='utf8')
    for before,after in [('CPU-stage-linked03-current.json','CPU-stage-linked03-postseal-current.json'),
                         ('generation-bindings-current.json','generation-bindings-postseal-current.json')]:
        assert before in old
        old=old.replace(before,after)
    old=old.replace("'publish_execution_preparation.py']","'publish_execution_preparation.py','publish_execution_preparation_linked02.py','repair_preparation_postseals.py']")
    before='旧源包和旧CPU回执均保留，不把重复的8项检查加成新独立样本。'
    after=before+' 工程汇总另检出旧CPU回执清单自包含空文件SHA的问题；旧清单/源码/日志保留，新关联postseal逐字节绑定原输出并覆盖原错误清单，未重跑CPU控制、未改源输入或放松哈希。详见execution-preparation-02/postseal-repair-current.json。'
    assert before in old;old=old.replace(before,after)
    with(HERE/'publish_execution_preparation_linked02.py').open('x',encoding='utf8',newline='\n')as f:f.write(old)
    print(json.dumps({'postseal_repair':str(repair),'original_seals_preserved':True,'new_model_GPU_GUI_calls':0}))


if __name__=='__main__':
    main()
