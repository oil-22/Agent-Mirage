"""Controller proxy to the isolated original native environment and acquisition."""
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

from native_rpc import dumps, loads
from receipt_protocol import ReceiptVerifier, digest


class CaptureClient:
    def __init__(self, root, *, fixture=False):
        self.root = Path(root)
        self.log = (self.root / 'capture-source.log').open('xb')
        argv = [sys.executable, '-B', '-u', str(Path(__file__).with_name('capture_source.py')),
                '--root', str(self.root / 'trusted-source'), '--environment-id', uuid.uuid4().hex]
        if fixture:
            argv.append('--fixture')
        self.child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
                                      env={**os.environ, 'CUDA_VISIBLE_DEVICES': '', 'PYTHONDONTWRITEBYTECODE': '1'})
        ready = self.read()['ready']
        if ready['source_code_sha256'] != digest(Path(__file__).with_name('capture_source.py').read_bytes()):
            raise RuntimeError('Unexpected capture-source program')
        if ready['identity']['pid'] != self.child.pid or ready['identity']['uid'] != os.getuid():
            raise RuntimeError('Unexpected acquisition process identity')
        self.ready = ready
        self.verifier = ReceiptVerifier(self.root / 'receipt-verifier.sqlite3', public_key=ready['public_key'],
                                        session_id=ready['session_id'], environment_id=ready['environment_id'],
                                        source_code_sha256=ready['source_code_sha256'])
        self.sequence = 0
        self.context = SimpleNamespace(pages=[])
        self.page = SimpleNamespace(wait_for_timeout=lambda ms: self.rpc('wait', milliseconds=ms))

    def read(self):
        raw = self.child.stdout.readline()
        if not raw:
            raise RuntimeError('Acquisition process closed pipe; inspect its preserved log')
        return loads(raw)

    def rpc(self, op, **kwargs):
        self.child.stdin.write(dumps({'op': op, **kwargs}))
        self.child.stdin.flush()
        response = self.read()
        if not response['ok']:
            raise RuntimeError('Acquisition RPC refused: ' + response['error'])
        return response['result']

    def bind_state(self, result):
        self.sequence = result['sequence']
        self.context.pages = [None] * result['tabs']

    def reset(self, seed, options):
        if seed != 20261011 or set(options) != {'config_file'}:
            raise ValueError('Original native seed/config required')
        result = self.rpc('reset', config=options['config_file'])
        self.bind_state(result)
        return result['observation'], result['info']

    def acquire(self):
        expected = self.verifier.issue(self.sequence)
        result = self.rpc('capture', request=expected)
        self.bind_state(result)
        return result['png'], result['receipt'], expected

    def step(self, action):
        result = self.rpc('step', action=action)
        self.bind_state(result)
        return result['result']

    def _get_obs(self):
        return self.rpc('snapshot')['observation']

    def score(self, final_stop):
        return self.rpc('score', final_stop=final_stop)['score']

    def save_trace(self, path):
        return self.rpc('save_trace', path=str(path))

    def close(self):
        error = None
        try:
            if self.child.poll() is None:
                try:
                    self.rpc('close')
                except (RuntimeError, BrokenPipeError) as exc:
                    error = exc
            self.child.wait(timeout=60)
            if self.child.returncode != 0:
                raise RuntimeError('Acquisition process failed; no automatic retry')
            if error is not None:
                raise error
        finally:
            self.log.flush()
            self.log.close()
