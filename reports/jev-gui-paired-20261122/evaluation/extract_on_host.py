"""Read-only evidence extraction; the caller supplies sealed package and role."""
import base64
import hashlib
import json
import struct
from collections import defaultdict
from functools import lru_cache
from pathlib import Path


def read(p):
    return json.loads(p.read_bytes())


def hx(raw):
    return hashlib.sha256(raw).hexdigest()


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def journal(path, *, live=False, source=False):
    raw = path.read_bytes()
    lines = raw.split(b'\n')
    assert live or not lines[-1], path
    result, head = [], '0'*64
    capture_index = 0
    for i, line in enumerate(lines[:-1]):
        value = json.loads(line)
        digest = value.pop('sha256')
        if source:
            capture_index += int(value['kind'] == 'actual_native_capture_signed')
            assert value['index'] == capture_index, (path, i)
        else:
            assert value['seq'] == i, (path, i)
        assert value['previous'] == head and hx(canonical(value)) == digest, (path, i)
        result.append({**value,'sha256':digest})
        head = digest
    return result, head


def sealed(root, seal, name):
    assert sha(root/name) == seal[name], (root, name)
    return root/name


def unique(items, key, value=lambda x:x):
    out = {}
    for item in items:
        k = key(item)
        assert k not in out, ('duplicate',k)
        out[k] = value(item)
    return out


def data(records, kind):
    return [r['data'] for r in records if r['kind']==kind]


def gui_extract(p, plan):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    out, unsealed, reused = {}, [], []
    runs = p/'batch/runs'
    allowed = {r['run_id']: r for r in plan['queue'] if r['run_id'] in OWNED_RUNS}
    if runs.exists():
        assert all(d.name in allowed for d in runs.iterdir() if d.is_dir())
    for run, slot in allowed.items():
        attempts = sorted((runs/run).glob('attempt-*'))
        assert len(attempts) <= 1, run
        if not attempts:
            continue
        attempt, = attempts
        if not (attempt/'seal.json').exists():
            unsealed.append(run)
            continue
        seal = read(attempt/'seal.json')
        t = read(sealed(attempt,seal,'terminal.json'))
        assert t['run'] == slot
        if run in KNOWN_TERMINALS:
            assert KNOWN_TERMINALS[run]==seal['terminal.json'], run
            reused.append(run)
            continue
        ctl, head = journal(sealed(attempt,seal,'controller/events.jsonl'))
        src, s_head = (journal(sealed(attempt,seal,'trusted-source/events.jsonl'),source=True)
                       if 'trusted-source/events.jsonl' in seal else ([],None))
        binding = source_seal = verify = None
        if 'trusted-source/ready.json' in seal:
            binding = read(sealed(attempt,seal,'trusted-source/ready.json'))
            public = bytes.fromhex(binding['public_key'])
            assert (not binding['fixture'] and binding['key_id'] == hx(public) and
                    binding['identity']['uid'] == 1015 and
                    binding['source_code_sha256'] == sha(p/'capture_source.py')), run
            verify = Ed25519PublicKey.from_public_bytes(public).verify
        if 'trusted-source/seal.json' in seal:
            source_root=attempt/'trusted-source'
            source_seal=read(sealed(attempt,seal,'trusted-source/seal.json'))
            source_end=read(sealed(source_root,source_seal,'terminal.json'))
            assert source_end['journal_head'] == (s_head or '0'*64), run
            assert not source_end['private_key_exported'], run
        official = data(src,'native_official_score')
        scored = t.get('scoring_status')=='complete'
        assert len(official) == int(scored), run
        assert not scored or official[0]['score'] == t['official_reward'], run
        signed = unique(data(src,'actual_native_capture_signed'),lambda x:x['receipt']['capture_id'])
        faults = unique(data(src,'PRIVATE_unsigned_native_fault_rendered'),lambda x:x['preceding_capture_id'])
        frames = defaultdict(list)
        for row in data(ctl,'PRIVATE_capture_injection'):
            prefix = 'capture-deliveries/'+f"{row['capture_index']:04d}"
            receipt = read(sealed(attempt,seal,prefix+'-signed-receipt.json'))
            challenge = read(sealed(attempt,seal,prefix+'-expected-challenge.json'))
            trusted = signed[row['capture_id']]
            assert receipt == trusted['receipt']
            sig_body={k:v for k,v in receipt.items() if k!='signature'}
            verify(bytes.fromhex(receipt['signature']),canonical(sig_body))
            assert all(receipt[k]==binding[k] for k in ('session_id','environment_id','protocol','key_id','source_code_sha256'))
            assert all(receipt[k]==challenge[k] for k in ('challenge','environment_id','action_sequence'))
            assert receipt['capture_index']==row['capture_index']
            assert receipt['image_sha256']==seal[row['raw_file']]==row['captured_sha256']
            assert sha(attempt/row['raw_file'])==row['captured_sha256']
            name='capture-'+row['capture_id']+'/original.png'
            trusted_image=attempt/'trusted-source'/name
            assert trusted_image==Path(trusted['original_file'])
            assert seal['trusted-source/'+name]==sha(trusted_image)==receipt['image_sha256']
            assert not source_seal or source_seal[name]==receipt['image_sha256']
            if row['delivered_file'] is None:
                assert row['delivered_sha256'] is None
            else:
                assert row['delivered_sha256']==seal[row['delivered_file']]==sha(attempt/row['delivered_file'])
            assert row['condition']==slot['condition']
            fault = faults.get(row['capture_id'])
            if row['injected'] and row['condition'] in ('blank_replace','buttons_only'):
                assert fault and fault['name']==row['condition'] and fault['signature_issued'] is False
                assert fault['preceding_signed_image_sha256']==row['captured_sha256']
                assert fault['delivered_sha256']==row['delivered_sha256']
                assert fault['action_sequence']==receipt['action_sequence']
            elif not row['injected']:
                assert row['captured_sha256']==row['delivered_sha256']
            frames[row['step']].append({**row,'session_id':receipt['session_id'], 'environment_id':receipt['environment_id'],
                'action_sequence':receipt['action_sequence'], 'challenge':receipt['challenge'], 'acquired_at_ns':receipt['acquired_at_ns']})
        injected = [v for group in frames.values() for v in group if v['injected']]
        assert len(injected) <= 1 and all(v['capture_kind']=='initial' for v in injected)
        if 'injection_fired' in t:
            assert t['injection_fired'] == bool(injected)
            assert t.get('trigger_step') == (injected[0]['step'] if injected else None)
        begins = unique(data(ctl,'observation_started_timing'),lambda r:r['step'])
        finishes = unique(data(ctl,'observation_finished_timing'),lambda r:r['step'])
        submits = unique(data(ctl,'actor_submit_timing'),lambda r:r['step'])
        actions = unique(data(ctl,'native_environment_action'),lambda r:r['step'])
        source_actions=data(src,'native_action_executed')
        assert [x['sequence'] for x in source_actions] == list(range(1,len(source_actions)+1)), run
        assert len(actions) <= len(source_actions) <= len(actions) + int(bool(t.get('infrastructure_failure'))), run
        for row, original in zip(actions.values(),source_actions):
            assert row['ok']==original['ok'], run
        proposals = unique(data(ctl,'native_proposal_dispatched'),lambda r:r['capture_id'])
        service_replies = unique(data(ctl,'actual_actor_reply'),lambda r:r['request_id'])
        requests = {}
        step = None
        gates = defaultdict(list)
        for event in ctl:
            row = event['data']; kind = event['kind']
            if kind=='observation_started_timing': step=row['step']
            elif kind=='actual_actor_request':
                assert step in submits and step not in requests, (run,step)
                requests[step]=row
            elif kind in ('precheck_decision','capture_receipt_decision','gate_decision','recapture_requested',
                          'gate_terminal','no_gate_control','main_image_forwarded','checker_failure'):
                assert step in begins, (run,kind)
                if kind=='capture_receipt_decision':
                    row={k:v for k,v in row.items() if k not in ('receipt','expected')}
                gates[step].append({'event':kind,'event_sha256':event['sha256'],'journal_time':event['time'],**row})
        assert set(service_replies) <= {r['request_id'] for r in requests.values()}
        assert t.get('environment_actions',len(actions))==len(actions)
        rows=[]
        for step, start in sorted(begins.items()):
            req=requests.get(step); submit=submits.get(step); fin=finishes.get(step)
            assert type(step) is int and 1<=step<=50
            initial=[v for v in frames[step] if v['capture_kind']=='initial']
            if initial:
                assert len(initial)==1 and initial[0]['capture_id']==start['initial_capture_id']
            if submit:
                assert submit['submit_monotonic_ns']>=start['initial_ready_monotonic_ns']
            if fin:
                assert fin['ended_monotonic_ns']>=start['initial_ready_monotonic_ns']
            reply=service_replies.get(req['request_id']) if req else None
            rows.append({'step':step,'start':start,'submit':submit,'finish':fin,'frames':frames[step],
                         'request':req,'reply':reply,'gates':gates[step],
                         'executed':actions.get(step),'proposal':proposals.get(submit['capture_id']) if submit else None})
        out[run]={'terminal':{k:t.get(k) for k in ('run','outcome','scoring_status','official_reward','infrastructure_failure',
            'elapsed_monotonic_ns','injection_fired','trigger_step','recaptures','environment_actions',
            'actor_calls','decisions','result_status','reason')},
            'attempt':str(attempt),'terminal_sha256':seal['terminal.json'],'controller_head':head,'source_head':s_head,
            'sealed_verified':True,'native_official_receipt_matches':scored,'rows':rows,
            'flash_replies':t.get('Flash_replies',[]),'actor_receipts':t.get('actor_receipts',[]),
            'end_notification_failed':bool(data(ctl,'end_notification_failure'))}
    assert set(reused)==set(KNOWN_TERMINALS)
    return {'runs':out,'live_unsealed':unsealed,'previously_audited_terminals_rechecked':reused}


def checked_tensor(q, seal, r, *, full_hash=False):
    f=q/r['file']
    if r.get('storage')=='exact-tensor-chunks-v1':
        spec=read(sealed(q,seal,r['file']))
        assert spec['format']=='exact-tensor-chunks-v1'
        assert spec['bytes']==r['bytes'] and spec['raw_sha256']==r['sha256']
        assert sum(n for _,n in spec['chunks'])==r['bytes']
        if full_hash:
            h=hashlib.sha256()
            for d,n in spec['chunks']:
                assert len(d)==64 and all(c in '0123456789abcdef' for c in d)
                raw=(q.parent.parent/'tensor-blobs'/d[:2]/d).read_bytes()
                assert len(raw)==n and hx(raw)==d
                h.update(raw)
            assert h.hexdigest()==r['sha256']
    else:
        assert f.stat().st_size==r['bytes'] and seal[r['file']]==r['sha256']
        if full_hash or r['bytes'] < 2*1024**2:
            sealed(q,seal,r['file'])


@lru_cache(maxsize=96)
def image_hash(url):
    prefix, encoded = url.split(',', 1)
    assert prefix == 'data:image/png;base64'
    raw = base64.b64decode(encoded, validate=True)
    assert raw.startswith(b'\x89PNG\r\n\x1a\n')
    return hx(raw)


def project_messages(messages, table):
    result = []
    for message in messages:
        assert set(message)=={'role','content'}
        content = message['content']
        if isinstance(content, list):
            blocks=[]
            for block in content:
                if block['type']=='image_url':
                    assert set(block)=={'type','image_url'} and set(block['image_url'])=={'url'}
                    blocks.append({'type':'image','sha256':image_hash(block['image_url']['url'])})
                else:
                    assert block['type']=='text' and set(block)=={'type','text'}
                    blocks.append(block)
            content=blocks
        else:
            assert isinstance(content,str)
        public={'role':message['role'],'content':content}
        digest=hx(canonical(public))
        table.setdefault(digest,public)
        result.append(digest)
    return result


def model_extract(p, output, plan):
    primary=output/'primary'
    allowed=set(OWNED_RUNS)
    events, head=journal(primary/'journal/events.jsonl',live=True)
    if OLD_PRIMARY_HEAD is not None:
        assert OLD_PRIMARY_HEAD in {'0'*64, *(e['sha256'] for e in events)}
    ends=unique(data(events,'run_end'),lambda r:r['run_id'])
    begins=unique(data(events,'run_begin'),lambda r:r['run_id'])
    seen_requests=unique(data(events,'actor_request'),lambda r:r['request_id'])
    replies=unique(data(events,'actor_reply_sealed'),lambda r:r['request_id'])
    flash_events=unique(data(events,'Flash_reply_forwarded'),lambda r:r['request_id'])
    assert set(ends)<=set(begins)<=allowed and replies.keys()<=seen_requests.keys()
    eligible=set(TARGET_RUNS) & set(begins)
    files={Path(r['folder'])/'seal.json' for r in replies.values() if r['run_id'] in eligible}
    files.update(f.parent/'seal.json' for f in (primary/'requests').glob('*/failure.json')
                 if (f.parent/'seal.json').exists())
    model={}; public_messages={}
    template=read(p/'actor-template.json')
    for seal_path in sorted(files):
        q=seal_path.parent
        seal=read(seal_path)
        wire=sealed(q,seal,'wire-request.bin').read_bytes()
        request=json.loads(wire); run=request['run_id']; rid=request['request_id']; n=request['decision_index']
        if run not in eligible:
            continue  # do not repeatedly hash the active arm on every evaluation pass
        assert run in begins and rid not in model
        body=request['body']
        assert body==read(sealed(q,seal,'body.json'))
        current=[v['image_url']['url'] for v in body['messages'][-1]['content'] if v['type']=='image_url']
        assert len(current)<=1
        current_hash=image_hash(current[0]) if current else None
        messages=project_messages(body['messages'],public_messages)
        assert body['messages'][0]==template['messages'][0]
        assert {k:v for k,v in body.items() if k!='messages'}=={k:v for k,v in template.items() if k!='messages'}
        actual_forward='first-forward.json' in seal
        forward_count=None; response_sha=None; reply_text=None; eos=None; image_count=None; exact_bytes=False
        input_tokens=output_tokens=fail_sha=None
        if actual_forward:
            first=read(sealed(q,seal,'first-forward.json')); prep=read(sealed(q,seal,'prepared.json'))
            assert first.keys()==prep.keys() and 'input_ids' in first
            for kind in first:
                a,b=first[kind],prep[kind]
                assert all(a[k]==b[k] for k in ('shape','dtype','bytes','sha256'))
                checked_tensor(q,seal,a,full_hash=n<=2); checked_tensor(q,seal,b,full_hash=False)
            exact_bytes=n<=2
            image_count=first['image_grid_thw']['shape'][0] if 'image_grid_thw' in first else 0
            body_images=sum(sum(v['type']=='image_url' for v in m['content']) for m in body['messages'] if isinstance(m['content'],list))
            assert image_count==body_images
        if 'response.json' in seal:
            assert actual_forward
            r=read(sealed(q,seal,'response.json')); g=read(sealed(q,seal,'actual-generation.json'))
            native=read(sealed(q,seal,'native-call.json')); cfg=read(sealed(q,seal,'effective-generation.json'))
            assert rid==r['request_id'] and r['request_sha256']==seal['wire-request.bin']
            eos_ids=cfg['eos_token_id']
            assert g['natural_EOS'] and g['actual_forward_calls']>=1 and cfg['max_new_tokens']==2048
            assert g['output_ids'] and g['output_ids'][-1] in ([eos_ids] if isinstance(eos_ids,int) else eos_ids)
            assert r['text']==native['text'] and g['output_ids']==native['generated_ids']
            ids=native['input_ids']
            assert len(ids)==g['input_tokens'] and first['input_ids']['shape']==[1,len(ids)]
            assert len(g['output_ids'])==g['output_tokens']<=2048
            assert hx(struct.pack('<'+'q'*len(ids),*ids))==first['input_ids']['sha256']
            assert replies[rid]['seal_sha256']==sha(seal_path)
            assert seen_requests[rid]['wire_sha256']==seal['wire-request.bin']
            reply_text=r['text']; response_sha=hx(reply_text.encode()); eos=True; forward_count=g['actual_forward_calls']
            input_tokens=g['input_tokens'];output_tokens=g['output_tokens']
        else:
            sealed(q,seal,'failure.json')
            fail_sha=seal['failure.json']
            if 'forward-count.json' in seal:
                forward_count=read(sealed(q,seal,'forward-count.json'))['actual_forward_calls']
        model[rid]={'run':run,'step':n,'actual_forward':actual_forward,'body_sha256':hx(canonical(body)),
            'current_image_sha256':current_hash,'reply_sha256':response_sha,'forward_calls':forward_count,
            'natural_EOS':eos,'images_all_history':image_count,'tensor_raw_bytes_fully_audited':exact_bytes,
            'messages_ordered':messages,'reply_text':reply_text,'failure_sha256':fail_sha,
            'input_tokens':input_tokens,'output_tokens':output_tokens,'wire_sha256':seal['wire-request.bin'],
            'runtime_request_directory':str(q),'seal_sha256':sha(seal_path)}
    flash={}
    flash_root=p/'flash/service'
    flash_records, flash_head=journal(flash_root/'journal/events.jsonl',live=True)
    if OLD_FLASH_HEAD is not None:
        assert OLD_FLASH_HEAD in {'0'*64, *(e['sha256'] for e in flash_records)}
    flash_received=unique(data(flash_records,'request_received'),lambda x:x['request_id'])
    flash_sealed=unique(data(flash_records,'request_sealed'),lambda x:x['request_id'])
    contract=read(p/'flash/gate-contract.json')
    flash_load=read(flash_root/'loaded.json')
    assert flash_load['revision']==contract['revision'] and flash_load['dtype']=='bfloat16'
    assert flash_load['single_image'] and flash_load['no_cross_request_KV']
    primary_load=read(primary/'loaded.json')
    registered,=data(events,'loaded')
    assert registered['loaded_sha256']==sha(primary/'loaded.json')
    flash_registered,=data(flash_records,'loaded')
    assert flash_registered['loaded_sha256']==sha(flash_root/'loaded.json')
    manifest=read(p/'manifest.json')
    precision=manifest.get('pair_precision')
    assert precision in (None,'27B NF4 double quantization, BF16 compute'), precision
    is_nf4=precision=='27B NF4 double quantization, BF16 compute'
    expected_dtype='NF4 weights; BF16 compute' if is_nf4 else 'bfloat16'
    assert primary_load['dtype']==expected_dtype and primary_load['attention']=='sdpa'
    assert primary_load['native_generate_unchanged'] and not primary_load['main_history_truncation']
    assert not primary_load['image_preprocessing_changed']
    if is_nf4:
        qcfg=primary_load['quantization']
        assert qcfg['load_in_4bit'] and qcfg['bnb_4bit_quant_type']=='nf4'
        assert qcfg['bnb_4bit_compute_dtype']=='bfloat16'
        assert primary_load['native_state']['quantized_language_linear_modules']==496
        if 'nf4-resume-link.json' in manifest['files']:
            assert sha(p/'nf4-resume-link.json')==manifest['files']['nf4-resume-link.json']
            readmitted,=data(events,'NF4_capacity_evidence_readmitted')
            assert readmitted['new_generation_calls']==0
            cap=primary/'capacity';seal=read(cap/'seal.json')
            assert sha(cap/'seal.json')==readmitted['seal_sha256']
            qualification=read(sealed(cap,seal,'qualification.json'))
            assert qualification['passed'] and qualification['new_engineering_generation_calls']==0
    for rid, event in flash_events.items():
        if event['run_id'] not in eligible:
            continue
        q=flash_root/'requests'/rid;seal=read(q/'seal.json')
        v=read(sealed(q,seal,'response.json')); raw=sealed(q,seal,'original.png')
        audit=read(sealed(q,seal,'audit.json')); trace=read(sealed(q,seal,'forward-trace.json'))
        assert rid==v['request_id'] and v['image_sha256']==event['image_sha256']==sha(raw)
        wire=read(sealed(q,seal,'wire-request.bin'))
        assert set(wire)=={'request_id','image_png_base64','image_sha256'}
        assert rid==wire['request_id'] and hx(base64.b64decode(wire['image_png_base64'],validate=True))==v['image_sha256']
        assert wire['image_sha256']==v['image_sha256']==flash_received[rid]['image_sha256']
        assert v['request_sha256']==seal['wire-request.bin']==flash_received[rid]['request_sha256']
        assert v['decision']==event['decision']
        assert flash_sealed[rid]['complete'] and flash_sealed[rid]['native_call_attempted']
        assert flash_sealed[rid]['seal_sha256']==sha(q/'seal.json')
        assert len(trace)==1 and not trace[0]['use_cache'] and trace[0]['past_key_values'] is None
        f,=trace
        assert {'input_ids','pixel_values','image_grid_thw'}<=f.keys()
        assert f['image_grid_thw']['shape'][0]==1 and f['input_ids']['shape'][0]==1
        assert f['image_grid_thw']['values']==audit['image_grid_thw']
        flash_ids=f['input_ids']['values'][0]
        assert hx(struct.pack('<'+'q'*len(flash_ids),*flash_ids))==f['input_ids']['sha256']
        assert len(flash_ids)==audit['input_tokens']
        native=read(sealed(q,seal,'native-request.json'))
        assert set(native)=={'state','images','questions'} and native['state']==contract['state']
        assert len(native['images'])==1 and native['images'][0]['sha256']==v['image_sha256']
        assert native['questions']=={'usable':{'type':'choice','instructions':contract['question'],'criteria':contract['options']}}
        raw_readout=read(sealed(q,seal,'raw-readout.json'))
        assert len(raw_readout)==1
        prob=audit['probabilities']
        assert set(prob)=={'YES','NO'} and v['decision']==max(prob,key=prob.__getitem__)
        assert v['revision']==contract['revision'] and v['contract_sha256']==sha(p/'flash/gate-contract.json')
        flash[rid]={'run':event['run_id'],'decision':v['decision'],'image_sha256':v['image_sha256'],
                    'probabilities':prob,'seal_sha256':sha(q/'seal.json'),'input_tokens':len(flash_ids),
                    'pixel_values_sha256':f['pixel_values']['sha256'],'memory':audit['memory']}
    return {'run_begin':list(begins),'run_end':ends,'requests':model,'flash':flash,'primary_chain_head':head,
            'flash_chain_head':flash_head,'public_legal_messages':public_messages,
            'actual_loaded_models':{'primary_dtype':primary_load['dtype'],'primary_loaded_sha256':registered['loaded_sha256'],
                'Flash_revision':flash_load['revision'],'Flash_loaded_sha256':flash_registered['loaded_sha256']}}


if __name__ == '__main__':
    package=Path(ROOT)
    assert sha(package/'manifest.json') == EXPECTED
    m=read(package/'manifest.json')
    assert sha(package/'plan.json')==m['plan_sha256']
    plan=read(package/'plan.json')
    result=gui_extract(package,plan) if HOST=='4090' else model_extract(package,Path(OUTPUT),plan)
    print(json.dumps(result,ensure_ascii=False))
