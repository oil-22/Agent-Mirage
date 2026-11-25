"""File and process utilities for the isolated temporal-gate panel."""

import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import threading


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def hash_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def put(path, raw):
    with Path(path).open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def save(path, value):
    put(path, canonical(value) + b'\n')


def verify_input(root):
    manifest = load(root / 'manifest.json')
    assert all(sha(root / p) == h for p, h in manifest['files'].items()), 'frozen input SHA mismatch'
    return manifest


def process(pid=None):
    pid = os.getpid() if pid is None else int(pid)
    d = Path('/proc') / str(pid)
    fields = (d / 'stat').read_text().rsplit(') ', 1)[1].split()
    return {'pid': pid, 'uid': d.stat().st_uid, 'start_ticks': fields[19],
            'cmdline': (d / 'cmdline').read_bytes().decode('utf-8').strip('\0').split('\0')}


class Child:
    """A single strictly sequenced private JSON stream per owned child."""
    def __init__(self, cmd, log, **kw):
        self.log = Path(log).open('xb')
        try:
            self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
                                      text=False, **kw)
        except BaseException:
            self.log.close()
            raise
        self.queue = queue.Queue()
        self.n = 0
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        try:
            for line in self.p.stdout:
                self.queue.put(line)
        finally:
            self.queue.put(None)

    def read(self, timeout):
        try:
            item = self.queue.get(timeout=timeout)
        except queue.Empty as exc:
            raise TimeoutError(f'No work response from owned process {self.p.pid}; log: {self.log.name}') from exc
        if item is None:
            raise RuntimeError(f'Owned worker exited before response ({self.p.poll()}); log: {self.log.name}')
        row = json.loads(item)
        if row.get('error'):
            raise RuntimeError(f'Owned worker error: {row["error"]}')
        return row

    def call(self, op, data=None, timeout=35):
        self.n += 1
        self.p.stdin.write(canonical({'seq': self.n, 'op': op, 'data': data}) + b'\n')
        self.p.stdin.flush()
        row = self.read(timeout)
        assert row['seq'] == self.n
        return row['result']

    def close(self):
        try:
            self.p.stdin.close()
            try:
                return self.p.wait(timeout=35)
            except subprocess.TimeoutExpired:
                self.p.terminate()  # Only this locally spawned child, never an enumerated PID.
                return self.p.wait(timeout=10)
        finally:
            self.reader.join(timeout=2)
            self.p.stdout.close()
            self.log.close()


def serve(handlers):
    import sys
    import traceback
    n = 0
    for line in sys.stdin.buffer:
        n += 1
        try:
            value = json.loads(line)
            assert set(value) == {'seq', 'op', 'data'} and value['seq'] == n
            result = handlers[value['op']](value['data'])
            reply = {'seq': n, 'result': result}
        except Exception as exc:
            traceback.print_exc(file=sys.stderr)
            reply = {'seq': n, 'error': f'{type(exc).__name__}: {exc}'}
            sys.stdout.buffer.write(canonical(reply) + b'\n'); sys.stdout.buffer.flush()
            raise
        sys.stdout.buffer.write(canonical(reply) + b'\n'); sys.stdout.buffer.flush()
