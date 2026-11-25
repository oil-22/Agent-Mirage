"""CPU mocks only: no SSH invocation, tunnel, service, or model request."""
import contextlib
import io
import json
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

import bridge_manager as b


CONFIG = b.load_config(Path(__file__).with_name('bridge_config.example.json'))
SECRET = b'unit-test-secret-never-an-artifact'


class FakeProcess:
    def __init__(self, pid):
        self.pid = pid
        self.terminated = False

    def terminate(self):
        self.terminated = True

    def wait(self, timeout):
        return 0


class FakeBackend:
    def __init__(self, bad_stage=False, identity_failure=False):
        self.procs = []
        self.commands = []
        self.terminated = []
        self.bad_stage = bad_stage
        self.identity_failure = identity_failure
        self.token_removed = False

    def copy_token(self, c):
        return {'created': True, 'dev': 1, 'ino': 2, 'uid': 1033, 'mode': 0o600}, None

    def spawn(self, command, log):
        self.commands.append(command)
        p = FakeProcess(100 + len(self.procs))
        self.procs.append(p)
        return p

    def identity(self, pid):
        if self.identity_failure:
            raise RuntimeError('CIM unavailable')
        return {'pid': pid, 'command_line': 'ssh fixed command ' + str(pid),
                'executable': CONFIG['ssh'], 'creation_filetime': pid * 1000}

    def terminate(self, record):
        actual = self.identity(record['pid'])
        if not b.owned_identity_matches(record, actual):
            raise RuntimeError('refused wrong process')
        self.terminated.append(record['pid'])

    def run(self, command):
        self.commands.append(command)
        if b.TOKEN_DELETE_SOURCE in shlex.split(command[-1]):
            self.token_removed = True
            return '{"removed":true}'
        phase = 'ready' if self.bad_stage else 'ready_preflight_only'
        return json.dumps([{'role': role, 'phase': phase, 'calls': 0,
                            'Authorization': SECRET.decode(), 'token': SECRET.decode()}
                           for role in CONFIG['roles']])


class BridgeTests(unittest.TestCase):
    def test_exact_loopback_mapping_and_no_window(self):
        local = b.ssh_command(CONFIG, '3090', forward=True)
        reverse = b.ssh_command(CONFIG, '4090', forward=True)
        self.assertIn('127.0.0.1:28427:127.0.0.1:18127', local)
        self.assertIn('127.0.0.1:28423:127.0.0.1:18223', local)
        self.assertIn('127.0.0.1:28427:127.0.0.1:28427', reverse)
        self.assertIn('127.0.0.1:28423:127.0.0.1:28423', reverse)
        self.assertIn('ExitOnForwardFailure=yes', local)
        self.assertIn('-N', reverse)
        self.assertIn('-T', reverse)
        with patch.object(b.subprocess, 'Popen') as popen:
            b.Backend.spawn(local, io.BytesIO())
            self.assertEqual(popen.call_args.kwargs['creationflags'], b.CREATE_NO_WINDOW)

    def test_preflight_never_online_ready(self):
        health = [{'role': r, 'phase': 'ready_preflight_only'} for r in CONFIG['roles']]
        self.assertEqual(b.classify_health(health, CONFIG['roles'], 'preflight_only'),
                         'authenticated_transport_preflight_only')
        with self.assertRaises(RuntimeError):
            b.classify_health(health, CONFIG['roles'], 'online_ready')
        health[0]['role'] = 'foreign'
        with self.assertRaises(RuntimeError):
            b.classify_health(health, CONFIG['roles'], 'preflight_only')

    def test_secret_pipe_does_not_capture_source_stdout(self):
        source_stream = io.BytesIO(SECRET)

        class PipeProcess:
            def __init__(self, stdout=None):
                self.stdout = stdout
                self.returncode = 0
            def communicate(self, timeout):
                return b'{"created":true,"dev":1,"ino":2,"uid":1033,"mode":384}', None
            def wait(self, timeout):
                return 0
            def poll(self):
                return self.returncode

        calls = []
        def popen(command, **kwargs):
            calls.append((command, kwargs))
            return PipeProcess(source_stream if len(calls) == 1 else None)
        with patch.object(b.subprocess, 'Popen', side_effect=popen):
            metadata, error = b.Backend.copy_token(CONFIG)
        self.assertIsNone(error)
        self.assertTrue(metadata['created'])
        self.assertIs(calls[1][1]['stdin'], source_stream)
        self.assertIs(calls[0][1]['stderr'], subprocess.DEVNULL)
        self.assertIs(calls[1][1]['stderr'], subprocess.DEVNULL)
        self.assertTrue(source_stream.closed)
        self.assertNotIn(SECRET.decode(), repr([c[0] for c in calls]))
        self.assertIn('os.O_EXCL', b.TOKEN_WRITE_SOURCE)
        self.assertIn('0o600', b.TOKEN_WRITE_SOURCE)
        self.assertIn('os.O_NOFOLLOW', b.TOKEN_WRITE_SOURCE)

    def test_health_headers_and_remote_file_no_token_argument(self):
        self.assertIn("'Authorization':'Bearer '+token.decode('ascii')", b.HEALTH_SOURCE)
        self.assertNotIn(SECRET.decode(), b.HEALTH_SOURCE)
        command = b.ssh_command(CONFIG, '4090', b.HEALTH_SOURCE,
                               [CONFIG['destination_token_file'], '[28427,28423]', '[]'])
        self.assertNotIn(SECRET.decode(), repr(command))

    def run_health_helper(self, public_health=False, mode=0o600):
        calls = []
        fake_os = SimpleNamespace(O_RDONLY=0, O_NOFOLLOW=1, getuid=lambda: 1033,
                                  open=lambda *args: 7,
                                  fstat=lambda _: SimpleNamespace(st_mode=stat.S_IFREG | mode, st_uid=1033),
                                  fdopen=lambda *args: io.BytesIO(SECRET))
        def urlopen(request, timeout):
            calls.append(request)
            if isinstance(request, str):
                if public_health:
                    return io.BytesIO(b'{}')
                raise urllib.error.HTTPError(request, 403, 'unauthorized', {}, None)
            self.assertEqual(request.get_header('Authorization'), 'Bearer ' + SECRET.decode())
            role = CONFIG['roles'][0 if ':18127/' in request.full_url else 1]
            return io.BytesIO(json.dumps({'role': role, 'phase': 'ready_preflight_only'}).encode())
        output = io.StringIO()
        with patch.dict(sys.modules, {'os': fake_os}), patch.object(sys, 'argv',
                ['helper', '/fake/token', '[18127,18223]', json.dumps(b.SAFE_HEALTH_FIELDS)]), \
                patch.object(urllib.request, 'urlopen', side_effect=urlopen), contextlib.redirect_stdout(output):
            exec(compile(b.HEALTH_SOURCE, '<frozen-health-helper>', 'exec'), {})
        return json.loads(output.getvalue()), calls

    def test_health_helper_requires_bearer_before_accepting_both_replies(self):
        responses, calls = self.run_health_helper()
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(x['bearer_required'] for x in responses))
        self.assertNotIn(SECRET.decode(), json.dumps(responses))

    def test_health_helper_rejects_public_endpoint_and_permissive_token_file(self):
        with self.assertRaises(SystemExit) as public:
            self.run_health_helper(public_health=True)
        self.assertEqual(public.exception.code, 43)
        with self.assertRaises(SystemExit) as insecure:
            self.run_health_helper(mode=0o644)
        self.assertEqual(insecure.exception.code, 41)

    def test_successful_start_records_actual_identity_and_filters_secrets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'session'
            backend = FakeBackend()
            manager = b.Manager(CONFIG, root, backend)
            result = manager.start()
            self.assertEqual(result['status'], 'authenticated_transport_preflight_only')
            self.assertFalse(result['health']['GUI_run_ready'])
            self.assertFalse(result['health']['inference_verified'])
            self.assertEqual(len(result['processes']), 2)
            self.assertIn('command_line', result['processes'][0])
            self.assertIn('creation_filetime', result['processes'][0])
            for file in root.rglob('*'):
                if file.is_file():
                    self.assertNotIn(SECRET, file.read_bytes())
            b.verify_seal(root)

    def test_failed_health_closes_only_owned_processes_and_token(self):
        with tempfile.TemporaryDirectory() as temporary:
            backend = FakeBackend(bad_stage=True)
            manager = b.Manager(CONFIG, Path(temporary) / 'session', backend)
            with self.assertRaises(RuntimeError):
                manager.start()
            self.assertEqual(backend.terminated, [101, 100])
            self.assertTrue(backend.token_removed)
            self.assertEqual(manager.state['cleanup_status'], 'owned_cleanup_complete')

    def test_identity_capture_failure_uses_original_popen_handle(self):
        with tempfile.TemporaryDirectory() as temporary:
            backend = FakeBackend(identity_failure=True)
            manager = b.Manager(CONFIG, Path(temporary) / 'session', backend)
            with self.assertRaises(RuntimeError):
                manager.start()
            self.assertTrue(backend.procs[0].terminated)
            self.assertEqual(backend.terminated, [])
            self.assertTrue(manager.state['spawn_identity_failure_cleaned_by_own_handle'])

    def test_pid_reuse_or_command_change_refused(self):
        record = FakeBackend().identity(100)
        for key in ('pid', 'command_line', 'executable', 'creation_filetime'):
            actual = dict(record)
            actual[key] = 'different'
            self.assertFalse(b.owned_identity_matches(record, actual))
        with self.assertRaises(RuntimeError):
            b.terminate_owned(record, identity=lambda _: {**record, 'creation_filetime': 999})

    def test_token_cleanup_checks_inode_uid_mode(self):
        self.assertIn("('dev','ino','uid')", b.TOKEN_DELETE_SOURCE)
        self.assertIn('stat.S_IMODE(s.st_mode)!=0o600', b.TOKEN_DELETE_SOURCE)
        self.assertIn('p.unlink()', b.TOKEN_DELETE_SOURCE)
        self.assertNotIn('rmtree', b.TOKEN_DELETE_SOURCE)

    def test_initial_receipt_immutable_while_live_logs_grow(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'session'
            manager = b.Manager(CONFIG, root, FakeBackend())
            manager.start()
            (root / 'ssh-3090.log').write_bytes(b'late ssh diagnostic')
            b.verify_seal(root)
            state = json.loads((root / 'state.json').read_text())
            state['model_calls'] = 99
            b.dump(root / 'state.json', state)
            with self.assertRaises(RuntimeError):
                b.verify_seal(root)

    def test_configuration_refuses_inline_secret_unknown_field_and_wrong_stage(self):
        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary) / 'config.json'
            for change in ({'token': SECRET.decode()}, {'expected_stage': 'ready'},
                           {'source_token_file': '/x/../token'}):
                file.write_text(json.dumps({**CONFIG, **change}))
                with self.assertRaises(ValueError):
                    b.load_config(file)


if __name__ == '__main__':
    unittest.main(verbosity=2)
