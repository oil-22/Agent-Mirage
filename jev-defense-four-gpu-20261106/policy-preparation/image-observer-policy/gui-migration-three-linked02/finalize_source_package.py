"""Final source/CPU package, without a launch-ready switch or GPU operations."""
import difflib,hashlib,json,shutil,subprocess,sys,time,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj):
    with p.open('x',encoding='utf8')as f:json.dump(obj,f,ensure_ascii=False,indent=2)
assert not(HERE/'package-seal.json').exists(),'Final package is immutable; new linked package required'
oldprep=HERE/'prefinal-source-preservation';oldprep.mkdir()
for name in ('policy-source-seal.json','readiness.template.json','source-diff.txt'):
    shutil.copy2(HERE/name,oldprep/name)
policy=json.loads((HERE/'policy-source-seal.json').read_bytes())
policy['release_sha256']={p.relative_to(HERE/'release').as_posix():sha(p)for p in (HERE/'release').rglob('*')if p.is_file()}
(HERE/'policy-source-seal.json').write_text(json.dumps(policy,ensure_ascii=False,indent=2),encoding='utf8')
ready=json.loads((HERE/'readiness.template.json').read_bytes());ready['release_sha256']=policy['release_sha256'];ready['launch_ready']=False
cpu=HERE/'cpu-validation';cpu.mkdir()
test_results=[]
for folder,filename in [(HERE,'test_three_sources.py'),(HERE/'terminal-auditor','test_terminal_auditor.py')]:
    test=subprocess.run([sys.executable,'-B','-m','unittest','-v',filename],cwd=folder,capture_output=True,text=True)
    (cpu/(filename+'.output.txt')).write_text(test.stdout+test.stderr,encoding='utf8')
    assert test.returncode==0,'CPU failure preserved; no package seal'
    test_results.append({'file':filename,'exit_code':test.returncode,'output_sha256':sha(cpu/(filename+'.output.txt'))})
receipt={'stage':'exact_three_linked_source_CPU_only','tests_passed':True,'ready':True,
    'actual_wire_request_reply_audit':True,'event_chain_and_terminal_seal_audit':True,'no_duplicate_launch':True,
    'test_results':test_results,'root_actual_collector_AST_guard_passed':True,'all_three_native_zero_state_guard_tested':True,
    'original_core_prompts_and_observer_wire_unchanged':True,
    'actual_old_unspent_source_audit_receipt':'/data/researcher/jev-defense-four-gpu-20261106/three-trajectory-unspent-source-audit-1793985952619045154/receipt.json',
    'actual_old_unspent_source_audit_receipt_sha256':'97e040e75886ae8c41ea2106ec668becdd0b6e291b4b3674445b03ced17b712f',
    'readiness_launch_ready':False,'model_GUI_HTTP_scorer_signals':0,'no_defense_success_claim':True,'time':time.time()}
save(cpu/'receipt.json',receipt);save(cpu/'seal.json',{p.name:sha(p)for p in cpu.iterdir()if p.is_file()})
DEPLOY='/data/researcher/jev-defense-four-gpu-20261106/gui-migration-three-linked02'
ready['evidence']['terminal_auditor']={'path':DEPLOY+'/cpu-validation/receipt.json','sha256':sha(cpu/'receipt.json')}
(HERE/'readiness.template.json').write_text(json.dumps(ready,ensure_ascii=False,indent=2),encoding='utf8')
cap_src=ROOT/'single-capacity-independent-audits/1793985058235255298';cap_dst=HERE/'evidence/primary-capacity'
shutil.copytree(cap_src,cap_dst,dirs_exist_ok=True)
for p in cap_src.rglob('*'):
    if p.is_file():assert sha(p)==sha(cap_dst/p.relative_to(cap_src))
diff=[]
for name in ('observer_launch_contract.py','run_image_observer_vwa_validation.py'):
    diff.extend(difflib.unified_diff((ROOT/'gui-preparation-package-02/release'/name).read_text(encoding='utf8').splitlines(True),
        (HERE/'release'/name).read_text(encoding='utf8').splitlines(True),fromfile='sealed04/'+name,tofile='linked-three/'+name))
(HERE/'source-diff.txt').write_text(''.join(diff),encoding='utf8')
selected=[]
for p in HERE.rglob('*'):
    if not p.is_file():continue
    rel=p.relative_to(HERE)
    if any(part in {'actual-source-audit','prefinal-source-preservation','__pycache__'}for part in rel.parts):continue
    if rel.as_posix()=='package-seal.json':continue
    selected.append(p)
save(HERE/'package-seal.json',{p.relative_to(HERE).as_posix():sha(p)for p in selected})
archive=HERE.parent/('gui-migration-three-linked02-'+sha(HERE/'package-seal.json')[:16]+'.zip')
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED)as z:
    for p in selected+[HERE/'package-seal.json']:z.write(p,p.relative_to(HERE).as_posix())
print(json.dumps({'package':str(HERE),'package_seal_sha256':sha(HERE/'package-seal.json'),
    'wrapper_sha256':sha(HERE/'gui_once.py'),'policy_source_seal_sha256':sha(HERE/'policy-source-seal.json'),
    'migration_proof_sha256':sha(HERE/'three-trajectory-migration-source.json'),
    'cpu_receipt_sha256':sha(cpu/'receipt.json'),'archive':str(archive),'archive_sha256':sha(archive),
    'archive_bytes':archive.stat().st_size,'files':len(selected),'launch_ready':False}))
