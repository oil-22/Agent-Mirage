"""Assemble a new, once-only eight-trajectory native-injection package."""
import ast
import json
import secrets
import shutil
import time
from pathlib import Path
from remote_util import HERE, save, sha

BASE = HERE.parent
PRIOR = BASE / 'flash-late-corruption-defense-20261115-02'
FRAMEWORK = BASE / 'flash-image-presence-precheck-20261115-01'


def checked(pointer):
    value = json.loads(pointer.read_bytes())
    root = Path(value['root'])
    assert sha(root / 'seal.json') == value['seal_sha256']
    for name, expected in json.loads((root / 'seal.json').read_bytes()).items():
        assert sha(root / name) == expected, name
    return value


def member(text, name):
    node = next(n for n in ast.parse(text).body if getattr(n, 'name', None) == 'LiveAdapter')
    return next(n for n in node.body if getattr(n, 'name', None) == name)


def main():
    assert not (HERE / 'preparation-current.json').exists()
    root = HERE / ('preparation-' + str(time.time_ns()))
    root.mkdir()
    package = root / 'package'
    previous = PRIOR / 'package'
    manifest = json.loads((previous / 'manifest.json').read_bytes())
    for name, expected in manifest['files'].items():
        assert sha(previous / name) == expected, name
    framework = checked(FRAMEWORK / 'publication-current.json')
    publication = checked(PRIOR / 'completed-publication-current.json')
    shutil.copytree(previous, package)
    # Only new unsealed copies are replaced. Prior packages and terminals stay sealed.
    for name in ['manifest.json', 'private.token', 'plan.json', 'analysis-plan.json',
                 'user-current-authorization.json', 'prior-3090.json', 'prior-4090.json',
                 'continuation_guard.py', 'injection.py']:
        (package / name).unlink()
    for name in ['continuation_guard.py', 'injection.py', 'prior-3090.json', 'prior-4090.json']:
        shutil.copyfile(HERE / name, package / name)
    shutil.copyfile(HERE / 'user-authorization.json', package / 'user-current-authorization.json')
    for name in ['gate_core.py', 'gate-contract.json', 'wire_contract.py']:
        shutil.copyfile(FRAMEWORK / 'source/flash' / name, package / 'flash' / name)
    (package / 'private.token').write_text(secrets.token_hex(32), encoding='utf8')

    original = (FRAMEWORK / 'source/gui_experiment.py').read_text('utf8')
    methods = {
        'initial_frame': '''def initial_frame(self):
        from injection import Episode
        if not hasattr(self,'corruption_episode'):self.corruption_episode=Episode(self.item['condition'])
        raw=self.observation_png_or_missing()
        missing=self.missing_frame(raw,'initial')
        if missing is not None:return missing
        blank=(P/'blank-source.png').read_bytes()if self.item['condition']=='blank_replace'else None
        delivered,record=self.corruption_episode.apply(raw,step=self.step,previous_png=self.last_image,previous_action=self.previous,recapture=False,env=self.env,encoder=self.png,blank=blank)
        self.fired=self.corruption_episode.started;self.trigger_step=self.corruption_episode.start_step
        return self.record_delivery(raw,delivered,record)''',
        'capture': '''def capture(self):
        self.obs=self.env._get_obs();raw=self.observation_png_or_missing()
        missing=self.missing_frame(raw,'recapture')
        if missing is not None:return missing
        delivered,record=self.corruption_episode.apply(raw,step=self.step,previous_png=self.last_image,previous_action=self.previous,recapture=True)
        return self.record_delivery(raw,delivered,record)'''
    }
    changed = original
    for name, replacement in methods.items():
        before = ast.get_source_segment(original, member(original, name))
        assert changed.count(before) == 1
        changed = changed.replace(before, replacement)
    record_method = '''    def record_delivery(self,raw,delivered,record):
        frame=Frame.captured(delivered)
        folder=self.root/'capture-deliveries';folder.mkdir(exist_ok=True)
        stem=f'{record["capture_index"]:04}'
        raw_file='capture-deliveries/'+stem+'-raw.png'
        delivered_file=None if delivered is None else'capture-deliveries/'+stem+'-delivered.png'
        (self.root/raw_file).write_bytes(raw)
        if delivered_file is not None:(self.root/delivered_file).write_bytes(delivered)
        self.log.emit('PRIVATE_capture_injection',{**record,'capture_id':frame.capture_id,'captured_sha256':digest(raw),'delivered_sha256':frame.sha256,'raw_file':raw_file,'delivered_file':delivered_file,'injection_before_gate':True,'not_model_input':True})
        if record['capture_kind']=='initial':
            (self.root/f'{self.step:03}-actually-captured.png').write_bytes(raw)
            if delivered is not None:(self.root/f'{self.step:03}-initial-delivered.png').write_bytes(delivered)
            self.log.emit('PRIVATE_delivery_ledger',{'step':self.step,'condition':self.item['condition'],'injected':record['injected'],'captured_sha256':digest(raw),'delivered_sha256':frame.sha256,'injection_before_gate':True,'transformation':record['transformation'],'not_model_input':True})
        return frame

'''
    changed = changed.replace('    def actor(self,frame):', record_method + '    def actor(self,frame):')
    for name in ['__init__', 'observation_png_or_missing', 'missing_frame', 'actor', 'call_main', 'parse', 'execute', 'commit']:
        assert ast.dump(member(original, name), include_attributes=False) == ast.dump(member(changed, name), include_attributes=False), name
    needle = '    transport=Transport();auth=root/'
    assert changed.count(needle) == 1
    blank_source = '''    # Original native blank injection source: an independent about:blank browser.
    from playwright.sync_api import sync_playwright
    with sync_playwright()as pw:
        blank_browser=pw.chromium.launch(headless=True)
        blank_page=blank_browser.new_page(viewport={'width':1280,'height':720})
        blank_page.goto('about:blank');blank=blank_page.screenshot();blank_browser.close()
    (P/'blank-source.png').write_bytes(blank)
    save(root/'blank-source.json',{'sha256':digest(blank),'source':'independent native about:blank page','not_main_observation':True})
'''
    changed = changed.replace(needle, blank_source + needle)
    changed = changed.replace("'Flash_request_attempts':gate.calls,", "'presence_checks':getattr(gate,'presence_checks',0),'precheck_NO_count':getattr(gate,'precheck_no',0),'Flash_request_attempts':gate.calls,")
    (package / 'gui_experiment.py').write_text(changed, encoding='utf8')

    native = ast.parse((BASE.parent / 'defense-resume-20261102/restored-release/run_vwa_pilot.py').read_text('utf8'))
    native_css = next(ast.literal_eval(n.value) for n in native.body if isinstance(n, ast.Assign) and any(getattr(t, 'id', None) == 'CSS' for t in n.targets))
    injection = ast.parse((package / 'injection.py').read_text('utf8'))
    actual_css = next(ast.literal_eval(n.value) for n in injection.body if isinstance(n, ast.Assign) and any(getattr(t, 'id', None) == 'CSS' for t in n.targets))
    assert native_css == actual_css

    plan = json.loads((previous / 'plan.json').read_bytes())
    conditions = ['silent_drop', 'blank_replace', 'stale_replace', 'buttons_only']
    queue = [{'run_id': f'four15-T{task:03}-{condition}-gate', 'task_id': task,
              'condition': condition, 'gate_enabled': True}
             for condition in conditions for task in [58, 89]]
    plan.update(version='four-native-injection-presence-Flash-development-v1', queue=queue,
                expected_trajectories=8, matched_pairs=0, conditions=conditions,
                injection={'once_per_trajectory': True, 'first_three_conditions': 'first changed native capture after click/type/press/back/tab',
                           'buttons_only': 'first native detail page, exact original CSS transient capture and removal',
                           'blank_source': 'independent native about:blank screenshot',
                           'recaptures': 'same live environment; original one-shot injection is not repeated'},
                current_user_authorization_sha256=sha(package / 'user-current-authorization.json'),
                acceptance={'per_condition_target': 2, 'required': 'actual injected frame rejected before primary, new same-live recapture, independently reviewed normal YES image byte-exact into primary, successful native environment action',
                            'not_required': 'normal-frame primary text reading accuracy or official task score',
                            'untriggered_or_NO_without_normal_recovery': 'not success',
                            'preserve_all_failures': True, 'no_rate_or_general_efficacy_claim': True},
                new_primary_preread=False, full_history_unchanged=True)
    save(package / 'plan.json', plan)
    save(package / 'analysis-plan.json', {'initial_trajectories': 8, 'per_condition_target': 2,
                                         'conditions': conditions, 'tasks': [58, 89],
                                         'all_results_retained': True, 'stale_and_sparse_may_pass': True,
                                         'no_history_or_freshness_oracle_to_Flash': True,
                                         'success_is_measured_not_selected_or_guaranteed': True})
    files = {p.relative_to(package).as_posix(): sha(p) for p in package.rglob('*')
             if p.is_file() and p.name != 'private.token'}
    manifest.update(files=files, version=plan['version'], study=plan['version'], created=time.time(),
                    auth_token_sha256=sha(package / 'private.token'), trajectories=8, remaining_queue=queue,
                    package3090='/home/researcher/jev-defense-four-gpu-20261106/runtime-preparation/' + HERE.name,
                    package4090='/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name,
                    output3090='/data/researcher/jev-defense-four-gpu-20261106/' + HERE.name,
                    source_prior_manifest_sha256=sha(previous / 'manifest.json'),
                    current_user_authorization_sha256=sha(package / 'user-current-authorization.json'),
                    parent_presence_framework=framework, prior_terminal_publication=publication,
                    new_GUI_queue=True, formal_Mirage_efficacy_proven=False)
    save(package / 'manifest.json', manifest)
    for name, expected in files.items():
        assert sha(package / name) == expected, name
        if name.endswith('.py'):
            ast.parse((package / name).read_text('utf8'))
    save(root / 'preparation.json', {'manifest_sha256': sha(package / 'manifest.json'),
                                   'package': str(package), 'new_model_GUI_calls': 0,
                                   'original_CSS_exact': True, 'queue': queue,
                                   'presence_gate_exact': sha(package / 'flash/gate_core.py') == sha(FRAMEWORK / 'source/flash/gate_core.py')})
    save(root / 'seal.json', {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()})
    save(HERE / 'preparation-current.json', {'root': str(root), 'package': str(package),
                                           'manifest_sha256': sha(package / 'manifest.json'),
                                           'seal_sha256': sha(root / 'seal.json')})
    print(json.dumps({'package': str(package), 'files': len(files), 'trajectories': 8,
                      'manifest_sha256': sha(package / 'manifest.json'), 'new_model_GUI_calls': 0}))


if __name__ == '__main__':
    main()
