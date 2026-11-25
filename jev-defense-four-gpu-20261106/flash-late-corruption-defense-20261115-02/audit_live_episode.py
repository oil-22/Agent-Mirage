"""Audit one already observed multi-capture episode without any model/GUI call."""
import ast
import hashlib
import json
import sys
import time
from pathlib import Path
from control import HERE,manifest,remote,save,sha


def literals(path):
    tree=ast.parse(path.read_text('utf8'));out={}
    for node in tree.body:
        if isinstance(node,ast.Assign)and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)and isinstance(node.value,ast.Constant)and isinstance(node.value.value,str):
            out[node.targets[0].id]=node.value.value
    return out


def main():
    run=sys.argv[1]
    resume=Path(sys.argv[2]).resolve()if len(sys.argv)>2 else None
    if resume is not None:
        assert resume.parent==HERE and (resume/'seal.json').exists()
        for n,h in json.loads((resume/'seal.json').read_bytes()).items():assert sha(resume/n)==h
    pointer=HERE/('episode-audit-'+run+'-current.json')
    assert not pointer.exists(),'Already audited this episode; use its immutable receipt'
    pp=json.loads((HERE/'live-progress-current.json').read_bytes());progress=Path(pp['root'])
    assert sha(progress/'seal.json')==pp['seal_sha256']
    for n,h in json.loads((progress/'seal.json').read_bytes()).items():assert sha(progress/n)==h
    collection=json.loads((progress/'result.json').read_bytes())['result']
    c=next(v for v in collection['4090']['attempts']if v['run_id']==run)
    events=c['events'];attacks=c['attacks'];assert len(attacks)==3
    start=attacks[0]['seq'];nos=[v for v in events if v['kind']=='gate_decision'and v['data']['decision']=='NO'and v['seq']>start]
    assert len(nos)==3
    yes=next(v for v in events if v['seq']>nos[-1]['seq']and v['kind']=='gate_decision'and v['data']['decision']=='YES')
    captures=[v for v in events if v['kind']=='capture'and start<v['seq']<yes['seq']]
    deliveries=[v for v in events if v['kind']=='PRIVATE_capture_injection'and start<=v['seq']<yes['seq']]
    assert len(captures)==len(deliveries)==4 and len({v['data']['capture_id']for v in captures})==4
    assert [v['data']['injected']for v in deliveries]==[True,True,True,False]
    assert [v['data']['injected_capture_ordinal']for v in deliveries[:3]]==[1,2,3]
    assert not any(v['kind']in ['actual_actor_request','main_image_forwarded','native_environment_action']for v in events if start<v['seq']<yes['seq'])
    for d,cap,gate in zip(deliveries,captures,nos+[yes]):
        assert d['seq']<cap['seq']<gate['seq']
        assert d['data']['delivered_sha256']==cap['data']['image_sha256']==gate['data']['image_sha256']
        assert cap['data']['capture_id']==gate['data']['capture_id']
    forwarded=next(v for v in events if v['kind']=='main_image_forwarded'and v['seq']>yes['seq'])
    request=next(v for v in events if v['kind']=='actual_actor_request'and v['seq']>forwarded['seq'])
    reply=next(v for v in events if v['kind']=='actual_actor_reply'and v['seq']>request['seq'])
    action=next(v for v in events if v['kind']=='native_environment_action'and v['seq']>reply['seq'])
    selected={'run_id':run,'chain':c['chain'],'deliveries':deliveries,'captures':captures,'NOs':nos,'YES':yes,'forwarded':forwarded,'request':request,'reply':reply,'actual_action':action,'progress':pp,'attempt':c['attempt']}
    reader=HERE.parent/'flash-injection-first-defense-20261115-01/audit_completed_group.py'
    sources=literals(reader)
    # Reading a sealed file may update atime. Keep identity/content stability
    # strict, excluding access time alone, and use ctime/inode in the cache key.
    sources['COMMON']=sources['COMMON'].replace(
        "key=(str(p),s.st_size,s.st_mtime_ns)",
        "key=(str(p),s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)")
    sources['COMMON']=sources['COMMON'].replace(
        "assert p.stat()==s,str(p)",
        "after=p.stat();assert (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)==(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns),str(p)")
    m=manifest();prefix='P='+repr(m['package3090'])+'\nO='+repr(m['output3090'])+'\n'+sources['COMMON']
    main_name=Path(reply['data']['receipt']).name
    flash_names=[v['data']['request_id']for v in nos+[yes]]
    expected={v['request_id']:v['seal_sha256']for v in collection['3090']['Flash_replies']if v['request_id']in flash_names}
    actual_main=next(v for v in collection['3090']['actor_replies']if v['request_id']==reply['data']['request_id'])
    bindings={'primary':{main_name:actual_main['seal_sha256']},'Flash':expected}
    code=prefix+'\nBINDINGS='+repr(bindings)+'\n'+r'''
p=Path(P);o=Path(O);global_map={}
for label,rows in BINDINGS.items():
 for name,expected in rows.items():
  d=(o/'primary/requests'if label=='primary'else p/'flash/service/requests')/name
  assert sha(d/'seal.json')==expected
  seal=json.loads((d/'seal.json').read_bytes());base=('primary/requests/'if label=='primary'else'flash/service/requests/')+name+'/'
  global_map.update({base+n:h for n,h in seal.items()});global_map[base+'seal.json']=expected
print(json.dumps({'global_map':global_map,'not_a_group_postexit_seal':True,'new_model_GUI_calls':0}))
'''
    raw,op=remote('3090',code,'live-episode-request-seal-admission',timeout=45);admitted=json.loads(raw)
    root=HERE/('live-episode-audit-'+run+'-'+str(time.time_ns()));root.mkdir()
    (root/'source.py').write_bytes(Path(__file__).read_bytes())
    save(root/'selection.json',selected);save(root/'admission.json',{'operation':str(op),'result':admitted})
    outputs={}
    for label,names in [('PRIMARY',[main_name]),('FLASH',flash_names)]:
        if resume is not None and label=='PRIMARY':
            prior=json.loads((resume/'PRIMARY.json').read_bytes())
            outputs[label]=prior['result']
            assert len(outputs[label]['requests'])==1 and outputs[label]['requests'][0]['seal_sha256']==actual_main['seal_sha256']
            save(root/(label+'.json'),{**prior,'reused_successful_readonly_proof_from':str(resume/'PRIMARY.json'),'reused_proof_sha256':sha(resume/'PRIMARY.json')})
        else:
            raw,op=remote('3090',prefix+'\nNAMES='+repr(names)+'\nGLOBAL='+repr(admitted['global_map'])+'\n'+sources[label],'live-episode-'+label.lower()+'-raw-forward-CPU-only',timeout=55)
            outputs[label]=json.loads(raw);save(root/(label+'.json'),{'operation':str(op),'result':outputs[label]})
    main_row=outputs['PRIMARY']['requests'][0]
    assert main_row['body_sha256']==request['data']['body_sha256']
    assert hashlib.sha256(main_row['native_text'].encode()).hexdigest()==reply['data']['text_sha256']
    assert main_row['current_image_sha256']==yes['data']['image_sha256']==forwarded['data']['image_sha256']
    assert not {v['data']['image_sha256']for v in nos}&set(main_row['all_image_sha256s'])
    for row,event in zip(outputs['FLASH']['requests'],nos+[yes]):
        assert row['request_id']==event['data']['request_id']and row['decision']==event['data']['decision']and row['image_sha256']==event['data']['image_sha256']
    code='P='+repr(m['package4090'])+'\nSELECTED='+repr(selected)+'\nEXPECTED='+repr(sha(HERE/'package/manifest.json'))+'\n'+sources['COMMON']+r'''
import sys
p=Path(P);assert os.getuid()==1015 and sha(p/'manifest.json')==EXPECTED
m=json.loads((p/'manifest.json').read_bytes())
for n in ['gui_experiment.py','injection.py','flash/gate_core.py']:assert sha(p/n)==m['files'][n]
sys.path.insert(0,str(p));from injection import transform
a=Path(SELECTED['attempt']);rows=[]
proof,events=chain(a/'controller/events.jsonl')
assert proof['events']>=SELECTED['chain']['events']
for event in SELECTED['deliveries']:
 d=event['data'];raw=(a/d['raw_file']).read_bytes();png=(a/d['delivered_file']).read_bytes()
 assert hashlib.sha256(raw).hexdigest()==d['captured_sha256']and hashlib.sha256(png).hexdigest()==d['delivered_sha256']
 assert (transform(raw,d['condition'])if d['injected']else raw)==png
 rows.append({'capture_index':d['capture_index'],'raw_sha256':d['captured_sha256'],'delivered_sha256':d['delivered_sha256'],'injected':d['injected'],'exact_declared_transformation_verified':True})
assert rows[-1]['raw_sha256']==rows[-1]['delivered_sha256']
print(json.dumps({'deliveries':rows,'fresh_chain':proof,'same_live_capture_method_and_episode_source_sha_verified':True,'new_model_GUI_calls':0}))
'''
    raw,op=remote('4090',code,'live-episode-original-capture-transformation-source',timeout=45);gui=json.loads(raw);save(root/'GUI-source.json',{'operation':str(op),'result':gui})
    save(root/'summary.json',{'time':time.time(),'run_id':run,'actual_continuous_NO_count':3,'actual_real_same_live_recaptures_before_YES':3,'no_actor_or_environment_action_before_YES':True,'rejected_corrupted_bytes_absent_from_full_main_input':True,'accepted_frame_is_unmodified_fresh_raw_capture':True,'actual_native_action':action['data'],'native_reply':main_row['native_text'],'all4_Flash_single_image_raw_tensors_probabilities_noKV_CPU_verified':True,'complete_trajectory_semantics_reviewed':False,'Mirage_reduction_proven':False,'group_postexit_fresh_audit_still_required':True,'new_model_GUI_calls':0})
    save(root/'seal.json',{q.name:sha(q)for q in root.iterdir()if q.is_file()})
    save(pointer,{'root':str(root),'seal_sha256':sha(root/'seal.json'),'actual_three_NO_then_fresh_YES_and_native_action':True,'Mirage_reduction_proven':False})
    print(json.dumps({'episode_audit':str(root),'actual_NO_count':3,'fresh_recaptures':3,'main_reply':main_row['native_text'],'native_action':action['data']['payload'],'Mirage_reduction_proven':False}))


if __name__=='__main__':main()
