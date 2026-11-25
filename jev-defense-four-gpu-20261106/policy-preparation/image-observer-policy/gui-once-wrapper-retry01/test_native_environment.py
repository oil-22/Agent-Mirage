import ast,hashlib,json
from pathlib import Path
import unittest
import native_environment as n

BASE=Path(__file__).resolve().parent


class NativeEnvBoundaries(unittest.TestCase):
    def test_exact_successful_parent_environment(self):
        source=BASE/'successful_parent_environment_transport.py'
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),n.PARENT_PREFLIGHT_SOURCE_SHA256)
        tree=ast.parse(source.read_text(encoding='utf8'));rows=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Call)and ast.unparse(node.func)=='os.environ.update':
                rows.append({k.arg:ast.literal_eval(k.value)for k in node.keywords})
        self.assertEqual(rows,[n.NATIVE_ENV])
    def test_original_gui_source_unchanged(self):
        release=BASE.parent/'gui-release-04/run_image_observer_vwa_validation.py'
        self.assertEqual(hashlib.sha256(release.read_bytes()).hexdigest(),
            '436c83293f557a8a3a3276bea32d28b20884110cc63b57dc3f743a15791a61f9')
    def test_wrapper_passes_full_env_to_child(self):
        tree=ast.parse((BASE/'gui_once.py').read_text(encoding='utf8'))
        rows=[node for node in ast.walk(tree)if isinstance(node,ast.Assign)and
            any(isinstance(t,ast.Name)and t.id=='env'for t in node.targets)]
        self.assertEqual(len(rows),1);self.assertIsInstance(rows[0].value,ast.Dict)
        unpack=[ast.unparse(v)for k,v in zip(rows[0].value.keys,rows[0].value.values)if k is None]
        self.assertEqual(unpack,['os.environ','NATIVE_ENV'])
    def test_no_auxiliary_model_local_gpu(self):self.assertEqual(n.NATIVE_ENV['CUDA_VISIBLE_DEVICES'],'')
    def test_native_browser_path_preserved(self):
        self.assertEqual(n.NATIVE_ENV['PLAYWRIGHT_BROWSERS_PATH'],'/data/researcher/playwright-browsers')
    def test_new_validation_has_no_task_action_or_scoring_call(self):
        tree=ast.parse((BASE/'validate_native_environment.py').read_text(encoding='utf8'))
        calls=[ast.unparse(v.func)for v in ast.walk(tree)if isinstance(v,ast.Call)]
        self.assertNotIn('env.step',calls);self.assertNotIn('env.reset',calls);self.assertNotIn('scorer',calls)
        self.assertNotIn('renew_comb',calls);self.assertNotIn('g.run',calls)


if __name__=='__main__':unittest.main()
