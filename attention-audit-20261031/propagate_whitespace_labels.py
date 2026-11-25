"""Reuse semantic reviews only when text differs by outer whitespace alone."""
import hashlib,json,pathlib,sys
root=pathlib.Path(__file__).parent;path=root/'semantic-labels.json';labels=json.loads(path.read_text(encoding='utf-8'));known={}
for p in root.glob('review-packets-*.json'):
    for row in json.loads(p.read_text(encoding='utf-8')):
        key=hashlib.sha256((row['condition']+'\0'+row['text']).encode()).hexdigest()
        if key in labels:known[(row['condition'],row['text'].strip())]=(key,labels[key])
packets=json.loads((root/sys.argv[1]).read_text(encoding='utf-8'));added=0
for row in packets:
    key=hashlib.sha256((row['condition']+'\0'+row['text']).encode()).hexdigest();old=known.get((row['condition'],row['text'].strip()))
    if key not in labels and old:
        labels[key]=dict(old[1],inherited_from_review_key=old[0],inheritance_rule='Exact same condition and text after stripping outer whitespace only',output_sha256=hashlib.sha256(row['text'].encode()).hexdigest());added+=1
path.write_text(json.dumps(labels,ensure_ascii=False,indent=2),encoding='utf-8')
print('Whitespace-only label copies',added)
print('\n'.join(str(row['group'])+' '+row['condition']+' '+repr(row['text']) for row in packets if hashlib.sha256((row['condition']+'\0'+row['text']).encode()).hexdigest() not in labels))
