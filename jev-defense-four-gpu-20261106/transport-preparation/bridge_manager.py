"""Owned Windows SSH bridge lifecycle. No inference; explicit start is required.

Token bytes travel only from SSH stdout directly to another SSH stdin. Health
helpers read remote mode600 files and return a small allowlist of health fields.
"""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import time

BASE = Path(__file__).resolve().parent
CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
MAPPINGS = [(28427, 18127), (28423, 18223)]
SAFE_HEALTH_FIELDS = ('phase', 'stage', 'state', 'role', 'calls', 'max_new_calls',
                      'GUI_actions', 'GUI_actions0', 'model', 'revision', 'bearer_required')

TOKEN_READ_SOURCE = '''import os,stat,sys
fd=os.open(sys.argv[1],os.O_RDONLY|os.O_NOFOLLOW)
s=os.fstat(fd)
if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_mode&0o077: raise SystemExit(11)
with os.fdopen(fd,'rb') as f: data=f.read(8193)
if not data or len(data)>8192 or any(c<33 or c>126 for c in data): raise SystemExit(12)
sys.stdout.buffer.write(data)
'''

TOKEN_WRITE_SOURCE = '''import json,os,pathlib,stat,sys
p=pathlib.Path(sys.argv[1]); parent=p.parent
try: parent.mkdir(mode=0o700,parents=True,exist_ok=False)
except FileExistsError: pass
s=parent.lstat()
if not stat.S_ISDIR(s.st_mode) or s.st_uid!=os.getuid() or s.st_mode&0o077: raise SystemExit(21)
data=sys.stdin.buffer.read(8193)
if not data or len(data)>8192 or any(c<33 or c>126 for c in data): raise SystemExit(22)
fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno()); s=os.fstat(f.fileno())
print(json.dumps({'created':True,'dev':s.st_dev,'ino':s.st_ino,'uid':s.st_uid,'mode':stat.S_IMODE(s.st_mode)}))
'''

TOKEN_DELETE_SOURCE = '''import json,os,pathlib,stat,sys
p=pathlib.Path(sys.argv[1]); expected=json.loads(sys.argv[2]); s=p.lstat()
if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600: raise SystemExit(31)
if any(getattr(s,'st_'+k)!=expected[k] for k in ('dev','ino','uid')): raise SystemExit(32)
p.unlink(); print(json.dumps({'removed':True}))
'''

HEALTH_SOURCE = '''import json,os,stat,sys,urllib.request,urllib.error
fd=os.open(sys.argv[1],os.O_RDONLY|os.O_NOFOLLOW); s=os.fstat(fd)
if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_mode&0o077: raise SystemExit(41)
with os.fdopen(fd,'rb') as f: token=f.read(8193)
if not token or len(token)>8192 or any(c<33 or c>126 for c in token): raise SystemExit(42)
out=[]
for port in json.loads(sys.argv[2]):
 try:
  with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/health',timeout=5): raise SystemExit(43)
 except urllib.error.HTTPError as e:
  if e.code not in (401,403): raise SystemExit(44)
 req=urllib.request.Request('http://127.0.0.1:'+str(port)+'/health',headers={'Authorization':'Bearer '+token.decode('ascii')})
 with urllib.request.urlopen(req,timeout=5) as r: raw=json.load(r)
 raw['bearer_required']=True
 out.append({k:raw[k] for k in json.loads(sys.argv[3]) if k in raw and isinstance(raw[k],(str,int,float,bool,type(None)))})
print(json.dumps(out))
'''


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def seal(root):
    files = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(root.rglob('*')) if p.is_file() and p.name != 'seal.json'
             and not (p.parent == root and p.name.startswith('ssh-') and p.suffix == '.log')}
    dump(root / 'seal.json', {'files': files, 'excluded_live_logs': ['ssh-3090.log', 'ssh-4090.log']})


def verify_seal(root):
    receipt = json.loads((root / 'seal.json').read_text(encoding='utf-8'))
    for relative, expected in receipt['files'].items():
        path = root / relative
        if not path.resolve().is_relative_to(root.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Source session seal mismatch')


def load_config(path):
    c = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    allowed = {'ssh', 'ssh_config', 'remote_python', 'source_token_file',
               'destination_token_file', 'expected_stage', 'roles'}
    if set(c) != allowed or c['expected_stage'] not in ('preflight_only', 'online_ready'):
        raise ValueError('Configuration fields or expected stage invalid')
    if len(c['roles']) != 2 or len(set(c['roles'])) != 2:
        raise ValueError('Exactly two distinct expected service roles required')
    for field in ('remote_python', 'source_token_file', 'destination_token_file'):
        value = c[field]
        if not isinstance(value, str) or not value.startswith('/') or '..' in PurePosixPath(value).parts or '\n' in value or '\r' in value:
            raise ValueError('Invalid fixed remote path')
    return c


def ssh_command(c, host, source=None, args=(), forward=False):
    command = [c['ssh'], '-F', c['ssh_config'], '-o', 'BatchMode=yes', '-T']
    if forward:
        command += ['-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=15',
                    '-o', 'ServerAliveCountMax=2', '-N']
        for local, target in MAPPINGS:
            command += (['-L', '127.0.0.1:%d:127.0.0.1:%d' % (local, target)] if host == '3090'
                        else ['-R', '127.0.0.1:%d:127.0.0.1:%d' % (local, local)])
        return command + [host]
    remote = shlex.join([c['remote_python'], '-c', source, *map(str, args)])
    return command + [host, remote]


def windows_identity(pid):
    if os.name != 'nt':
        raise RuntimeError('This lifecycle manager requires Windows')
    script = ("$ErrorActionPreference='Stop';$p=Get-CimInstance Win32_Process -Filter 'ProcessId=" + str(int(pid)) + "';"
              "if($null -eq $p){exit 3};"
              "$p|Select-Object ProcessId,CommandLine,ExecutablePath,@{N='CreationDate';E={$_.CreationDate.ToUniversalTime().ToFileTimeUtc().ToString()}}|ConvertTo-Json -Compress")
    r = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                       creationflags=CREATE_NO_WINDOW, timeout=20, check=False, text=True)
    if r.returncode == 3:
        raise ProcessLookupError('Recorded process has exited')
    r.check_returncode()
    raw = json.loads(r.stdout)
    if not raw['CommandLine'] or not raw['ExecutablePath']:
        raise RuntimeError('Actual process command unavailable')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, int(pid))
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        creation, exited, ktime, utime = (wintypes.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exited), ctypes.byref(ktime), ctypes.byref(utime)):
            raise ctypes.WinError(ctypes.get_last_error())
        exact_start = creation.dwLowDateTime | (creation.dwHighDateTime << 32)
        # CIM timestamps have microsecond precision; kernel process handles retain 100ns.
        if exact_start // 10 != int(raw['CreationDate']) // 10:
            raise RuntimeError('Process reused while recording identity')
    finally:
        kernel.CloseHandle(handle)
    return {'pid': int(raw['ProcessId']), 'command_line': raw['CommandLine'],
            'executable': raw['ExecutablePath'], 'creation_filetime': exact_start}


def owned_identity_matches(expected, actual):
    return all(expected.get(k) == actual.get(k) for k in
               ('pid', 'command_line', 'executable', 'creation_filetime'))


def terminate_owned(expected, identity=windows_identity):
    """Validate command and start time, then terminate the same open process handle."""
    if not owned_identity_matches(expected, identity(expected['pid'])):
        raise RuntimeError('Process identity changed; refused cleanup')
    if os.name != 'nt':
        raise RuntimeError('Windows process handles required')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x0001 | 0x1000 | 0x00100000, False, expected['pid'])
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        creation, exited, ktime, utime = (wintypes.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exited), ctypes.byref(ktime), ctypes.byref(utime)):
            raise ctypes.WinError(ctypes.get_last_error())
        actual_start = creation.dwLowDateTime | (creation.dwHighDateTime << 32)
        if actual_start != expected['creation_filetime']:
            raise RuntimeError('PID reused before process handle opened; refused cleanup')
        if not kernel.TerminateProcess(handle, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        if kernel.WaitForSingleObject(handle, 10000) != 0:
            raise RuntimeError('Owned SSH process did not exit in time')
    finally:
        kernel.CloseHandle(handle)


class Backend:
    identity = staticmethod(windows_identity)
    terminate = staticmethod(terminate_owned)

    @staticmethod
    def spawn(command, log):
        return subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                creationflags=CREATE_NO_WINDOW)

    @staticmethod
    def run(command):
        return subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW,
                              timeout=30, check=True, text=True).stdout

    @staticmethod
    def copy_token(c):
        read = ssh_command(c, '3090', TOKEN_READ_SOURCE, [c['source_token_file']])
        write = ssh_command(c, '4090', TOKEN_WRITE_SOURCE, [c['destination_token_file']])
        source = subprocess.Popen(read, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
        destination = None
        try:
            destination = subprocess.Popen(write, stdin=source.stdout, stdout=subprocess.PIPE,
                                           stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
            source.stdout.close()
            output, _ = destination.communicate(timeout=30)
            source.wait(timeout=10)
            # Preserve destination ownership even when the source exits unsuccessfully.
            metadata = json.loads(output.decode('utf-8')) if destination.returncode == 0 else None
            if source.returncode or destination.returncode:
                if metadata:
                    return metadata, 'source_transfer_failed'
                raise RuntimeError('Secret transfer failed; token bytes were not recorded')
            return metadata, None
        finally:
            for process in (source, destination):
                if process is not None and process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)


def classify_health(responses, roles, expected):
    if len(responses) != 2:
        raise RuntimeError('Exactly two authenticated health replies required')
    for response, role in zip(responses, roles):
        if response.get('role') != role:
            raise RuntimeError('Health role mismatch')
        phase, stage = response.get('phase'), response.get('stage')
        if expected == 'preflight_only':
            if phase != 'ready_preflight_only':
                raise RuntimeError('Expected explicit preflight-only health')
        elif stage != 'online_ready' or phase == 'ready_preflight_only':
            raise RuntimeError('Preflight health cannot establish online readiness')
    return 'authenticated_transport_preflight_only' if expected == 'preflight_only' else 'authenticated_transport_online_stage_only'


class Manager:
    def __init__(self, c, root, backend=None):
        self.c, self.root, self.backend = c, Path(root), backend or Backend()
        self.state = {'status': 'preparing', 'model_calls': 0, 'GUI_actions': 0,
                      'token_bytes_in_artifacts': False, 'config': c, 'processes': []}
        self.handles, self.logs = [], []

    def save(self):
        dump(self.root / 'state.json', self.state)

    def start(self):
        self.root.mkdir(parents=True, exist_ok=False)
        self.save()
        try:
            metadata, failure = self.backend.copy_token(self.c)
            self.state['copied_token_identity'] = metadata
            self.save()
            if failure:
                raise RuntimeError(failure)
            for host in ('3090', '4090'):
                command = ssh_command(self.c, host, forward=True)
                log = (self.root / ('ssh-' + host + '.log')).open('wb')
                self.logs.append(log)
                process = self.backend.spawn(command, log)
                self.handles.append(process)
                try:
                    actual = self.backend.identity(process.pid)
                except Exception:
                    # This still-live Popen handle belongs to exactly this spawn, even if CIM fails.
                    process.terminate()
                    process.wait(timeout=10)
                    self.state['spawn_identity_failure_cleaned_by_own_handle'] = True
                    raise
                # Query the actual command after creation, not an inferred command list.
                actual['requested_argv'] = command
                self.state['processes'].append(actual)
                self.save()
            for attempt in range(10):
                try:
                    self.state['health'] = self.health()
                    break
                except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    if attempt == 9:
                        raise
                    time.sleep(1)
            self.state['status'] = self.state['health']['status']
            self.snapshot_logs('initial-log-snapshots')
            self.save()
            seal(self.root)
            return self.state
        except Exception as error:
            # Error text from remote requests never enters the artifact.
            self.state.update(status='technical_failure', error_type=type(error).__name__)
            self.save()
            self.cleanup()
            raise
        finally:
            for log in self.logs:
                log.close()

    def health(self):
        for record in self.state['processes']:
            if not owned_identity_matches(record, self.backend.identity(record['pid'])):
                raise RuntimeError('Bridge identity changed')
        replies = {}
        for host, token, ports in [('3090', self.c['source_token_file'], [18127, 18223]),
                                   ('4090', self.c['destination_token_file'], [28427, 28423])]:
            command = ssh_command(self.c, host, HEALTH_SOURCE,
                                  [token, json.dumps(ports), json.dumps(SAFE_HEALTH_FIELDS)])
            data = json.loads(self.backend.run(command))
            # Apply the allowlist locally too, including against unexpected remote output.
            data = [{k: v for k, v in item.items() if k in SAFE_HEALTH_FIELDS and
                     isinstance(v, (str, int, float, bool, type(None)))} for item in data]
            classify_health(data, self.c['roles'], self.c['expected_stage'])
            replies[host] = data
        return {'status': classify_health(replies['4090'], self.c['roles'], self.c['expected_stage']),
                'authenticated_health': replies, 'inference_verified': False,
                'GUI_run_ready': False, 'method': 'Bearer GET /health only, zero inference'}

    def cleanup(self):
        errors = []
        for record in reversed(self.state['processes']):
            try:
                self.backend.terminate(record)
                record['cleanup'] = 'same_handle_terminated'
            except ProcessLookupError:
                record['cleanup'] = 'already_exited_no_signal'
            except Exception as error:
                errors.append(type(error).__name__)
                record['cleanup'] = 'refused_or_unavailable'
        token = self.state.get('copied_token_identity')
        if token:
            try:
                command = ssh_command(self.c, '4090', TOKEN_DELETE_SOURCE,
                                      [self.c['destination_token_file'], json.dumps(token)])
                result = json.loads(self.backend.run(command))
                self.state['token_cleanup'] = bool(result.get('removed'))
            except Exception as error:
                errors.append(type(error).__name__)
                self.state['token_cleanup'] = False
        self.state['cleanup_errors'] = errors
        self.state['cleanup_status'] = 'owned_cleanup_complete' if not errors else 'cleanup_requires_review'
        self.snapshot_logs('cleanup-log-snapshots')
        self.save()
        seal(self.root)
        return self.state

    def snapshot_logs(self, name):
        source = Path(self.state.get('source_session', self.root))
        target = self.root / name
        target.mkdir(exist_ok=False)
        for file in source.glob('ssh-*.log'):
            (target / file.name).write_bytes(file.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('start', 'inspect', 'stop'))
    parser.add_argument('--config', type=Path)
    parser.add_argument('--session', type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'start':
        if not args.config:
            parser.error('start requires --config')
        manager = Manager(load_config(args.config), args.session)
        state = manager.start()
    else:
        verify_seal(args.session)
        previous = json.loads((args.session / 'state.json').read_text(encoding='utf-8'))
        # Never rewrite a sealed initial session; each inspection/cleanup has its own linked receipt.
        operation = args.session / ('operation-' + str(time.time_ns()))
        operation.mkdir(exist_ok=False)
        manager = Manager(previous['config'], operation)
        manager.state = previous
        manager.state['source_session'] = str(args.session)
        manager.state['source_state_sha256'] = hashlib.sha256((args.session / 'state.json').read_bytes()).hexdigest()
        if args.action == 'inspect':
            state = manager.health()
            dump(operation / 'receipt.json', state)
            seal(operation)
        else:
            state = manager.cleanup()
    print(json.dumps({'session': str(manager.root), 'status': state.get('status'),
                      'cleanup_status': state.get('cleanup_status'), 'model_calls': 0}))


if __name__ == '__main__':
    main()
