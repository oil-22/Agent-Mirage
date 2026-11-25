"""PRIVATE finite native fault renderer; never a signing or defense interface.

The CSS, JS and item predicate are frozen from the original injection module.
Rendering happens after a normal signed capture and is always undone before
the receiver sees the substituted PNG. No labels or selector metadata go to
Flash, the receipt verifier or the actor.
"""
from urllib.parse import parse_qs, urlsplit

CSS = '''body * { visibility: hidden !important; }
button, button *, a.button, a.button *, a.btn, a.btn *, a.publish, a.publish *,
[role="button"], [role="button"] *, input[type="submit"] { visibility: visible !important; }
body img, body picture, body video, body canvas, body svg image { opacity: 0 !important; visibility: hidden !important; }'''
APPLY = '''css=>{const s=new CSSStyleSheet();s.replaceSync(css);document.adoptedStyleSheets=[...document.adoptedStyleSheets,s];return s;}'''
REMOVE = '(s)=>{document.adoptedStyleSheets=document.adoptedStyleSheets.filter(x=>x!==s)}'
PRESENT = '(s)=>document.adoptedStyleSheets.includes(s)'


def detail(url):
    u = urlsplit(url)
    q = parse_qs(u.query)
    return u.hostname == '192.0.2.10' and u.port == 29980 and u.path == '/index.php' and q.get('page') == ['item'] and q.get('id', [''])[0].isdigit()


def render_buttons(env, encoder):
    if not detail(env.page.url):
        raise ValueError('Original native detail-page trigger required')
    sheet = env.page.evaluate_handle(APPLY, CSS)
    try:
        delivered = encoder(env._get_obs())
    finally:
        sheet.evaluate(REMOVE)
    if sheet.evaluate(PRESENT):
        raise RuntimeError('Original buttons-only CSS not removed; preserve and stop')
    return delivered


def render_blank(playwright):
    # Same original independent Chromium about:blank procedure; never reset or
    # navigate the live task. The returned PNG has no acquisition signature.
    browser = playwright.chromium.launch(headless=True)
    try:
        page = browser.new_page(viewport={'width': 1280, 'height': 720})
        page.goto('about:blank')
        return page.screenshot()
    finally:
        browser.close()
