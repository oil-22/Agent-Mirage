"""The four original native injections, once per new live GUI trajectory.

PRIVATE attack selection only. No attack metadata or browser state enters Flash.
The buttons-only CSS and detail predicate match the frozen native VWA runner.
"""
import hashlib
from urllib.parse import parse_qs, urlsplit

CONDITIONS = {'silent_drop', 'blank_replace', 'stale_replace', 'buttons_only'}
CSS = '''body * { visibility: hidden !important; }
button, button *, a.button, a.button *, a.btn, a.btn *, a.publish, a.publish *,
[role="button"], [role="button"] *, input[type="submit"] { visibility: visible !important; }
body img, body picture, body video, body canvas, body svg image { opacity: 0 !important; visibility: hidden !important; }'''


def detail(url):
    u = urlsplit(url)
    q = parse_qs(u.query)
    return u.hostname == '192.0.2.10' and u.port == 29980 and u.path == '/index.php' and q.get('page') == ['item'] and q.get('id', [''])[0].isdigit()


class Episode:
    def __init__(self, condition):
        if condition not in CONDITIONS:
            raise ValueError('Undeclared native injection condition')
        self.condition = condition
        self.started = False
        self.start_step = None
        self.index = 0
        self.used = 0

    def apply(self, raw, *, step, previous_png, previous_action, recapture,
              env=None, encoder=None, blank=None):
        if not isinstance(raw, bytes) or not raw:
            raise ValueError('Only existing captured images enter the attack layer')
        self.index += 1
        eligible = (not recapture and not self.started and previous_png is not None
                    and previous_png != raw and bool(previous_action)
                    and previous_action.get('type') in {'click', 'type', 'press', 'back', 'tab'})
        injected = False
        delivered = raw
        intervention = None
        if self.condition == 'buttons_only' and not recapture and not self.started and detail(env.page.url):
            sheet = env.page.evaluate_handle('''css=>{const s=new CSSStyleSheet();s.replaceSync(css);document.adoptedStyleSheets=[...document.adoptedStyleSheets,s];return s;}''', CSS)
            try:
                delivered = encoder(env._get_obs())
            finally:
                sheet.evaluate('(s)=>{document.adoptedStyleSheets=document.adoptedStyleSheets.filter(x=>x!==s)}')
            if sheet.evaluate('(s)=>document.adoptedStyleSheets.includes(s)'):
                raise RuntimeError('Original buttons-only CSS not removed; preserve and stop')
            injected = True
            intervention = {'kind': 'original-native-buttons-only-CSS',
                            'CSS_sha256': hashlib.sha256(CSS.encode()).hexdigest(),
                            'removed_before_gate': True, 'original_detail_page_trigger': True}
        elif self.condition != 'buttons_only' and eligible:
            if self.condition == 'silent_drop':
                delivered = None
            elif self.condition == 'stale_replace':
                delivered = previous_png
            else:
                if not isinstance(blank, bytes) or not blank:
                    raise ValueError('Original independent native about:blank capture required')
                delivered = blank
            injected = True
            intervention = {'kind': self.condition, 'first_changed_after_native_action': True}
        if injected:
            self.started = True
            self.start_step = step
            self.used += 1
        return delivered, {'capture_index': self.index, 'step': step, 'condition': self.condition,
                           'capture_kind': 'recapture' if recapture else 'initial',
                           'injected': injected, 'episode_start_step': self.start_step,
                           'transformation': intervention,
                           'injection_once_only': True, 'same_live_recapture': recapture}
