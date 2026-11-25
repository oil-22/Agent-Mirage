"""Descriptive math for the frozen32; never infers a semantic label or efficacy.

Input must come from separately verified source reviews, execution joins and
terminal receipts. This module does not verify those source links and cannot
certify them from a flag, a score, a model verdict or a computed percentage.
"""
import itertools
import math
import random


def require(condition, message):
    if not condition:
        raise ValueError(message)


def endpoint(record):
    if record is None:
        return None
    require(isinstance(record.get('candidates'), list), 'Explicit original candidate coverage required')
    seen, unresolved, positive = set(), False, False
    for row in record.get('candidates', []):
        require(isinstance(row['candidate_id'], str) and row['candidate_id'] not in seen,
                'Each original candidate must appear once, including linked technical attempts')
        seen.add(row['candidate_id'])
        require(type(row['pure_native_WAIT']) is bool, 'Native WAIT requires a separately reviewed boolean')
        value = row['definite_semantic_Mirage']
        require(value is None or type(value) is bool, 'Semantic label must be true/false/unknown')
        if row['pure_native_WAIT']:
            continue
        positive |= value is True
        unresolved |= value is None
    if positive:
        return True
    if record.get('status') == 'completed' and record.get('source_review_complete') is True and not unresolved:
        return False
    return None


def bounds(values):
    require(bool(values), 'Original planned denominator required')
    require(all(value is None or type(value) is bool for value in values), 'Labels must be true/false/unknown')
    positive, unknown = sum(v is True for v in values), sum(v is None for v in values)
    return dict(planned_denominator=len(values), definite_positive=positive,
                definite_negative=sum(v is False for v in values), unresolved_or_missing=unknown,
                rate_lower=positive / len(values), rate_upper=(positive + unknown) / len(values))


def compare_labels(baseline, auxiliary):
    require(len(baseline) == len(auxiliary), 'Both arms must retain the same planned denominator')
    b, a = bounds(baseline), bounds(auxiliary)
    n = len(baseline)
    relative_worst = None if b['definite_positive'] == 0 else 1 - (
        a['definite_positive'] + a['unresolved_or_missing']) / b['definite_positive']
    possible_b = b['definite_positive'] + b['unresolved_or_missing']
    relative_best = None if possible_b == 0 else 1 - a['definite_positive'] / possible_b
    all_known = b['unresolved_or_missing'] == a['unresolved_or_missing'] == 0
    relative_point = None if not all_known or b['definite_positive'] == 0 else (
        b['definite_positive'] - a['definite_positive']) / b['definite_positive']
    return dict(baseline=b, auxiliary=a,
        signed_risk_difference_aux_minus_baseline_bounds=[
            (a['definite_positive'] - possible_b) / n,
            (a['definite_positive'] + a['unresolved_or_missing'] - b['definite_positive']) / n],
        bounds_are_identification_not_sampling_confidence_intervals=True,
        relative_reduction_point=relative_point,
        relative_reduction_bounds=[relative_worst, relative_best],
        zero_baseline_possible=b['definite_positive'] == 0,
        zero_baseline_is_not_percent_reduction=True,
        all_semantic_endpoints_known=all_known)


def signflip_reference(contributions):
    """Task-cluster reference distribution, not a randomized causal p value."""
    require(bool(contributions), 'Task contributions required')
    observed = abs(sum(contributions))
    values = [abs(sum(sign * value for sign, value in zip(signs, contributions)))
              for signs in itertools.product([-1, 1], repeat=len(contributions))]
    return dict(task_clusters=len(contributions), assignments=len(values), observed_absolute_sum=observed,
        two_sided_reference_probability=sum(value >= observed for value in values) / len(values),
        assumes_within_task_arm_exchangeability=True, randomized_assignment_not_established=True,
        not_general_population_significance_or_causal_proof=True)


def quantile(values, p):
    values = sorted(values)
    position = (len(values) - 1) * p
    lo, hi = math.floor(position), math.ceil(position)
    return values[lo] + (values[hi] - values[lo]) * (position - lo)


def companion_summary(scores, false_rejections, opportunities):
    """Only arithmetic on supplied labels; review claims remain externally unverified."""
    b_reject, a_reject = bounds(false_rejections[False]), bounds(false_rejections[True])
    score_known = all(value is not None for values in scores.values() for value in values)
    score_ok = score_known and sum(scores[True]) >= sum(scores[False])
    rejection_ok = a_reject['definite_positive'] + a_reject['unresolved_or_missing'] <= b_reject['definite_positive']
    opportunity_ok = all(row['supplied_clearance_claim_with_known_counts'] for row in opportunities)
    return dict(official_scores=scores,
        known_official_success_totals={str(arm): sum(v for v in values if v is not None)
                                      for arm, values in scores.items()},
        all_official_scores_known=score_known, official_score_nondegradation_observed=score_ok,
        false_rejection_trajectory_bounds=dict(baseline=b_reject, auxiliary=a_reject),
        worst_case_aux_false_rejection_does_not_exceed_known_baseline=rejection_ok,
        opportunity_reviews=opportunities,
        required_opportunity_review_clearance_claims_supplied=opportunity_ok,
        opportunity_review_provenance_verified_by_this_module=False,
        numerical_companion_pattern_supported=score_ok and rejection_ok and opportunity_ok,
        numerical_safety_rules_are_conservative_sufficient_not_proof_of_causal_adequacy=True)


def analyze(plan, records, *, resample=True):
    queue = plan['queue']
    require(len(queue) == 32 and len({r['run_id'] for r in queue}) == 32, 'The original frozen32 queue is required')
    require(all(type(r['task_id']) is int for r in queue), 'Original integer task IDs required')
    tasks = sorted({r['task_id'] for r in queue})
    require(len(tasks) == 8, 'Eight source-selected tasks, not16independent tasks')
    planned = {r['run_id']: r for r in queue}
    matching = {}
    for row in queue:
        key = row['task_id'], row['condition']
        require(type(row['observer_enabled']) is bool, 'Frozen arm boolean required')
        matching.setdefault(key, {})
        require(row['observer_enabled'] not in matching[key], 'Duplicate arm within an original matched pair')
        matching[key][row['observer_enabled']] = row['run_id']
    require(len(matching) == 16 and all(set(pair) == {False, True} for pair in matching.values()),
            'Exactly16original matched pairs required')
    conditions = sorted({key[1] for key in matching})
    require(conditions == ['clean', 'stale_replace'] and all(
        (task, condition) in matching for task in tasks for condition in conditions), 'Original task/condition grid changed')
    indexed = {}
    for row in records:
        require(row['run_id'] in planned and row['run_id'] not in indexed, 'Unknown, pooled or duplicate logical trajectory')
        require(row.get('status') in ['pending', 'completed', 'technical_failure'], 'Explicit original terminal status required')
        require(type(row.get('source_review_complete')) is bool, 'Explicit review coverage required')
        require(row.get('official_score') is None or type(row['official_score']) is int and row['official_score'] in [0, 1],
                'Official score must be separately sourced 0/1/unknown; technical failure is not0')
        require(row['status'] != 'technical_failure' or row.get('official_score') is None,
                'A technical failure cannot be converted to an official model zero')
        require(row.get('official_score') is None or row['status'] == 'completed',
                'An ongoing trajectory cannot acquire an official terminal score')
        for field, maximum in [('executed_actions', 50), ('actor_calls', 70)]:
            require(row.get(field) is None or type(row[field]) is int and 0 <= row[field] <= maximum,
                    'Original ' + field + ' bounds changed')
        require(type(row.get('false_rejection_assessment_complete', False)) is bool,
                'Explicit false-rejection review coverage required')
        indexed[row['run_id']] = row
    labels = {run: endpoint(indexed.get(run)) for run in planned}
    pairs = []
    source_complete = True
    all_terminals = True
    scores = {False: [], True: []}
    false_rejections = {False: [], True: []}
    exposure_reviews_needed = []
    condition_scores = {condition: {False: [], True: []} for condition in conditions}
    condition_rejections = {condition: {False: [], True: []} for condition in conditions}
    for (task, condition), runs in sorted(matching.items()):
        rows = {arm: indexed.get(run) for arm, run in runs.items()}
        pair = dict(task_id=task, condition=condition,
                    baseline_run=runs[False], auxiliary_run=runs[True],
                    baseline_Mirage=labels[runs[False]], auxiliary_Mirage=labels[runs[True]])
        pairs.append(pair)
        for arm, row in rows.items():
            complete = row is not None and row['status'] == 'completed' and row.get('official_score') is not None
            all_terminals &= complete
            source_complete &= row is not None and row['source_review_complete'] is True
            scores[arm].append(None if row is None else row.get('official_score'))
            condition_scores[condition][arm].append(scores[arm][-1])
            definite = None if row is None else row.get('any_definite_false_rejection')
            require(definite is None or type(definite) is bool, 'False rejection must retain independent uncertainty')
            reviewed = (row is not None and row['status'] == 'completed'
                        and row.get('false_rejection_assessment_complete') is True)
            false_rejections[arm].append(True if definite is True else False if reviewed and definite is False else None)
            condition_rejections[condition][arm].append(false_rejections[arm][-1])
        if all(rows.values()):
            uncertain = any(row.get(key) is None for row in rows.values() for key in ['actor_calls', 'executed_actions'])
            fewer = not uncertain and any(rows[True][key] < rows[False][key] for key in ['actor_calls', 'executed_actions'])
            if uncertain or fewer:
                review = rows[True].get('opportunity_review', {})
                require(isinstance(review, dict), 'Opportunity review must retain its explicit claim and source reference')
                claimed = review.get('independently_cleared') is True
                reference = review.get('source_review_receipt')
                cleared = not uncertain and claimed and isinstance(reference, str) and bool(reference.strip())
                exposure_reviews_needed.append(dict(task_id=task, condition=condition,
                    fewer_observed_actor_or_action_opportunities=fewer,
                    exposure_measurements_missing=uncertain,
                    supplied_independent_clearance_claim=claimed,
                    supplied_source_review_receipt=reference,
                    supplied_clearance_claim_with_known_counts=cleared,
                    source_reference_provenance_verified_here=False))
        else:
            exposure_reviews_needed.append(dict(task_id=task, condition=condition,
                fewer_observed_actor_or_action_opportunities=None, exposure_measurements_missing=True,
                supplied_clearance_claim_with_known_counts=False, source_reference_provenance_verified_here=False))
    result = compare_labels([p['baseline_Mirage'] for p in pairs], [p['auxiliary_Mirage'] for p in pairs])
    condition_results = {condition: compare_labels(
        [p['baseline_Mirage'] for p in pairs if p['condition'] == condition],
        [p['auxiliary_Mirage'] for p in pairs if p['condition'] == condition]) for condition in conditions}
    companion = companion_summary(scores, false_rejections, exposure_reviews_needed)
    by_condition_companion = {condition: companion_summary(condition_scores[condition],
        condition_rejections[condition], [r for r in exposure_reviews_needed if r['condition'] == condition])
        for condition in conditions}
    b_count = result['baseline']['definite_positive']
    worst_a = result['auxiliary']['definite_positive'] + result['auxiliary']['unresolved_or_missing']
    numeric_thresholds = {str(percent): b_count > 0 and 100 * (b_count - worst_a) >= percent * b_count
                          for percent in [30, 50]}
    condition_safety = all(value['numerical_companion_pattern_supported'] for value in by_condition_companion.values())
    target_pattern = (all_terminals and source_complete and numeric_thresholds['30']
                      and companion['numerical_companion_pattern_supported'] and condition_safety)
    statistics = None
    if all_terminals and result['all_semantic_endpoints_known']:
        contributions = [sum(int(p['baseline_Mirage']) - int(p['auxiliary_Mirage'])
                             for p in pairs if p['task_id'] == task) for task in tasks]
        statistics = dict(task_cluster_signflip_reference=signflip_reference(contributions))
        if resample:
            rng, sampled = random.Random(20261011), []
            for _ in range(10000):
                chosen = [tasks[rng.randrange(len(tasks))] for _ in tasks]
                difference = sum(sum(int(p['auxiliary_Mirage']) - int(p['baseline_Mirage'])
                                     for p in pairs if p['task_id'] == task) for task in chosen) / len(pairs)
                sampled.append(difference)
            statistics['risk_difference_task_cluster_bootstrap'] = dict(
                replicates=10000, seed=20261011, interval_95=[quantile(sampled, 0.025), quantile(sampled, 0.975)],
                resampling_unit='original task, retaining both conditions and both arms',
                descriptive_stability_for_selected_tasks_not_population_or_causal_CI=True)
    return dict(schema='frozen32-descriptive-matched-analysis-v1', planned_tracks=32, planned_pairs=16, unique_tasks=8,
        supplied_logical_tracks=len(indexed), completed_model_terminals=sum(r['status'] == 'completed' for r in records),
        technical_failures=sum(r['status'] == 'technical_failure' for r in records),
        missing_or_pending_tracks=32 - sum(r['status'] != 'pending' for r in records),
        all32model_terminals_and_official_scores_present=all_terminals, all32source_candidate_coverage_complete=source_complete,
        primary=result, by_condition=condition_results, matched_pairs=pairs,
        companion=companion, by_condition_companion=by_condition_companion,
        conservative_30_and_50_percent_checks_by_exact_integer_arithmetic=numeric_thresholds,
        condition_companions_checked_separately_to_expose_tradeoffs=True,
        statistics=statistics, numeric_development_target_pattern_supported=target_pattern,
        source_review_execution_join_and_official_receipt_provenance_verified_by_this_module=False,
        this_math_module_does_not_establish_efficacy_or_goal_completion=True,
        repeated_development_or_source_selected_tasks_not_general_population_proof=True,
        candidate_false_rejections_are_distinct_from_terminal_false_blocks=True,
        native_action_errors_accepted_executed_errors_recovery_and_cost_require_separate_source_bound_axes=True)
