"""Finite, once-only full-GUI protocol. No model or network imports."""
import copy

class RunBudget:
    def __init__(self, plan, carryover):
        self.queue = copy.deepcopy(plan['queue']); self.index = 0; self.active = None
        self.carryover = copy.deepcopy(carryover)
        self.ids = set(carryover['disallowed_prior_request_ids']); self.counts = {}; self.done = []; self.failed = False

    def admit(self, path, body):
        assert isinstance(body, dict) and isinstance(body.get('request_id'), str) and len(body['request_id']) == 32
        assert body['request_id'] not in self.ids, 'Duplicate request, no automatic retry'
        assert not self.failed and self.index < len(self.queue), 'Batch terminal'
        item = self.queue[self.index]
        assert body.get('trajectory_id') == item['run_id'], 'Frozen run order mismatch'
        if path == '/begin':
            assert set(body) == {'trajectory_id','request_id'} and self.active is None
            self.active = item['run_id']
            self.counts = copy.deepcopy(self.carryover['initial_transport_counts']) if self.index == 0 else {'actor':0,'judge':0,'evidence':0}
        elif path == '/end':
            assert set(body) == {'trajectory_id','request_id','status','terminal_receipt_sha256'}
            assert self.active == item['run_id'] and body['status'] in ['completed','technical_failure','stopped']
            assert len(body['terminal_receipt_sha256']) == 64
            self.done.append({'run_id':self.active,'counts':copy.deepcopy(self.counts),'status':body['status'],
                              'GUI_terminal_sha256':body['terminal_receipt_sha256']})
            self.failed = body['status'] != 'completed'; self.active = None; self.index += 1
        else:
            assert path in ['/','/evidence'] and self.active == item['run_id']
            assert set(body) == {'trajectory_id','decision_index','attempt_index','request_id','payload'}
            assert type(body['decision_index']) is int and 1 <= body['decision_index'] <= 50
            op = 'evidence' if path == '/evidence' else body['payload']['operation']
            assert op in self.counts and (op != 'evidence' or item['observer_enabled'])
            cap = {'actor':70,'judge':140,'evidence':60}[op]
            assert type(body['attempt_index']) is int and body['attempt_index'] == self.counts[op]+1 <= cap
            self.counts[op] += 1
        self.ids.add(body['request_id'])
        return copy.deepcopy(item)

    @property
    def terminal(self): return self.failed or self.index == len(self.queue)
