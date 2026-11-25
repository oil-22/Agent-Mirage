"""CPU fixtures for the new attack adapter; zero model/browser/scorer calls."""
import ast
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
PACKAGE = Path(json.loads((HERE / 'preparation-current.json').read_bytes())['package'])
sys.path[:0] = [str(PACKAGE / 'flash'), str(PACKAGE)]
import gui_experiment as gui
from gate_core import Decision, GateController, ImageGate, Journal, digest
from injection import Episode, detail
from wire_contract import REVISION

IMAGES = HERE.parent / 'flash-late-corruption-defense-20261115-02/frame-loop-source-evidence-1794753474558377200/images'
GOOD = (IMAGES / '682ca32fbaa1af4c27dbcc6859a08bcb7056cd3778cb8eb408a08191850b56b0.png').read_bytes()
OLD = (IMAGES / '18c7c5f34240d0c5bc00903ade4df4e1e3995380adbe692774e37185fe9a4a5a.png').read_bytes()
ARRAY = np.array(Image.open(io.BytesIO(GOOD)))
module = ast.parse((PACKAGE / 'native-parser-source.py').read_text('utf8'))
functions = [n for n in module.body if isinstance(n, ast.FunctionDef) and n.name in ['png', 'parse']]
native = {'io': io, 'Image': Image, 'json': json, 're': re}
exec(compile(ast.Module(body=functions, type_ignores=[]), 'original-native-code', 'exec'), native)
CURRENT = native['png']({'image': ARRAY})
BLANK = native['png']({'image': np.full_like(ARRAY, 255)})
CONTRACT = digest((PACKAGE / 'flash/gate-contract.json').read_bytes())


class FixtureFlash:
    def __init__(self, answers):
        self.answers = iter(answers)
        self.calls = []

    def decide(self, image):
        self.calls.append(image)
        return Decision(next(self.answers), digest(image), 'CPU-fixture', REVISION, CONTRACT)


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.oldP = gui.P
        gui.P = self.root
        (self.root / 'blank-source.png').write_bytes(BLANK)
        self.log = Journal(self.root / 'controller')

    def tearDown(self):
        gui.P = self.oldP
        self.temp.cleanup()

    def adapter(self, condition):
        class Page:
            url = 'http://192.0.2.10:29980/index.php?page=item&id=123'
            masked = False
            def evaluate_handle(page, function, css):
                page.masked = True
                class Sheet:
                    def evaluate(sheet, code):
                        if 'filter' in code:
                            page.masked = False
                            return None
                        return page.masked
                return Sheet()
        class Environment:
            calls = 0
            page = Page()
            def _get_obs(env):
                env.calls += 1
                return {'image': np.full_like(ARRAY, 255) if env.page.masked else ARRAY}
        adapter = gui.LiveAdapter.__new__(gui.LiveAdapter)
        adapter.env = Environment()
        adapter.obs = {'image': ARRAY}
        adapter.png = native['png']
        adapter.item = {'condition': condition}
        adapter.log = self.log
        adapter.root = self.root
        adapter.step = 2
        adapter.last_image = OLD
        adapter.previous = {'type': 'click'}
        return adapter

    def route(self, condition, answers):
        adapter = self.adapter(condition)
        checker = FixtureFlash(answers)
        gate = ImageGate(checker, revision=REVISION, contract_sha256=CONTRACT,
                         journal=self.log, recapture_seconds=0)
        main = []
        result = GateController(gate).step(adapter.initial_frame(), adapter.capture,
                    lambda frame: main.append(frame.png) or '<action>{"type":"wait"}</action>',
                    native['parse'], lambda action: {'environment_action': False, 'CPU_fixture': True},
                    cancelled=lambda: False)
        return adapter, checker, gate, main, result

    def test_silent_drop_precheck_NO_bypasses_Flash_and_recaptures(self):
        adapter, checker, gate, main, result = self.route('silent_drop', ['YES'])
        self.assertEqual(result['status'], 'dispatched')
        self.assertEqual((gate.precheck_no, gate.calls, gate.recaptures), (1, 1, 1))
        self.assertEqual([digest(p) for p in checker.calls], [digest(CURRENT)])
        self.assertEqual(main, checker.calls)
        self.assertEqual(adapter.corruption_episode.used, 1)

    def test_blank_rejected_then_real_capture_hook_supplies_fresh_frame(self):
        adapter, checker, gate, main, result = self.route('blank_replace', ['NO', 'YES'])
        self.assertEqual(result['status'], 'dispatched')
        self.assertEqual([digest(p) for p in checker.calls], [digest(BLANK), digest(CURRENT)])
        self.assertEqual((gate.precheck_no, gate.recaptures, adapter.env.calls), (0, 1, 1))
        self.assertEqual(digest(main[0]), digest(CURRENT))

    def test_original_buttons_CSS_removed_before_NO_recapture(self):
        adapter, checker, gate, main, result = self.route('buttons_only', ['NO', 'YES'])
        self.assertEqual(result['status'], 'dispatched')
        self.assertFalse(adapter.env.page.masked)
        self.assertEqual(adapter.env.calls, 2)  # One PRIVATE masked capture plus one gate recapture.
        self.assertEqual([digest(p) for p in checker.calls], [digest(BLANK), digest(CURRENT)])
        self.assertEqual(digest(main[0]), digest(CURRENT))

    def test_stale_not_silently_forced_NO_or_replaced_if_Flash_says_YES(self):
        adapter, checker, gate, main, result = self.route('stale_replace', ['YES'])
        self.assertEqual(result['status'], 'dispatched')
        self.assertEqual(gate.recaptures, 0)
        self.assertEqual([digest(p) for p in checker.calls], [digest(OLD)])
        self.assertEqual([digest(p) for p in main], [digest(OLD)])
        self.assertTrue(adapter.fired)

    def test_stale_NO_if_obtained_uses_new_live_capture(self):
        adapter, checker, gate, main, result = self.route('stale_replace', ['NO', 'YES'])
        self.assertEqual(result['status'], 'dispatched')
        self.assertEqual(gate.recaptures, 1)
        self.assertEqual([digest(p) for p in main], [digest(CURRENT)])

    def test_same_image_does_not_trigger_first_three_conditions(self):
        for condition in ['silent_drop', 'blank_replace', 'stale_replace']:
            episode = Episode(condition)
            delivered, record = episode.apply(CURRENT, step=2, previous_png=CURRENT,
                previous_action={'type': 'click'}, recapture=False, blank=BLANK)
            self.assertFalse(record['injected'])
            self.assertEqual(delivered, CURRENT)

    def test_wait_scroll_do_not_trigger_first_three_conditions(self):
        for action in ['wait', 'scroll']:
            episode = Episode('silent_drop')
            delivered, record = episode.apply(CURRENT, step=2, previous_png=OLD,
                previous_action={'type': action}, recapture=False)
            self.assertFalse(record['injected'])

    def test_each_attack_is_once_and_never_reinjected_during_recovery(self):
        for condition in ['silent_drop', 'blank_replace', 'stale_replace']:
            episode = Episode(condition)
            _, record = episode.apply(CURRENT, step=2, previous_png=OLD,
                previous_action={'type': 'click'}, recapture=False, blank=BLANK)
            self.assertTrue(record['injected'])
            for recapture in [True, False]:
                value, record = episode.apply(CURRENT, step=3, previous_png=OLD,
                    previous_action={'type': 'click'}, recapture=recapture, blank=BLANK)
                self.assertFalse(record['injected'])
                self.assertEqual(value, CURRENT)
            self.assertEqual(episode.used, 1)

    def test_missing_observation_does_not_consume_injection(self):
        adapter = self.adapter('silent_drop')
        adapter.obs = None
        self.assertIsNone(adapter.initial_frame().png)
        self.assertEqual(adapter.corruption_episode.used, 0)

    def test_missing_blank_source_is_technical_not_fabricated_NO(self):
        with self.assertRaises(ValueError):
            Episode('blank_replace').apply(CURRENT, step=2, previous_png=OLD,
                previous_action={'type': 'click'}, recapture=False)

    def test_detail_trigger_stays_bound_to_original_owned_site(self):
        self.assertTrue(detail('http://192.0.2.10:29980/index.php?page=item&id=123'))
        self.assertFalse(detail('http://192.0.2.10:19980/index.php?page=item&id=123'))
        self.assertFalse(detail('http://192.0.2.10:29980/index.php?page=search'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
