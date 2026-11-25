"""Source-bound positive and tampering controls for the new receipt reader."""
import json
import time
from control import HERE, remote, save, sha
from prepare_offline_receipt_repair import PREP, PACKAGE, REMOTE


code = 'PACKAGE=' + repr(REMOTE) + '\nEXPECTED=' + repr(sha(PACKAGE / 'offline-manifest.json')) + '\n' + r'''
import copy,hashlib,json,os,shutil,sys,time
from pathlib import Path
p=Path(PACKAGE);sys.path.insert(0,str(p))
from receipt_binding import verify_cpu_receipt
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
def load(q):return json.loads(q.read_bytes())
def write(q,v):q.write_text(json.dumps(v,ensure_ascii=False,indent=2))
assert sha(p/'offline-manifest.json')==EXPECTED and 'torch'not in sys.modules
manifest=load(p/'offline-manifest.json');plan=load(p/'development-plan.json');original=plan['inputs'][0]
source=Path(original['proposed_full_body']).parent
root=Path('/data/researcher/jev-defense-four-gpu-20261106')/('receipt-binding-source-controls-'+str(time.time_ns()));root.mkdir()
rows=[]
def fixture(name):
 r=root/name;r.mkdir();s=r/'source';s.mkdir();q=r/'package';(q/'CPU-receipts').mkdir(parents=True)
 for n in load(source/'seal.json'):shutil.copyfile(source/n,s/n)
 shutil.copyfile(source/'seal.json',s/'seal.json')
 f=copy.deepcopy(original);m=copy.deepcopy(manifest);w=load(p/'CPU-receipts/case-01.json');w['remote_case']=str(s)
 wp=q/'CPU-receipts/case-01.json';write(wp,w);f['native_CPU_input_receipt_sha256']=sha(wp)
 return q,s,f,m,w
def reseal(q,s,f,m,w):
 write(s/'seal.json',{n:sha(s/n)for n in load(s/'seal.json')})
 w['remote_seal_sha256']=sha(s/'seal.json');m['CPU_case_seals']['1']=sha(s/'seal.json')
 write(q/'CPU-receipts/case-01.json',w);f['native_CPU_input_receipt_sha256']=sha(q/'CPU-receipts/case-01.json')
def check(name,change=None,accepted=False):
 q,s,f,m,w=fixture(name)
 if change:change(q,s,f,m,w)
 error=None
 try:verify_cpu_receipt(q,s,f,m)
 except (RuntimeError,KeyError,FileNotFoundError)as exc:error=str(exc)
 assert (error is None)==accepted,(name,error)
 rows.append({'name':name,'expected_accept':accepted,'accepted':error is None,'rejection':error})
check('source-bound-valid-fixture',accepted=True)
check('wrapper-byte-changed',lambda q,s,f,m,w:(q/'CPU-receipts/case-01.json').write_bytes((q/'CPU-receipts/case-01.json').read_bytes()+b' '))
def wrongpath(q,s,f,m,w):
 w['remote_case']=str(s/'different');write(q/'CPU-receipts/case-01.json',w);f['native_CPU_input_receipt_sha256']=sha(q/'CPU-receipts/case-01.json')
check('wrapper-source-path-mismatch',wrongpath)
check('manifest-seal-mismatch',lambda q,s,f,m,w:m['CPU_case_seals'].__setitem__('1','0'*64))
def tensorchange(q,s,f,m,w):
 target=s/'proposed_input_ids.tensor';raw=bytearray(target.read_bytes());raw[-1]^=1;target.write_bytes(raw)
check('native-input-tensor-byte-changed',tensorchange)
check('full-body-byte-changed',lambda q,s,f,m,w:(s/'proposed-full-body.json').write_bytes((s/'proposed-full-body.json').read_bytes()+b' '))
def resultchange(q,s,f,m,w):
 v=load(s/'result.json');v['proposed_input_tokens']+=1;write(s/'result.json',v);reseal(q,s,f,m,w)
check('resealed-inner-result-not-approved-payload',resultchange)
def originalchange(q,s,f,m,w):
 v=load(s/'result.json');v['source_body_sha256']='0'*64;write(s/'result.json',v);w['result']=v;reseal(q,s,f,m,w)
check('resealed-original-body-identity-changed',originalchange)
def deltachange(q,s,f,m,w):
 v=load(s/'result.json');v['full_input_token_delta']=293;write(s/'result.json',v);w['result']=v;reseal(q,s,f,m,w)
check('resealed-token-delta-changed',deltachange)
def historychange(q,s,f,m,w):
 v=load(s/'result.json');v['full_original_PNGs_and_non_system_history_preserved']=False;write(s/'result.json',v);w['result']=v;reseal(q,s,f,m,w)
check('resealed-full-history-preservation-removed',historychange)
def missing(q,s,f,m,w):
 seal=load(s/'seal.json');seal.pop('result.json');write(s/'seal.json',seal);w['remote_seal_sha256']=sha(s/'seal.json');m['CPU_case_seals']['1']=sha(s/'seal.json');write(q/'CPU-receipts/case-01.json',w);f['native_CPU_input_receipt_sha256']=sha(q/'CPU-receipts/case-01.json')
check('inner-result-missing-from-native-seal',missing)
def bodychange(q,s,f,m,w):
 raw=(s/'proposed-full-body.json').read_bytes()+b' ';(s/'proposed-full-body.json').write_bytes(raw);v=load(s/'result.json');v['proposed_full_body_sha256']=sha(s/'proposed-full-body.json');write(s/'result.json',v);w['result']=v;reseal(q,s,f,m,w)
check('resealed-proposed-full-body-changed',bodychange)
assert not Path(manifest['output']).exists() and 'torch'not in sys.modules
result={'time':time.time(),'root':str(root),'manifest_sha256':EXPECTED,'controls':rows,'passed':len(rows),
 'synthetic_fixture_path_rebinding_for_CPU_controls_only':True,'actual_approved_plan_inputs_not_modified':True,
 'new_model_GPU_GUI_calls':0,'torch_imported':False,'semantic_or_WAIT_model_controls_not_claimed':True}
write(root/'result.json',result)
write(root/'seal.json',{str(q.relative_to(root)):sha(q)for q in root.rglob('*')if q.is_file()})
print(json.dumps(result))
'''

if __name__ == '__main__':
    assert not (PREP / 'CPU-binding-controls.json').exists(), 'Use the existing controls'
    raw, op = remote('3090', code, 'receipt-reader-source-bound-positive-and-negative-controls')
    result = json.loads(raw)
    save(PREP / 'CPU-binding-controls.json', {'result': result, 'operation': str(op),
        'source_sha256': sha(__file__)})
    print(json.dumps({'passed': result['passed'], 'root': result['root'],
        'manifest_sha256': result['manifest_sha256'], 'new_model_GPU_GUI_calls': 0}))
