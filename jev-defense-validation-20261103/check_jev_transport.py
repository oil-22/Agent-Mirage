"""Temporary, loopback-only SSH bridge check. GET health only; zero inference."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

BASE = Path(__file__).resolve().parent
SSH = r'D:\Git\usr\bin\ssh.exe'
CONFIG = r'C:\Users\researcher\.ssh\config'


def check():
    root = BASE / 'transport-evidence' / str(time.time_ns())
    root.mkdir(parents=True, exist_ok=False)
    common = [SSH, '-F', CONFIG, '-o', 'BatchMode=yes', '-o', 'ExitOnForwardFailure=yes',
              '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=2', '-N']
    commands = [common + ['-L', '127.0.0.1:28421:127.0.0.1:18221',
                         '-L', '127.0.0.1:28422:127.0.0.1:18222', '3090'],
                common + ['-R', '127.0.0.1:28421:127.0.0.1:28421',
                          '-R', '127.0.0.1:28422:127.0.0.1:28422', '4090']]
    out = {'model_calls': 0, 'method': 'GET /health only', 'credentials_copied': False,
           'commands': commands, 'services_modified': False}
    processes, logs = [], []
    try:
        for i, command in enumerate(commands):
            log = (root / ('ssh-' + str(i) + '.log')).open('wb'); logs.append(log)
            proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            processes.append(proc)
        out['owned_bridge_pids'] = [p.pid for p in processes]
        for _ in range(15):
            if any(p.poll() is not None for p in processes):
                raise RuntimeError('One temporary SSH bridge exited; no inference attempted')
            try:
                health = []
                for port in [28421, 28422]:
                    with urllib.request.urlopen('http://127.0.0.1:' + str(port) + '/health', timeout=2) as r:
                        health.append(json.load(r))
                break
            except OSError:
                time.sleep(1)
        else:
            raise RuntimeError('Local bridge health timeout')
        out['local_health'] = health
        remote = "import json,urllib.request; print(json.dumps([json.load(urllib.request.urlopen('http://127.0.0.1:'+str(p)+'/health',timeout=5)) for p in [28421,28422]]))"
        # The remote command contains only this fixed source, never a token or user string.
        command = [SSH, '-F', CONFIG, '-o', 'BatchMode=yes', '4090',
                   '/data/researcher/venvs/qwen35-9b-full-20261019/bin/python -c ' + "'" + remote.replace("'", "'\"'\"'") + "'"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=25)
        (root / 'remote-stderr.txt').write_text(result.stderr, encoding='utf-8')
        result.check_returncode()
        out['remote_health'] = json.loads(result.stdout)
        for i, (model, revision) in enumerate([
            ('jev_style', '9d3147c2ba1d793958e447b0e7e20c7436ec34b5'),
            ('neohorse', '434cb21d3a994a953d3ae5788405fcb2c4970554')]):
            for responses in [out['local_health'], out['remote_health']]:
                assert responses[i]['model'] == model
                assert responses[i]['revision'] == revision
                assert responses[i]['phase'] == 'ready'
        out['status'] = 'health_transport_verified_not_inference'
    except Exception as error:
        out.update(status='technical_failure', error=type(error).__name__ + ': ' + str(error))
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=10)
        for log in logs:
            log.close()
        out['temporary_bridges_closed'] = all(p.poll() is not None for p in processes)
        (root / 'receipt.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
        (root / 'seal.json').write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.iterdir() if p.is_file()}, indent=2), encoding='utf-8')
    print(json.dumps({'root': str(root), 'status': out['status'], 'error': out.get('error'),
                      'model_calls': 0, 'temporary_bridges_closed': out['temporary_bridges_closed']}))


if __name__ == '__main__':
    check()
