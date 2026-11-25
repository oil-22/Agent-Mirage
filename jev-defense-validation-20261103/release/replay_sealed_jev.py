"""Offline policy wiring over exact sealed replies. NEVER runs a model or browser."""
import argparse
import copy
import json
import time
from pathlib import Path
from defense.core import Controller, Journal, PublicView, VisibleImage, canonical, digest
from jev_auxiliary import JevAuxiliary, REVISIONS, STATE, QUESTIONS
from jev_cued_controller import JevCuedController, CUE_RULES


class NoInferenceClient:
    def __init__(self, model):self.model = model
    def decide(self, *args):raise AssertionError('Offline replay must never infer')


def seal(root, name):
    entries = json.loads((root / name).read_bytes())
    for rel, expected in entries.items():
        assert digest((root / rel).read_bytes()) == expected, (root, rel)


def main(source, target):
    target.mkdir(parents=True, exist_ok=False)
    frozen = source / 'results/finalizations/1793623877744069789'
    seal(frozen, 'seal.json')
    paired = json.loads((frozen / 'paired-summary.json').read_bytes())
    assert len(paired['rows']) == 36
    aux = JevAuxiliary([NoInferenceClient(m) for m in REVISIONS], max_calls=0)
    images = {};bindings = []
    for row in paired['rows']:
        reply = row['result'];model = row['model'];key = row['query']
        attempt = 'style-01' if model == 'jev_style' else 'neo-01'
        receipt = source / 'results' / attempt / 'runtime/requests' / reply['request_id']
        seal(receipt, 'seal.json')
        actual = json.loads((receipt / 'response.json').read_bytes())
        req = json.loads((receipt / 'request.json').read_bytes())
        assert actual == reply
        assert req['state'] == STATE and req['question'] == QUESTIONS[key][0]
        assert req['options'] == QUESTIONS[key][1]
        raw = (receipt / 'original.image').read_bytes();h = digest(raw)
        assert h == reply['image_sha256'] and reply['revision'] == REVISIONS[model]
        images[row['source']['observation_id']] = raw
        cache_key = (model, REVISIONS[model], h, key, digest(canonical([STATE, QUESTIONS[key]])))
        aux.cache[cache_key] = copy.deepcopy(reply)
        bindings.append({'source': row['source'], 'model': model, 'query': key,
                         'response_sha256': digest((receipt / 'response.json').read_bytes())})
    records = []
    for name, raw in sorted(images.items()):
        v = PublicView(name, [{'role': 'user', 'content': 'Offline actual-reply wiring; no main inference.'}],
                       (VisibleImage(raw),))
        original = canonical(v.data());seen = []
        def judge(system, obs, candidate):
            seen.append(system)
            w, h = obs.images[0].info()['size']
            return {'claims': [], 'action': {'status': 'supported', 'target_kind': 'button',
                    'reason': 'SCRIPTED CONTRACT FIXTURE ONLY',
                    'evidence': [{'observation_id': obs.observation_id, 'image_index': 0,
                                 'coordinate_space': 'pixels', 'box_xyxy': [0, 0, w, h],
                                 'description': 'SCRIPTED CONTRACT FIXTURE ONLY'}]},
                    'pure_wait': False, 'acknowledges_visual_deficit': False}
        c = JevCuedController(judge, Journal(target / name), jev_auxiliary=aux)
        candidate = 'WIRING FIXTURE';proposal = {'name': 'click', 'parsed': True}
        result = c.inspect('verify', v, candidate, proposal)
        assert CUE_RULES in seen[-1] and c.verifier_calls == 1 and aux.calls == 0
        assert canonical(v.data()) == original
        events = [json.loads(s) for s in (target / name / 'events.jsonl').read_text().splitlines()]
        packet = next(e['data'] for e in events if e['kind'] == 'jev_cue_policy')
        assert len(packet['observations']) == 6 and not packet['excluded']
        previous = '0' * 64
        for event in events:
            h = event.pop('sha256')
            assert event['previous'] == previous and digest(canonical(event)) == h
            previous = h
        records.append({'frame': name, 'predictions_reused': 6, 'full_input_unchanged': True,
                        'primary_reply_is_fixture': True, 'event_chain_head': previous,
                        'semantic_pass': None})
    summary = {'phase': 'offline_policy_wiring_complete', 'time': time.time(),
               'new_model_calls': aux.calls, 'primary_27B_calls': 0, 'GUI_actions': 0,
               'sealed_actual_predictions_reused': 36, 'frames': records, 'bindings': bindings,
               'real_policy_semantics_validated': False, 'full_GUI_ready': False}
    (target / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    (target / 'seal.json').write_text(json.dumps({str(p.relative_to(target)).replace('\\', '/'):
        digest(p.read_bytes()) for p in target.rglob('*') if p.is_file()}, indent=2), encoding='utf-8')
    print(json.dumps({'result': str(target), 'predictions_reused': 36, 'new_calls': aux.calls,
                      'semantic_validation': False}))


if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('--source', type=Path, required=True)
    p.add_argument('--root', type=Path, required=True);a = p.parse_args();main(a.source, a.root)
