"""New tail31 selection/path boundaries only; no old model controls rerun."""
import copy
import unittest

import collect_tail_terminal_once as collector


class TailTerminalBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = collector.read(collector.PACKAGE / 'plan.json')
        cls.manifest = collector.read(collector.PACKAGE / 'manifest.json')
        cls.predecessor = collector.read(collector.PACKAGE / 'predecessor.json')

    def test_all_and_only_original_tail31_selected(self):
        rows = [collector.select_tail_run(self.plan, self.manifest, self.predecessor, row['run_id'])
            for row in self.plan['queue'][1:]]
        self.assertEqual(rows, self.plan['queue'][1:])
        self.assertEqual(len(rows), 31)
        self.assertEqual({row['task_id'] for row in rows}, {0, 3, 17, 58, 89, 94, 114, 125})

    def test_completed_original_first_track_rejected(self):
        with self.assertRaises(ValueError):
            collector.select_tail_run(self.plan, self.manifest, self.predecessor, self.plan['queue'][0]['run_id'])

    def test_foreign_and_path_traversal_runs_rejected(self):
        for run in ['foreign-run', '../fullhistory23-T000-clean-aux', 'fullhistory23-T000-clean-aux/other']:
            with self.subTest(run=run), self.assertRaises(ValueError):
                collector.select_tail_run(self.plan, self.manifest, self.predecessor, run)

    def test_nonzero_tail_initial_counts_rejected(self):
        for source in ['manifest', 'predecessor']:
            m, p = copy.deepcopy(self.manifest), copy.deepcopy(self.predecessor)
            if source == 'manifest':
                m['initial_transport_counts_for_all_remaining_tracks']['judge'] = 140
            else:
                p['current_root_initial_counts']['actor'] = 38
            with self.subTest(source=source), self.assertRaises(ValueError):
                collector.select_tail_run(self.plan, m, p, self.plan['queue'][1]['run_id'])

    def test_changed_scope_or_excluded_terminal_rejected(self):
        for change in ['duplicate', 'wrong_excluded', 'wrong_original_manifest', 'wrong_tail_size']:
            plan, m, p = copy.deepcopy(self.plan), copy.deepcopy(self.manifest), copy.deepcopy(self.predecessor)
            if change == 'duplicate':
                plan['queue'][2] = copy.deepcopy(plan['queue'][1])
            elif change == 'wrong_excluded':
                p['excluded_run_ids'] = [plan['queue'][1]['run_id']]
            elif change == 'wrong_original_manifest':
                m['original32_manifest_sha256'] = '0' * 64
            else:
                m['tracks'] = 32
            with self.subTest(change=change), self.assertRaises(ValueError):
                collector.select_tail_run(plan, m, p, self.plan['queue'][1]['run_id'])

    def test_old_source_checks_preserved_with_only_explicit_package_path_change(self):
        original, service, helper = collector.source_components()
        self.assertEqual(service.replace('package=Path(PACKAGE_ROOT)', "package=r.parent/'runtime-preparation'/r.name", 1), original.SERVICE_CODE)
        self.assertEqual(helper, (collector.SOURCE_ROOT / 'logical_terminal_checks.py').read_text(encoding='utf8'))
        self.assertIn("assert os.getuid()==1033 and sha(package/'manifest.json')==EXPECTED", service)
        self.assertIn('check_terminal_counters(terminal,PLANNED,CARRYOVER)', original.GUI_CODE)

    def test_actual_new_package_admission_and_prior_ID_exclusion(self):
        run = self.plan['queue'][1]['run_id']
        planned, carry, _, _, _ = collector.admission(run)
        self.assertEqual(planned, self.plan['queue'][1])
        self.assertNotEqual(run, carry['original_track'])
        self.assertTrue(set(self.predecessor['disallowed_completed_model_request_ids']).issubset(carry['disallowed_prior_request_ids']))
        self.assertTrue(collector.OUTPUT.startswith('/data/researcher/'))
        self.assertTrue(collector.REMOTE_PACKAGE.startswith('/home/researcher/'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
