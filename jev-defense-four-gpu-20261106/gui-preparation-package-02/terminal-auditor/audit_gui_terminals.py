"""Read-only structural/source audit. Detector outputs are never semantic labels.

No inference, browser, scorer, pickle loading, process control or terminal mutation.
The caller supplies original manifest hashes and explicit copies of service receipts.
"""
import argparse,base64,copy,hashlib,io,json,re,sys
from pathlib import Path
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from image_observer import (POLICY,MODEL,REVISION,STATE,QUESTIONS,contract,wire,
                            SHARED_ACTOR_INSTRUCTIONS,valid_answer)


def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(obj):return json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()


class AuditError(ValueError):pass


def require(ok,message):
    if not ok:raise AuditError(message)


def read(path):return json.loads(Path(path).read_bytes())


def under(root,name):
    root=Path(root).resolve();path=(root/name).resolve()
    require(path.is_relative_to(root),'Manifest path escaped its bound root')
    return path


def manifest(root,path,expected_sha,exhaustive=True):
    """Verify an existing relative-name -> SHA map, never write/update a seal."""
    root=Path(root).resolve();path=Path(path).resolve()
    require(sha(path.read_bytes())==expected_sha,'Manifest identity mismatch: '+str(path))
    mapping=read(path);require(isinstance(mapping,dict)and bool(mapping),'Empty/non-flat manifest')
    for name,digest in mapping.items():
        require(isinstance(name,str)and isinstance(digest,str)and len(digest)==64,'Malformed manifest entry')
        target=under(root,name);require(target.is_file(),'Missing sealed file: '+name)
        require(sha(target.read_bytes())==digest,'Sealed file mismatch: '+name)
    if exhaustive:
        actual={str(p.relative_to(root)).replace('\\','/')for p in root.rglob('*')if p.is_file()and p.resolve()!=path}
        require(actual==set(mapping),'Manifest omits or invents terminal files')
    return mapping


def chain(path):
    rows=[];previous='0'*64
    for index,line in enumerate(Path(path).read_text(encoding='utf8').splitlines()):
        event=json.loads(line);digest=event.pop('sha256',None)
        require(event.get('seq')==index and event.get('previous')==previous,'Broken event sequence/previous SHA')
        require(digest==sha(canonical(event)),'Broken event body SHA')
        event['sha256']=digest;rows.append(event);previous=digest
    require(bool(rows),'Empty journal')
    return rows,previous


def image_raw(block):
    url=block['image_url'];url=url['url']if isinstance(url,dict)else url
    require(url.startswith('data:image/'),'Nonembedded model image')
    return base64.b64decode(url.split(',',1)[1],validate=True)


def public_images(public,attempt):
    for item in public['images']:
        p=Path(attempt)/(item['sha256']+'.image');raw=p.read_bytes()
        require(sha(raw)==item['sha256'],'Public image raw SHA mismatch')
        with Image.open(io.BytesIO(raw))as im:
            im.load();require(list(im.size)==item['size']and item['decoded']is True,'Public native image metadata mismatch')
        require(item['role']in {'current','reference'},'Unknown image role')
    declared={i['sha256']for i in public['images']}
    for message in public['messages']:
        if not isinstance(message['content'],list):continue
        for block in message['content']:
            if block.get('type')=='image_url':require(sha(image_raw(block))in declared,'Message image not in exact PublicView inventory')
            if message['role']=='user'and block.get('type')=='text':
                require(not block['text'].startswith(SHARED_ACTOR_INSTRUCTIONS),'Observer packet persisted into original public/judge input')


def public_from_judge(value):
    public=copy.deepcopy(value);images=[]
    for item in value['images']:
        raw=base64.b64decode(item['raw_base64'],validate=True)
        with Image.open(io.BytesIO(raw))as im:im.load();size=list(im.size)
        images.append({'sha256':sha(raw),'size':size,'role':item['role'],'decoded':True})
    public['images']=images
    return public


def generation_messages(payload):
    if payload['operation']=='actor':return payload['body']['messages']
    value=payload['view'];public=public_from_judge(value)
    for message in public['messages']:
        if not isinstance(message['content'],list):continue
        parts=[]
        for block in message['content']:
            if block['type']=='image_url':
                digest=sha(image_raw(block));matches=[i for i,im in enumerate(public['images'])if im['sha256']==digest]
                require(bool(matches),'Judge message image absent from native image inventory')
                parts.append({'type':'image_reference','image_index':matches[0]})
            else:parts.append(block)
        message['content']=parts
    blocks=[{'type':'text','text':json.dumps({'public':public,'candidate':payload.get('candidate')},ensure_ascii=False)}]
    for i,item in enumerate(value['images']):
        blocks.append({'type':'text','text':f'Image index {i}, role {item["role"]}, original pixels:'})
        blocks.append({'type':'image_url','image_url':{'url':'data:image/png;base64,'+item['raw_base64']}})
    return [{'role':'system','content':payload['system']},{'role':'user','content':blocks}]


def native_forward(request,payload,response,role):
    trace=read(request/'forward-trace.json')
    require(sha((request/'forward-trace.json').read_bytes())==response['forward_trace_sha256'],'Actual forward trace response binding mismatch')
    prefills=[r for r in trace if 'input_ids'in r.get('tensors',{})and len(r['tensors']['input_ids']['shape'])==2
              and r['tensors']['input_ids']['shape'][-1]>1]
    require(len(prefills)==1,'Expected one actual native input-ID prefill')
    tensor=prefills[0]['tensors'];ids=tensor['input_ids'].get('values')
    require(isinstance(ids,list)and len(ids)==1 and len(ids[0])==tensor['input_ids']['shape'][-1],'Actual forward input IDs absent/inconsistent')
    if role=='primary':
        gen=read(request/'generation.json');op=payload['operation'];cap={'actor':2048,'judge':4096}[op]
        require(gen['input_ids']==ids[0],'Generation vs actual forward input IDs mismatch')
        require(gen['request_messages_sha256']==sha(canonical(generation_messages(payload))),'Full native generation messages differ from actual payload')
        require(gen['generation_config']['max_new_tokens']==cap,'Original output budget changed')
        require(gen['hit_output_cap']is False and 0<len(gen['generated_ids'])<cap,'Incomplete/capped primary generation is not a completed model reply')
        eos=gen['generation_config']['eos_token_id'];eos=[eos]if type(eos)is int else eos
        require(gen['generated_ids'][-1]in eos,'Primary output does not end at actual configured EOS')
        require(gen['text']==response['text'if op=='actor'else'verdict'],'Server native generation/reply text mismatch')
        return {'input_tokens':len(ids[0]),'output_tokens':len(gen['generated_ids']),'natural_EOS':True}
    body=payload
    require(body['state']==STATE and body['questions']==QUESTIONS and list(body['questions'])==list(QUESTIONS),'Observer native constants/order changed')
    require(set(body)=={'request_id','image_base64','image_sha256','state','questions','provenance'},'Observer received task/history/candidate or unknown fields')
    require(set(body['provenance'])=={'observation_id','image_sha256'},'Observer provenance contains forbidden context')
    raw=base64.b64decode(body['image_base64'],validate=True)
    require(sha(raw)==body['image_sha256']==body['provenance']['image_sha256']==response['image_sha256'],'Observer received-image binding mismatch')
    require((request/'original.image').read_bytes()==raw,'Observer native original image bytes differ')
    require('pixel_values'in tensor and 'image_grid_thw'in tensor,'Observer actual pixels/grid absent from forward')
    readouts=[r['raw_readout']for r in trace if 'raw_readout'in r]
    require(len(readouts)==1 and readouts[0]['shape']==[3,255],'Observer expected three raw native marker readouts')
    require(response['model']==MODEL and response['revision']==REVISION and response['usage']['sequences']==1,'Observer model/native sequence identity changed')
    require(set(response['answers'])==set(QUESTIONS),'Observer answer identities differ')
    for key,q in QUESTIONS.items():
        require(list(body['questions'][key]['criteria'])==list(q['criteria']),'Observer native option order changed')
        require(valid_answer(response['answers'][key],q['criteria']),'Observer invalid native probability contract')
    require(response['generation_tokens']==0,'Observer decision model must not claim generation')
    native=read(request/'native-request.json')
    require(native=={'state':STATE,'questions':QUESTIONS,'images_sha256':[sha(raw)]},'Observer actual native call differs from screenshot-only constants')
    require(read(request/'native-result.json')['answers']==response['answers'],'Actual native answers differ from served predictions')
    return {'input_tokens':len(ids[0]),'native_marker_readouts':3,'generation_tokens':0}


def service_index(bindings):
    """Index explicit bound request directories, never trust remote receipt strings."""
    index={}
    for item in bindings:
        request=Path(item['path']);seal=request/'seal.json'
        manifest(request,seal,item['seal_sha256'],True)
        raw=(request/'request.json').read_bytes();external=sha(raw)
        require(external not in index,'Duplicate actual service external request wire')
        envelope=json.loads(raw)
        response=read(request/'response.json')if(request/'response.json').exists()else None
        if response is not None:
            require(response.get('external_wire_sha256')==external,'Service response external wire binding differs')
            if 'payload'in envelope:require(response['payload_sha256']==sha(canonical(envelope['payload'])),'Service native payload canonical binding differs')
        else:require((request/'failure.json').is_file(),'Service request has neither sealed reply nor failure')
        index[external]={'path':request,'raw':raw,'envelope':envelope,'response':response,'role':item['role'],'used':False}
    return index


def accepted_candidate_binding(candidate,proposal):
    blocks=re.findall(r'<action>\s*(.*?)\s*</action>',candidate,re.S)
    require(len(blocks)==1 and json.loads(blocks[0])==proposal['payload'],'Accepted native payload differs from original candidate action JSON')
    require(proposal['parsed']is True and proposal['executor_fallback_wait']is False and proposal['name']==proposal['payload']['type'],'Native parser binding differs')
    # Deliberately no semantic/prose direction classifier here. A structurally
    # bound wrong action still requires independent original-image/text review.


def service_chain(path):
    rows=[];previous=None
    for index,line in enumerate(Path(path).read_bytes().splitlines()):
        row=json.loads(line);body={k:v for k,v in row.items()if k!='sha256'}
        require(row['index']==index and row['previous_sha256']==previous,'Broken online service journal sequence/previous SHA')
        require(row['sha256']==sha(canonical(body)),'Broken online service journal body SHA')
        rows.append(row);previous=row['sha256']
    require(bool(rows),'Empty online service journal')
    return rows,previous


def join_service_journal(rows,index):
    by_name={r['path'].name:r for r in index.values()}
    require(len(by_name)==len(index),'Ambiguous mirrored native/lifecycle receipt names')
    started=set();finished=set();transitions=set()
    for row in rows:
        event,p=row['event'],row['payload']
        if event=='model_request_started':
            external=p['external_wire_sha256'];require(external in index,'Service journal starts an unbound actual request')
            require(external not in started,'Service journal repeats an actual model start');started.add(external)
            source=index[external];envelope=source['envelope']
            require('payload'in envelope and Path(p['receipt']).name==source['path'].name,'Service request-start receipt mismatch')
            require(p['trajectory_id']==envelope['trajectory_id']and p['request_id']==envelope['request_id']and
                p['decision_index']==envelope['decision_index']and p['attempt_index']==envelope['attempt_index']and
                p['payload_sha256']==sha(canonical(envelope['payload'])),'Service journal start fields differ from actual wire')
            if source['response']is not None:
                require(source['response']['request_started_journal_sha256']==row['sha256'],'Served response does not bind actual journal start')
        elif event in {'model_request_completed','model_request_failed'}:
            source=by_name.get(Path(p['receipt']).name);require(source is not None,'Service journal finishes unknown receipt')
            external=sha(source['raw']);require(external in started and external not in finished,'Service request finish absent, duplicate or before start')
            finished.add(external)
            require(p['request_seal_sha256']==sha((source['path']/'seal.json').read_bytes()),'Service journal request seal differs')
            if event=='model_request_completed':
                require(source['response']is not None and p['response_sha256']==sha((source['path']/'response.json').read_bytes()),'Service journal response file binding differs')
            else:require(source['response']is None and(source['path']/'failure.json').is_file(),'Service failure incorrectly treated as a completed reply')
        elif event=='trajectory_transition':
            external=p['external_wire_sha256'];require(external in index and external not in transitions,'Missing or duplicate service lifecycle receipt')
            source=index[external];require('payload'not in source['envelope']and source['response']==p,'Service lifecycle journal/reply differ')
            transitions.add(external)
        else:require(event=='worker_loaded','Unknown online service journal event')
    model={key for key,r in index.items()if 'payload'in r['envelope']}
    control=set(index)-model
    require(started==finished==model,'Not all actual native calls have unique started/terminal journal bindings')
    require(transitions==control,'Not all lifecycle calls have exact service journal bindings')
    return {'actual_model_starts':len(started),'actual_model_terminals':len(finished),'lifecycle_transitions':len(transitions)}


def audit_attempt(attempt,item,index):
    attempt=Path(attempt);events,head=chain(attempt/'events.jsonl')
    pending_actor=pending_verifier=native_actor=packet=None
    last_actor_response=last_verifier_response=None
    measured={};counts={'actor':0,'judge':0,'observer':0};accepted=[];executed=[];candidates=[]
    used=[];last_step=0;forward=[];active=False;began=ended=False
    pending_primary_service=pending_observer_service=None
    for event in events:
        kind,d=event['kind'],event['data']
        if kind in {'online_run_begin_request','online_run_end_request'}:
            raw=d['wire_utf8'].encode();external=sha(raw)
            require(external==d['wire_sha256']and json.loads(raw)==d['body'],'Lifecycle actual wire differs')
            require(external in index and not index[external]['used'],'Lifecycle service receipt missing or duplicated')
            server=index[external];server['used']=True;used.append(external)
            require(server['raw']==raw and server['envelope']['trajectory_id']==item['run_id'],'Lifecycle bound to wrong run')
            require(server['response']is not None,'Lifecycle request has no complete server reply')
            pending_primary_service=server
            if kind=='online_run_begin_request':
                require(not began and not active and not ended,'Duplicate/out-of-order trajectory begin')
                require(set(server['envelope'])=={'trajectory_id','request_id'},'Invalid begin request shape')
                began=active=True
            else:
                require(began and active and not ended,'Duplicate/out-of-order trajectory end')
                require(set(server['envelope'])=={'trajectory_id','request_id','status','terminal_receipt_sha256'},'Invalid end request shape')
                terminal=next((attempt/n for n in ['complete.json','technical-failure.json','failure.json','paused.json','cleanup-failure.json']if(attempt/n).exists()),None)
                require(terminal is not None and server['envelope']['terminal_receipt_sha256']==sha(terminal.read_bytes()),'Lifecycle end terminal SHA differs')
                active=False;ended=True
        elif kind.endswith('_raw_response')and kind.startswith(('actual_primary_wire','online_run_')):
            raw=base64.b64decode(d['raw_base64'],validate=True)
            require(sha(raw)==d['raw_sha256'],'Actual primary/control reply raw hash differs')
            require(pending_primary_service is not None,'Primary/control raw reply lacks actual request')
            expected=pending_primary_service['response']
            if expected is None:expected=read(pending_primary_service['path']/'failure.json')
            require(json.loads(raw)==expected,'Network primary/control raw reply differs from sealed service reply')
        elif kind in {'actual_observer_wire_reply','actual_observer_error_reply'}:
            raw=base64.b64decode(d['raw_base64'],validate=True)
            require(sha(raw)==d['raw_sha256'],'Actual observer reply raw hash differs')
            require(pending_observer_service is not None,'Observer raw reply lacks actual request')
            expected=pending_observer_service['response']
            if expected is None:expected=read(pending_observer_service['path']/'failure.json')
            require(json.loads(raw)==expected,'Network observer raw reply differs from sealed service reply')
        elif kind=='observation':public_images(d['public'],attempt)
        elif kind=='private_delivery_ledger':
            step=d['step'];require(1<=step<=50,'GUI decision cap exceeded')
            require(sha((attempt/'screenshots'/f'{step:03}-captured.png').read_bytes())==d['capture_sha256'],'Actual capture SHA differs')
            if d['delivered_sha256']is not None:require(sha((attempt/'screenshots'/f'{step:03}-delivered.png').read_bytes())==d['delivered_sha256'],'Delivered capture SHA differs')
        elif kind=='actor_request':pending_actor=d;public_images(d['public'],attempt)
        elif kind=='verifier_request':pending_verifier=d;public_images(d['public'],attempt)
        elif kind=='actor_observer_packet':packet=d
        elif kind=='actor_observer_native_payload':
            require(pending_actor is not None and packet is not None,'Observer native payload lacks original public/packet')
            native_actor=d['body'];require(sha(d['wire_utf8'].encode())==d['wire_sha256']and json.loads(d['wire_utf8'])==native_actor,'Actor native payload bytes/hash differ')
            require(sha(canonical(native_actor))==d['canonical_sha256'],'Actor native canonical payload differs')
            messages=copy.deepcopy(native_actor['body']['messages']);i=d['current_user_message_index']
            require(i==next((j for j in range(len(messages)-1,-1,-1)if messages[j]['role']=='user'and isinstance(messages[j]['content'],list)),None),'Packet attached to historical instead of latest multimodal message')
            block=messages[i]['content'].pop()
            require(block['type']=='text'and block['text'].startswith(SHARED_ACTOR_INSTRUCTIONS),'Actor shared boundary differs')
            require(json.loads(block['text'][len(SHARED_ACTOR_INSTRUCTIONS):])==packet,'Actual actor packet differs from logged source-bound packet')
            require(messages==pending_actor['public']['messages'],'Original full actor history/images/corrections changed')
            require(sha(canonical(pending_actor['public']))==d['original_public_sha256'],'Original actor public SHA binding differs')
            if not item['observer_enabled']:
                require(packet['status']=='observer_not_run'and not packet['observations']and 'image_sha256'not in packet,'Baseline obtained auxiliary image information')
            elif packet['observations']:
                current=[im for im in pending_actor['public']['images']if im['role']=='current']
                require(len(current)==1 and current[0]['sha256']==packet['image_sha256'],'Observer packet bound to wrong current image')
                require(packet['response_sha256']in measured,'Observer packet lacks measured exact-input source')
                source=measured[packet['response_sha256']]
                require(source['image_sha256']==packet['image_sha256'],'Cached packet carries prior different-frame predictions')
                require(packet['observations']==[{'question':key,'model_prediction':source['answers'][key]['choice'],
                    'probabilities':source['answers'][key]['probabilities']}for key in QUESTIONS],'Actor packet predictions differ from native source')
            else:require(packet['status']in {'unavailable','technical_failure','preserved_failure_no_retry','auxiliary_budget_exhausted'},'Unknown unavailable observer status')
        elif kind in {'actual_primary_wire_request','actual_observer_wire'}:
            require(active,'Inference occurred outside the once-only active trajectory')
            raw=d['wire_utf8'].encode();external=sha(raw)
            declared=d.get('wire_sha256',d.get('external_wire_sha256'))
            require(external==declared and json.loads(raw)==d['body'],'Actual external wire log/hash differs')
            require(external in index,'No exact actual service request matches journal wire')
            server=index[external];require(not server['used'],'Repeated actual inference request journal entry')
            server['used']=True;used.append(external);envelope=server['envelope']
            require(server['raw']==raw and set(envelope)=={'trajectory_id','decision_index','attempt_index','request_id','payload'},'Actual online envelope differs')
            require(envelope['trajectory_id']==item['run_id'],'Cross-trajectory actual service request')
            step=envelope['decision_index'];require(type(step)is int and last_step<=step<=50 and step>=1,'Invalid/nonmonotone decision index');last_step=step
            payload=envelope['payload'];role='observer'if kind=='actual_observer_wire'else payload['operation']
            if role=='observer':pending_observer_service=server
            else:pending_primary_service=server
            counts[role]+=1;require(envelope['attempt_index']==counts[role],'Actual role attempt counter is not once-only sequential')
            cap={'actor':70,'judge':140,'observer':60 if item['observer_enabled']else 0}[role]
            require(counts[role]<=cap,'Actual online role budget exceeded')
            response=server['response']
            if role=='actor':require(native_actor==payload,'Actual main actor payload differs from source-bound augmentation')
            elif role=='judge':
                require(pending_verifier is not None,'Actual judge lacks original verifier request')
                require(payload['system']==pending_verifier['system']and payload.get('candidate')==pending_verifier['candidate'],'Strict original verifier system/candidate modified')
                require(public_from_judge(payload['view'])==pending_verifier['public'],'Primary original full PublicView changed')
            else:
                require(item['observer_enabled'],'Baseline invoked observer')
                require(pending_actor is not None,'Observer not before a native actor proposal')
                current=[im for im in pending_actor['public']['images']if im['role']=='current']
                require(len(current)==1 and current[0]['sha256']==payload['image_sha256'],'Observer was not sent the actual received current screenshot')
                require(payload['provenance']['observation_id']==pending_actor['public']['observation_id'],'Observer provenance points to a different observation')
            if response is not None:
                require(response['request_id']==envelope['request_id'],'Actual response outer request ID differs')
                forward.append(native_forward(server['path'],payload,response,'pplx_flash'if role=='observer'else'primary'))
                if role=='actor':last_actor_response=response['text']
                elif role=='judge':last_verifier_response=response['verdict']
                else:measured[sha(canonical(response))]=response
        elif kind=='candidate':
            require(d['text']==last_actor_response,'Candidate is not the actual native actor reply');candidates.append(d)
            last_actor_response=None
        elif kind=='verifier_raw':
            require(d['response']==last_verifier_response,'Verifier raw reply differs from actual native reply');last_verifier_response=None
        elif kind=='decision_accepted':
            require(any(c['text']==d['candidate']and c['observation_id']==d['observation_id']for c in candidates),'Accepted candidate/source absent')
            accepted_candidate_binding(d['candidate'],d['proposal'])
            accepted.append(d)
        elif kind=='action_executed':
            matches=[a for a in accepted if a['observation_id']==d['observation_id']and a['proposal']==d['proposal']]
            require(len(matches)==1,'Execution lacks one exact accepted native proposal')
            key=(d['observation_id'],sha(canonical(d['proposal'])))
            require(key not in executed,'Accepted action executed more than once');executed.append(key)
            require(d['proposal']['payload']['type']!='stop','STOP incorrectly counted as environment action')
    require(began and ended and not active,'Attempt lacks complete once-only lifecycle seal')
    complete=attempt/'complete.json'
    result=read(complete)if complete.exists()else None
    if result is not None:
        require(result['actor_calls']==counts['actor']and result['verifier_calls']==counts['judge']and result['auxiliary_calls']==counts['observer'],'Terminal per-role call counts disagree')
        require(result['environment_actions']==len(executed),'Terminal actual action count disagrees with execution journal')
        require(result['semantic_mirage']is None and result.get('repair_success')is None,'Infrastructure terminal improperly contains semantic gold labels')
        require(result['run']==item and result['observer_enabled']==item['observer_enabled'],'Terminal run condition identity differs')
        require(result['decisions']<=50 and result['step_cap']==50,'Terminal step budget changed')
    return {'event_count':len(events),'event_chain_head':head,'counts':counts,
        'candidate_count':len(candidates),'accepted_count':len(accepted),'actual_execution_log_count':len(executed),
        'forward_audits':forward,'service_request_sha256':used,'complete':result is not None,
        'semantic_labels_inferred':False,'native_execution_binding':'exact candidate action JSON -> original parsed proposal -> execution-returned journal under SHA-bound unchanged native action source; native trace/pickle bytes bound by terminal manifest; pickle not executed'}


def audit(spec):
    base=Path(spec['batch_root']);plan_path=Path(spec['plan']['path'])
    require(sha(plan_path.read_bytes())==spec['plan']['sha256'],'Plan source identity differs')
    plan=read(plan_path);require(plan['policy']==POLICY and len(plan['queue'])==4,'Unbound GUI plan')
    admission_path=Path(spec['runtime_admission']['path'])
    require(sha(admission_path.read_bytes())==spec['runtime_admission']['sha256'],'Online admission identity differs')
    admission=read(admission_path)
    # Parent supplies this summary from the exact real runtime admission; preserve
    # its source hash so renamed or broadened queues cannot pass a boolean flag.
    require(admission['plan_sha256']==spec['plan']['sha256'],'Actual runtime admission bound to different plan')
    require(admission['run_order']==[q['run_id']for q in plan['queue']],'Runtime admitted unexpected trajectory order')
    caps=admission['per_run_caps']
    require(set(caps)=={q['run_id']for q in plan['queue']},'Runtime admitted additional/missing run IDs')
    for item in plan['queue']:
        require(caps[item['run_id']]=={'actor':70,'judge':140,'observer':60 if item['observer_enabled']else 0,'steps':50},'Runtime actual per-run role budget differs')
    src_path=Path(spec['policy_source_seal']['path'])
    require(sha(src_path.read_bytes())==spec['policy_source_seal']['sha256'],'Policy source seal identity differs')
    source=read(src_path);release=Path(spec['release_root'])
    for name,digest in source['release_sha256'].items():require(sha(under(release,name).read_bytes())==digest,'Actual active source changed: '+name)
    require(source['plan_sha256']==spec['plan']['sha256'],'Source seal plan binding differs')
    sealed=[]
    for item in spec['terminal_manifests']:
        mapping=manifest(item['root'],item['path'],item['sha256'],item.get('exhaustive',True))
        sealed.append({'root':item['root'],'files':len(mapping),'manifest_sha256':item['sha256']})
    index=service_index(spec['service_requests']);rows=[]
    for item in plan['queue']:
        run=base/'runs'/item['run_id'];attempts=sorted(run.glob('attempt-*'))
        require(len(attempts)<=1,'Unexpected repeated completed/failed trajectory attempts')
        if not attempts:
            rows.append({'run_id':item['run_id'],'complete':False,'status':'not_attempted'});continue
        attempt=attempts[0]
        require(any(Path(m['root']).resolve()==attempt.resolve()or attempt.resolve().is_relative_to(Path(m['root']).resolve())for m in spec['terminal_manifests']),'Attempt terminal files lack bound original manifest')
        row=audit_attempt(attempt,item,index);row.update(run_id=item['run_id'],attempt=str(attempt));rows.append(row)
        pointer=run/'complete.json'
        if row['complete']:
            obj=read(pointer);require(Path(obj['attempt']).name==attempt.name and obj['sha256']==sha((attempt/'complete.json').read_bytes()),'Run terminal pointer differs')
    require(all(row['used']for row in index.values()),'Unjoined actual service requests or unexpected auxiliary activity')
    journals=spec['service_journals'];require(len(journals)==1,'Bind the single new group online journal explicitly')
    service= journals[0];path=Path(service['path'])
    require(sha(path.read_bytes())==service['sha256'],'Service journal file SHA differs')
    global_rows,global_head=service_chain(path)
    global_join=join_service_journal(global_rows,index)
    return {'integrity_audit_passed':True,'all_four_trajectories_complete':len(rows)==4 and all(r['complete']for r in rows),
        'runs':rows,'sealed_roots':sealed,'service_request_count':len(index),
        'service_journal_event_count':len(global_rows),'service_journal_chain_head':global_head,
        'service_journal_actual_request_terminal_join':global_join,
        'semantic_labels_inferred':False,'official_success_recomputed':False,
        'Mirage_trigger_rate_or_defense_success_claim':False,
        'technical_failure_is_not_semantic_zero':True}


def main(a):
    a.output.mkdir(parents=True,exist_ok=False)
    try:result=audit(read(a.spec));code=0
    except Exception as error:
        result={'integrity_audit_passed':False,'error':type(error).__name__+': '+str(error),
            'all_four_trajectories_complete':False,'semantic_labels_inferred':False,
            'Mirage_trigger_rate_or_defense_success_claim':False};code=1
    result['audit_spec_sha256']=sha(a.spec.read_bytes())
    (a.output/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    (a.output/'seal.json').write_text(json.dumps({'audit.json':sha((a.output/'audit.json').read_bytes())},indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False));return code

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    raise SystemExit(main(p.parse_args()))
