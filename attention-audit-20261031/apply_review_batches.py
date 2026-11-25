import hashlib,json,pathlib
root=pathlib.Path(__file__).parent;path=root/'semantic-labels.json';labels=json.loads(path.read_text(encoding='utf-8'))
for batch in json.loads((root/'review_batches.json').read_text(encoding='utf-8')):
    packets=json.loads((root/batch['packet_file']).read_text(encoding='utf-8'));assert len(packets)==batch['packet_count']
    for label in batch['labels']:
        for i in label['indices']:
            p=packets[i];assert p['group']==i;key=hashlib.sha256((p['condition']+'\0'+p['text']).encode()).hexdigest()
            entry={'recognizes_invalid_observation':label['recognition'],'unsupported_current_state_assertion':label['claim'],'explicit_state_assumption':label.get('assumption',False),'reason':label['reason'],'reviewer':'Codex assistant semantic review; not independent human annotation','output_sha256':hashlib.sha256(p['text'].encode()).hexdigest(),'condition':p['condition']}
            if key in labels:assert labels[key]==entry,'Existing review differs; record a deliberate adjudication instead of overwriting'
            labels[key]=entry
path.write_text(json.dumps(labels,ensure_ascii=False,indent=2),encoding='utf-8');print('Stored label entries including whitespace aliases',len(labels))
