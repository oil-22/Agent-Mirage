"""Source contact sheets and blind reviews; no browser or model calls."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
PARSER = (HERE.parents[1] / 'jev-defense-four-gpu-20261106/flash-native-source-loop-20261116-linked11'
          / 'preparation-1794820110211682400/package/native-parser-source.py')
EXPECTED_PARSER = 'af825cdf46601f4b12efb8fe614f1eb1c924af750a7fbc85bc6a565119267cf7'


def read(p):
    return json.loads(p.read_bytes())


def text(content):
    return content if isinstance(content, str) else '\n'.join(b['text'] for b in content if b['type'] == 'text')


def sources(root):
    from PIL import Image, ImageDraw
    cases = root / 'cases'
    dst = root / 'review-boards'
    dst.mkdir(exist_ok=True)
    files = sorted(cases.glob('T*.json'))
    for p in files:
        data = read(p)
        last = data['legal_messages'][-1]
        prior = [m for m in data['legal_messages'][:-1] if m['role'] == 'assistant']
        actions = [re.findall(r'<action>\s*(.*?)\s*</action>', text(m['content']), flags=re.S) for m in prior[-4:]]
        print(p.stem + ': ' + text(last['content']).splitlines()[0])
        print('  recent actions: ' + ' / '.join(k[-1] for k in actions if k))
        print('  current: ' + data['current_image_sha256'])
    for start in range(0, len(files), 4):
        width, height, pad = 704, 396, 36
        sheet = Image.new('RGB', (2 * width, 2 * (height + pad)), '#142233')
        d = ImageDraw.Draw(sheet)
        for n, p in enumerate(files[start:start + 4]):
            data = read(p)
            src = cases / 'source-images' / (data['current_image_sha256'] + '.png')
            assert hashlib.sha256(src.read_bytes()).hexdigest() == data['current_image_sha256']
            original = Image.open(src).convert('RGB')
            x, y = (n % 2) * width, (n // 2) * (height + pad)
            tile = original.resize((width, height), Image.Resampling.LANCZOS)
            sheet.paste(tile, (x, y + pad))
            d.text((x + 9, y + 9), p.stem, fill='white', font_size=21)
        sheet.save(dst / f'source-{start // 4 + 1}.png')


def action_namespace():
    payload = PARSER.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == EXPECTED_PARSER
    src = ast.parse(payload)
    functions = [n for n in src.body if isinstance(n, ast.FunctionDef) and n.name in ('parse', 'action')]
    assert len(functions) == 2
    scope = {'re': re, 'json': json}

    class Coords(list):
        def astype(self, ty):
            return Coords(ty(x) for x in self)

    constructors = sorted({n.func.id for fn in functions for n in ast.walk(fn)
                           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id.startswith('create_')})
    def factory(kind):
        def create(*args):
            return {'constructor': kind, 'args': args, 'coords': Coords(args)}
        return create
    scope.update((c, factory(c)) for c in constructors)
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(PARSER), 'exec'), scope)
    return scope


def candidate_packets(root, blind, case_filter):
    scope = action_namespace()
    grouped = {}
    for p in sorted(blind.glob('*.json')):
        v = read(p)
        if case_filter and not v['case'].startswith(case_filter):
            continue
        assert v['candidate_sha256'] == hashlib.sha256(v['candidate'].encode('utf-8')).hexdigest()
        legal = read(root / 'cases' / (v['case'] + '.json'))['legal_messages'][-1]
        observed = text(legal['content'])
        detail = None
        payload = None
        try:
            x = scope['parse'](v['candidate'])
            if x['type'] == 'tab':
                available = int(re.search(r'Available tab count:\s*(\d+)', observed).group(1))
                assert 0 <= int(x['index']) < available, 'Tab out of range'
            else:
                scope['action'](x)
            payload = x
        except Exception as exc:
            detail = f'{type(exc).__name__}: {exc}'
        if v['case'] not in grouped:
            grouped[v['case']] = []
        grouped[v['case']].append({'opaque_id': p.stem, **v, 'native_payload': payload, 'native_error': detail})
    for key, items in sorted(grouped.items()):
        print('CASE ' + key)
        for row in items:
            suffix = f"native={json.dumps(row['native_payload'], ensure_ascii=False)}" if row['native_error'] is None else row['native_error']
            print(f" [{row['opaque_id']}] EOS={row['natural_EOS']} {suffix}\n   {row['candidate']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--blind', type=Path)
    parser.add_argument('--case')
    args = parser.parse_args()
    if args.blind:
        candidate_packets(args.root, args.blind, args.case)
    else:
        sources(args.root)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
