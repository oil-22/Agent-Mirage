"""Read-only, resumable audit of this completed new study; never launches models."""
import ast
import base64
import hashlib
import json
import sys
import time
from pathlib import Path
from control import HERE, manifest, remote, save, sha


COMMON = r'''
import base64,hashlib,json,os,struct,time
from pathlib import Path
cache={}
def sha(p):
 p=Path(p);s=p.stat();key=(str(p),s.st_size,s.st_mtime_ns)
 if key not in cache:
  h=hashlib.sha256()
  with p.open('rb')as f:
   for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
  assert p.stat()==s,str(p)
  cache[key]=h.hexdigest()
 return cache[key]
def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def identity(saved):
 q=Path('/proc',str(saved['pid']));v=None
 if q.exists():
  s=(q/'stat').read_text().rsplit(')',1)[1].split()
  v={'pid':saved['pid'],'uid':q.stat().st_uid,'command':(q/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'start_ticks':s[19],'state':s[0]}
 same=v is not None and v['state']not in ['Z','X']and all(v[k]==saved[k]for k in ['uid','command','start_ticks'])
 assert not same,'Completed study still running'
 return {'saved':saved,'current_if_PID_exists':v,'same_live_process':False}
def chain(path):
 raw=path.read_bytes();assert raw.endswith(b'\n'),str(path)
 head='0'*64;rows=[]
 for n,line in enumerate(raw.splitlines()):
  row=json.loads(line);h=row.pop('sha256')
  assert row['seq']==n and row['previous']==head and h==hashlib.sha256(canonical(row)).hexdigest()
  head=h;rows.append(row)
 return {'events':len(rows),'head':head,'sha256':sha(path)},rows
def verify(root,seal_name='seal.json',global_map=None,prefix=''):
 seal=json.loads((root/seal_name).read_bytes())
 actual={str(f.relative_to(root))for f in root.rglob('*')if f.is_file()and f!=root/seal_name}
 assert actual==set(seal),(str(root),'file coverage')
 for n,h in seal.items():assert sha(root/n)==h,(str(root),n)
 if global_map is not None:
  expected={prefix+n:h for n,h in seal.items()};expected[prefix+seal_name]=sha(root/seal_name)
  assert expected=={n:h for n,h in global_map.items()if n.startswith(prefix)}
 return {'root':str(root),'members':len(seal),'seal_sha256':sha(root/seal_name)}
'''

ADMISSION = r'''
p=Path(P);o=Path(O);assert os.getuid()==1033
assert sha(p/'manifest.json')==MANIFEST
m=json.loads((p/'manifest.json').read_bytes())
for n,h in m['files'].items():assert sha(p/n)==h,n
status=json.loads((o/'primary/status.json').read_bytes());exit=json.loads((o/'exit.json').read_bytes())
assert status['phase']=='completed'and status['done']==status['expected']==4 and status['active']is None
assert status['attempted_actor_calls']==status['complete_actor_replies']==103
assert exit['exit_code']==0 and exit['failure']is None and all(x['exit_code']==0 for x in exit['children'])
processes=[identity(json.loads(q.read_bytes()))for q in [o/'launcher-process.json',o/'primary/process.json',p/'flash/service/process.json']]
global_map=json.loads((o/'postexit-seal.json').read_bytes())
actual={str(f.relative_to(o))for f in o.rglob('*')if f.is_file()and f!=o/'postexit-seal.json'}|{str(f.relative_to(p))for f in(p/'flash/service').rglob('*')if f.is_file()and f.name!='token'}
assert actual==set(global_map)
primary_chain,primary_events=chain(o/'primary/journal/events.jsonl');flash_chain,flash_events=chain(p/'flash/service/journal/events.jsonl')
loaded=json.loads((o/'primary/loaded.json').read_bytes());fl=json.loads((p/'flash/service/loaded.json').read_bytes())
assert loaded['physical_gpus']==list(range(7))and loaded['dtype']=='bfloat16'and loaded['attention']=='sdpa'and loaded['native_generate_unchanged']
assert not loaded['main_history_truncation']and not loaded['image_preprocessing_changed']
assert fl['revision']=='9ff7cf9838e59df461c276b7699d56b244d2af58'and fl['single_image']and fl['no_cross_request_KV']and fl['dtype']=='bfloat16'
names=sorted(q.name for q in(o/'primary/requests').iterdir());fnames=sorted(q.name for q in(p/'flash/service/requests').iterdir())
assert len(names)==103 and len(fnames)==70
lease=json.loads((o/'expanded-lease.json').read_bytes())
print(json.dumps({'time':time.time(),'manifest_sha256':MANIFEST,'global':global_map,'global_seal_sha256':sha(o/'postexit-seal.json'),'status':status,'exit':exit,'exited_identities':processes,'primary_chain':primary_chain,'Flash_chain':flash_chain,'primary_events':primary_events,'Flash_events':flash_events,'primary_names':names,'Flash_names':fnames,'loaded':loaded,'Flash_loaded':fl,'recorded_group_eight_GPU_interval':{'start':lease['created'],'end':exit['time'],'seconds':exit['time']-lease['created'],'GPU_seconds':8*(exit['time']-lease['created']),'excludes_earlier_holder_and_postexit_audit_time':True}}))
'''

PRIMARY = r'''
p=Path(P);o=Path(O);template=json.loads((p/'actor-template.json').read_bytes());history={};out=[]
for name in NAMES:
 d=o/'primary/requests'/name
 proof=verify(d,global_map=GLOBAL,prefix='primary/requests/'+name+'/')
 w=json.loads((d/'wire-request.bin').read_bytes());b=json.loads((d/'body.json').read_bytes());r=json.loads((d/'response.json').read_bytes());a=json.loads((d/'actual-generation.json').read_bytes());n=json.loads((d/'native-call.json').read_bytes());e=json.loads((d/'effective-generation.json').read_bytes())
 assert b==w['body']and b['messages'][0]==template['messages'][0]
 assert{k:v for k,v in b.items()if k!='messages'}=={k:v for k,v in template.items()if k!='messages'}
 assert r['request_sha256']==sha(d/'wire-request.bin')and r['request_id']==w['request_id']and n['text']==r['text']
 assert n['request_messages_sha256']==hashlib.sha256(canonical(b['messages'])).hexdigest()
 assert n['generation_config']==e and n['generated_ids']==a['output_ids']and not n['hit_output_cap']
 run=w['run_id'];decision=w['decision_index']
 if decision>1:
  prior=next(q for q in (o/'primary/requests').iterdir()if q.name<name and json.loads((q/'wire-request.bin').read_bytes())['run_id']==run and json.loads((q/'wire-request.bin').read_bytes())['decision_index']==decision-1)
  pb=json.loads((prior/'body.json').read_bytes());pr=json.loads((prior/'response.json').read_bytes())
  assert b['messages'][:len(pb['messages'])]==pb['messages']and b['messages'][len(pb['messages'])]=={'role':'assistant','content':pr['text']}
  assert len(b['messages'])==len(pb['messages'])+2
 prepared=json.loads((d/'prepared.json').read_bytes());first=json.loads((d/'first-forward.json').read_bytes())
 for k,v in prepared.items():
  assert all(v[f]==first[k][f]for f in ['shape','dtype','bytes','sha256'])
  assert sha(d/v['file'])==v['sha256']and sha(d/first[k]['file'])==first[k]['sha256']
 def ids(file):
  raw=file.read_bytes();assert len(raw)%8==0
  return list(struct.unpack('<'+str(len(raw)//8)+'q',raw))
 inputs=ids(d/prepared['input_ids']['file']);seq=ids(d/'sequence_ids.tensor')
 assert inputs==n['input_ids']and len(inputs)==a['input_tokens']
 assert seq==inputs+a['output_ids']and len(a['output_ids'])==a['output_tokens']
 eos=e['eos_token_id'];eos=[eos]if isinstance(eos,int)else eos
 assert a['natural_EOS']and a['output_ids'][-1]in eos and 0<a['output_tokens']<=2048 and e['max_new_tokens']==2048
 images=[hashlib.sha256(base64.b64decode(c['image_url']['url'].split(',',1)[1],validate=True)).hexdigest()for msg in b['messages']if isinstance(msg.get('content'),list)for c in msg['content']if c['type']=='image_url']
 out.append({**proof,'folder':str(d),'request_id':w['request_id'],'run_id':run,'decision':decision,'wire_sha256':sha(d/'wire-request.bin'),'body_sha256':hashlib.sha256(canonical(b)).hexdigest(),'input_tokens':a['input_tokens'],'output_tokens':a['output_tokens'],'natural_EOS':True,'native_text':r['text'],'current_image_sha256':images[-1],'all_image_sha256s':images,'history_messages':len(b['messages']),'actual_tensor_files_verified':True,'exact_full_history_preserved':True,'native_seconds':n['seconds'],'memory':a['memory']})
print(json.dumps({'requests':out,'new_model_GPU_GUI_calls':0}))
'''

FLASH = r'''
os.environ['CUDA_VISIBLE_DEVICES']=''
import torch
torch.set_num_threads(2)
p=Path(P);root=p/'flash';contract=json.loads((root/'gate-contract.json').read_bytes());config=json.loads((root/'service-config.json').read_bytes());temperature=json.loads((Path(config['model_dir'])/'decision_config.json').read_bytes())['temperature'];keys=list(contract['options']);out=[]
for name in NAMES:
 d=root/'service/requests'/name;proof=verify(d,global_map=GLOBAL,prefix='flash/service/requests/'+name+'/')
 response=json.loads((d/'response.json').read_bytes());wire=json.loads((d/'wire-request.bin').read_bytes());request=json.loads((d/'native-request.json').read_bytes());trace=json.loads((d/'forward-trace.json').read_bytes())
 assert set(wire)=={'request_id','image_png_base64','image_sha256'}and wire['request_id']==response['request_id']==name
 assert hashlib.sha256(base64.b64decode(wire['image_png_base64'],validate=True)).hexdigest()==sha(d/'original.png')==wire['image_sha256']==response['image_sha256']
 assert response['request_sha256']==sha(d/'wire-request.bin')and response['contract_sha256']==sha(root/'gate-contract.json')
 assert response['revision']=='9ff7cf9838e59df461c276b7699d56b244d2af58'
 assert request['state']==contract['state']and request['questions']=={'usable':{'type':'choice','instructions':contract['question'],'criteria':contract['options']}}and len(request['images'])==1 and request['images'][0]['sha256']==response['image_sha256']
 assert len(trace)==1 and trace[0]['past_key_values']is None and trace[0]['use_cache']is False
 actual=torch.load(d/'actual-forward-inputs.pt',map_location='cpu',weights_only=True)
 assert {'input_ids','pixel_values','image_grid_thw'}<=set(actual)
 for k,v in actual.items():
  v=v.contiguous();t=trace[0][k]
  assert list(v.shape)==t['shape']and str(v.dtype)==t['dtype']and hashlib.sha256(v.view(torch.uint8).numpy().tobytes()).hexdigest()==t['sha256']
 raw=json.loads((d/'raw-readout.json').read_bytes());head=torch.tensor(raw[0]['values'],dtype=getattr(torch,raw[0]['dtype'].split('.')[-1]))
 assert hashlib.sha256(head.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()==raw[0]['sha256']
 probabilities=(head[0,:2].float()/float(temperature)).softmax(-1).tolist();native=json.loads((d/'native-result.json').read_bytes())['answers']['usable'];audit=json.loads((d/'audit.json').read_bytes())
 assert native['probabilities']==audit['probabilities']and all(abs(native['probabilities'][k]-probabilities[i])<2e-6 for i,k in enumerate(keys))
 assert response['decision']==native['choice']==max(native['probabilities'],key=native['probabilities'].__getitem__)
 out.append({**proof,**response,'probabilities':audit['probabilities'],'actual_forward_tensor_bytes_verified':True,'full_raw_head_probability_binding_verified':True,'input_tokens':audit['input_tokens'],'elapsed_seconds_with_input_capture':audit['elapsed_seconds_with_input_capture'],'memory':audit['memory']})
assert not torch.cuda.is_initialized()
print(json.dumps({'requests':out,'new_model_GPU_GUI_calls':0,'audit_CUDA_initialized':False}))
'''

GUI = r'''
p=Path(P);assert os.getuid()==1015 and sha(p/'manifest.json')==MANIFEST
for n,h in json.loads((p/'manifest.json').read_bytes())['files'].items():assert sha(p/n)==h,n
processes=[identity(json.loads((p/n).read_bytes()))for n in ['control/process.json','control/runner-process.json']]
control=verify(p/'control','postexit-seal.json')
batch=verify(p/'batch',global_map=None)if(p/'batch/seal.json').exists()else None
batch_seal=json.loads((p/'control/batch-terminal-seal.json').read_bytes())
assert {str(f.relative_to(p/'batch'))for f in(p/'batch').rglob('*')if f.is_file()}==set(batch_seal)
for n,h in batch_seal.items():assert sha(p/'batch'/n)==h,n
assert json.loads((p/'control/exit.json').read_bytes())['child_exit']==0
status=json.loads((p/'batch/status.json').read_bytes());assert status['phase']=='completed'and status['completed']==status['processed']==status['expected']==4
controllers=[]
for a in sorted((p/'batch/runs').glob('*/attempt-*')):
 proof=verify(a);t=json.loads((a/'terminal.json').read_bytes());cp,events=chain(a/'controller/events.jsonl')
 for event in events:
  if event['kind']=='capture':assert sha(a/'controller'/(event['data']['image_sha256']+'.png'))==event['data']['image_sha256']
  if event['kind']=='PRIVATE_delivery_ledger':
   v=event['data'];assert sha(a/('%03d-actually-captured.png'%v['step']))==v['captured_sha256']and sha(a/('%03d-initial-delivered.png'%v['step']))==v['delivered_sha256']
 controllers.append({**proof,'attempt':str(a),'terminal':t,'terminal_sha256':sha(a/'terminal.json'),'chain':cp,'events':events})
assert len(controllers)==4
print(json.dumps({'time':time.time(),'controllers':controllers,'processes':processes,'control':control,'batch_member_count':len(batch_seal),'status':status,'new_model_GPU_GUI_calls':0}))
'''


def call(dest, name, host, code):
    q = dest / (name + '.json')
    if q.exists():
        return json.loads(q.read_bytes())['result']
    raw, op = remote(host, code, 'injection-first-completed-' + name, timeout=55)
    result = json.loads(raw)
    save(q, {'result': result, 'operation': str(op)})
    return result


def main():
    assert not (HERE / 'completed-group-audit-current.json').exists(), 'Already audited; use the immutable receipt'
    if len(sys.argv) > 1:
        dest = Path(sys.argv[1]).resolve()
        assert dest.parent == HERE and not (dest / 'seal.json').exists()
        assert sha(dest / 'source.py') == sha(__file__)
    else:
        dest = HERE / ('completed-group-audit-' + str(time.time_ns()))
        dest.mkdir()
        (dest / 'source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'audit_root': str(dest)}), flush=True)
    m = manifest()
    prefix = 'P=' + repr(m['package3090']) + '\nO=' + repr(m['output3090']) + '\nMANIFEST=' + repr(sha(HERE / 'package/manifest.json')) + '\n' + COMMON
    admitted = call(dest, 'admission', '3090', prefix + ADMISSION)
    gm = admitted['global']; mains = []; flashes = []
    for label, names, source in [('primary', admitted['primary_names'], PRIMARY), ('Flash', admitted['Flash_names'], FLASH)]:
        for i in range(0, len(names), 8):
            value = call(dest, label + '-%03d' % i, '3090', prefix + '\nGLOBAL=' + repr(gm) + '\nNAMES=' + repr(names[i:i+8]) + '\n' + source)
            (mains if label == 'primary' else flashes).extend(value['requests'])
            print(json.dumps({'verified_primary': len(mains), 'verified_Flash': len(flashes)}), flush=True)
    others = {n:h for n,h in gm.items() if not n.startswith(('primary/requests/','flash/service/requests/'))}
    call(dest, 'other-global-members', '3090', prefix + '\nROWS=' + repr(others) + '\n' + r'''
p=Path(P);o=Path(O)
for n,h in ROWS.items():assert sha((p if n.startswith('flash/service/')else o)/n)==h,n
print(json.dumps({'freshly_verified_nonrequest_files':len(ROWS),'new_model_GPU_GUI_calls':0}))
''')
    gui = call(dest, 'GUI', '4090', 'P=' + repr(m['package4090']) + '\nMANIFEST=' + repr(sha(HERE / 'package/manifest.json')) + '\n' + COMMON + GUI)
    # Import only frozen reader functions; no old experiment or finalizer entrypoints.
    old = HERE.parent / 'flash-resource-continuation-20261115-linked12'
    namespace = {'hashlib':hashlib}
    src = old / 'controller_audit_reader.py'
    tree = ast.parse(src.read_text('utf8'))
    function = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='check_controller')
    exec(compile(ast.Module(body=[function],type_ignores=[]),str(src)+':reader','exec'),namespace)
    parser_src = HERE / 'package/native-parser-source.py'
    assert sha(parser_src) == m['files']['native-parser-source.py']
    tree = ast.parse(parser_src.read_text('utf8')); functions = [n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='parse']
    import re
    parsers = {'json':json,'re':re};exec(compile(ast.Module(body=functions,type_ignores=[]),str(parser_src)+':parse','exec'),parsers)
    byid = {v['request_id']:v for v in mains};fb = {v['request_id']:v for v in flashes};bindings=[];loops=[]
    for c in gui['controllers']:
        c['chain']['verified_prefix_events'] = c['chain']['events']
        bound = {'terminal_sha256':c['terminal_sha256'],'seal_sha256':c['seal_sha256'],'event_chain_head':c['chain']['head'],'event_chain_count':c['chain']['events']}
        bindings.append(namespace['check_controller'](c,byid,fb,bound,parsers['parse']))
        events=c['events'];attack=next(v for v in events if v['kind']=='PRIVATE_delivery_ledger'and v['data']['injected'])
        t=c['terminal'];assert t['injection_fired']and t['trigger_step']==2 and t['scoring_status']=='complete'and t['outcome']=='model_stop'
        if t['run']['gate_enabled']:
            no=next(v for v in events if v['seq']>attack['seq']and v['kind']=='gate_decision'and v['data']['decision']=='NO')
            yes=next(v for v in events if v['seq']>no['seq']and v['kind']=='gate_decision'and v['data']['decision']=='YES')
            cap=next(v for v in events if no['seq']<v['seq']<yes['seq']and v['kind']=='capture')
            assert no['data']['image_sha256']==attack['data']['delivered_sha256']and cap['data']['capture_id']!=no['data']['capture_id']
            assert cap['data']['image_sha256']==yes['data']['image_sha256']==attack['data']['captured_sha256']
            assert not any(v['kind']in ['actual_actor_request','main_image_forwarded','native_environment_action']for v in events if attack['seq']<v['seq']<yes['seq'])
            forward=next(v for v in events if v['seq']>yes['seq']and v['kind']=='main_image_forwarded')
            request=next(v for v in events if v['seq']>forward['seq']and v['kind']=='actual_actor_request')
            assert forward['data']['image_sha256']==yes['data']['image_sha256']
            assert no['data']['image_sha256']not in byid[request['data']['request_id']]['all_image_sha256s']
            loops.append({'run_id':t['run']['run_id'],'NO':no['data'],'fresh_capture':cap['data'],'YES':yes['data'],'forwarded':forward['data'],'actor_request_id':request['data']['request_id'],'actual_native_reply':byid[request['data']['request_id']]['native_text'],'one_real_recapture':t['recaptures']==1})
        else:
            main=next(v for v in mains if v['run_id']==t['run']['run_id']and v['decision']==2)
            assert parsers['parse'](main['native_text'])['type']=='wait'
    assert len(mains)==103 and len(flashes)==70 and len(loops)==2
    assert len([r for b in bindings for r in b['actor_requests']])==len(byid)==103
    assert len([r for b in bindings for r in b['Flash_requests']])==len(fb)==70
    for kind,key in [('actor_reply_sealed','primary_events')]:
        rows=[v['data']for v in admitted[key]if v['kind']==kind]
        assert {v['request_id']:v['seal_sha256']for v in rows}=={v['request_id']:v['seal_sha256']for v in mains}
    final = call(dest, 'final-identities-and-seals', '3090', prefix + ADMISSION)
    assert final['global_seal_sha256']==admitted['global_seal_sha256']and final['primary_chain']==admitted['primary_chain']and final['Flash_chain']==admitted['Flash_chain']
    summary={'time':time.time(),'complete_GUI_trajectories':4,'actual_primary_replies_verified':103,'actual_Flash_replies_verified':70,'Flash_YES':sum(v['decision']=='YES'for v in flashes),'Flash_NO':sum(v['decision']=='NO'for v in flashes),'fresh_global_files_verified':len(gm),'full_history_original_system_generation_and_input_output_tensors_verified':True,'fresh_raw_Flash_single_image_probabilities_and_no_KV_verified':True,'all_original_model_GUI_launcher_identities_exited':True,'controller_request_reply_native_action_and_all_seals_verified':True,'real_NO_fresh_capture_YES_actor_resume_sequences':loops,'real_consecutive_multiple_NO_exercised':False,'baseline_both_whiteouts_native_WAIT_excluded_from_Mirage':True,'primary_input_tokens':sum(v['input_tokens']for v in mains),'primary_output_tokens':sum(v['output_tokens']for v in mains),'primary_native_seconds_sum':sum(v['native_seconds']for v in mains),'Flash_input_tokens':sum(v['input_tokens']for v in flashes),'Flash_elapsed_seconds_sum_including_input_capture':sum(v['elapsed_seconds_with_input_capture']for v in flashes),'recorded_group_eight_GPU_interval':admitted['recorded_group_eight_GPU_interval'],'new_model_GPU_GUI_calls_by_audit':0,'complete_semantic_review':False,'Mirage_reduction_proven':False,'official_scores_are_not_semantic_labels':True,'terminal_rows':[{k:c['terminal'][k]for k in ['run','actor_calls','environment_actions','recaptures','official_reward','infrastructure_failure','cleanup_error']}for c in gui['controllers']]}
    save(dest/'native-and-Flash.json',{'primary':mains,'Flash':flashes})
    save(dest/'Controller-bindings.json',{'bindings':bindings,'reader_source':str(src),'reader_sha256':sha(src)})
    save(dest/'summary.json',summary)
    save(dest/'seal.json',{str(p.relative_to(dest)).replace('\\','/'):sha(p)for p in dest.rglob('*')if p.is_file()})
    save(HERE/'completed-group-audit-current.json',{'root':str(dest),'seal_sha256':sha(dest/'seal.json'),'Mirage_reduction_proven':False})
    print(json.dumps({'completed_audit':str(dest),'primary':103,'Flash':70,'four_GUI':4,'Mirage_reduction_proven':False}),flush=True)


if __name__=='__main__':main()
