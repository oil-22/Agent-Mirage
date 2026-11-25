"""Linked CPU replay repair: start from full public view, not screen projection."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
original = HERE / 'pipeline-replay-failure-preservation-1794225419441668500/original-replay.py'
assert original.read_bytes() == (HERE / 'replay_pending_pipeline_once.py').read_bytes()
body = original.read_text(encoding='utf8')
old = "equal(actual_view, original_ready['view'])"
assert body.count(old) == 1
body = body.replace(old, "equal(actual_view, original_post['view'])")
old = "controller.decide(view(original_ready['view']), actor, parser, recapture)"
assert body.count(old) == 1
body = body.replace(old, "controller.decide(view(original_post['view']), actor, parser, recapture)")
old = "'strict_Controller_and_validators_unchanged': True,"
assert body.count(old) == 1
body = body.replace(old, old + "\n        'linked_source_only_repair': 'Hydrate complete22-message/11-image original PublicView; original Controller itself projects current-only screen view. Never promote projected readiness input to complete actor history.',")
exec(compile(body, str(original), 'exec'), {'__name__': '__main__', '__file__': str(Path(__file__).resolve())})
