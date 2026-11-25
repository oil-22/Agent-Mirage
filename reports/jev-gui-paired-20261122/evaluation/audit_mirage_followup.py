"""Trace definite Mirage replies to native actions and separately review later self-correction."""

import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import re
import time

from collect import HERE, read, save, sha
from extract_on_host import canonical, hx
from link import verify
from review_cycle import review_pairs
from summarize import load_reviews


ACTION = ('proposed_native_action_error', 'no_definite_native_action_error',
          'proposed_native_action_unresolved', 'no_environment_action_proposed')
REVISION = ('confirmed_self_correction', 'no_confirmed_self_correction',
            'possible_revision_unresolved', 'no_later_delivered_reply')


def source(ledger_path, report_path):
    verify(ledger_path)
    verify(report_path)
    ledger = read(ledger_path/'private-linked.json')
    report = read(report_path/'condition-by-version.json')
    assert report['ledger_seal_sha256'] == sha(ledger_path/'seal.json')
    quality, labels, sources = load_reviews(ledger, review_pairs(report_path))
    assert sources == report['review_sources']
    return ledger, labels, report


def material(ledger, labels):
    cases, refs, picked_messages = {}, {}, {}
    legal = ledger['public_legal_messages']
    for row in ledger['rows']:
        slot, tape = row['slot'], row['evidence']
        if not tape:
            continue
        run = slot['run_id']
        events = {j:v for (r,j),v in labels.items() if r == run and v['semantic_label'] == 'definite'}
        if not events:
            continue
        first = min(events)
        later = []
        for step in tape['steps']:
            n, main = step['step'], step['main']
            if n < first or not (main and main['natural_EOS']):
                continue
            assert step['actual_first_forward'] and step['reply'] and step['request']['request_id'] == step['reply']['request_id']
            for digest in main['messages_ordered']:
                item = legal[digest]
                assert hx(canonical(item)) == digest
                picked_messages[digest] = item
            reply = main['reply_text']
            assert hx(reply.encode('utf-8')) == main['reply_sha256']
            later.append({'decision':n, 'legal_message_ids':main['messages_ordered'],
                'current_image_sha256':main['current_image_sha256'], 'raw_reply_sha256':main['reply_sha256'],
                'raw_reply':reply})
        theses = [{'decision':n, 'original_claim_type':v.get('claim_type'),
                    'original_independent_note':v.get('note') or v['evidence']} for n,v in sorted(events.items())]
        assert [t['decision'] for t in theses] == [a['decision'] for a in later if a['decision'] in events]
        case = {'definite_claims':theses, 'delivered_tree_in_decision_order':later}
        key = 'F' + hx(canonical(case))[:20]
        assert cases.setdefault(key, case) == case
        refs.setdefault(key,[]).append({'run':run,'terminal_sha256':tape['terminal_sha256']})
    assert sum(len(cases[k]['definite_claims'])*len(v) for k,v in refs.items()) == sum(
        label['semantic_label']=='definite' for label in labels.values())
    # Each user image element is already hash-projected in the independently reviewed source.
    images = {x['sha256'] for message in picked_messages.values() if isinstance(message['content'],list)
              for x in message['content'] if x['type']=='image'}
    return cases, picked_messages, refs, images


def export(ledger_path, report_path):
    ledger, labels, _ = source(ledger_path, report_path)
    cases, messages, refs, images = material(ledger, labels)
    stamp = str(time.time_ns())
    public = HERE/'followup-review-packets'/stamp
    private = HERE/'followup-review-private'/stamp
    (public/'images').mkdir(parents=True,exist_ok=False)
    private.mkdir(parents=True,exist_ok=False)
    for digest in sorted(images):
        original = HERE/'original-images'/(digest+'.png')
        assert sha(original)==digest
        os.link(original, public/'images'/original.name)
    save(public/'cases.json', {'cases':cases, 'legal_messages':messages,
        'scope':'Secondary review of already sealed definite claims. Includes only delivered legal messages, '
                'actual native replies and original images. Score, arm, gate outcome, private native receipts '
                'and terminal state omitted. Campaign history was known, so this is not full blinding.',
        'original_png_sha256':sorted(images)})
    save(public/'seal.json', {'cases.json':sha(public/'cases.json')})
    save(private/'mapping.json', {'ledger_seal':sha(ledger_path/'seal.json'), 'report_seal':sha(report_path/'seal.json'),
        'packet':str(public),'packet_seal':sha(public/'seal.json'),'sources':refs})
    save(private/'seal.json', {'mapping.json':sha(private/'mapping.json')})
    return {'public':str(public), 'private':str(private), 'trajectory_reviews':len(cases),
            'trajectory_instances':sum(map(len,refs.values())), 'PNG_count':len(images)}


def validate_notes(case, actual):
    ds = {t['decision'] for t in case['delivered_tree_in_decision_order']}
    assert [v['decision'] for v in actual] == [v['decision'] for v in case['definite_claims']]
    fields = {'decision','native_proposal','proposal_basis','later_revision','later_evidence_decisions','revision_basis'}
    for v in actual:
        assert set(v) == fields
        assert v['native_proposal'] in ACTION and v['later_revision'] in REVISION
        assert v['proposal_basis'].strip() and v['revision_basis'].strip()
        d = v['decision']
        later = sorted(j for j in ds if j > d)
        indices = v['later_evidence_decisions']
        assert indices == sorted(set(indices)) and set(indices)<=set(later)
        assert (v['later_revision']=='no_later_delivered_reply') == (not later)
        if v['later_revision'] in ('confirmed_self_correction','possible_revision_unresolved'):
            assert indices


def review_pack(public, reviewed, ancestors=frozenset()):
    verify(public)
    verify(reviewed)
    assert reviewed.resolve() not in ancestors, 'Follow-up reuse cycle'
    pkt = read(public/'cases.json')
    notes = read(reviewed/'judgments.json')
    assert notes['packet_seal'] == sha(public/'seal.json') and not notes['joined_private_execution']
    assert notes['cases'].keys() == pkt['cases'].keys()
    for key, items in notes['cases'].items():
        validate_notes(pkt['cases'][key],items)
    prior = notes.get('exact_prior')
    if prior:
        other_public, other_notes = (Path(prior[k]['path']) for k in ('packet','judgments'))
        assert sha(other_public/'seal.json') == prior['packet']['seal_sha256']
        assert sha(other_notes/'seal.json') == prior['judgments']['seal_sha256']
        other, old = review_pack(other_public,other_notes,ancestors | {reviewed.resolve()})
        expected = exact_cases(pkt,other)
        assert prior['case_keys'] == sorted(expected)
        assert all(notes['cases'][key] == old['cases'][key] for key in expected)
    return pkt,notes


def exact_cases(packet, previous):
    return {key for key, case in packet['cases'].items() if previous['cases'].get(key) == case}


def prior_cases(packet, original):
    old_packet,old_notes = review_pack(*original)
    keys = exact_cases(packet,old_packet)
    links = {k:{'path':str(p.resolve()),'seal_sha256':sha(p/'seal.json')}
             for k,p in zip(('packet','judgments'),original)}
    return {'case_keys':sorted(keys),**links}, {k:old_notes['cases'][k] for k in keys}


def seal_notes(public, notes_path, original=None):
    verify(public)
    pkt = read(public/'cases.json')
    notes = read(notes_path)
    assert set(notes)=={'review_scope','cases'} and notes['review_scope'].strip()
    prior, reused = prior_cases(pkt,original) if original else (None,{})
    assert notes['cases'].keys() == pkt['cases'].keys() - reused.keys()
    combined = {k:reused[k] if k in reused else notes['cases'][k] for k in pkt['cases']}
    for key, items in combined.items():
        validate_notes(pkt['cases'][key],items)
    for name in pkt['original_png_sha256']:
        assert sha(public/'images'/(name+'.png')) == name
    out = HERE/'followup-review-labels'/str(time.time_ns())
    out.mkdir(parents=True,exist_ok=False)
    save(out/'judgments.json', {**notes,'cases':combined,'exact_prior':prior,
        'packet_seal':sha(public/'seal.json'),'joined_private_execution':False})
    save(out/'seal.json', {'judgments.json':sha(out/'judgments.json')})
    return {'judgments':str(out),'seal_sha256':sha(out/'seal.json'),
        'exact_prior_cases':len(reused),'manual_cases':len(notes['cases'])}


def execution_binding(item, step, tape):
    """Join the raw actor proposal to the native result, including an early executor failure."""
    proposal, receipt, reply, submit = (step[k] for k in ('proposal','executed','main','submit'))
    assert step['actual_first_forward'] and reply['natural_EOS'] and submit
    assert submit['image_sha256'] == reply['current_image_sha256']
    assert step['reply']['text_sha256'] == reply['reply_sha256']
    assert step['reply']['request_id'] == step['request']['request_id']
    if proposal:
        assert proposal['candidate_sha256'] == reply['reply_sha256']
        assert proposal['capture_id'] == submit['capture_id']
        assert proposal['image_sha256'] == reply['current_image_sha256']
        assert proposal['environment_action'] == bool(receipt)
    if not receipt:
        return 'no_native_environment_action'
    assert receipt['step'] == step['step'] == item['decision']
    assert type(receipt['ok']) is bool and item['native_proposal'] != 'no_environment_action_proposed'
    if not proposal:
        # The executor writes the native receipt before raising on a rejected action;
        # the controller only emits a proposal-dispatch event after execute() returns.
        assert receipt['ok'] is False and tape['terminal']['infrastructure_failure']
        assert tape['terminal']['reason'] == 'native_execution_failure'
        assert step['step'] == tape['steps'][-1]['step']
        raw = re.findall(r'<action>(.*?)</action>',reply['reply_text'],re.S)
        assert len(raw) == 1 and json.loads(raw[0]) == receipt['payload']
    if receipt['ok'] is False:
        return 'native_environment_returned_failure'
    return {'proposed_native_action_error':'reviewed_wrong_action_returned_ok',
            'proposed_native_action_unresolved':'native_action_ok_validity_unresolved',
            'no_definite_native_action_error':'native_action_ok_no_definite_action_error'}[item['native_proposal']]


def audit(ledger_path, report_path, private, reviewed):
    ledger, labels, report = source(ledger_path,report_path)
    verify(private)
    m = read(private/'mapping.json')
    assert m['ledger_seal']==sha(ledger_path/'seal.json') and m['report_seal']==sha(report_path/'seal.json')
    public = Path(m['packet'])
    packet,notes = review_pack(public,reviewed)
    assert sha(public/'seal.json') == m['packet_seal'] == notes['packet_seal']
    assert not notes['joined_private_execution']
    cases, messages, refs, images = material(ledger,labels)
    assert cases==packet['cases'] and messages==packet['legal_messages'] and refs==m['sources']
    assert sorted(images)==packet['original_png_sha256']
    assert all(sha(public/'images'/(digest+'.png'))==digest for digest in images)
    assert notes['cases'].keys() == cases.keys()
    inventory = {r['slot']['run_id']:r for r in ledger['rows'] if r['evidence']}
    result = []
    for key, items in notes['cases'].items():
        validate_notes(cases[key],items)
        for ref in refs[key]:
            r = inventory[ref['run']]
            slot, tape = r['slot'], r['evidence']
            assert tape['terminal_sha256']==ref['terminal_sha256']
            steps = {s['step']:s for s in tape['steps']}
            for item in items:
                d = item['decision']
                step = steps[d]
                reply = step['main']
                dd = [steps[j] for j in item['later_evidence_decisions']]
                receipt = step['executed']
                interpretation = execution_binding(item,step,tape)
                result.append({'run_id':slot['run_id'],'task_id':slot['task_id'],'version':r['version'],
                    'condition':slot['condition'],'arm':slot['arm'],'stage':r['stage_id'],
                    'terminal_sha256':tape['terminal_sha256'],'native_official_score':tape['terminal']['official_reward']
                    if tape['official_score_bound'] else None, 'opaque_case':key,'review':item,
                    'actual_first_forward':{'request_id':step['request']['request_id'],'wire_sha256':reply['wire_sha256'],
                        'current_original_sha256':reply['current_image_sha256'],'raw_reply_sha256':reply['reply_sha256']},
                    'native_proposal_receipt':step['proposal'],
                    'native_action_receipt':receipt,'native_execution_interpretation':interpretation,
                    'later_delivered_evidence':[{'decision':s['step'],'request_id':s['request']['request_id'],
                        'raw_reply_sha256':s['main']['reply_sha256'],'original_sha256':s['main']['current_image_sha256']}
                        for s in dd]})
    expected = {(run,j) for (run,j),v in labels.items() if v['semantic_label']=='definite'}
    assert len(result)==len(expected) and {(x['run_id'],x['review']['decision']) for x in result}==expected
    groups = defaultdict(list)
    for record in result:
        groups[(record['version'], record['condition'], record['arm'])].append(record)

    def totals(records):
        return {'trajectories':len({t['run_id'] for t in records}),'definite_replies':len(records),
                'native_proposal_review':dict(Counter(r['review']['native_proposal'] for r in records)),
                'native_execution':dict(Counter(r['native_execution_interpretation'] for r in records)),
                'later_revision':dict(Counter(r['review']['later_revision'] for r in records))}
    out = {'reviewed_slots':report['overall_counts_only_no_pooled_effect_estimate']['sealed_terminals'],
           'ledger_seal':m['ledger_seal'],'report_seal':m['report_seal'],'packet_seal':m['packet_seal'],
           'judgments_seal':sha(reviewed/'seal.json'),'all_confirmed_definite':totals(result),
           'inputs':{k:{'path':str(p.resolve()),'seal_sha256':sha(p/'seal.json')}
                     for k,p in (('packet',public),('private',private),('judgments',reviewed))},
           'exact_reused_groups':len((notes.get('exact_prior') or {}).get('case_keys',[])),
           'by_version_condition_arm':[dict(zip(('version','condition','arm'),k),**totals(v)) for k,v in groups.items()],
           'cases':result,
           'scope':'Follow-up of confirmed original claims only. Native dispatch does not imply a bad action or successful '
                   'outcome. A later correction needs the same claim and legal evidence; it never subtracts a Mirage.',
           'original_reviews_or_conditions_changed':False,'new_model_GUI_scorer_calls':0}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='verb',required=True)
    a = sub.add_parser('export')
    a.add_argument('ledger',type=Path)
    a.add_argument('report',type=Path)
    a = sub.add_parser('seal-notes')
    a.add_argument('packet',type=Path)
    a.add_argument('notes',type=Path)
    a.add_argument('--reuse-exact',type=Path,nargs=2,metavar=('PRIOR_PACKET','PRIOR_JUDGMENTS'))
    a = sub.add_parser('reuse-plan')
    a.add_argument('packet',type=Path)
    a.add_argument('prior_packet',type=Path)
    a.add_argument('prior_judgments',type=Path)
    a = sub.add_parser('audit')
    for k in ('ledger','report','private','judgments'):
        a.add_argument(k,type=Path)
    a = parser.parse_args()
    if a.verb == 'export':
        out = export(a.ledger,a.report)
    elif a.verb == 'seal-notes':
        out = seal_notes(a.packet,a.notes,a.reuse_exact)
    elif a.verb == 'reuse-plan':
        verify(a.packet)
        packet = read(a.packet/'cases.json')
        _,reused = prior_cases(packet,(a.prior_packet,a.prior_judgments))
        out = {'exact_groups':sorted(reused), 'groups_for_manual_review':sorted(packet['cases'].keys() - reused.keys())}
    else:
        result = audit(a.ledger,a.report,a.private,a.judgments)
        dst = HERE/'mirage-followup-audits'/str(time.time_ns())
        dst.mkdir(parents=True,exist_ok=False)
        save(dst/'index.json',result)
        save(dst/'seal.json',{'index.json':sha(dst/'index.json')})
        out = {'audit':str(dst),'seal_sha256':sha(dst/'seal.json'),**result['all_confirmed_definite']}
    print(json.dumps(out,ensure_ascii=False))


if __name__ == '__main__':
    main()
