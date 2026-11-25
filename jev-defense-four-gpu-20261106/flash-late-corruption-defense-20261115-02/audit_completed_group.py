"""Read-only postexit audit for the new twelve-trajectory experiment.

Use only after the current group actually exits. Supports native-contract
terminals, untriggered episodes, and multiple NO recaptures without reruns.
"""
import ast
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from control import HERE, manifest, remote, save, sha


def old_readers():
    src=HERE.parent/'flash-injection-first-defense-20261115-01/audit_completed_group.py'
    tree=ast.parse(src.read_text('utf8'));values={}
    for n in tree.body:
        if isinstance(n,ast.Assign)and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)and isinstance(n.value,ast.Constant)and isinstance(n.value.value,str):
            values[n.targets[0].id]=n.value.value
    common=values['COMMON']
    common=common.replace('key=(str(p),s.st_size,s.st_mtime_ns)','key=(str(p),s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)')
    common=common.replace('assert p.stat()==s,str(p)','after=p.stat();assert (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)==(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns),str(p)')
    values['COMMON']=common
    admission=values['ADMISSION']
    replacements={
        "status['done']==status['expected']==4":"status['done']==status['expected']==12",
        "assert status['attempted_actor_calls']==status['complete_actor_replies']==103":"assert status['attempted_actor_calls']==status['complete_actor_replies'] and 0<status['complete_actor_replies']<=12*50",
        'assert len(names)==103 and len(fnames)==70':"assert len(names)==status['complete_actor_replies'] and len(fnames)>0",
    }
    for old,new in replacements.items():
        assert admission.count(old)==1
        admission=admission.replace(old,new)
    values['ADMISSION']=admission
    gui=values['GUI']
    assert gui.count("status['expected']==4")==1 and gui.count('len(controllers)==4')==1
    values['GUI']=gui.replace("status['expected']==4","status['expected']==12").replace('len(controllers)==4','len(controllers)==12')+r'''
'''
    return src,values


def call(dest,name,host,code):
    q=dest/(name+'.json')
    if q.exists():return json.loads(q.read_bytes())['result']
    raw,op=remote(host,code,'late-corruption-postexit-'+name,timeout=55)
    result=json.loads(raw);save(q,{'result':result,'operation':str(op)})
    return result


EPISODE_READER=r'''
import sys
p=Path(P);sys.path.insert(0,str(p));from injection import Episode
plan=json.loads((p/'plan.json').read_bytes());rows=[]
for attempt in sorted((p/'batch/runs').glob('*/attempt-*')):
 t=json.loads((attempt/'terminal.json').read_bytes());_,events=chain(attempt/'controller/events.jsonl')
 episode=Episode(t['run']['condition']);previous_png=None;previous_action=None;deliveries=[];captures=[];forwards=[]
 for event in events:
  kind=event['kind'];d=event['data']
  if kind=='PRIVATE_capture_injection':
   raw=(attempt/d['raw_file']).read_bytes();delivered=(attempt/d['delivered_file']).read_bytes()
   assert hashlib.sha256(raw).hexdigest()==d['captured_sha256']and hashlib.sha256(delivered).hexdigest()==d['delivered_sha256']
   expected,record=episode.apply(raw,step=d['step'],previous_png=previous_png,previous_action=previous_action,recapture=d['capture_kind']=='recapture')
   assert expected==delivered and all(d[k]==v for k,v in record.items())
   deliveries.append(event)
  elif kind=='capture':captures.append(event)
  elif kind=='main_image_forwarded':
   forwards.append(event);previous_png=(attempt/'controller'/(d['image_sha256']+'.png')).read_bytes()
  elif kind=='native_environment_action':previous_action=d['payload']
 assert len(deliveries)==len(captures)
 capture_source={}
 for delivery,capture in zip(deliveries,captures):
  assert delivery['seq']<capture['seq']and delivery['data']['delivered_sha256']==capture['data']['image_sha256']
  capture_source[capture['data']['capture_id']]=delivery
 assert len(capture_source)==len(captures)
 assert t['injection_fired']==episode.started and t['trigger_step']==episode.start_step
 injected=[v for v in deliveries if v['data']['injected']]
 assert len(injected)==episode.used<=3
 if episode.started:assert episode.start_step>=10
 gates=[v for v in events if v['kind']=='gate_decision'];bad_gates=[];good_no=[];loops=[]
 for gate in gates:
  source=capture_source[gate['data']['capture_id']]
  if source['data']['injected']:bad_gates.append({'gate':gate,'source':source})
  elif gate['data']['decision']=='NO':good_no.append({'gate':gate,'source':source})
 for terminal in [v for v in events if v['kind']=='gate_terminal']:
  last=next(v for v in gates if v['data']['capture_id']==terminal['data']['last_capture_id'])
  first_seq=max([v['seq']for v in events if v['kind']=='gate_terminal'and v['seq']<terminal['seq']]+[-1])
  part=[v for v in gates if first_seq<v['seq']<=last['seq']]
  no=[v for v in part if v['data']['decision']=='NO']
  if not no:continue
  assert part[-1]['data']['decision']=='YES'and len(part)==len(no)+1
  assert not any(v['kind']in ['actual_actor_request','native_environment_action','main_image_forwarded']for v in events if no[0]['seq']<v['seq']<last['seq'])
  forward=next(v for v in forwards if v['seq']>last['seq'])
  assert forward['data']['capture_id']==last['data']['capture_id']
  source=capture_source[last['data']['capture_id']]['data']
  loops.append({'NO_count':len(no),'first_NO':no[0]['data'],'YES':last['data'],'accepted_source':source,'accepted_fresh_unmodified_raw':not source['injected']and source['capture_kind']=='recapture'and source['captured_sha256']==source['delivered_sha256'],'forwarded':forward['data']})
 rows.append({'run_id':t['run']['run_id'],'condition':t['run']['condition'],'gate_enabled':t['run']['gate_enabled'],'injection_fired':episode.started,'trigger_step':episode.start_step,'actual_injected_captures':len(injected),'source_transformation_and_fixed_dose_replayed':True,'injected_gate_decisions':bad_gates,'unmodified_raw_NO_for_source_review':good_no,'real_NO_to_fresh_capture_YES_sequences':loops,'complete_semantics_reviewed':False})
assert {v['run_id']for v in rows}=={v['run_id']for v in plan['queue']}and len(rows)==12
print(json.dumps({'episodes':rows,'new_model_GPU_GUI_calls':0}))
'''


def main():
    assert not(HERE/'completed-group-audit-current.json').exists(),'Use existing completed receipt'
    src,readers=old_readers()
    if len(sys.argv)>1:
        dest=Path(sys.argv[1]).resolve()
        assert dest.parent==HERE and not(dest/'seal.json').exists()and sha(dest/'source.py')==sha(__file__)
    else:
        dest=HERE/('completed-group-audit-'+str(time.time_ns()));dest.mkdir();(dest/'source.py').write_bytes(Path(__file__).read_bytes())
        (dest/'reused-reader-source.py').write_bytes(src.read_bytes())
    print(json.dumps({'audit_root':str(dest)}),flush=True)
    m=manifest();prefix='P='+repr(m['package3090'])+'\nO='+repr(m['output3090'])+'\nMANIFEST='+repr(sha(HERE/'package/manifest.json'))+'\n'+readers['COMMON']
    admitted=call(dest,'admission','3090',prefix+readers['ADMISSION']);gm=admitted['global'];mains=[];flashes=[]
    for label,names,source in [('primary',admitted['primary_names'],readers['PRIMARY']),('Flash',admitted['Flash_names'],readers['FLASH'])]:
        for i in range(0,len(names),8):
            value=call(dest,label+'-%03d'%i,'3090',prefix+'\nGLOBAL='+repr(gm)+'\nNAMES='+repr(names[i:i+8])+'\n'+source)
            (mains if label=='primary'else flashes).extend(value['requests'])
            print(json.dumps({'verified_primary':len(mains),'verified_Flash':len(flashes)}),flush=True)
    others={n:h for n,h in gm.items()if not n.startswith(('primary/requests/','flash/service/requests/'))}
    call(dest,'other-global-members','3090',prefix+'\nROWS='+repr(others)+'\n'+r'''
p=Path(P);o=Path(O)
for n,h in ROWS.items():assert sha((p if n.startswith('flash/service/')else o)/n)==h,n
print(json.dumps({'freshly_verified_nonrequest_files':len(ROWS),'new_model_GPU_GUI_calls':0}))
''')
    gui_prefix='P='+repr(m['package4090'])+'\nMANIFEST='+repr(sha(HERE/'package/manifest.json'))+'\n'+readers['COMMON']
    gui=call(dest,'GUI','4090',gui_prefix+readers['GUI'])
    episodes=call(dest,'capture-episodes','4090',gui_prefix+EPISODE_READER)
    checker=HERE.parent/'flash-resource-continuation-20261115-linked12/controller_audit_reader.py'
    namespace={'hashlib':hashlib};tree=ast.parse(checker.read_text('utf8'));function=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='check_controller')
    exec(compile(ast.Module(body=[function],type_ignores=[]),str(checker)+':reader','exec'),namespace)
    parser_src=HERE/'package/native-parser-source.py';assert sha(parser_src)==m['files']['native-parser-source.py']
    tree=ast.parse(parser_src.read_text('utf8'));functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='parse'];parsers={'json':json,'re':re}
    exec(compile(ast.Module(body=functions,type_ignores=[]),str(parser_src)+':parse','exec'),parsers)
    byid={v['request_id']:v for v in mains};fb={v['request_id']:v for v in flashes};bindings=[]
    for c in gui['controllers']:
        c['chain']['verified_prefix_events']=c['chain']['events']
        bound={'terminal_sha256':c['terminal_sha256'],'seal_sha256':c['seal_sha256'],'event_chain_head':c['chain']['head'],'event_chain_count':c['chain']['events']}
        bindings.append(namespace['check_controller'](c,byid,fb,bound,parsers['parse']))
    assert len([r for b in bindings for r in b['actor_requests']])==len(byid)==len(mains)
    assert len([r for b in bindings for r in b['Flash_requests']])==len(fb)==len(flashes)
    rows=[v['data']for v in admitted['primary_events']if v['kind']=='actor_reply_sealed']
    assert {v['request_id']:v['seal_sha256']for v in rows}=={v['request_id']:v['seal_sha256']for v in mains}
    final=call(dest,'final-identities-and-seals','3090',prefix+readers['ADMISSION'])
    assert final['global_seal_sha256']==admitted['global_seal_sha256']and final['primary_chain']==admitted['primary_chain']and final['Flash_chain']==admitted['Flash_chain']
    summary={'time':time.time(),'processed_GUI_trajectories':len(bindings),'actual_primary_replies_verified':len(mains),'actual_Flash_replies_verified':len(flashes),'Flash_YES':sum(v['decision']=='YES'for v in flashes),'Flash_NO':sum(v['decision']=='NO'for v in flashes),'fresh_global_files_verified':len(gm),'full_history_original_system_generation_and_input_output_tensors_verified':True,'fresh_raw_Flash_single_image_probabilities_and_no_KV_verified':True,'all_original_model_GUI_launcher_identities_exited':True,'controller_request_reply_native_action_and_all_seals_verified':True,'fixed_capture_episode_source_verified':True,'injection_triggered_trajectories':sum(v['injection_fired']for v in episodes['episodes']),'untriggered_trajectories':sum(not v['injection_fired']for v in episodes['episodes']),'primary_input_tokens':sum(v['input_tokens']for v in mains),'primary_output_tokens':sum(v['output_tokens']for v in mains),'primary_native_seconds_sum':sum(v['native_seconds']for v in mains),'Flash_input_tokens':sum(v['input_tokens']for v in flashes),'Flash_elapsed_seconds_sum_including_input_capture':sum(v['elapsed_seconds_with_input_capture']for v in flashes),'recorded_group_eight_GPU_interval':admitted['recorded_group_eight_GPU_interval'],'new_model_GPU_GUI_calls_by_audit':0,'complete_semantic_review':False,'Mirage_reduction_proven':False,'official_scores_are_not_semantic_labels':True,'terminal_rows':[{k:c['terminal'][k]for k in ['run','outcome','actor_calls','environment_actions','recaptures','injection_fired','trigger_step','official_reward','infrastructure_failure','cleanup_error']}for c in gui['controllers']]}
    save(dest/'native-and-Flash.json',{'primary':mains,'Flash':flashes})
    save(dest/'Controller-bindings.json',{'bindings':bindings,'reader_source':str(checker),'reader_sha256':sha(checker)})
    save(dest/'summary.json',summary)
    save(dest/'seal.json',{str(q.relative_to(dest)).replace('\\','/'):sha(q)for q in dest.rglob('*')if q.is_file()})
    save(HERE/'completed-group-audit-current.json',{'root':str(dest),'seal_sha256':sha(dest/'seal.json'),'Mirage_reduction_proven':False})
    print(json.dumps({'completed_audit':str(dest),'primary':len(mains),'Flash':len(flashes),'GUI':len(bindings),'Mirage_reduction_proven':False}),flush=True)


if __name__=='__main__':main()
