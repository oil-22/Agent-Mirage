"""Run only readiness/config finalization on4090 after actual fresh proof arrives."""
import argparse,json,shlex,subprocess,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--ownership-path',required=True);ap.add_argument('--ownership-sha256',required=True)
a=ap.parse_args()
remote=['/data/researcher/venvs/qwen35-9b-full-20261019/bin/python','-B',
    '/data/researcher/jev-defense-four-gpu-20261106/gui-once-wrapper-01/gui_once.py','prepare',
    '--package','/data/researcher/jev-defense-four-gpu-20261106/gui-preparation-01',
    '--capacity-evidence','/data/researcher/jev-defense-four-gpu-20261106/primary-capacity-independent-evidence-01/receipt.json',
    '--capacity-sha256','5a89138010f8cf005cbcd03bc2a4b249af0e253178666388fb17652bb0571fb8',
    '--ownership-evidence',a.ownership_path,'--ownership-sha256',a.ownership_sha256,
    '--output','/data/researcher/jev-defense-four-gpu-20261106/gui-final-readiness-01',
    '--batch-root','/data/researcher/jev-defense-four-gpu-20261106/gui-batch-image-observer-01']
out=BASE/('final-readiness-invocation-'+str(time.time_ns()));out.mkdir(exist_ok=False)
r=subprocess.run(['D:/Git/usr/bin/ssh.exe','-F','C:/Users/researcher/.ssh/config','4090',shlex.join(remote)],
    capture_output=True,text=True,timeout=90)
(out/'stdout.txt').write_text(r.stdout,encoding='utf8');(out/'stderr.txt').write_text(r.stderr,encoding='utf8')
(out/'receipt.json').write_text(json.dumps({'returncode':r.returncode,'remote_argv':remote,
    'model_GUI_calls':0,'actual_GUI_run_started':False}),encoding='utf8')
print(r.stdout);print(json.dumps({'returncode':r.returncode,'local_receipt':str(out)}))
if r.returncode:raise SystemExit(r.returncode)
