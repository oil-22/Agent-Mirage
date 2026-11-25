"""Seal CPU-tested auditor capability only, never claim a real GUI audit."""
import json,subprocess,sys,time
from pathlib import Path
from audit_gui_terminals import sha
BASE=Path(__file__).resolve().parent
root=BASE/'cpu-evidence'/str(time.time_ns());root.mkdir(parents=True)
r=subprocess.run([sys.executable,str(BASE/'test_terminal_auditor.py')],capture_output=True,text=True)
(root/'test-output.txt').write_text(r.stdout+r.stderr,encoding='utf8')
ok=r.returncode==0
receipt={'ready':ok,'actual_wire_request_reply_audit':ok,
    'event_chain_and_terminal_seal_audit':ok,'no_duplicate_launch':ok,
    'scope':'auditor implementation capability prepared and tested on synthetic CPU fixtures only',
    'preparation_only':True,'CPU_integrity_tests':14,'CPU_tests_passed':ok,
    'actual_GUI_terminal_audits_completed':0,'new_model_GPU_GUI_scorer_calls':0,
    'semantic_labels_automatically_inferred':False,'detector_outputs_used_as_gold':False,
    'primary_native_execution_binding':'SHA-bound unchanged native source + original parsed proposal + execution-returned journal; trace/pickle raw bytes sealed, pickle never executed',
    'source_sha256':{name:sha((BASE/name).read_bytes())for name in ['audit_gui_terminals.py','test_terminal_auditor.py','README.md']},
    'actual_evidence_required':['SHA-bound new GUI batch and active source release',
       'actual online-admission plan/order/per-run role caps',
       'original postexit terminal manifests including traces/logs',
       'all explicit inference and lifecycle sealed service request directories',
       'full attempt event journals and actual original public images'],
    'actual_audit_pass_is_not_defense_success':True,
    'runtime_schema':'runtime-preparation/gui-linked-01 online-admission.json plus exact request/response/seal directories; no old preflight or queue reused'}
(root/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
(root/'seal.json').write_text(json.dumps({p.name:sha(p.read_bytes())for p in root.iterdir()if p.is_file()},indent=2),encoding='utf8')
print(json.dumps({'root':str(root),'ready':ok,'tests':14,'real_GUI_audits':0,'receipt_sha256':sha((root/'receipt.json').read_bytes())}))
if not ok:raise SystemExit(1)
