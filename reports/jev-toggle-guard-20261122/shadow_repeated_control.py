"""Offline entry-coverage replay. No model calls, no gate or release change."""

import argparse
from collections import Counter
import io
from pathlib import Path

from PIL import Image, ImageChops

from audit_panel import chain, event, only
from audit_toggle import checked_controls
from live_common import load, save, sha
from toggle_protocol import eligible


def repeat_entry(binding, click, dispatch, signed_frames):
    """Would the signed control justify *asking* the same precise question?"""
    frames, packets = zip(*signed_frames, strict=True)
    scope = eligible(binding, click, dispatch, frames, packets)
    if not scope['eligible']:
        return scope
    box = scope['comparison_box']
    with Image.open(io.BytesIO(frames[1].png)) as a, Image.open(io.BytesIO(frames[2].png)) as b:
        same_post_pixels = ImageChops.difference(a.convert('RGB').crop(box), b.convert('RGB').crop(box)).getbbox() is None
    return {**scope, 'eligible': same_post_pixels,
            'reason': 'stable_changed_control_requires_semantic_review' if same_post_pixels else 'recent_control_pixels_still_changing'}


def replay(audit):
    summary = load(audit)
    assert summary['status'] == 'completed_panel' and summary['audited_episodes'] == 36
    root = Path(summary['attempt'])
    assert sha(root / 'local-seal.json') == summary['all_raw_sha256_seal']
    lookup = load(root / 'remote-seal.json')['files']
    examined = []
    for row in summary['episodes']:
        if row['case']['arm'] != 'scoped':
            continue
        label = row['id']
        if not row['action']:
            examined.append({'episode': label, 'result': 'no_dispatched_action'})
            continue
        journal = root / 'run' / 'episodes' / label / 'events.jsonl'
        assert sha(journal) == lookup[journal.relative_to(root).as_posix()]
        head, events = chain(journal)
        assert head == row['journal_head']
        end = only(w['end_ns'] for w in event(events, 'study_window_started') if w['stage'] == 'post_action')
        frames = {f['capture_id']: f for f in row['frames']}
        for f in frames.values():
            png = Path(f['acquisition_png'])
            assert sha(png) == f['source_sha256'] == lookup[png.relative_to(root).as_posix()]
        b, click, dispatch, records = checked_controls(root / 'run' / 'source' / label, frames, row['action'])
        initial = row['initial']['capture_id']
        standard = {r['capture_id']: r for r in row['flash'] if r['kind'] == 'temporal'}
        rejected, booking, previous = Counter(), None, None
        for cap, frame in frames.items():
            current = standard.get(cap)
            if (not current or current['decision'] != 'NO' or current['finished_ns'] >= end):
                previous = None
                continue
            if previous:
                source_caps = (initial, previous['capture_id'], cap)
                scope = repeat_entry(b, click, dispatch, [records[k] for k in source_caps])
                if scope['eligible']:
                    booking = {'candidate_capture_ids': source_caps, 'png_sha256': [frames[k]['source_sha256'] for k in source_caps],
                               'independently_audited_fixture_truth': frame['truth'], 'prereview_p_yes': [previous['p_yes'], current['p_yes']],
                               'elapsed_before_possible_question_seconds': (current['finished_ns'] - row['action']['send_end_ns'])/1e9,
                               'time_remaining_in_study_seconds': (end - current['finished_ns'])/1e9, 'scope': scope}
                    break  # At most one extra question per action, even in shadow.
                rejected[scope['reason']] += 1
            previous = current
        examined.append({'episode': label, 'scenario': row['case']['scenario'], 'original_delivery': bool(row['delivery']),
                         'result': 'would_ask_only' if booking else 'no_extra_question', 'entry': booking,
                         'scope_rejection_reasons': dict(rejected)})
    assert len(examined) == 12
    return {'scope': 'Retrospective eligibility replay on signed trial frames. Neither a native targeted result nor a recovered delivery.',
            'parent_audit_sha256': sha(audit), 'episodes': examined,
            'ready_frames_that_would_trigger': sum(bool(r.get('entry') and r['entry']['independently_audited_fixture_truth']=='ready') for r in examined),
            'bad_or_unresolved_frames_that_would_trigger': sum(bool(r.get('entry') and r['entry']['independently_audited_fixture_truth']!='ready') for r in examined),
            'new_model_calls': 0, 'new_GUI_actions': 0, 'production_changed': False}


if __name__ == '__main__':
    opt = argparse.ArgumentParser(description=__doc__)
    opt.add_argument('audit', type=Path)
    opt.add_argument('result', type=Path)
    args = opt.parse_args()
    result = replay(args.audit)
    save(args.result, result)
    print(result['ready_frames_that_would_trigger'], 'ready frames would become eligible for a supplemental question; 0 sent.')
