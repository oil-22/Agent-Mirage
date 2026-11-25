"""Verify original GUI HTTP exchanges and source-rebuild observer insertion."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import types


def collect(root, manifest_sha, service, sources):
    import os
    root = Path(root)
    sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    read = lambda path: json.loads(Path(path).read_bytes())
    assert os.getuid() == 1015 and sha(root / 'manifest.json') == manifest_sha
    for name, value in read(root / 'manifest.json')['files'].items():
        assert sha(root / name) == value, name
    for filename in ['mixed_journal_map.py', 'mixed_audit_selection.py', 'mixed_exchange_checks.py']:
        module = types.ModuleType(filename[:-3])
        sys.modules[filename[:-3]] = module
        exec(compile(sources[filename], filename, 'exec'), module.__dict__)
    selector = sys.modules['mixed_audit_selection']
    exchange = sys.modules['mixed_exchange_checks']
    sys.path.insert(0, str(root / 'release'))
    from image_evidence import ACTOR_BOUNDARY, canonical, digest
    from evidence_observer import NeutralEvidenceObserver
    bindings = service['bindings']
    by_request_id = {value['request_id']: value for value in bindings.values()}
    assert len(by_request_id) == len(bindings)
    wanted = set(by_request_id)
    http, windows, snapshots = {}, {}, []
    for path in sorted((root / 'batch/runs').glob('*/attempt-*/events.jsonl')):
        with path.open('rb') as stream:
            selected = selector.collect_GUI_prefix(stream, wanted)
        assert not set(http).intersection(selected['http']), 'Duplicate original request across GUI journals'
        http.update(selected['http'])
        windows.update(selected['actor_windows'])
        snapshots.append(dict(path=str(path), **selected['prefix']))
    assert set(http) == wanted, 'Some sealed server requests lack original GUI HTTP events'
    reports, insertions = [], []
    for request_id, binding in by_request_id.items():
        wire = http[request_id]
        assert set(wire) == {'request', 'raw_response', 'response'}, 'Incomplete actual GUI HTTP exchange'
        proof = exchange.check_http_exchange(request_event=wire['request'], raw_response_event=wire['raw_response'],
            response_event=wire['response'], server_binding=binding, mapped_request=binding['mapped_request'])
        reports.append(proof)
        if binding['mapped_request']['operation'] != 'actor':
            continue
        window = windows[request_id]
        def one(kind):
            values = [event for event in window if event['kind'] == kind]
            assert len(values) == 1, kind
            return values[0]
        context = one('actor_request')
        enabled = binding['frozen_run']['observer_enabled']
        ref = read(root / 'auxiliary-identity-reference.json')['base_model']
        prior = binding['mapped_request']['preceding_auxiliary_request']
        observer_request = observer_reply = evidence_exchange = None
        envelope = None
        if prior is not None:
            assert enabled and prior in bindings
            auxiliary = bindings[prior]
            assert auxiliary['mapped_request']['operation'] == 'evidence'
            observer_request, observer_reply = one('neutral_evidence_request'), one('neutral_evidence_raw_reply')
            evidence_exchange = http[auxiliary['request_id']]
            envelope = auxiliary['response']['evidence_response']
            starting_calls = auxiliary['mapped_request']['original_track_attempt_index'] - 1
        else:
            assert not any(event['kind'] in ['neutral_evidence_request', 'neutral_evidence_raw_reply'] for event in window)
            starting_calls = binding['mapped_request']['prior_evidence_calls_in_this_track']
        # Reconstruct the packet through the exact frozen observer with its
        # recorded envelope. This callback never contacts a model or a service.
        def replay_envelope(request):
            assert prior is not None
            actual_request = evidence_exchange['request']['data']['body']['payload']
            assert request == actual_request
            return envelope
        observer = NeutralEvidenceObserver(replay_envelope if enabled else None,
            model=ref['repo'], revision=ref['revision'], enabled=enabled, max_calls=60)
        observer.calls = starting_calls
        public = context['data']['public']
        current = [item for item in public['images'] if item['role'] == 'current']
        assert len(current) <= 1
        image = None
        if current:
            blocks = [block for message in public['messages'] if isinstance(message.get('content'), list)
                      for block in message['content'] if block.get('type') == 'image_url']
            matches = [base64.b64decode(block['image_url']['url'].split(',', 1)[1], validate=True)
                       for block in blocks]
            image = next(raw for raw in matches if digest(raw) == current[0]['sha256'])
        packet = observer.packet(image)
        proof = exchange.check_actor_insertion(context_event=context, packet_event=one('neutral_evidence_packet'),
            insertion_event=one('neutral_evidence_actor_insertion'), actor_request_event=wire['request'],
            actor_template=read(root / 'actor-template.json'), actor_boundary=ACTOR_BOUNDARY,
            expected_packet=packet, observer_enabled=enabled, evidence_exchange=evidence_exchange,
            observer_request_event=observer_request, observer_raw_reply_event=observer_reply)
        proof.update(request=binding['mapped_request']['request'],
                     preceding_auxiliary_request=prior,
                     source_reconstruction_callback_only_not_a_new_model_call=True,
                     selected_context_event_sha256=context['sha256'],
                     selected_packet_event_sha256=one('neutral_evidence_packet')['sha256'])
        insertions.append(proof)
    assert 'torch' not in sys.modules, 'GUI read-only audit imported a model runtime'
    return dict(passed=True, HTTP=reports, actor_insertions=insertions, GUI_prefixes=snapshots,
                no_model_weights_loaded=True, no_CUDA_initialization=True, new_model_GUI_scorer_calls=0,
                semantic_correctness_or_efficacy_established=False)
