"""Source/CPU helper checks. Never call main, prepare, health or background."""
import ast,copy,hashlib,json,tempfile,unittest
from pathlib import Path
import prepare_bound_once as p

class ControlHelperTests(unittest.TestCase):
    def resource(self,source):
        return {'group':p.GROUP,'reviewed_spec_sha256':p.REVIEWED_SPEC_SHA,'decoder_layer_counts':[14,22,22,6],
            'allocator':'expandable_segments:True',**{key:True for key in p.RESOURCE_FLAGS},
            'source_evidence':[{'path':str(source),'sha256':p.sha(source)}]}
    def test_resource_requires_actual_new_group_spec_and_source(self):
        with tempfile.TemporaryDirectory()as tmp:
            f=Path(tmp)/'loaded.json';f.write_text('{"loaded":true}')
            p.validate_resource(self.resource(f))
            for key,value in [('group','old-group'),('reviewed_spec_sha256','0'*64),
                ('decoder_layer_counts',[14.0,22,22,6]),('allocator',''),('source_evidence',[])]:
                obj=self.resource(f);obj[key]=value
                with self.assertRaises(RuntimeError):p.validate_resource(obj)
    def test_missing_or_false_actual_resource_flag_rejected(self):
        with tempfile.TemporaryDirectory()as tmp:
            f=Path(tmp)/'source';f.write_text('original')
            for key in p.RESOURCE_FLAGS:
                obj=self.resource(f);obj[key]=False
                with self.assertRaises(RuntimeError):p.validate_resource(obj)
    def test_modified_source_rejected(self):
        with tempfile.TemporaryDirectory()as tmp:
            f=Path(tmp)/'source';f.write_text('original');obj=self.resource(f);f.write_text('changed')
            with self.assertRaises(RuntimeError):p.validate_resource(obj)
    def test_template_bindings_preserved_exactly(self):
        old={'launch_ready':False,'evidence':{'original':{'path':'old.json','sha256':'a'*64}}}
        result=p.make_bindings(old,{'path':'resource','sha256':'b'*64},{'path':'owner','sha256':'c'*64})
        self.assertEqual(result['original'],old['evidence']['original']);self.assertEqual(len(result),3)
        self.assertNotIn('ownership_transport',old['evidence'])
    def test_template_may_not_already_contain_fresh_or_ready_flags(self):
        for template in [{'launch_ready':True,'evidence':{}},{'launch_ready':False,'evidence':{'ownership_transport':{}}}]:
            with self.assertRaises(RuntimeError):p.make_bindings(template,{}, {})
    def test_helpers_have_no_HTTP_or_model_calls(self):
        here=Path(__file__).resolve().parent
        for name in ('prepare_bound_once.py','background_three_once.py'):
            tree=ast.parse((here/name).read_text(encoding='utf8'))
            calls=[x for x in ast.walk(tree)if isinstance(x,ast.Call)]
            methods={x.func.attr for x in calls if isinstance(x.func,ast.Attribute)}
            self.assertTrue(methods.isdisjoint({'fetch_health','urlopen','post','generate','forward'}))
        prep=ast.parse((here/'prepare_bound_once.py').read_text(encoding='utf8'))
        self.assertFalse(any(isinstance(x,ast.Call)and isinstance(x.func,ast.Attribute)and x.func.attr=='Popen'for x in ast.walk(prep)))
        back=ast.parse((here/'background_three_once.py').read_text(encoding='utf8'))
        self.assertEqual(sum(isinstance(x,ast.Call)and isinstance(x.func,ast.Attribute)and x.func.attr=='Popen'for x in ast.walk(back)),1)
    def test_fixed_package_wrapper_and_new_roots(self):
        self.assertEqual(p.PACKAGE_SHA,'1dc3568fe581574856ee7457982103d1d50a3348179bec91687c0e32767bbd44')
        self.assertEqual(p.WRAPPER_SHA,'e660bd664ca94355a3d1109611dc18aa8069abd77f92c9dcb18265477f58792d')
        self.assertIn('three-01',str(p.BATCH));self.assertNotIn('retry01',str(p.BATCH))

if __name__=='__main__':unittest.main()
