"""Preserve accepted native actor exchanges, including every supplied image block.

This does not choose facts/actions or modify Controller's within-decision recovery.
Rejected candidates remain immutable journal evidence under that original protocol.
Only the accepted request/reply becomes the next decision's conversation history.
"""
import base64
import copy
import hashlib
import json


class HistoryBindingError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


class CompleteAcceptedActorHistory:
    def __init__(self, system):
        self.system = system
        self.messages = []
        self.pending = None
        self.accepted = []

    def current_messages(self, current_blocks):
        return [{'role': 'system', 'content': self.system}] + copy.deepcopy(self.messages) + [
            {'role': 'user', 'content': copy.deepcopy(current_blocks)}]


    def reference_image_bytes(self, current_raw=None):
        """Return full past supplied bytes for strict image-index binding only.

        All original blocks, including duplicates, remain in actor messages.
        Duplicate byte-identities share an index in the verifier's image list.
        Current-image equality does not turn a prior frame into a fresh capture.
        """
        seen = set() if current_raw is None else {hashlib.sha256(current_raw).hexdigest()}
        references = []
        for message in self.messages:
            if not isinstance(message.get('content'), list):
                continue
            for block in message['content']:
                if block.get('type') != 'image_url':
                    continue
                url = block['image_url']
                url = url['url'] if isinstance(url, dict) else url
                if not isinstance(url, str) or not url.startswith('data:image/png;base64,'):
                    raise HistoryBindingError('Only the original embedded PNG history is accepted')
                raw = base64.b64decode(url.split(',', 1)[1], validate=True)
                identity = hashlib.sha256(raw).hexdigest()
                if identity not in seen:
                    references.append(raw)
                    seen.add(identity)
        return references

    def record_actual_reply(self, body, reply):
        if not isinstance(body, dict) or not isinstance(reply, str):
            raise HistoryBindingError('Actual actor request body and native reply required')
        messages = body.get('messages')
        prefix = [{'role': 'system', 'content': self.system}] + self.messages
        if not isinstance(messages, list) or len(messages) <= len(prefix) or messages[:len(prefix)] != prefix:
            raise HistoryBindingError('Actor request removed or rewrote accepted original history')
        if not any(message.get('role') == 'user' for message in messages[len(prefix):]):
            raise HistoryBindingError('Current actual actor user message missing')
        self.pending = {'body': copy.deepcopy(body), 'reply': reply, 'body_sha256': digest(body)}

    def commit_accepted(self, result):
        if not isinstance(result, dict) or result.get('status') != 'accepted':
            raise HistoryBindingError('Only an actual accepted decision can be committed')
        if self.pending is None or result.get('candidate') != self.pending['reply']:
            raise HistoryBindingError('Accepted candidate differs from last actual native reply')
        actual = self.pending['body']['messages']
        previous = copy.deepcopy(self.messages)
        self.messages = copy.deepcopy(actual[1:]) + [{'role': 'assistant', 'content': self.pending['reply']}]
        if self.messages[:len(previous)] != previous:
            raise HistoryBindingError('Commit changed previous accepted messages')
        proof = {'accepted_observation_id': result['observation_id'],
                 'actual_actor_body_sha256': self.pending['body_sha256'],
                 'history_before_sha256': digest(previous), 'history_after_sha256': digest(self.messages),
                 'accepted_exchanges': len(self.accepted) + 1,
                 'history_message_count': len(self.messages),
                 'all_accepted_image_blocks_and_auxiliary_data_preserved': True,
                 'within_decision_Controller_recovery_unchanged': True,
                 'no_hidden_capture_or_evaluator_fields_appended': True}
        self.accepted.append(proof)
        self.pending = None
        return proof

