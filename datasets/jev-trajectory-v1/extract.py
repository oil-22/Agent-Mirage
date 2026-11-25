"""Extract the existing signed screenshots and executed actions. No browser/model calls."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from PIL import Image


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
R = ROOT / 'reports'
GUI = R / 'jev-gui-paired-20261122/evaluation'
sys.path.insert(0, str(R / 'jev-temporal-gate-20261122'))
from temporal_request import action_json

def check(ok, why):
    if not ok:
        raise ValueError(str(why))

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'), sort_keys=True, allow_nan=False).encode()

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def sha(p):
    return digest(p.read_bytes())

def rel(p):
    return p.resolve().relative_to(ROOT).as_posix()

def load(p):
    return json.loads(p.read_bytes())

def dump(name, obj):
    (HERE / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')

def lines(name, obj):
    with (HERE / name).open('w', encoding='utf-8', newline='\n') as f:
        for item in obj:
            f.write(json.dumps(item, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n')

def archive(p, expected=None):
    h = sha(p)
    check(expected is None or h == expected, ('source seal mismatch', p))
    inputs[rel(p)] = h
    return load(p)

def image(p, h):
    check(p.is_file() and sha(p) == h, ('original PNG not bound', p, h))
    dest = HERE / 'images' / (h+'.png')
    if h not in pngs:
        with Image.open(p) as im:
            check(im.format == 'PNG' and im.size == (1280, 720) and im.n_frames == 1, p)
            im.verify()
        if not dest.exists():
            dest.write_bytes(p.read_bytes())
        check(sha(dest) == h, ('copied PNG', h))
        pngs.add(h)

def store(row):
    action_json(row['action'])
    row['pair_id'] = digest(canonical([row['before_sha256'],row['action'],row['candidate_sha256']]))
    obs.append(row)

def controlled(name, directory):
    base = R / directory
    if name == 'scale':
        curr = archive(base / 'completion-receipt.json')
        mapping = curr['files_sha256']
        fname = '逐条独立审计.json'
    else:
        curr = archive(base / 'current.json')
        mapping = curr['sha256']
        fname = 'run-audit.json'
        vb = archive(base/'visual-review/bound-review.json',mapping['visual-review/bound-review.json'])
        reading = 'independent-visual-observations.json' if name == 'guard' else 'visual-readings.json'
        archive(base/'visual-review'/reading, vb['observations_sha256'])
    audit = archive(base/fname, mapping[fname])
    attempt = base/'attempts'/Path(audit['attempt']).name
    sealpath = attempt/'local-seal.json'
    local_seal = archive(sealpath, mapping[sealpath.relative_to(base).as_posix()])
    def sealed(p):
        check(sha(p) == local_seal[p.relative_to(attempt).as_posix()], p)
        return load(p)
    for ep in audit['episodes']:
        case = ep['case']; run = ep['id']; src = attempt/'run/source'/run
        act = sealed(src/'action.json')
        check(act['dispatch_calls'] == act['action_sequence'] == 1 and act['native_action']==ep['action']['native_action'], run)
        ss = sealed(src/'session.json')
        pub = bytes.fromhex(ss['public_key']); verifier = Ed25519PublicKey.from_public_bytes(pub)
        frames = ep['truth_frames'] if name == 'scale' else ep['frames']
        pre, = [f for f in frames if f['action_sequence']==0]
        check(pre['truth']=='initial' and pre['receipt']==pre['presence']=='YES', run)
        for f in frames:
            cap = src/('capture-%03d.json' % f['capture_index'])
            obj = sealed(cap); rec = obj['receipt']
            verifier.verify(bytes.fromhex(rec['signature']),canonical({k:v for k,v in rec.items() if k!='signature'}))
            check(rec['key_id']==digest(pub) and all(rec[k]==ss[k] for k in ('session_id','environment_id','source_code_sha256')), cap)
            check(all(rec[k]==f[k] for k in ('capture_id','action_sequence','capture_index')) and rec['image_sha256']==f['source_sha256'], cap)
            check(rec['challenge'] not in challenges, cap); challenges.add(rec['challenge'])
            if not f['action_sequence']:
                check(obj['capture_finished_ns'] < act['send_begin_ns'], cap)
                continue
            check(obj['capture_started_ns'] > act['send_end_ns'], cap)
            if f['presence']!='YES' or f['receipt']!='YES' or f['source_sha256']!=f['candidate_sha'] or f['transport_fault']:
                excluded.append(dict(suite=name,run=run,capture_id=f['capture_id'],reason='delivery_'+f['truth'])); continue
            preh, posth = pre['candidate_sha'],f['candidate_sha']
            for frame,h in [(pre,preh),(f,posth)]:
                local = src/'originals'/(h+'.png')
                check(sha(local)==local_seal[local.relative_to(attempt).as_posix()]==h,local)
                check(sha(Path(frame['candidate_png']))==h,frame['capture_id'])
                image(local,h)
            truth=f['truth']
            targets={'ready':('YES','settled'),'early':('NO','early'),'white':('NO','early'),
                     'buttons':('NO','early'),'target_unchanged':('NO','unrelated'),
                     'boundary':(None,'no_change'),'ambiguous':(None,'unknown')}
            label,phase=targets[truth]
            store(dict(suite=name,family=case['family'],run=run,task=case['group'],event=run+'/1',flow=case['flow'],
                       scenario=case['scenario'],arm=case['arm'],capture_id=f['capture_id'],before_capture_id=pre['capture_id'],
                       before_sha256=preh,candidate_sha256=posth,action=act['native_action'],label=label,phase=phase,
                       truth=truth,original_phase=f['phase_after_the_fact'],visual_override=f.get('visual_label_override_reason'),
                       source_audit=rel(base/fname),source_before=rel(src/('capture-%03d.json'%pre['capture_index'])),
                       source_after=rel(cap),source_action=rel(src/'action.json'),session=ss['session_id']))
    scope[name] = {'audited_trajectories':len(audit['episodes']), 'attempt':rel(attempt)}

def gui():
    lp=GUI/'ledgers/1795515204676783100/private-linked.json'
    np=GUI/'native-execution-audits/1795517466893232100/index.json'
    ls=archive(lp.parent/'seal.json'); ns=archive(np.parent/'seal.json')
    tape=archive(lp,ls[lp.name]); native=archive(np,ns[np.name])
    check(native['ledger_seal_sha256']==sha(lp.parent/'seal.json'),'ledger version mismatch')
    n=0
    for ent in tape['rows']:
        ev=ent['evidence']
        if ev is None: continue
        n+=1; slot=ent['slot']; run=slot['run_id']
        tn=native['result']['stages'][ent['stage_id']][run]
        check((tn['terminal_sha256'],tn['controller_head'],tn['trusted_source_head'])==
              (ev['terminal_sha256'],ev['controller_head'],ev['source_head']),run)
        tx={r['decision']:r for r in tn['actions_in_browser_order']}
        for step,nxt in zip(ev['steps'],ev['steps'][1:]):
            def skip(reason,cap=None):
                excluded.append(dict(suite='gui',run=run,decision=step['step'],capture_id=cap,reason=reason))
            exe=step['executed']; b=tx.get(step['step']); sub=step['submit']
            if not exe or not exe['ok'] or not sub or not b or b['binding']!='native_parameter_bound' or not b['browser_returned_ok']:
                skip('no_confirmed_parameter_bound_action'); continue
            if exe['payload']['type']=='wait':
                skip('native_wait_no_specific_visible_outcome'); continue
            check(step['step']+1==nxt['step'] and b['controller_native_payload_sha256']==digest(canonical(exe['payload'])),run)
            try: action_json(exe['payload'])
            except ValueError: skip('unsupported_native_action'); continue
            before,=[f for f in step['frames'] if f['capture_id']==sub['capture_id']]
            preh=before['captured_sha256']
            if before['injected'] or before['delivered_sha256']!=preh or sub['image_sha256']!=preh or not step['actual_first_forward'] or step['main']['current_image_sha256']!=preh:
                skip('prior_observation_not_untouched_and_forwarded'); continue
            for f in nxt['frames']:
                if f['injected'] or not f['delivered_sha256'] or f['delivered_sha256']!=f['captured_sha256']:
                    skip('altered_or_missing_delivery',f['capture_id']);continue
                posth=f['captured_sha256']
                check(before['session_id']==f['session_id'] and before['environment_id']==f['environment_id'] and
                      f['action_sequence']==b['source_sequence']==before['action_sequence']+1 and
                      before['acquired_at_ns']<f['acquired_at_ns'] and before['capture_index']<f['capture_index'],run)
                if slot['gate_enabled']:
                    for s,frame in ((step,before),(nxt,f)):
                        check(any(g['event']=='capture_receipt_decision' and g.get('capture_id')==frame['capture_id']
                                  and g.get('decision')=='YES' for g in s['gates']),run)
                paths=[GUI/'original-images'/(h+'.png') for h in (preh,posth)]
                if not all(p.is_file() for p in paths): skip('original_png_not_in_local_archive',f['capture_id']);continue
                for p,h in zip(paths,[preh,posth]): image(p,h)
                store(dict(suite='gui',family='classifieds',run=run,task='T%03d'%slot['task_id'],event=run+'/'+str(step['step']),
                           flow=exe['payload']['type'],scenario=slot['condition'],arm=slot['arm'],capture_id=f['capture_id'],
                           before_capture_id=before['capture_id'],before_sha256=preh,candidate_sha256=posth,action=exe['payload'],
                           label=None,phase='unknown',truth='unreviewed_temporal',source_audit=rel(lp),
                           source_action=rel(np),native_trace_call=b['call_id'],source_sequence=b['source_sequence'],
                           controller_decision=step['step'],terminal_sha256=ev['terminal_sha256'],session=f['session_id']))
    scope['gui']={'sealed_trajectories':n,'planned_slots':len(tape['rows']),'archive':rel(lp)}

if __name__=='__main__':
    inputs={};obs=[];excluded=[];pngs=set();challenges=set();scope={}
    (HERE/'images').mkdir(exist_ok=True)
    for name,d in [('scale','jev-defense-scale-20261122'),('guard','jev-toggle-guard-20261122'),('outcome','jev-toggle-outcome-20261122')]:
        controlled(name,d)
    gui()
    lines('observations.jsonl',obs);lines('exclusions.jsonl',excluded)
    dump('source-index.json',dict(scope=scope,source_sha256=inputs,controlled_signed_captures_reverified=len(challenges),
                                 unique_pngs=len(pngs),eligible_occurrences=dict(Counter(o['suite'] for o in obs)),
                                 distinct_pairs={k:len({r['pair_id'] for r in obs if r['suite']==k}) for k in scope}))
    print((HERE/'source-index.json').read_text(encoding='utf-8')[-440:])
