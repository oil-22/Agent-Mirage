import json,os,pathlib,signal,subprocess,time
root=pathlib.Path('/home/researcher/attention-20261031');main=json.loads((root/'glm/status.json').read_text());queue=json.loads((root/'source-queue-glm.json').read_text());tail=json.loads((root/'glm-tail-queue.json').read_text())
assert tail['phase']=='finished' and not tail['duplicates']
assert main['phase']=='running' and main['index']<240 and queue['phase']=='waiting_for_main'
cmd=pathlib.Path('/proc/2763611/cmdline');assert b'/home/researcher/queue_source.py\x00glm\x00' in cmd.read_bytes()
os.kill(2763611,signal.SIGTERM)
(root/'source-glm-resource-switch.json').write_text(json.dumps({'main':main,'previous_queue':queue,'new_gpus':'0,1','time':time.time()},indent=2))
with (root/'source-glm-free-controller.log').open('w') as log:
    rc=subprocess.run(['/opt/whz/conda-envs/webmall-vlm/bin/python','/home/researcher/queue_source_now.py','glm','--now','--gpus','0,1'],stdout=log,stderr=log).returncode
(root/'source-glm-resource-switch-result.json').write_text(json.dumps({'exit_code':rc,'queue':json.loads((root/'source-queue-glm.json').read_text())},indent=2))
