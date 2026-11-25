"""Own one isolated Chromium. Sign screenshots here; never substitute image bytes."""

import asyncio
import base64
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from live_common import canonical, hash_bytes, process, save, serve, sha, verify_input
from receipt_protocol import PROTOCOL

ROOT = Path(__file__).resolve().parent


class Source:
    def __init__(self, out, plan):
        assert os.getuid() == 1033
        self.out, self.plan = out, plan
        self.cases = {row['id']: row for row in plan['cases']}
        self.width, self.height = plan['viewport']
        self.key = Ed25519PrivateKey.generate()
        self.public = self.key.public_key().public_bytes_raw()
        self.loop = asyncio.new_event_loop()
        self.transport = self.case = self.cdp_session = None
        self.ordinal = 0
        self.chrome_err = (out / 'chrome-stderr.log').open('xb')
        profile = out.parent.parent / 'browser-profile'
        assert not profile.exists()
        to_chrome, from_driver = os.pipe()
        to_driver, from_chrome = os.pipe()
        read_fd, write_fd = [fcntl.fcntl(fd, fcntl.F_DUPFD_CLOEXEC, 20) for fd in (to_chrome, from_chrome)]
        try:
            self.chrome = subprocess.Popen([
                sys.executable, '-B', '-c',
                'import os,sys; a,b=map(int,sys.argv[1:3]); os.dup2(a,3); os.dup2(b,4); '
                'os.close(a); os.close(b); os.execv(sys.argv[3],sys.argv[3:])', str(read_fd), str(write_fd),
                '/usr/bin/google-chrome-stable', '--headless', '--disable-gpu', '--disable-dev-shm-usage',
                '--no-first-run', '--no-default-browser-check', '--disable-background-networking',
                '--remote-debugging-pipe', '--user-data-dir=' + str(profile), '--window-size=1280,720', 'about:blank',
            ], stdin=subprocess.DEVNULL, stdout=self.chrome_err, stderr=self.chrome_err,
                pass_fds=(read_fd, write_fd))
        except BaseException:
            os.close(to_driver); os.close(from_driver); self.chrome_err.close(); raise
        finally:
            for fd in (to_chrome, from_chrome, read_fd, write_fd):
                os.close(fd)
        self.chrome_identity = process(self.chrome.pid)
        self.browser_input = os.fdopen(from_driver, 'wb')
        self.browser_output = os.fdopen(to_driver, 'rb', buffering=0)

    def run(self, coro):
        return self.loop.run_until_complete(asyncio.wait_for(coro, timeout=20))

    async def connect(self):
        self.incoming = asyncio.StreamReader(limit=20 * 1024**2)
        self.transport, _ = await self.loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(self.incoming),
                                                               self.browser_output)
        self.seq = 0
        version = await self.cdp('Browser.getVersion')
        self.chrome_identity = process(self.chrome.pid)
        argv_words = ' '.join(self.chrome_identity['cmdline']).split()
        assert '--remote-debugging-pipe' in argv_words and not any(x.startswith('--remote-debugging-port') for x in argv_words)
        assert self.chrome_identity['uid'] == os.getuid() and Path(f'/proc/{self.chrome.pid}/exe').resolve().name == 'chrome'
        self.target = (await self.cdp('Target.createTarget', url='about:blank'))['targetId']
        self.cdp_session = (await self.cdp('Target.attachToTarget', targetId=self.target, flatten=True))['sessionId']
        await self.cdp('Page.enable')
        await self.cdp('Emulation.setDeviceMetricsOverride', width=self.width, height=self.height,
                       deviceScaleFactor=1, mobile=False)
        proof = {'source': process(), 'browser': self.chrome_identity, 'browser_version': version['product'],
                 'debug_transport': 'inherited anonymous pipes (no listener)', 'target': self.target, 'device_scale_factor': 1,
                 'fixture_sha256': sha(ROOT / 'fixture.html'), 'source_code_sha256': sha(Path(__file__))}
        save(self.out / 'source.json', proof)
        return proof

    async def cdp(self, method, **payload):
        self.seq += 1
        req = {'id': self.seq, 'method': method, 'params': payload}
        if self.cdp_session is not None and not method.startswith(('Target.', 'Browser.')):
            req['sessionId'] = self.cdp_session
        self.browser_input.write(canonical(req) + b'\0'); self.browser_input.flush()
        while True:
            msg = json.loads((await self.incoming.readuntil(b'\0'))[:-1])
            if msg.get('id') == self.seq:
                if 'error' in msg:
                    raise RuntimeError(f"Chromium {method}: {msg['error']}")
                return msg.get('result', {})
            assert 'method' in msg, 'Unexpected CDP reply sequence'

    async def js(self, expression):
        answer = await self.cdp('Runtime.evaluate', expression=expression, returnByValue=True)
        if 'exceptionDetails' in answer:
            raise RuntimeError('Browser fixture expression failed: ' + str(answer['result']))
        return answer['result'].get('value')

    async def snapshot(self):
        value = await self.js('window.fixtureSnapshot?.()')
        assert value and self.case['action'] == value['kind']
        return value

    async def new(self, case_id):
        assert self.case is None
        self.case = case = self.cases[case_id]
        self.session = uuid.uuid4().hex
        self.environment = self.target + ':' + self.session
        self.ordinal = self.index = 0
        self.seen = set()
        self.dest = self.out / case_id
        self.dest.mkdir()
        # Use a distinct top-level navigation for every trial, then leave the
        # same CDP target/loader alive for the whole action/capture loop.
        url = (ROOT / 'fixture.html').as_uri() + f"?kind={case['action']}&delay={case['delay_ms']}&session={self.session}"
        nav = await self.cdp('Page.navigate', url=url)
        assert nav.get('loaderId') and 'errorText' not in nav
        self.loader = nav['loaderId']
        for _ in range(80):
            value = await self.js('window.fixtureSnapshot?.()')
            if value and [e['kind'] for e in value['events']] == ['initial_painted']:
                break
            await asyncio.sleep(.025)
        else:
            raise RuntimeError('Fixture did not paint')
        await self.verify_document()
        identity = {'session_id': self.session, 'environment_id': self.environment, 'loader': self.loader,
                    'target': self.target, 'source_code_sha256': sha(Path(__file__)), 'public_key': self.public.hex(),
                    'viewport': [self.width, self.height], 'initial_dom': value}
        save(self.dest / 'session.json', identity)
        return identity

    async def verify_document(self):
        frame = (await self.cdp('Page.getFrameTree'))['frameTree']['frame']
        assert frame['loaderId'] == self.loader and frame['url'].endswith('&session=' + self.session)

    async def dispatch(self, data):
        assert data == 1 and self.ordinal == 0 and self.index == 1
        await self.verify_document()
        before = await self.snapshot()
        assert [e['kind'] for e in before['events']] == ['initial_painted']
        self.ordinal = 1  # Claim once before sending any input; no retry on an uncertain transport failure.
        begin = time.monotonic_ns()
        kind = self.case['action']
        if kind == 'search':
            center = await self.js("Array.from((()=>{const r=document.querySelector('#search').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]})())")
            assert 0 < center[0] < self.width and 0 < center[1] < self.height
            x, y = center
            native = {'type': 'click', 'x': round(1000*x/self.width, 5), 'y': round(1000*y/self.height, 5)}
            await self.cdp('Input.dispatchMouseEvent', type='mousePressed', x=x, y=y, button='left', buttons=1, clickCount=1)
            await self.cdp('Input.dispatchMouseEvent', type='mouseReleased', x=x, y=y, button='left', buttons=0, clickCount=1)
        elif kind == 'type':
            assert before['active'] == 'city' and before['city'] == ''
            native = {'type': 'type', 'text': 'Virginia'}
            await self.cdp('Input.insertText', text=native['text'])
        else:
            assert before['scroll_top'] + before['client_height'] == before['scroll_height']
            native = {'type': 'scroll', 'direction': 'down'}
            await self.cdp('Input.dispatchMouseEvent', type='mouseWheel', x=900, y=550, deltaX=0, deltaY=664)
        expected = 'wheel' if kind == 'boundary' else 'input'
        for _ in range(12):
            after = await self.snapshot()
            events = [e for e in after['events'] if e['kind'] == expected]
            if events:
                break
            await asyncio.sleep(.01)
        assert len(events) == 1 and events[0]['trusted'] is True
        result = {'action_sequence': 1, 'native_action': native, 'environment': self.environment, 'target': self.target,
                  'loader': self.loader, 'send_begin_ns': begin, 'send_end_ns': time.monotonic_ns(),
                  'before': before, 'after': after, 'dispatch_calls': 1}
        save(self.dest / 'action.json', result)
        return result

    async def capture(self, expected):
        assert set(expected) == {'challenge', 'environment_id', 'action_sequence'}
        assert expected['environment_id'] == self.environment and expected['action_sequence'] == self.ordinal
        assert expected['challenge'] not in self.seen
        self.seen.add(expected['challenge'])
        await self.verify_document()
        before = await self.snapshot()
        started = time.monotonic_ns()
        png = (await self.cdp('Page.captureScreenshot', format='png', fromSurface=True, captureBeyondViewport=False))['data']
        finished = time.monotonic_ns()
        raw = base64.b64decode(png, validate=True)
        assert raw.startswith(b'\x89PNG\r\n\x1a\n')
        self.index += 1
        body = {'protocol': PROTOCOL, 'session_id': self.session, 'environment_id': self.environment,
                'capture_id': uuid.uuid4().hex, 'challenge': expected['challenge'], 'action_sequence': self.ordinal,
                'capture_index': self.index, 'acquired_at_ns': time.time_ns(), 'image_sha256': hash_bytes(raw),
                'source_code_sha256': sha(Path(__file__)), 'key_id': hash_bytes(self.public)}
        receipt = {**body, 'signature': self.key.sign(canonical(body)).hex()}
        after = await self.snapshot()
        await self.verify_document()
        audit = {'receipt': receipt, 'scope': self.case['id'], 'constituent_source': 'Page.captureScreenshot',
                 'target': self.target, 'loader': self.loader, 'before': before, 'after': after,
                 'capture_started_ns': started, 'capture_finished_ns': finished}
        save(self.dest / f'capture-{self.index:03}.json', audit)
        return {'png': png, 'receipt': receipt, 'audit': audit}

    async def finish(self, case_id):
        assert self.case['id'] == case_id and self.ordinal == 1
        await self.verify_document()
        result = {'final_dom': await self.snapshot(), 'session_id': self.session, 'environment_id': self.environment,
                  'loader': self.loader, 'capture_count': self.index, 'dispatch_calls': self.ordinal}
        save(self.dest / 'finish.json', result)
        self.case = None
        return result

    def close(self):
        try:
            if self.transport is not None and self.chrome.poll() is None:
                try:
                    self.browser_input.write(canonical({'id': self.seq + 1, 'method': 'Browser.close'}) + b'\0')
                    self.browser_input.flush()
                except OSError:
                    pass
            try:
                self.browser_input.close()
            except OSError:
                pass
            if self.transport is not None:
                self.transport.close()
            else:
                self.browser_output.close()
            try:
                return self.chrome.wait(timeout=6)
            except subprocess.TimeoutExpired:
                self.chrome.terminate()  # This Popen instance only.
                return self.chrome.wait(timeout=5)
        finally:
            self.loop.close()
            self.chrome_err.close()


if __name__ == '__main__':
    from live_common import load
    verify_input(ROOT)
    out = ROOT / 'run' / 'source'
    out.mkdir()
    source = Source(out, load(ROOT / 'live_plan.json'))
    try:
        serve({key: lambda data, fn=method: source.run(fn(data)) for key, method in (
            ('new', source.new), ('action', source.dispatch), ('capture', source.capture), ('finish', source.finish))}
            | {'connect': lambda _: source.run(source.connect())})
    finally:
        save(out / 'exit.json', {'browser_exit': source.close(), 'identity': source.chrome_identity})
