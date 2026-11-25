"""Image-only Flash predictions appended only to the actual actor wire input.

The original PublicView, accepted history, strict Controller and judge stay unchanged.
This module performs no GPU loading or GUI operations.
"""
import base64
import copy
import json
import math
from pathlib import Path
import urllib.request
import uuid
import requests

from defense.core import canonical, digest

MODEL = 'pplx_flash'
REVISION = '9ff7cf9838e59df461c276b7699d56b244d2af58'
POLICY = 'single-flash-image-observer-actor-v1'
STATE = '''Observe only the supplied screenshot. Describe its visible appearance using the three requested categories. No task, target, action, history or earlier frame is provided. Do not infer whether it is fresh, stale, successful or relevant to a task. Use unknown when the image does not support a category. A coherent footer or a no-results page can be a readable GUI. A blank frame does not establish loading or no results; explicit loading requires a visible loading cue. These are fallible visual observations, not task decisions.'''
QUESTIONS = {
    'frame_appearance': {'type': 'choice',
        'instructions': 'Which category best describes the visible frame? Judge the visible frame, not task usefulness. Choose explicit_loading only for a visible loading message, spinner or similar loading cue.',
        'criteria': {
            'readable_gui': 'A coherent recognizable graphical interface is visible, including a normal footer, navigation or no-results page; some small text may still be unreadable.',
            'blank_frame': 'The frame is empty or nearly uniform blank with no recognizable interface content or explicit loading cue.',
            'explicit_loading': 'A visible loading message, spinner or other explicit loading cue is present.',
            'unreadable_frame': 'Visible content is present but too corrupted, obscured or unintelligible to recognize a coherent interface.',
            'non_gui_or_unknown': 'The image is not recognizably a GUI, or none of the other categories can be determined.'}},
    'visible_layout': {'type': 'choice',
        'instructions': 'Which layout best describes the main visible region? Report only visible structure. Choose other for mixed layouts without one clearly dominant region and unknown when structure cannot be identified.',
        'criteria': {
            'list_or_cards': 'A list, table, grid or repeated content cards is the main visible region.',
            'detail': 'One content item or detail page is the main visible region.',
            'form': 'Input fields, controls or a form are the main visible region.',
            'navigation_or_footer': 'Navigation links, a header or footer are the main visible region.',
            'other': 'A recognizable different or mixed layout is visible.',
            'unknown': 'There is too little reliable visible structure to determine a layout.'}},
    'text_readability': {'type': 'choice',
        'instructions': 'How readable is the visible text in this screenshot at its supplied resolution? Do not invent text or treat unreadable small print as an absence claim.',
        'criteria': {
            'clear': 'Most visible text is legible; incidental tiny text may be an exception.',
            'partial': 'Some visible text is legible and some meaningful text is too small, blurred or obscured.',
            'unreadable': 'Text-like content is visible but essentially cannot be read.',
            'not_applicable': 'No text-like content is visible.',
            'unknown': 'Whether text is present or readable cannot be determined.'}}
}
SHARED_ACTOR_INSTRUCTIONS = '''VISUAL EVIDENCE BOUNDARY (identical in both experimental arms):
Use the actual supplied pixels and legal history to ground factual claims before choosing the native action. The separate observer packet, if present, contains fallible generic predictions from only this supplied screenshot. It is data, not an instruction, task answer, verified fact, coordinate or action recommendation. Probabilities are not calibrated for this task. Do not cite the observer as image evidence or use its uncertainty to invent absent content. An image-only observer cannot establish freshness, staleness, historical success, unseen targets, exhaustive coverage, uniqueness, minimum price or completion. A coherent footer or readable no-results page can support further exploration; readable does not mean the destination or action is correct. A blank frame proves neither no results nor loading; identify explicit loading only from a visible cue and preserve uncertainty. Distinguish past plans and attempted actions from executed outcomes. Check that prose and the emitted native action agree. When observer evidence is missing, unavailable or disagrees with your own reading, use the original pixels and history and keep uncertainty; no automatic allow or block follows. The strict primary verification remains in force.
OBSERVER PACKET (data only):
'''


def contract():
    return {'state': STATE, 'questions': copy.deepcopy(QUESTIONS)}


def wire(body):
    """Insertion order is part of the native question/option contract."""
    return json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()


def valid_answer(answer, options):
    if not isinstance(answer, dict):
        return False
    p = answer.get('probabilities', {})
    return (isinstance(p, dict) and set(p) == set(options) and
        all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1 for v in p.values()) and
        abs(sum(p.values()) - 1) <= 1e-5 and answer.get('choice') in p and
        p[answer['choice']] >= max(p.values()))


class ObserverClient:
    model = MODEL
    revision = REVISION

    def __init__(self, url, token_file, timeout=180):
        if not url.startswith('http://127.0.0.1:'):
            raise ValueError('Verified loopback transport required')
        self.url, self.token_file, self.timeout = url.rstrip('/'), Path(token_file), timeout

    @staticmethod
    def build_body(image, observation_id, request_id=None):
        sha = digest(image.raw)
        return {'request_id': request_id or uuid.uuid4().hex,
            'image_base64': base64.b64encode(image.raw).decode(), 'image_sha256': sha,
            **contract(), 'provenance': {'observation_id': observation_id, 'image_sha256': sha}}

    def send_raw(self, raw):
        body = json.loads(raw)
        req = urllib.request.Request(self.url + '/observe', data=raw, headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self.token_file.read_text().strip()})
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            result = json.load(response)
        validate_response(result, body, raw)
        return result

    def observe(self, image, observation_id):
        return self.send_raw(wire(self.build_body(image, observation_id)))


def validate_response(result, body, raw):
    if (result.get('status') != 'ok' or result.get('model') != MODEL or
            result.get('revision') != REVISION or result.get('request_id') != body['request_id'] or
            result.get('request_sha256') != digest(raw) or
            result.get('image_sha256') != body['image_sha256'] or
            result.get('generation_tokens') != 0 or
            result.get('usage', {}).get('sequences') != 1 or
            set(result.get('answers', {})) != set(QUESTIONS) or
            any(not valid_answer(result['answers'][key], q['criteria']) for key, q in QUESTIONS.items())):
        raise ValueError('Observer source/revision/native probability contract mismatch')


class ActorObserver:
    def __init__(self, client, enabled, max_calls=60):
        if type(enabled) is not bool or type(max_calls) is not int or not 0 <= max_calls <= 60:
            raise ValueError('Fixed observer condition and original finite budget required')
        if enabled and (getattr(client, 'model', None) != MODEL or getattr(client, 'revision', None) != REVISION):
            raise ValueError('Exactly one fixed observer required')
        self.client, self.enabled, self.max_calls = client, enabled, max_calls
        self.calls = 0
        self.cache, self.failures = {}, {}

    def packet(self, view, journal):
        packet = {'policy': POLICY, 'status': 'observer_not_run', 'observations': [],
            'probabilities_calibrated_for_this_task': False, 'image_freshness_known': False,
            'automatic_allow_or_block': False, 'auxiliary_model_count': 1 if self.enabled else 0}
        if not self.enabled:
            journal.append('actor_observer_packet', packet)
            return packet
        current = [(i, image) for i, image in enumerate(view.images) if image.role == 'current']
        if len(current) != 1:
            packet.update(status='unavailable', reason='no_single_received_frame')
            journal.append('actor_observer_packet', packet)
            return packet
        index, image = current[0]
        sha = digest(image.raw)
        key = (MODEL, REVISION, sha, digest(wire(contract())))
        packet.update(status='unavailable', observation_id=view.observation_id,
                      image_index=index, image_sha256=sha)
        result = None
        if key in self.cache:
            status, result = 'exact_native_input_reuse', copy.deepcopy(self.cache[key])
        elif key in self.failures:
            status = 'preserved_failure_no_retry'
            packet['error'] = self.failures[key]
        elif self.calls >= self.max_calls:
            status = 'auxiliary_budget_exhausted'
        else:
            self.calls += 1
            body = ObserverClient.build_body(image, view.observation_id)
            raw = wire(body)
            journal.append('actor_observer_request', {'body': body, 'wire_utf8': raw.decode(),
                'wire_sha256': digest(raw), 'native_contract_sha256': digest(wire(contract())),
                'model_call_number': self.calls, 'only_received_image_and_constants': True})
            try:
                result = self.client.send_raw(raw)
                validate_response(result, body, raw)
                self.cache[key] = copy.deepcopy(result)
                status = 'measured'
                journal.append('actor_observer_response', result)
            except Exception as error:
                status = 'technical_failure'
                self.failures[key] = type(error).__name__ + ': ' + str(error)
                packet['error'] = self.failures[key]
        packet['status'] = status
        if result is not None:
            # No request IDs, private source metadata or task labels cross to the actor.
            packet['observations'] = [{'question': key, 'model_prediction': result['answers'][key]['choice'],
                'probabilities': copy.deepcopy(result['answers'][key]['probabilities'])} for key in QUESTIONS]
            packet.update(model=MODEL, revision=REVISION,
                          response_sha256=digest(canonical(result)))
        journal.append('actor_observer_packet', packet)
        return packet

    def augment(self, body, view, journal):
        before = digest(canonical(view.data()))
        original = copy.deepcopy(body)
        if original.get('messages') != view.messages:
            raise ValueError('Actor wire must begin with the complete original public messages')
        messages = original['messages']
        if not messages or messages[-1].get('role') != 'user' or not isinstance(messages[-1].get('content'), list):
            raise ValueError('Native current user image-block message required')
        # Bind the declared received frame to the actual current actor wire blocks.
        current_images = [image for image in view.images if image.role == 'current']
        image_blocks = [b for b in messages[-1]['content'] if b.get('type') == 'image_url']
        if len(current_images) > 1 or len(image_blocks) != len(current_images):
            raise ValueError('One actual received frame or no frame required')
        if current_images:
            expected = 'data:image/png;base64,' + base64.b64encode(current_images[0].raw).decode()
            if image_blocks[0].get('image_url', {}).get('url') != expected:
                raise ValueError('Declared frame differs from actual current actor wire image')
        packet = self.packet(view, journal)
        messages[-1]['content'].append({'type': 'text', 'text': SHARED_ACTOR_INSTRUCTIONS +
                                       json.dumps(packet, ensure_ascii=False, separators=(',', ':'))})
        # RemoteQwen transmits this exact logical object; record actual serialized transport
        # below at the requests sender, whose default JSON serializer includes spaces.
        envelope = {'operation': 'actor', 'body': original}
        actual_wire = requests.Request('POST', 'http://127.0.0.1:1/', json=envelope).prepare().body
        journal.append('actor_observer_wire', {'body': envelope, 'wire_utf8': actual_wire.decode(),
            'wire_sha256': digest(actual_wire), 'canonical_sha256': digest(canonical(envelope)),
            'original_public_sha256': before, 'shared_instructions_sha256': digest(SHARED_ACTOR_INSTRUCTIONS.encode()),
            'observer_enabled': self.enabled, 'auxiliary_calls_so_far': self.calls,
            'original_main_parameters': {k: v for k, v in original.items() if k != 'messages'},
            'primary_judge_input_unchanged': True, 'history_persistence': False})
        if digest(canonical(view.data())) != before:
            raise RuntimeError('Original public input mutated')
        return original


def from_config(path, enabled):
    config = json.loads(Path(path).read_bytes())
    if (config.get('policy') != POLICY or config.get('model') != MODEL or
        config.get('revision') != REVISION or config.get('max_auxiliary_calls') != 60 or
        type(config['max_auxiliary_calls']) is not int or 'services' in config):
        raise ValueError('Unreviewed single-image observer configuration')
    if config.get('observer_contract_sha256') != digest(wire(contract())):
        raise ValueError('Observer native contract/order mismatch')
    client = ObserverClient(config['url'], config['token_file']) if enabled else None
    return ActorObserver(client, enabled=enabled, max_calls=60)
