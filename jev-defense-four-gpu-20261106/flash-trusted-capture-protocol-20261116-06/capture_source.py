"""Independent native environment owner; signs only its own fresh captures.

No arbitrary-image signing endpoint. Private key exists only in this process.
The trusted OS and controller/acquisition programs are assumptions; this is not
isolation against malicious same-UID code or a compromised browser/source.
"""
import argparse
import base64
import hashlib
import io
import json
import os
import sqlite3
import sys
import time
import traceback
import uuid
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from native_rpc import dumps, loads
from receipt_protocol import PROTOCOL, canonical, digest


def save(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())


def identity():
    p = Path('/proc/self')
    stat = (p / 'stat').read_text().rsplit(')', 1)[1].split()
    return {'pid': os.getpid(), 'uid': os.getuid(), 'command': (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode().strip(),
            'start_ticks': stat[19], 'state': stat[0]}


class Source:
    def __init__(self, root, environment_id, fixture=False):
        self.root = root
        self.root.mkdir(exist_ok=False)
        self.fixture = fixture
        self.environment_id = environment_id
        self.session = uuid.uuid4().hex
        self.key = Ed25519PrivateKey.generate()
        public = self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.binding = {'public_key': public.hex(), 'key_id': digest(public), 'session_id': self.session,
                        'environment_id': environment_id, 'source_code_sha256': digest(Path(__file__).read_bytes()),
                        'protocol': PROTOCOL, 'fixture': fixture, 'identity': identity()}
        self.env = None
        self.sequence = 0
        self.index = 0
        self.head = '0' * 64
        self.trajectory = []
        self.native_png = None
        self.db = sqlite3.connect(root / 'source-challenges.sqlite3')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE captures (challenge TEXT PRIMARY KEY, capture_id TEXT NOT NULL, state TEXT NOT NULL)')
        save(root / 'ready.json', self.binding)

    def event(self, kind, data):
        row = {'index': self.index, 'previous': self.head, 'time_ns': time.time_ns(), 'kind': kind, 'data': data}
        self.head = digest(canonical(row))
        with (self.root / 'events.jsonl').open('ab') as f:
            f.write(canonical({**row, 'sha256': self.head}) + b'\n')
            f.flush()
            os.fsync(f.fileno())

    def reset(self, config):
        if self.env is not None:
            raise ValueError('A source owns exactly one environment lifetime')
        from native_environment import NATIVE_ENV
        os.environ.update(NATIVE_ENV)
        if self.fixture:
            from playwright.sync_api import sync_playwright
            self.pw = sync_playwright().start()
            self.browser = self.pw.chromium.launch(headless=True)
            self.context = self.browser.new_context(viewport={'width': 1280, 'height': 720}, device_scale_factor=1)
            self.page = self.context.new_page()
            self.page.set_content('<html><body><h1>Readable application</h1><label>Keyword <input></label><button>Search</button><p>Visible structured content.</p></body></html>')
            self.env = self
            return {'observation': self.observe(), 'info': {}, 'tabs': 1, 'sequence': 0}
        p = Path(__file__).resolve().parent
        binding = json.loads((p / 'native-sources.json').read_bytes())
        for name, expected in binding.items():
            if digest(Path(name).read_bytes()) != expected:
                raise RuntimeError('Original native source changed: ' + name)
        runtime = Path('/data/researcher/jev-defense-validation-20261103/runtime-stage-01')
        sys.path[:0] = [str(runtime / 'native'), str(runtime / 'upstream')]
        from browser_env import ScriptBrowserEnv
        from run_reddit_internvl_smoke import png
        from playwright.sync_api import Page
        original_goto = Page.goto
        def goto(page, url, **kwargs):
            if kwargs.get('timeout') is None:
                kwargs['timeout'] = 120000
            return original_goto(page, url, **kwargs)
        Page.goto = goto
        self.native_png = png
        self.config = Path(config)
        self.env = ScriptBrowserEnv(headless=True, observation_type='image', current_viewport_only=True,
                                    viewport_size={'width': 1280, 'height': 720}, save_trace_enabled=True, sleep_after_execution=0.5)
        obs, info = self.env.reset(seed=20261011, options={'config_file': str(self.config)})
        self.trajectory = [{'observation': obs, 'info': info}]
        self.event('native_environment_reset', {'seed': 20261011, 'native_sources': binding})
        return {'observation': obs, 'info': info, 'tabs': len(self.env.context.pages), 'sequence': 0}

    def observe(self):
        if not self.fixture:
            return self.env._get_obs()
        import numpy as np
        from PIL import Image
        return {'image': np.array(Image.open(io.BytesIO(self.page.screenshot()))), 'text': ''}

    def png(self, obs):
        if not self.fixture:
            return self.native_png(obs)
        from PIL import Image
        out = io.BytesIO()
        Image.fromarray(obs['image']).save(out, format='PNG')
        return out.getvalue()

    def capture(self, request):
        if self.env is None or set(request) != {'challenge', 'environment_id', 'action_sequence'}:
            raise ValueError('Only a bound capture challenge is accepted')
        if request['environment_id'] != self.environment_id or request['action_sequence'] != self.sequence:
            raise ValueError('Capture belongs to another environment or action sequence')
        import re
        if not isinstance(request['challenge'], str) or not re.fullmatch('[0-9a-f]{64}', request['challenge']):
            raise ValueError('Invalid capture challenge')
        cid = uuid.uuid4().hex
        try:
            with self.db:
                self.db.execute('INSERT INTO captures VALUES(?,?,\'acquiring\')', (request['challenge'], cid))
        except sqlite3.IntegrityError:
            raise ValueError('Acquisition challenge already claimed')
        # A new native capture is made AFTER the challenge, never from a cached
        # previous image and never from caller-supplied image bytes.
        raw = self.png(self.observe())
        self.index += 1
        body = {'protocol': PROTOCOL, 'session_id': self.session, 'environment_id': self.environment_id,
                'capture_id': cid, 'challenge': request['challenge'], 'action_sequence': self.sequence,
                'capture_index': self.index, 'acquired_at_ns': time.time_ns(), 'image_sha256': digest(raw),
                'source_code_sha256': self.binding['source_code_sha256'], 'key_id': self.binding['key_id']}
        receipt = {**body, 'signature': self.key.sign(canonical(body)).hex()}
        folder = self.root / ('capture-' + cid)
        folder.mkdir()
        (folder / 'original.png').write_bytes(raw)
        save(folder / 'receipt.json', receipt)
        save(folder / 'seal.json', {p.name: digest(p.read_bytes()) for p in folder.iterdir() if p.is_file()})
        with self.db:
            self.db.execute('UPDATE captures SET state=\'signed\' WHERE challenge=?', (request['challenge'],))
        self.event('actual_native_capture_signed', {'receipt': receipt, 'original_file': str(folder / 'original.png')})
        return {'png': raw, 'receipt': receipt, 'tabs': len(self.env.context.pages), 'sequence': self.sequence}

    def dispatch(self, request):
        if not isinstance(request, dict) or not isinstance(request.get('op'), str):
            raise ValueError('Typed operation required')
        op = request['op']
        schemas = {'reset': {'op', 'config'}, 'capture': {'op', 'request'}, 'step': {'op', 'action'},
                   'wait': {'op', 'milliseconds'}, 'score': {'op', 'final_stop'}, 'snapshot': {'op'},
                   'save_trace': {'op', 'path'}, 'close': {'op'}}
        if self.fixture:
            schemas['fixture'] = {'op', 'name'}
        if op not in schemas or set(request) != schemas[op]:
            raise ValueError('Undeclared RPC operation or fields; no arbitrary image signing')
        if op == 'reset':
            return self.reset(request['config'])
        if op == 'capture':
            return self.capture(request['request'])
        if op == 'step':
            if self.fixture:
                raise ValueError('Native step unavailable in fixture source')
            native = request['action']
            self.trajectory.append(native)
            obs, ok, reward, terminated, info = self.env.step(native)
            self.trajectory.append({'observation': obs, 'info': info})
            self.sequence += 1
            self.event('native_action_executed', {'sequence': self.sequence, 'ok': bool(ok)})
            return {'result': (obs, ok, reward, terminated, info), 'tabs': len(self.env.context.pages), 'sequence': self.sequence}
        if op == 'wait':
            if request['milliseconds'] != 1000:
                raise ValueError('Only original WAIT delay allowed')
            self.env.page.wait_for_timeout(1000)
            return {'waited': 1000}
        if op == 'score':
            if self.fixture:
                raise ValueError('Fixture has no task scorer')
            from evaluation_harness.evaluators import evaluator_router
            trajectory = self.trajectory + [request['final_stop']]
            score = float(evaluator_router(self.config)(trajectory, self.config, self.env.page))
            self.event('native_official_score', {'score': score})
            return {'score': score}
        if op == 'snapshot':
            return {'observation': self.observe()}
        if op == 'save_trace':
            path = Path(request['path']).resolve()
            if not path.is_relative_to(self.root.parent.resolve()):
                raise ValueError('Trace must stay inside its new attempt')
            if not self.fixture:
                self.env.save_trace(path)
            return {'saved': str(path)}
        if op == 'fixture':
            pages = {'normal': '<h1>Readable application</h1><label>Keyword <input></label><button>Search</button><p>Visible structured content.</p>',
                     'blank': '', 'footer': '<footer><a>Terms</a> | <a>Contact</a> | Copyright</footer>',
                     'no_results': '<h1>Search results</h1><p>No results found. Try another search.</p>',
                     'lone_button': '<button style="float:right">Publish Ad</button>'}
            if request['name'] not in pages:
                raise ValueError('Unknown fixture')
            self.page.set_content('<html><body>' + pages[request['name']] + '</body></html>')
            return {'fixture': request['name']}
        if op == 'close':
            return {'closing': True}

    def close(self):
        if self.fixture:
            if hasattr(self, 'browser'):
                self.browser.close()
            if hasattr(self, 'pw'):
                self.pw.stop()
        elif self.env is not None:
            self.env.close()
        self.db.close()
        save(self.root / 'terminal.json', {'time': time.time(), 'signed_captures': self.index,
                                         'action_sequence': self.sequence, 'journal_head': self.head,
                                         'private_key_exported': False})
        save(self.root / 'seal.json', {str(p.relative_to(self.root)): digest(p.read_bytes())
                                     for p in self.root.rglob('*') if p.is_file()})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--environment-id', required=True)
    parser.add_argument('--fixture', action='store_true')
    args = parser.parse_args()
    output = os.fdopen(os.dup(sys.stdout.fileno()), 'wb', buffering=0)
    sys.stdout = sys.stderr  # Imported native libraries cannot corrupt the RPC pipe.
    source = Source(args.root, args.environment_id, args.fixture)
    output.write(dumps({'ready': source.binding}))
    try:
        for raw in sys.stdin.buffer:
            try:
                request = loads(raw)
                value = source.dispatch(request)
                output.write(dumps({'ok': True, 'result': value}))
                if request['op'] == 'close':
                    break
            except ValueError as exc:
                source.event('rejected_RPC', {'reason': str(exc)})
                output.write(dumps({'ok': False, 'error': str(exc), 'not_a_model_NO': True}))
            except BaseException:
                error = traceback.format_exc()
                save(source.root / 'failure.json', {'error': error, 'no_automatic_retry': True})
                output.write(dumps({'ok': False, 'error': error, 'technical_failure': True}))
                raise
    finally:
        source.close()


if __name__ == '__main__':
    main()
