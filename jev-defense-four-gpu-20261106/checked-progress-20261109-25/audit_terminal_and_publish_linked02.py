"""Linked reporting-only repair: original text-only judges have no image grid."""
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
preserved = HERE / 'reporter-failure-preservation-1794224533776218600'
source = preserved / 'original-auditor.py'
assert source.read_bytes() == (HERE / 'audit_terminal_and_publish_once.py').read_bytes()
body = source.read_text(encoding='utf8')
old = "'image_count': prepared['image_grid_thw']['shape'][0],"
new = "'image_count': prepared['image_grid_thw']['shape'][0] if 'image_grid_thw' in prepared else 0,"
assert body.count(old) == 1
body = body.replace(old, new)
needle = "        row = {'request': folder.name,"
assert body.count(needle) == 1
body = body.replace(needle, """        if 'image_grid_thw' not in prepared:
            assert op == 'judge' and not payload['view']['images']
            assert 'pixel_values' not in prepared
        row = {'request': folder.name,""")
needle = "'no_new_experiment_calls': True, 'goal': 'active'})"
assert body.count(needle) == 1
body = body.replace(needle, "'no_new_experiment_calls': True, 'goal': 'active', "
                    "'reporter_only_linked_repair': 'Native text-only judge calls have zero images and no image_grid_thw; no experiment changes', "
                    "'original_auditor_preservation_seal_sha256': " + repr(hashlib.sha256((preserved / 'seal.json').read_bytes()).hexdigest()) + "})")
namespace = {'__name__': '__main__', '__file__': str(Path(__file__).resolve())}
exec(compile(body, str(source), 'exec'), namespace)
