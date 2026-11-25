"""CPU-testable actor wiring for one image-only generative observer.

No runtime client or launcher is supplied here. A real backend must separately
prove its native forward, full images, precision, generation and ownership.
"""
import base64
import copy
import json
from image_evidence import (ACTOR_BOUNDARY, EvidenceContractError, POLICY, actor_packet,
    build_image_only_request, canonical, digest)


class NeutralEvidenceObserver:
    def __init__(self, backend, *, model, revision, enabled, max_calls=60, emit=None):
        if type(enabled) is not bool or type(max_calls) is not int or not 0 <= max_calls <= 60:
            raise EvidenceContractError('Fixed arm and original finite observer call budget required')
        if enabled and not callable(backend):
            raise EvidenceContractError('A separately admitted native backend is required')
        self.backend, self.model, self.revision = backend, model, revision
        self.enabled, self.max_calls = enabled, max_calls
        self.emit = emit or (lambda kind, value: None)
        self.calls = 0
        self.terminals = {}

    def packet(self, image_raw):
        unavailable = {'policy': POLICY, 'status': 'observer_not_run', 'reading': None,
            'automatic_allow_or_block': False, 'semantic_correctness_established': False,
            'inventory_is_exhaustive': False, 'auxiliary_model_count': int(self.enabled)}
        if not self.enabled:
            self.emit('neutral_evidence_packet', copy.deepcopy(unavailable))
            return unavailable
        if image_raw is None:
            unavailable.update(status='unavailable_no_current_image')
            self.emit('neutral_evidence_packet', copy.deepcopy(unavailable))
            return unavailable
        request = build_image_only_request(image_raw, self.model, self.revision)
        key = digest(canonical(request))
        if key in self.terminals:
            result = copy.deepcopy(self.terminals[key])
            result['exact_input_reuse'] = True
            self.emit('neutral_evidence_reuse', {'request_sha256': key, 'not_a_new_observation': True})
            self.emit('neutral_evidence_packet', copy.deepcopy(result))
            return result
        if self.calls >= self.max_calls:
            unavailable.update(status='unavailable_budget_exhausted', image_sha256=digest(image_raw))
            self.emit('neutral_evidence_packet', copy.deepcopy(unavailable))
            return unavailable
        self.calls += 1
        self.emit('neutral_evidence_request', {'call_number': self.calls,
            'request': copy.deepcopy(request), 'request_sha256': key})
        try:
            # One call only. Any original one-format-retry allowance must be
            # enforced and recorded by an independently frozen runtime plan;
            # this adapter neither retries nor repairs a terminal reply.
            response = self.backend(copy.deepcopy(request))
            self.emit('neutral_evidence_raw_reply', {'response': copy.deepcopy(response),
                'request_sha256': key, 'preserved_before_contract_validation': True})
            required = {'request_sha256', 'image_sha256', 'model', 'revision', 'raw_output', 'natural_eos'}
            if not isinstance(response, dict) or set(response) != required:
                raise EvidenceContractError('Native response/provenance envelope mismatch')
            if (response['request_sha256'] != key or response['image_sha256'] != request['image_sha256'] or
                    response['model'] != self.model or response['revision'] != self.revision):
                raise EvidenceContractError('Native response is bound to a different image/model/request')
            result = actor_packet(request, response['raw_output'], response['natural_eos'])
            result['exact_input_reuse'] = False
        except Exception as error:
            result = copy.deepcopy(unavailable)
            result.update(status='preserved_technical_or_contract_failure_no_retry',
                image_sha256=request['image_sha256'], request_sha256=key,
                error_type=type(error).__name__, error=str(error))
            self.emit('neutral_evidence_failure', copy.deepcopy(result))
        self.terminals[key] = copy.deepcopy(result)
        self.emit('neutral_evidence_packet', copy.deepcopy(result))
        return result

    def augment(self, body, view):
        """Append one data block; all original messages/images/corrections remain."""
        original_view = canonical(view.data())
        if body.get('messages') != view.messages:
            raise EvidenceContractError('Actor must retain the complete original public messages')
        result = copy.deepcopy(body)
        messages = result['messages']
        current_index = next((i for i in range(len(messages) - 1, -1, -1)
            if messages[i].get('role') == 'user' and isinstance(messages[i].get('content'), list)), None)
        if current_index is None:
            raise EvidenceContractError('Current multimodal user message missing')
        images = [im for im in view.images if im.role == 'current']
        blocks = [block for block in messages[current_index]['content'] if block.get('type') == 'image_url']
        if len(images) > 1 or len(images) != len(blocks):
            raise EvidenceContractError('One received original image or explicit missing-image condition required')
        raw = images[0].raw if images else None
        if raw is not None:
            expected = 'data:image/png;base64,' + base64.b64encode(raw).decode('ascii')
            if blocks[0].get('image_url', {}).get('url') != expected:
                raise EvidenceContractError('Actor wire image differs from observer received image')
        packet = self.packet(raw)
        messages[current_index]['content'].append({'type': 'text', 'text': ACTOR_BOUNDARY +
            json.dumps(packet, ensure_ascii=False, separators=(',', ':'))})
        assert canonical(view.data()) == original_view
        assert {k: v for k, v in body.items() if k != 'messages'} == {k: v for k, v in result.items() if k != 'messages'}
        self.emit('neutral_evidence_actor_insertion', {'current_message_index': current_index,
            'original_actor_body_sha256': digest(canonical(body)), 'augmented_actor_body_sha256': digest(canonical(result)),
            'original_view_sha256': digest(original_view), 'packet_sha256': digest(canonical(packet)),
            'full_original_history_and_trailing_corrections_retained': True})
        return result
