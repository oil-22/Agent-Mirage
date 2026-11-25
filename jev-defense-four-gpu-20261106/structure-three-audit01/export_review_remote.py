"""New read-only public legal-input projection for 73 judges and20 observers."""
import base64,copy,hashlib,io,json,os,struct,time,zipfile
from pathlib import Path

BASE=Path('/data/researcher/jev-defense-four-gpu-20261106')
ATTEMPT=BASE/'gui-batch-image-observer-three-01/runs/image-observer-v1--classifieds_112--clean--joint--observer/attempt-1793987248242098761'
TERMINAL_SHA='66d18d91d05e635d58363a54b9a26aa78bcfde06bcd6edeb66f4c86b1e52f01a'
EXPECTED_HEAD='c120b3b6ea1a739a91b29726628995a0a35703ed6b8514b55fe7a7c8a6748b20'
ROOT=BASE/('three-legal-review-projection-'+str(time.time_ns()))
sha=lambda raw:hashlib.sha256(raw).hexdigest()
canon=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()

def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf8')as f:json.dump(obj,f,ensure_ascii=False,indent=2)

def image(raw):
    assert raw[:8]==b'\x89PNG\r\n\x1a\n'
    key=sha(raw);path=ROOT/'review/images'/(key+'.png')
    if path.exists():assert path.read_bytes()==raw
    else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    w,h=struct.unpack('>II',raw[16:24])
    return {'original_image_sha256':key,'original_size':[w,h],'review_relative_path':'images/'+key+'.png'}

def project(value):
    if isinstance(value,list):return[project(v)for v in value]
    if isinstance(value,dict):
        if value.get('type')=='image_url':
            url=value['image_url'];url=url['url']if isinstance(url,dict)else url
            assert url.startswith('data:image/png;base64,')
            return {'type':'original_image_reference',**image(base64.b64decode(url.split(',',1)[1],validate=True))}
        result={}
        for key,v in value.items():
            if key=='raw_base64':result['original_raw_image_binding']=image(base64.b64decode(v,validate=True))
            elif key=='image_base64':result['original_image_binding']=image(base64.b64decode(v,validate=True))
            else:result[key]=project(v)
        return result
    return value

def main():
    terminal=(ATTEMPT/'technical-failure.json').read_bytes();assert sha(terminal)==TERMINAL_SHA
    raw=(ATTEMPT/'events.jsonl').read_bytes();assert raw.endswith(b'\n')
    ROOT.mkdir(mode=0o700,exist_ok=False)
    previous='0'*64;pending_judge=None;pending_aux=None;judges=[];aux=[];actor_packets=[]
    for index,line in enumerate(raw.splitlines()):
        row=json.loads(line);assert row['seq']==index and row['previous']==previous
        assert row['sha256']==sha(canon({k:v for k,v in row.items()if k!='sha256'}));previous=row['sha256']
        kind=row['kind']
        if kind.startswith('private'):continue
        data=row['data']
        if kind=='verifier_request':pending_judge={'request_event_sha256':row['sha256'],'request_event_seq':index,'phase':data['phase'],'original_verifier_request':project(copy.deepcopy(data))}
        elif kind=='actual_primary_wire_request'and data['body'].get('payload',{}).get('operation')=='judge':
            assert pending_judge is not None
            envelope=data['body'];assert sha(data['wire_utf8'].encode())==data['wire_sha256']
            pending_judge.update(actual_wire_sha256=data['wire_sha256'],original_payload_sha256=sha(canon(envelope['payload'])),actual_envelope_without_payload={k:v for k,v in envelope.items()if k!='payload'},actual_native_payload=project(envelope['payload']))
        elif kind=='verifier_raw':
            assert pending_judge is not None;assert pending_judge['phase']==data['phase']
            pending_judge.update(raw_response=data['response'],response_event_sha256=row['sha256'],response_event_seq=index,format_retry=data['format_retry'])
            judges.append(pending_judge);pending_judge=None
        elif kind=='actual_observer_wire':
            envelope=data['body'];wire=sha(data['wire_utf8'].encode());assert wire==data.get('wire_sha256',data.get('external_wire_sha256'))
            pending_aux={'request_event_seq':index,'request_event_sha256':row['sha256'],'actual_wire_sha256':wire,'actual_envelope_without_payload':{k:v for k,v in envelope.items()if k!='payload'},'actual_native_payload':project(envelope['payload'])}
        elif kind=='actual_observer_wire_reply':
            assert pending_aux is not None;response_raw=base64.b64decode(data['raw_base64'],validate=True);assert sha(response_raw)==data['raw_sha256']
            pending_aux.update(actual_response=json.loads(response_raw),response_event_seq=index,response_event_sha256=row['sha256'],response_raw_sha256=data['raw_sha256'])
            aux.append(pending_aux);pending_aux=None
        elif kind=='actor_observer_packet':actor_packets.append({'event_seq':index,'event_sha256':row['sha256'],'packet':data})
    assert index+1==1103 and previous==EXPECTED_HEAD and pending_judge is None and pending_aux is None
    assert len(judges)==73 and len(aux)==20 and len(actor_packets)==24
    for i,value in enumerate(judges,1):save(ROOT/'review/judges'/f'{i:03}.json',value)
    for i,value in enumerate(aux,1):save(ROOT/'review/observers'/f'{i:03}.json',value)
    save(ROOT/'review/actor-packets.json',actor_packets)
    receipt={'status':'all_legal_inputs_and_raw_replies_exported','judge_count':len(judges),'observer_count':len(aux),'actor_packet_count':len(actor_packets),'unique_original_images':len(list((ROOT/'review/images').glob('*.png'))),'events_file_sha256':sha(raw),'event_count':1103,'event_chain_head':previous,'technical_terminal_sha256':sha(terminal),'original_wire_or_model_input_modified':False,'image_base64_only_replaced_in_review_projection':True,'PRIVATE_values_or_expected_labels_exported':False,'semantic_or_execution_join_labels_added':False,'new_health_POST_model_GUI_scorer_calls':0,'source_path':str(ATTEMPT),'source_code_sha256':sha(Path(__file__).read_bytes())}
    save(ROOT/'receipt.json',receipt)
    assert (ATTEMPT/'events.jsonl').read_bytes()==raw and(ATTEMPT/'technical-failure.json').read_bytes()==terminal
    (ROOT/'export-source.py').write_bytes(Path(__file__).read_bytes())
    mapping={str(p.relative_to(ROOT)):sha(p.read_bytes())for p in ROOT.rglob('*')if p.is_file()}
    save(ROOT/'seal.json',mapping)
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED,compresslevel=5)as z:
        for p in ROOT.rglob('*'):
            if p.is_file():z.write(p,str(p.relative_to(ROOT)))
    print(json.dumps({'root':str(ROOT),'receipt_sha256':sha((ROOT/'receipt.json').read_bytes()),'seal_sha256':sha((ROOT/'seal.json').read_bytes()),'zip_base64':base64.b64encode(buf.getvalue()).decode()}))

if __name__=='__main__':main()
