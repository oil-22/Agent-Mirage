"""Seal one CPU qualification attempt; never launch a model or browser."""
import ast
import hashlib
import json
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / 'flash-late-corruption-defense-20261115-02'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def member(source, name):
    nodes = ast.parse(source).body
    for part in name.split('.'):
        node = next(n for n in nodes if getattr(n, 'name', None) == part)
        nodes = getattr(node, 'body', [])
    return ast.dump(node, include_attributes=False)


def main():
    attempt = HERE / ('cpu-qualification-' + str(time.time_ns()))
    attempt.mkdir()
    files = sorted(p for p in (HERE / 'source').rglob('*') if p.is_file())
    files += [HERE / 'test_presence_precheck.py', Path(__file__),
              HERE / 'parent-binding.json', HERE / 'user-authorization.json']
    before = {}
    for file in files:
        relative = file.relative_to(HERE)
        raw = file.read_bytes()
        destination = attempt / 'snapshot' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as handle:
            handle.write(raw)
        before[relative.as_posix()] = sha(raw)
    result = {'scope': 'CPU fixture routing and source preservation only',
              'real_model_calls': 0, 'real_GUI_calls': 0, 'scorer_calls': 0,
              'paid_API_calls': 0, 'live_deployment_changed': False,
              'source_snapshot_sha256': before, 'passed': False}
    prior = sorted(p for p in HERE.glob('cpu-qualification-*')
                   if p != attempt and (p / 'seal.json').exists())
    if prior:
        result['previous_attempt'] = str(prior[-1])
        result['previous_seal_sha256'] = sha((prior[-1] / 'seal.json').read_bytes())
        result['runner_repair'] = 'Stream subprocess output to files; retain timeout output; allow 300 seconds for CPU checks. Production source unchanged.'
        result['test_fixture_repair'] = 'Compare the original native local PNG encoder output to the exact bytes forwarded through Flash and main; verify its pixel equality with the archived source. Do not assume cross-machine PNG compression identity. Production source unchanged.'
    try:
        binding = json.loads((HERE / 'parent-binding.json').read_bytes())
        assert sha((PARENT / 'package/manifest.json').read_bytes()) == binding['parent_manifest_sha256']
        changed = {'flash/gate_core.py', 'gui_experiment.py'}
        preserved = []
        for name, expected in binding['original_files'].items():
            assert sha((PARENT / 'package' / name).read_bytes()) == expected, name
            if name not in changed:
                assert sha((HERE / 'source' / name).read_bytes()) == expected, name
                preserved.append(name)
        oldgate = (PARENT / 'package/flash/gate_core.py').read_text('utf8')
        newgate = (HERE / 'source/flash/gate_core.py').read_text('utf8')
        oldgui = (PARENT / 'package/gui_experiment.py').read_text('utf8')
        newgui = (HERE / 'source/gui_experiment.py').read_text('utf8')
        members = []
        for name in ['Journal', 'GateController', 'NativeHistoryActor']:
            assert member(oldgate, name) == member(newgate, name), name
            members.append(name)
        for name in ['Transport', 'Bypass', 'LiveAdapter.__init__', 'LiveAdapter.actor',
                     'LiveAdapter.call_main', 'LiveAdapter.parse', 'LiveAdapter.commit', 'main']:
            assert member(oldgui, name) == member(newgui, name), name
            members.append(name)
        # The native action dispatch remains identical; only the post-action
        # image-diagnostic encoding is made tolerant of an absent observation.
        original_log = "self.log.emit('native_environment_action',{'step':self.step,'payload':payload,'ok':bool(ok),'current_capture_sha256':digest(self.png(self.obs))})"
        revised_log = "observed=self.observation_png_or_missing()\n            self.log.emit('native_environment_action',{'step':self.step,'payload':payload,'ok':bool(ok),'current_capture_sha256':digest(observed)if observed else None,'current_image_present':check_image_presence(observed).value=='YES'})"
        assert newgui.count(revised_log) == 1
        assert member(oldgui, 'LiveAdapter.execute') == member(newgui.replace(revised_log, original_log), 'LiveAdapter.execute')
        for file in files:
            if file.suffix == '.py':
                compile(file.read_bytes(), str(file), 'exec')
        command = [sys.executable, '-B', '-u', '-X', 'utf8', str(HERE / 'test_presence_precheck.py')]
        with (attempt / 'stdout.bin').open('xb') as stdout, (attempt / 'stderr.bin').open('xb') as stderr:
            completed = subprocess.run(command, cwd=HERE, stdout=stdout, stderr=stderr, timeout=300)
        output = (attempt / 'stdout.bin').read_text('utf8') + (attempt / 'stderr.bin').read_text('utf8')
        count = re.search(r'Ran (\d+) tests? in ', output)
        result.update(command=command, return_code=completed.returncode,
                      tests_run=int(count.group(1)) if count else None,
                      unchanged_files=preserved, unchanged_AST_members=members,
                      native_execution_change='post-action image diagnostics only')
        assert completed.returncode == 0, output
        assert count and int(count.group(1)) == 18, output
        assert all(sha((HERE / name).read_bytes()) == expected for name, expected in before.items())
        result['passed'] = True
    except BaseException:
        result['qualification_error'] = traceback.format_exc()
    save(attempt / 'result.json', result)
    seal = {p.relative_to(attempt).as_posix(): sha(p.read_bytes())
            for p in sorted(attempt.rglob('*')) if p.is_file()}
    save(attempt / 'seal.json', seal)
    print(json.dumps({'attempt': str(attempt), 'passed': result['passed'],
                      'tests_run': result.get('tests_run'),
                      'seal_sha256': sha((attempt / 'seal.json').read_bytes())}))
    if not result['passed']:
        print(result['qualification_error'])
        raise SystemExit(1)


if __name__ == '__main__':
    main()
