"""Build useful training-only views and verify every delivered input against the native protocol."""
import ast,base64,collections,copy,hashlib,json,random,sys,typing,zipfile
from pathlib import Path
from PIL import Image
from export import HERE,ROOT,BASE,ENC,SPLITS,read,rows,write_json,write_rows,sha,canon,oid,split_groups,part,action_json,prompt
from temporal_request import native_request,QUESTION_ID,STATE
from temporal_head import heldout_images

def native_messages():
    # Isolate the reference encoder's pure formatting methods (the rest of its
    # module imports torch). No reimplementation of its formatting or options.
    src=ast.parse(ENC.read_bytes());functions={z.name:z for z in src.body if isinstance(z,ast.FunctionDef)}
    c=next(z for z in src.body if isinstance(z,ast.ClassDef) and z.name=='Encoder')
    cc=copy.deepcopy(c);cc.body=[fn for fn in cc.body if isinstance(fn,ast.FunctionDef) and fn.name in ('messages','_text')]
    nodes=[s for s in src.body if isinstance(s,ast.ImportFrom) and s.module=='__future__']+[functions['describe'],functions['options'],cc]
    constants={t.id:ast.literal_eval(s.value) for s in src.body if isinstance(s,ast.Assign) for t in s.targets if isinstance(t,ast.Name) and t.id in ('MARKER','SYSTEM_PROMPT','DEFAULT_INSTRUCTIONS')}
    env=dict(constants,json=json);exec(compile(ast.Module(body=nodes,type_ignores=[]),str(ENC),'exec'),env)
    v=env['Encoder']();v.codes=read(BASE/'decision_config.json')['codes'];v._escapes=['<|fim_suffix|>']
    return v
def main():
    m=rows(HERE/'manifest.jsonl'); views={s:rows(HERE/(s+'.jsonl')) for s in SPLITS}; lookup={}
    protocol=read(HERE/'protocol.json');engine=native_messages();native_examples={};protected=heldout_images();image_splits={};stats=read(HERE/'stats.json')
    assert len(m)==stats['total']==sum(map(len,views.values()))
    for split in SPLITS:
        mm=[r for r in m if r['split']==split];assert len(mm)==len(views[split])
        for r,v in zip(mm,views[split]):
            assert set(v)=={'images','prompt','label'} and len(v['images'])==2 and v['label']==r['label'] in {'YES','NO'}
            assert v['images']==[r['before_png'],r['candidate_png']] and v['prompt']==prompt(r['action'])
            assert v['prompt'].count('<|fim_suffix|>')==1 and not any(s in action_json(r['action']) for s in ('<|','|>'))
            assert r['sample_id'] not in lookup;lookup[r['sample_id']]=v
            for k,im in zip(('before','candidate'),v['images']):
                h=r[k+'_sha256'];assert im=='images/'+h+'.png' and h not in protected
                assert image_splits.setdefault(h,split)==split
            typ=r['action']['type']
            if typ not in native_examples:
                a,b=[(HERE/q).read_bytes() for q in v['images']]
                req=native_request(a,r['action'],b)
                assert [base64.b64decode(x.split(',')[1]) for x in req['images']]==[a,b]
                native_examples[typ]=req['questions']
            req=dict(images=[0,1],questions=native_examples[typ],state=STATE+'\nDispatched native action (JSON): '+action_json(r['action']))
            sms=engine.messages(req)
            assert sms[0]['content']==protocol['system_prompt'] and sms[1]['content']==[{'type':'image'},{'type':'image'},{'type':'text','text':v['prompt']}]
    id_rows={oid(z):z for f in [HERE/'observations.jsonl',HERE/'additional-archive-observations.jsonl'] for z in rows(f)}
    selected=set();observed_groups={};reconciled=0
    for r in m:
        assert r['source_observation_id'] in r['all_observation_ids']
        src=id_rows[r['source_observation_id']]
        a,b=r['before_sha256'],r['candidate_sha256']
        assert [src[x] for x in ('before_sha256','action','candidate_sha256')]==[a,r['action'],b]
        for z in r['all_observation_ids']:
            assert z not in selected;selected.add(z);o=id_rows[z]
            assert part(o)==r['split'] and o['pair_id'] in r['supporting_pair_ids']
            for key in split_groups(o):assert observed_groups.setdefault(key,r['split'])==r['split'],key
            reconciled+=1
    write_rows('provenance.jsonl',[dict(observation_id=k,**id_rows[k]) for k in sorted(selected)])
    # Keep ALL available negatives. Prefer a real positive with the same initial
    # PNG+action, then the same suite/action type. No repeats or validation images.
    tt=[r for r in m if r['split']=='train'];ns=[r for r in tt if r['label']=='NO'];ps={r['sample_id']:r for r in tt if r['label']=='YES'}
    ns.sort(key=lambda r:sha(('balance'+r['sample_id']).encode()));sample=list(ns)
    for n in ns:
        def rank(p):
            return (not (p['before_sha256']==n['before_sha256'] and p['action']==n['action']),p['action']['type']!=n['action']['type'],p['source_suite']!=n['source_suite'],sha(('balance'+n['sample_id']+p['sample_id']).encode()))
        v=min(ps.values(),key=rank);sample.append(v);del ps[v['sample_id']]
    sample.sort(key=lambda r:sha(('mix'+r['sample_id']).encode()))
    write_rows('train-balanced.jsonl',[lookup[r['sample_id']] for r in sample])
    assert len(set(r['sample_id'] for r in sample))==2*len(ns) and {r['split'] for r in sample}=={'train'}
    assert collections.Counter(r['action']['type'] for r in sample if r['label']=='YES')==collections.Counter(r['action']['type'] for r in ns)
    # Real matched before+action with opposite outcomes; no synthetic image swaps.
    groups=collections.defaultdict(list)
    for r in m:groups[r['split'],r['before_sha256'],action_json(r['action'])].append(r)
    contrast=[dict(split=k[0],before_png='images/'+k[1]+'.png',action=json.loads(k[2]),YES=[r['sample_id'] for r in g if r['label']=='YES'],NO=[r['sample_id'] for r in g if r['label']=='NO']) for k,g in sorted(groups.items()) if len({r['label'] for r in g})==2]
    write_rows('contrast-index.jsonl',contrast)
    oak=[r for r in tt if r['action']=={'type':'type','text':'Oak Avenue'}]
    assert {r['label'] for r in oak}=={'YES','NO'} and len({r['before_sha256'] for r in oak})==1
    write_rows('example-oak-avenue.jsonl',[lookup[r['sample_id']] for r in sorted(oak,key=lambda r:r['label'])])
    size=sum((HERE/'images'/(h+'.png')).stat().st_size for h in image_splits)
    validation=dict(verified_rows=len(m),protocol_checked_against='native_request + reference Encoder.messages',distinct_action_types=sorted(native_examples),source_occurrences_reconciled=reconciled,original_supervised_pngs=len(image_splits),supervised_png_bytes=size,balanced_train_rows=len(sample),contrast_groups=len(contrast),cross_split_shared_pngs=0,supervised_input_schema=['images','prompt','label'],sha256={n:sha((HERE/n).read_bytes()) for n in ('train.jsonl','val.jsonl','test.jsonl','manifest.jsonl','protocol.json','train-balanced.jsonl','archive-label-evidence.jsonl','provenance.jsonl')})
    write_json('validation.json',validation);print({k:v for k,v in validation.items() if k!='sha256'})
def pack():
    members=['README.md','train.jsonl','val.jsonl','test.jsonl','train-balanced.jsonl','example-oak-avenue.jsonl','contrast-index.jsonl','manifest.jsonl','protocol.json','stats.json','validation.json','source-index.json','archive-join-counts.json','archive-label-evidence.jsonl','provenance.jsonl']
    m=rows(HERE/'manifest.jsonl'); members+=sorted({r[k] for r in m for k in ('before_png','candidate_png')})
    dest=HERE.parent/'jev-trajectory-v1.zip'
    with zipfile.ZipFile(dest,'w',allowZip64=True) as z:
        for n in members:z.write(HERE/n,n,compress_type=zipfile.ZIP_STORED if n.endswith('.png') else zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(dest) as z:
        assert z.testzip() is None and set(z.namelist())==set(members)
        for n,h in read(HERE/'validation.json')['sha256'].items():assert sha(z.read(n))==h
    h=hashlib.sha256()
    with dest.open('rb') as f:
        for block in iter(lambda:f.read(2**20),b''):h.update(block)
    (HERE/'bundle.sha256').write_bytes((h.hexdigest()+'  '+dest.name+'\n').encode())
    print(dest,dest.stat().st_size,h.hexdigest())
if __name__=='__main__':pack() if sys.argv[1:] == ['zip'] else main()
