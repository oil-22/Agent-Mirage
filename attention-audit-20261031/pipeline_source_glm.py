import json,os,pathlib,signal,subprocess,time
root=pathlib.Path('/home/researcher/attention-20261031');path=root/'source-pipeline.json'
def state(phase,**kw):path.write_text(json.dumps(dict(phase=phase,time=time.time(),**kw),indent=2))
state('waiting_for_qwen9_source')
while True:
    p=root/'source-qwen9/status.json'
    if p.exists():
        try:s=json.loads(p.read_text())
        except json.JSONDecodeError:time.sleep(2);continue
        if s.get('phase')=='finished' and s.get('total')==33 and s.get('completed')==33:break
    time.sleep(10)
time.sleep(5)
main=json.loads((root/'glm/status.json').read_text());queue=json.loads((root/'source-queue-glm.json').read_text())
if main.get('phase')=='finished' or main.get('index',324)>=240 or queue.get('phase')!='waiting_for_main':
    state('original_glm_source_queue_retained',main=main,queue=queue);raise SystemExit()
oldpid=2763611;cmd=pathlib.Path('/proc')/str(oldpid)/'cmdline'
if not cmd.exists() or b'/home/researcher/queue_source.py\x00glm\x00' not in cmd.read_bytes():state('old_queue_process_not_verified');raise SystemExit()
os.kill(oldpid,signal.SIGTERM)
state('source_glm_on_released_qwen9_gpus',main=main)
with (root/'source-glm-pipeline.log').open('w') as log:
    rc=subprocess.run(['/opt/whz/conda-envs/webmall-vlm/bin/python','/home/researcher/queue_source_now.py','glm','--now','--gpus','4,5'],stdout=log,stderr=log).returncode
state('finished',exit_code=rc,queue=json.loads((root/'source-queue-glm.json').read_text()))
