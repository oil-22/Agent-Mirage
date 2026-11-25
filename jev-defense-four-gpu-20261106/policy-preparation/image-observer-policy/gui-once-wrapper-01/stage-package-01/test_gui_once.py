"""CPU integrity boundaries; no private task, transport, model or GUI calls."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import gui_once as g


class Boundaries(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.source = self.root/'source.json'; g.write(self.source, {'actual':'fixture'})
        self.owner = {**dict.fromkeys(g.OWNERSHIP_FIELDS, True), 'collected_time':1000,
            'physical_gpu_uuids':{str(i):'GPU-'+str(i) for i in range(4,8)},
            'actual_allowed_pids':[31,32],
            'source_evidence':[{'path':str(self.source),'sha256':g.sha(self.source)}]}
        self.plan = {'queue':[{'run_id':'r'+str(i),'observer_enabled':i%2==1} for i in range(4)]}
        self.state = {'phase':'ready','active':None,'next_run_index':0,
            'runs':{q['run_id']:{'status':'not_started','last_decision_index':0,
                'calls':{'actor':0,'judge':0,'observe':0}} for q in self.plan['queue']}}
        self.primary = {'role':'primary','phase':'ready_gui','stage':'online_ready',
            'exclusive_task_group':True,'actual_allowed_pids':[32,31],
            'physical_gpu_uuids':self.owner['physical_gpu_uuids'],'state':copy.deepcopy(self.state)}
        self.observer = {**copy.deepcopy(self.primary),'role':'pplx_flash'}

    def tearDown(self): self.tmp.cleanup()
    def rejects_owner(self, value, now=1001):
        with self.assertRaises(RuntimeError): g.ownership(value, now)
    def rejects_health(self, primary=None, observer=None):
        with self.assertRaises(RuntimeError):
            g.validate_health(primary or self.primary, observer or self.observer, self.owner, self.plan)

    def test_valid_bound_owner(self): g.ownership(self.owner, 1001)
    def test_stale_owner(self): self.rejects_owner(self.owner,1121)
    def test_future_owner(self): self.rejects_owner(self.owner,999)
    def test_incomplete_gate(self):
        obj=copy.deepcopy(self.owner);obj[g.OWNERSHIP_FIELDS[0]]=False;self.rejects_owner(obj)
    def test_missing_source(self):
        obj=copy.deepcopy(self.owner);obj['source_evidence']=[];self.rejects_owner(obj)
    def test_changed_source(self):
        self.source.write_text('{}');self.rejects_owner(self.owner)
    def test_wrong_gpu(self):
        obj=copy.deepcopy(self.owner);obj['physical_gpu_uuids']['3']=obj['physical_gpu_uuids'].pop('4');self.rejects_owner(obj)
    def test_duplicate_gpu_uuid(self):
        obj=copy.deepcopy(self.owner);obj['physical_gpu_uuids']['4']=obj['physical_gpu_uuids']['5'];self.rejects_owner(obj)
    def test_one_peer(self):
        obj=copy.deepcopy(self.owner);obj['actual_allowed_pids']=[31];self.rejects_owner(obj)
    def test_duplicate_peer(self):
        obj=copy.deepcopy(self.owner);obj['actual_allowed_pids']=[31,31];self.rejects_owner(obj)
    def test_valid_actual_health(self): g.validate_health(self.primary,self.observer,self.owner,self.plan)
    def test_missing_full_resource_health(self):
        obj=copy.deepcopy(self.primary);obj.pop('exclusive_task_group');self.rejects_health(primary=obj)
    def test_loading_peer(self):
        obj=copy.deepcopy(self.observer);obj['phase']='loading_peer';self.rejects_health(observer=obj)
    def test_foreign_peer(self):
        obj=copy.deepcopy(self.primary);obj['actual_allowed_pids']=[31,999];self.rejects_health(primary=obj)
    def test_reallocated_card(self):
        obj=copy.deepcopy(self.primary);obj['physical_gpu_uuids']['7']='other';self.rejects_health(primary=obj)
    def test_started_queue(self):
        obj=copy.deepcopy(self.primary);obj['state']['next_run_index']=1;self.rejects_health(primary=obj)
    def test_active_trajectory(self):
        obj=copy.deepcopy(self.primary);obj['state']['active']='r0';self.rejects_health(primary=obj)
    def test_spent_budget(self):
        obj=copy.deepcopy(self.observer);obj['state']['runs']['r0']['calls']['observe']=1;self.rejects_health(observer=obj)
    def test_wrong_run_order(self):
        obj=copy.deepcopy(self.primary);obj['state']['runs']=dict(reversed(list(obj['state']['runs'].items())));self.rejects_health(primary=obj)
    def test_bound_command_only_new_runner(self):
        argv=g.argv_for(Path('/package'),Path('/linked'),Path('/newbatch'))
        self.assertEqual(argv[2],str(Path('/package')/'release/run_image_observer_vwa_validation.py'))
        self.assertEqual(argv[-1],'http://127.0.0.1:28427')
        self.assertNotIn('--resume',argv);self.assertNotIn('--only-runs',argv)
    def test_exclusive_claim(self):
        p=self.root/'claim';g.write(p,{'once':True})
        with self.assertRaises(FileExistsError):g.write(p,{'again':True})
    def test_sha_tamper(self):
        with self.assertRaises(RuntimeError):g.bound(self.source,'0'*64)
    def test_empty_batch_not_semantic_zero(self):
        obj=g.terminal_summary(self.root,self.plan)
        self.assertFalse(obj['all_four_complete']);self.assertTrue(obj['semantic_Mirage_review_pending'])
    def test_repeated_attempts_rejected(self):
        run=self.root/'runs/r0';(run/'attempt-1').mkdir(parents=True);(run/'attempt-2').mkdir()
        with self.assertRaises(RuntimeError):g.terminal_summary(self.root,self.plan)
    def test_wrong_pointer_rejected(self):
        run=self.root/'runs/r0';at=run/'attempt-1';at.mkdir(parents=True)
        g.write(at/'complete.json',{});g.write(run/'complete.json',{'attempt':str(at),'sha256':'0'*64})
        with self.assertRaises(RuntimeError):g.terminal_summary(self.root,self.plan)
    def event(self,kind,data,seq=0,previous='0'*64):
        obj={'seq':seq,'previous':previous,'time':1000,'kind':kind,'data':data}
        obj['sha256']=hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return json.dumps(obj).encode()+b'\n'
    def events_path(self):
        path=self.root/'runs/r0/attempt-1/events.jsonl';path.parent.mkdir(parents=True);return path
    def test_monitor_normal_packet(self):
        path=self.events_path();path.write_bytes(self.event('actor_observer_packet',{'status':'measured'}))
        self.assertIsNone(g.ObserverFailureMonitor().scan(self.root))
    def test_monitor_technical_failure(self):
        path=self.events_path();path.write_bytes(self.event('actor_observer_packet',{'status':'technical_failure'}))
        self.assertTrue(g.ObserverFailureMonitor().scan(self.root)['request_safe_decision_boundary_stop'])
    def test_monitor_partial_line(self):
        path=self.events_path();raw=self.event('actor_observer_packet',{'status':'technical_failure'})
        path.write_bytes(raw[:30]);monitor=g.ObserverFailureMonitor();self.assertIsNone(monitor.scan(self.root))
        with path.open('ab') as handle:handle.write(raw[30:])
        self.assertEqual(monitor.scan(self.root)['status'],'technical_failure')
    def test_monitor_chain_corruption(self):
        path=self.events_path();path.write_bytes(self.event('actor_observer_packet',{'status':'measured'},seq=2))
        with self.assertRaises(RuntimeError):g.ObserverFailureMonitor().scan(self.root)
    def test_monitor_journal_truncation(self):
        path=self.events_path();path.write_bytes(self.event('actor_observer_packet',{'status':'measured'}))
        monitor=g.ObserverFailureMonitor();monitor.scan(self.root);path.write_bytes(b'')
        with self.assertRaises(RuntimeError):monitor.scan(self.root)
    def test_manifest_exhaustive(self):
        root=self.root/'terminal';root.mkdir();g.write(root/'data.json',{'raw':'bound'})
        g.write(root/'seal.json',{'data.json':g.sha(root/'data.json')})
        g.flat_manifest(root,root/'seal.json',g.sha(root/'seal.json'))
        g.write(root/'omitted.json',{})
        with self.assertRaises(RuntimeError):g.flat_manifest(root,root/'seal.json',g.sha(root/'seal.json'))


if __name__=='__main__':unittest.main()
