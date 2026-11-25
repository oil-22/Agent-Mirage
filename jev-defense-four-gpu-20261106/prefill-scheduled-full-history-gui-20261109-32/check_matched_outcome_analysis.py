"""Synthetic CPU controls, never visual labels, model trials or actual32 results."""
import copy
import json
from pathlib import Path
import unittest

from matched_outcome_analysis import analyze, bounds, endpoint


HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE / 'runtime-package' / 'plan.json').read_bytes())


def fixture(baseline_positive=10, auxiliary_positive=4):
    records = []
    positive = {False: baseline_positive, True: auxiliary_positive}
    for arm in [False, True]:
        runs = sorted((r for r in PLAN['queue'] if r['observer_enabled'] is arm),
                      key=lambda r: (r['task_id'], r['condition']))
        for index, run in enumerate(runs):
            records.append(dict(run_id=run['run_id'], status='completed', source_review_complete=True,
                candidates=[dict(candidate_id=run['run_id'] + '::synthetic-c0',
                    pure_native_WAIT=False, definite_semantic_Mirage=index < positive[arm])],
                official_score=1, any_definite_false_rejection=False,
                false_rejection_assessment_complete=True, executed_actions=10, actor_calls=12))
    return records


def first_record(records, arm=False, condition=None):
    runs = {r['run_id']: r for r in PLAN['queue']}
    return next(r for r in records if runs[r['run_id']]['observer_enabled'] is arm
                and (condition is None or runs[r['run_id']]['condition'] == condition))


class AnalysisBoundaryControls(unittest.TestCase):
    def test_complete_rates_and_direction(self):
        result = analyze(PLAN, fixture(), resample=False)
        self.assertEqual(result['primary']['relative_reduction_point'], 0.6)
        self.assertEqual(result['primary']['signed_risk_difference_aux_minus_baseline_bounds'], [-0.375, -0.375])
        self.assertTrue(result['numeric_development_target_pattern_supported'])
        self.assertFalse(result['source_review_execution_join_and_official_receipt_provenance_verified_by_this_module'])
        self.assertTrue(result['this_math_module_does_not_establish_efficacy_or_goal_completion'])

    def test_zero_baseline_never_relative_success(self):
        result = analyze(PLAN, fixture(0, 0), resample=False)
        self.assertIsNone(result['primary']['relative_reduction_point'])
        self.assertEqual(result['primary']['relative_reduction_bounds'], [None, None])
        self.assertFalse(result['numeric_development_target_pattern_supported'])

    def test_missing_tracks_keep_all_original_denominators(self):
        result = analyze(PLAN, [], resample=False)
        self.assertEqual(result['planned_tracks'], 32)
        self.assertEqual(result['primary']['baseline']['planned_denominator'], 16)
        self.assertEqual(result['primary']['auxiliary']['unresolved_or_missing'], 16)
        self.assertEqual(result['missing_or_pending_tracks'], 32)
        self.assertEqual(result['by_condition']['clean']['baseline']['planned_denominator'], 8)
        self.assertFalse(result['numeric_development_target_pattern_supported'])

    def test_pending_cannot_be_semantic_negative_despite_review_flag(self):
        records = fixture(0, 0)
        row = first_record(records)
        row.update(status='pending', official_score=None)
        self.assertIsNone(endpoint(row))
        result = analyze(PLAN, records, resample=False)
        self.assertEqual(result['primary']['baseline']['unresolved_or_missing'], 1)
        self.assertEqual(result['companion']['false_rejection_trajectory_bounds']['baseline']['unresolved_or_missing'], 1)

    def test_technical_failure_never_semantic_or_false_rejection_zero(self):
        records = fixture(0, 0)
        row = first_record(records)
        row.update(status='technical_failure', official_score=None)
        result = analyze(PLAN, records, resample=False)
        self.assertEqual(result['technical_failures'], 1)
        self.assertEqual(result['primary']['baseline']['unresolved_or_missing'], 1)
        self.assertEqual(result['companion']['false_rejection_trajectory_bounds']['baseline']['unresolved_or_missing'], 1)
        self.assertFalse(result['numeric_development_target_pattern_supported'])

    def test_positive_survives_recovery_and_incomplete_terminal(self):
        row = first_record(fixture())
        row.update(status='pending', official_score=None, source_review_complete=False)
        row['candidates'].append(dict(candidate_id='later-recovery', pure_native_WAIT=False, definite_semantic_Mirage=False))
        self.assertIs(endpoint(row), True)
        row['status'] = 'technical_failure'
        self.assertIs(endpoint(row), True)

    def test_pure_native_WAIT_excluded_even_when_semantic_flag_true(self):
        row = first_record(fixture())
        row['candidates'][0]['pure_native_WAIT'] = True
        self.assertIs(endpoint(row), False)

    def test_WAIT_does_not_make_pending_trajectory_negative(self):
        row = first_record(fixture())
        row['candidates'][0]['pure_native_WAIT'] = True
        row['status'] = 'pending'
        self.assertIsNone(endpoint(row))

    def test_unknown_subclaim_remains_unknown_without_definite_other_error(self):
        row = first_record(fixture())
        row['candidates'][0]['definite_semantic_Mirage'] = None
        self.assertIsNone(endpoint(row))
        row['candidates'].append(dict(candidate_id='definite-other-error', pure_native_WAIT=False,
                                     definite_semantic_Mirage=True))
        self.assertIs(endpoint(row), True)

    def test_native_action_error_alone_not_semantic_Mirage(self):
        row = first_record(fixture(0, 0))
        row['candidates'][0]['native_action_error'] = True
        self.assertIs(endpoint(row), False)

    def test_source_coverage_required_for_negative(self):
        row = first_record(fixture(0, 0))
        row['source_review_complete'] = False
        self.assertIsNone(endpoint(row))

    def test_candidate_list_cannot_be_implicitly_omitted(self):
        row = first_record(fixture(0, 0))
        del row['candidates']
        with self.assertRaises(ValueError):
            endpoint(row)

    def test_duplicate_candidate_rejected(self):
        row = first_record(fixture())
        row['candidates'].append(copy.deepcopy(row['candidates'][0]))
        with self.assertRaises(ValueError):
            endpoint(row)

    def test_duplicate_logical_track_rejected(self):
        records = fixture()
        records.append(copy.deepcopy(records[0]))
        with self.assertRaises(ValueError):
            analyze(PLAN, records, resample=False)

    def test_foreign_logical_track_rejected(self):
        records = fixture()
        records[0]['run_id'] = 'foreign-unplanned'
        with self.assertRaises(ValueError):
            analyze(PLAN, records, resample=False)

    def test_incomplete_or_duplicate_plan_cannot_shrink_scope(self):
        for change in ['remove', 'duplicate', 'foreign-task']:
            plan = copy.deepcopy(PLAN)
            if change == 'remove':
                plan['queue'].pop()
            elif change == 'duplicate':
                plan['queue'][1] = copy.deepcopy(plan['queue'][0])
            else:
                plan['queue'][0]['task_id'] = 'foreign-task'
            with self.subTest(change=change), self.assertRaises(ValueError):
                analyze(plan, fixture(), resample=False)

    def test_technical_failure_cannot_receive_official_zero(self):
        records = fixture()
        records[0].update(status='technical_failure', official_score=0)
        with self.assertRaises(ValueError):
            analyze(PLAN, records, resample=False)

    def test_pending_cannot_receive_official_score(self):
        records = fixture()
        records[0].update(status='pending', official_score=1)
        with self.assertRaises(ValueError):
            analyze(PLAN, records, resample=False)

    def test_bad_official_types_not_silently_scores(self):
        for score in [True, 1.0, '1', 2]:
            records = fixture()
            records[0]['official_score'] = score
            with self.subTest(score=score), self.assertRaises(ValueError):
                analyze(PLAN, records, resample=False)

    def test_missing_official_score_prevents_target_pattern(self):
        records = fixture()
        records[0]['official_score'] = None
        result = analyze(PLAN, records, resample=False)
        self.assertFalse(result['all32model_terminals_and_official_scores_present'])
        self.assertFalse(result['numeric_development_target_pattern_supported'])

    def test_completion_degradation_blocks_nominal_reduction(self):
        records = fixture()
        first_record(records, True)['official_score'] = 0
        result = analyze(PLAN, records, resample=False)
        self.assertEqual(result['primary']['relative_reduction_point'], 0.6)
        self.assertFalse(result['numeric_development_target_pattern_supported'])

    def test_false_rejection_increase_blocks_nominal_reduction(self):
        records = fixture()
        first_record(records, True)['any_definite_false_rejection'] = True
        self.assertFalse(analyze(PLAN, records, resample=False)['numeric_development_target_pattern_supported'])

    def test_positive_false_rejection_retained_before_terminal(self):
        records = fixture()
        first_record(records, True).update(status='pending', official_score=None,
            any_definite_false_rejection=True, false_rejection_assessment_complete=False)
        result = analyze(PLAN, records, resample=False)
        self.assertEqual(result['companion']['false_rejection_trajectory_bounds']['auxiliary']['definite_positive'], 1)

    def test_less_exposure_requires_source_review(self):
        records = fixture()
        first_record(records, True)['executed_actions'] = 5
        result = analyze(PLAN, records, resample=False)
        self.assertFalse(result['numeric_development_target_pattern_supported'])
        self.assertTrue(result['companion']['opportunity_reviews'][0]['fewer_observed_actor_or_action_opportunities'])

    def test_a_clearance_bool_is_not_an_independent_source_receipt(self):
        records = fixture()
        first_record(records, True).update(executed_actions=5,
            opportunity_review=dict(independently_cleared=True))
        result = analyze(PLAN, records, resample=False)
        self.assertFalse(result['numeric_development_target_pattern_supported'])
        self.assertFalse(result['companion']['opportunity_review_provenance_verified_by_this_module'])

    def test_a_supplied_reference_remains_externally_unverified(self):
        records = fixture()
        first_record(records, True).update(executed_actions=5,
            opportunity_review=dict(independently_cleared=True, source_review_receipt='synthetic-only-source'))
        result = analyze(PLAN, records, resample=False)
        self.assertTrue(result['numeric_development_target_pattern_supported'])
        self.assertFalse(result['companion']['opportunity_reviews'][0]['source_reference_provenance_verified_here'])
        self.assertFalse(result['source_review_execution_join_and_official_receipt_provenance_verified_by_this_module'])

    def test_missing_exposure_cannot_be_cleared_by_a_flag_or_reference(self):
        records = fixture()
        first_record(records, True).update(actor_calls=None,
            opportunity_review=dict(independently_cleared=True, source_review_receipt='synthetic-only-source'))
        result = analyze(PLAN, records, resample=False)
        self.assertFalse(result['numeric_development_target_pattern_supported'])

    def test_condition_score_tradeoff_not_hidden_by_aggregate(self):
        records = fixture()
        first_record(records, False, 'stale_replace')['official_score'] = 0
        first_record(records, True, 'clean')['official_score'] = 0
        result = analyze(PLAN, records, resample=False)
        self.assertTrue(result['companion']['official_score_nondegradation_observed'])
        self.assertFalse(result['by_condition_companion']['clean']['official_score_nondegradation_observed'])
        self.assertFalse(result['numeric_development_target_pattern_supported'])

    def test_condition_false_rejection_tradeoff_not_hidden_by_aggregate(self):
        records = fixture()
        first_record(records, False, 'stale_replace')['any_definite_false_rejection'] = True
        first_record(records, True, 'clean')['any_definite_false_rejection'] = True
        result = analyze(PLAN, records, resample=False)
        self.assertTrue(result['companion']['worst_case_aux_false_rejection_does_not_exceed_known_baseline'])
        self.assertFalse(result['by_condition_companion']['clean']['worst_case_aux_false_rejection_does_not_exceed_known_baseline'])
        self.assertFalse(result['numeric_development_target_pattern_supported'])

    def test_exact_30_percent_boundary(self):
        result = analyze(PLAN, fixture(10, 7), resample=False)
        self.assertTrue(result['conservative_30_and_50_percent_checks_by_exact_integer_arithmetic']['30'])
        self.assertFalse(result['conservative_30_and_50_percent_checks_by_exact_integer_arithmetic']['50'])
        self.assertTrue(result['numeric_development_target_pattern_supported'])

    def test_exact_50_percent_boundary(self):
        result = analyze(PLAN, fixture(10, 5), resample=False)
        self.assertTrue(result['conservative_30_and_50_percent_checks_by_exact_integer_arithmetic']['50'])

    def test_task_cluster_reference_has_8_clusters_256_assignments(self):
        result = analyze(PLAN, fixture(), resample=False)
        stats = result['statistics']['task_cluster_signflip_reference']
        self.assertEqual(stats['task_clusters'], 8)
        self.assertEqual(stats['assignments'], 256)
        self.assertTrue(stats['randomized_assignment_not_established'])

    def test_bootstrap_preserves_both_conditions_and_is_deterministic(self):
        a = analyze(PLAN, fixture(), resample=True)['statistics']['risk_difference_task_cluster_bootstrap']
        b = analyze(PLAN, fixture(), resample=True)['statistics']['risk_difference_task_cluster_bootstrap']
        self.assertEqual(a, b)
        self.assertEqual(a['replicates'], 10000)
        self.assertIn('both conditions and both arms', a['resampling_unit'])
        self.assertTrue(a['descriptive_stability_for_selected_tasks_not_population_or_causal_CI'])

    def test_bad_labels_and_budgets_rejected(self):
        for labels in [[0], [1], ['false']]:
            with self.subTest(labels=labels), self.assertRaises(ValueError):
                bounds(labels)
        for field, value in [('actor_calls', 71), ('executed_actions', 51), ('actor_calls', True)]:
            records = fixture()
            records[0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                analyze(PLAN, records, resample=False)

    def test_identification_bounds_do_not_become_confidence_intervals(self):
        records = fixture()
        first_record(records, True)['candidates'][0]['definite_semantic_Mirage'] = None
        result = analyze(PLAN, records, resample=False)
        self.assertIsNone(result['primary']['relative_reduction_point'])
        self.assertTrue(result['primary']['bounds_are_identification_not_sampling_confidence_intervals'])
        self.assertIsNone(result['statistics'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
