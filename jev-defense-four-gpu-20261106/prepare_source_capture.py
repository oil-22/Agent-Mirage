"""Create a linked native-browser control capture; never run the source here."""
from pathlib import Path
import hashlib
import json

BASE = Path(__file__).resolve().parent
parent = BASE / 'environment_preflight_refresh.py'
text = parent.read_text(encoding='utf8')
text = text.replace('import urllib.request\n', 'import urllib.request\nfrom urllib.parse import urlencode\n')
helper = '''
def capture_extra_controls(env, root, png):
    """Real owned GUI source preparation, not model-agent task actions."""
    controls = root / 'controls'
    controls.mkdir()
    operations = []
    def capture(name, label):
        path = controls / name
        path.mkdir()
        (path / 'original.png').write_bytes(png(env._get_obs()))
        (path / 'public-dom.html').write_text(env.page.content())
        record = {'name': name, 'url': env.page.url, 'time': time.time(),
                  'source': 'same live owned native GUI, manual source preparation',
                  'model_calls': 0, 'formal_task_actions': 0, 'site_reset': False,
                  'operations_so_far': list(operations), 'intended_control': label,
                  'image_sha256': sha(path / 'original.png'),
                  'dom_sha256': sha(path / 'public-dom.html')}
        (path / 'source.json').write_text(json.dumps(record, indent=2))
    capture('fresh-home', 'mixed search form and listing cards; not exclusive form/list')
    operations.append({'operation': 'scrollTo', 'value': 'bottom'})
    env.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    env.page.wait_for_timeout(500)
    capture('normal-footer', 'real coherent footer/offscreen targets; independently review image')
    operations.append({'operation': 'scrollTo', 'value': 'top'})
    env.page.evaluate('window.scrollTo(0, 0)')
    env.page.wait_for_timeout(200)
    css = """body * { visibility: hidden !important; }
button, button *, a.button, a.button *, a.btn, a.btn *, a.publish, a.publish *,
[role="button"], [role="button"] *, input[type="submit"] { visibility: visible !important; }
body img, body picture, body video, body canvas, body svg image { opacity: 0 !important; visibility: hidden !important; }"""
    operations.append({'operation': 'mount_original_buttons_only_css',
                       'css_sha256': hashlib.sha256(css.encode()).hexdigest()})
    sheet = env.page.evaluate_handle('css=>{const s=new CSSStyleSheet();s.replaceSync(css);document.adoptedStyleSheets=[...document.adoptedStyleSheets,s];return s;}', css)
    try:
        capture('buttons-only-home', 'original CSS sparse button view; not loading or absence proof')
    finally:
        sheet.evaluate('(s)=>{document.adoptedStyleSheets=document.adoptedStyleSheets.filter(x=>x!==s)}')
        assert not sheet.evaluate('(s)=>document.adoptedStyleSheets.includes(s)')
        operations.append({'operation': 'remove_original_buttons_only_css', 'verified': True})
    query = '__mirage_observer_no_match_20261106_1793974000__'
    target = 'http://192.0.2.10:29980/index.php?' + urlencode({'page': 'search', 'sPattern': query})
    operations.append({'operation': 'native_GET_search', 'url': target,
                       'purpose': 'source control only; no database mutation'})
    response = env.page.goto(target, wait_until='domcontentloaded')
    env.page.wait_for_timeout(500)
    capture('native-no-results', 'native response to unmatched search; HTTP404 may be normal template')
    result = {'model_calls': 0, 'formal_task_actions': 0, 'source_GUI_operations': operations,
              'search_http_status': None if response is None else response.status,
              'no_site_reset_or_fixture_import': True, 'not_a_defense_trajectory': True}
    (controls / 'capture-summary.json').write_text(json.dumps(result, indent=2))
    return result

'''
text = text.replace('def main(root):\n', helper + '\ndef main(root):\n')
text = text.replace('            scorer = evaluator_router(config)\n',
                    "            source_capture = capture_extra_controls(env, root, png)\n"
                    "            result['source_capture'] = source_capture\n"
                    '            scorer = evaluator_router(config)\n')
text = text.replace("'environment-preflight-' + str(time.time_ns())", "'observer-source-controls-' + str(time.time_ns())")
target = BASE / 'capture_observer_source_controls.py'
assert not target.exists()
target.write_text(text, encoding='utf8')
(BASE / 'source-capture-preparation.json').write_text(json.dumps({
    'parent_sha256': hashlib.sha256(parent.read_bytes()).hexdigest(),
    'new_source_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'extra_source_browser_operations_declared': True, 'model_calls': 0,
    'formal_task_actions': 0, 'site_reset': False,
}, indent=2), encoding='utf8')
print(json.dumps({'prepared': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}))
