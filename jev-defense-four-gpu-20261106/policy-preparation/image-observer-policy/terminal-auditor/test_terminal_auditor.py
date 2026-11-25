"""Synthetic CPU integrity fixtures only, never model/GUI semantic controls."""
import base64,copy,io,json,tempfile,unittest
from pathlib import Path
from PIL import Image
from audit_gui_terminals import *


def put(path,obj):path.write_bytes(canonical(obj))


def events(path,rows):
    prev='0'*64;lines=[]
    for i,(kind,data)in enumerate(rows):
        obj={'seq':i,'previous':prev,'time':0,'kind':kind,'data':data};obj['sha256']=sha(canonical(obj));prev=obj['sha256'];lines.append(json.dumps(obj))
    path.write_text('\n'.join(lines),encoding='utf8')


class Tests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()

    def test_seal_detects_mutated_original_file(self):
        p=self.root/'original';p.write_bytes(b'raw image bytes');m=self.root/'seal.json'
        put(m,{'original':sha(p.read_bytes())});digest=sha(m.read_bytes())
        manifest(self.root,m,digest)
        p.write_bytes(b'modified')
        with self.assertRaisesRegex(AuditError,'mismatch'):manifest(self.root,m,digest)

    def test_terminal_manifest_must_cover_all_files(self):
        (self.root/'a').write_bytes(b'a');m=self.root/'seal.json';put(m,{'a':sha(b'a')});digest=sha(m.read_bytes())
        (self.root/'unsealed').write_bytes(b'b')
        with self.assertRaisesRegex(AuditError,'omits'):manifest(self.root,m,digest)

    def test_manifest_cannot_escape_root(self):
        m=self.root/'seal.json';put(m,{'../foreign':'0'*64})
        with self.assertRaisesRegex(AuditError,'escaped'):manifest(self.root,m,sha(m.read_bytes()))

    def test_event_chain_valid_then_changed_body_rejected(self):
        p=self.root/'events.jsonl';events(p,[('candidate',{'text':'original'}),('decision_blocked',{'reason':'x'})])
        self.assertEqual(len(chain(p)[0]),2)
        p.write_text(p.read_text().replace('original','edited'),encoding='utf8')
        with self.assertRaisesRegex(AuditError,'body SHA'):chain(p)

    def test_event_chain_cannot_reorder_events(self):
        p=self.root/'events.jsonl';events(p,[('a',{}),('b',{})]);lines=p.read_text().splitlines()
        p.write_text('\n'.join(reversed(lines)),encoding='utf8')
        with self.assertRaisesRegex(AuditError,'sequence'):chain(p)

    def test_actual_public_pixels_source_required(self):
        data=io.BytesIO();Image.new('RGB',(8,6),'white').save(data,format='PNG');raw=data.getvalue();digest=sha(raw)
        (self.root/(digest+'.image')).write_bytes(raw)
        public={'images':[{'sha256':digest,'size':[8,6],'role':'current','decoded':True}],
            'messages':[{'role':'user','content':[{'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(raw).decode()}}]}]}
        public_images(public,self.root)
        public['images'][0]['size']=[4,3]
        with self.assertRaisesRegex(AuditError,'metadata'):public_images(public,self.root)

    def test_detector_semantics_not_automatically_used_as_gold(self):
        candidate='I will scroll UP.\n<action>{"type":"scroll","direction":"down"}</action>'
        proposal={'name':'scroll','parsed':True,'executor_fallback_wait':False,'payload':{'type':'scroll','direction':'down'}}
        accepted_candidate_binding(candidate,proposal)
        changed=copy.deepcopy(proposal);changed['payload']['direction']='up'
        with self.assertRaisesRegex(AuditError,'differs'):accepted_candidate_binding(candidate,changed)

    def primary_generation(self):
        payload={'operation':'actor','body':{'messages':[{'role':'user','content':'COMPLETE original history'}]}}
        trace=[{'tensors':{'input_ids':{'shape':[1,3],'values':[[1,2,3]]}}}]
        put(self.root/'forward-trace.json',trace)
        gen={'input_ids':[1,2,3],'request_messages_sha256':sha(canonical(payload['body']['messages'])),
            'generation_config':{'max_new_tokens':2048,'eos_token_id':[9]},'hit_output_cap':False,
            'generated_ids':[4,9],'text':'same reply'}
        put(self.root/'generation.json',gen)
        response={'forward_trace_sha256':sha((self.root/'forward-trace.json').read_bytes()),'text':'same reply'}
        return payload,gen,response

    def test_primary_actual_input_ids_and_full_history_bind(self):
        payload,gen,response=self.primary_generation();native_forward(self.root,payload,response,'primary')
        payload['body']['messages'][0]['content']='truncated'
        with self.assertRaisesRegex(AuditError,'Full native generation'):native_forward(self.root,payload,response,'primary')

    def test_primary_cap_or_nonEOS_is_not_completed_generation(self):
        payload,gen,response=self.primary_generation();gen['generated_ids']=[4,5];put(self.root/'generation.json',gen)
        with self.assertRaisesRegex(AuditError,'EOS'):native_forward(self.root,payload,response,'primary')
        gen['generated_ids']=[4,9];gen['hit_output_cap']=True;put(self.root/'generation.json',gen)
        with self.assertRaisesRegex(AuditError,'capped'):native_forward(self.root,payload,response,'primary')

    def test_service_reply_cannot_bind_wrong_wire(self):
        request=self.root/'service';request.mkdir();raw=wire({'request_id':'id','trajectory_id':'run'})
        (request/'request.json').write_bytes(raw);put(request/'response.json',{'external_wire_sha256':'wrong'})
        put(request/'seal.json',{p.name:sha(p.read_bytes())for p in request.iterdir()if p.is_file()})
        with self.assertRaisesRegex(AuditError,'external wire'):service_index([{'path':str(request),'seal_sha256':sha((request/'seal.json').read_bytes()),'role':'primary'}])

    def test_actual_admission_role_budget_overrun_is_rejected(self):
        item={'run_id':'r','observer_enabled':False};index={};rows=[]
        begin={'trajectory_id':'r','request_id':'begin'};raw=wire(begin);digest=sha(raw)
        index[digest]={'raw':raw,'envelope':begin,'used':False,'response':{},'path':self.root}
        rows.append(('online_run_begin_request',{'body':begin,'wire_utf8':raw.decode(),'wire_sha256':digest}))
        public={'observation_id':'o','messages':[],'images':[],'recent_action':'','execution_feedback':'','observed_at':0}
        rows.append(('verifier_request',{'system':'strict','candidate':None,'public':public}))
        for i in range(1,142):
            payload={'operation':'judge','system':'strict','candidate':None,'view':public}
            env={'trajectory_id':'r','decision_index':1,'attempt_index':i,'request_id':str(i),'payload':payload}
            raw=wire(env);digest=sha(raw)
            index[digest]={'raw':raw,'envelope':env,'used':False,'response':None,'path':self.root}
            rows.append(('actual_primary_wire_request',{'body':env,'wire_utf8':raw.decode(),'wire_sha256':digest}))
        events(self.root/'events.jsonl',rows)
        with self.assertRaisesRegex(AuditError,'role budget exceeded'):audit_attempt(self.root,item,index)

    def test_duplicate_trajectory_begin_is_rejected(self):
        rows=[];index={}
        for name in ['first','second']:
            env={'trajectory_id':'r','request_id':name};raw=wire(env);digest=sha(raw)
            index[digest]={'raw':raw,'envelope':env,'used':False,'response':{},'path':self.root}
            rows.append(('online_run_begin_request',{'body':env,'wire_utf8':raw.decode(),'wire_sha256':digest}))
        events(self.root/'events.jsonl',rows)
        with self.assertRaisesRegex(AuditError,'Duplicate/out-of-order'):audit_attempt(self.root,{'run_id':'r','observer_enabled':False},index)

    def observer(self):
        out=io.BytesIO();Image.new('RGB',(8,6),'white').save(out,format='PNG');raw=out.getvalue();digest=sha(raw)
        payload={'request_id':'id','image_base64':base64.b64encode(raw).decode(),'image_sha256':digest,
            **contract(),'provenance':{'observation_id':'o','image_sha256':digest}}
        trace=[{'tensors':{'input_ids':{'shape':[1,2],'values':[[1,2]]},'pixel_values':{'shape':[1,3]},'image_grid_thw':{'shape':[1,3]}}},
               {'raw_readout':{'shape':[2,255]}}]
        put(self.root/'forward-trace.json',trace);(self.root/'original.image').write_bytes(raw)
        response={'forward_trace_sha256':sha((self.root/'forward-trace.json').read_bytes()),'image_sha256':digest}
        return payload,response

    def test_observer_cannot_receive_hidden_task_field(self):
        payload,response=self.observer();payload['task']='forbidden task'
        with self.assertRaisesRegex(AuditError,'unknown fields'):native_forward(self.root,payload,response,'pplx_flash')

    def test_observer_requires_actual_three_marker_readout(self):
        payload,response=self.observer()
        with self.assertRaisesRegex(AuditError,'three raw native marker'):native_forward(self.root,payload,response,'pplx_flash')

if __name__=='__main__':unittest.main(verbosity=2)
