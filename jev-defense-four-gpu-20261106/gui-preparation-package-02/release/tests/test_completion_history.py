import tempfile,unittest,json
from pathlib import Path
from test_controller import view,verdict
from defense.core import *

class CompletionHistoryTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def ctl(self,judge):
        c=Controller(judge,Journal(self.root/'run'),'post_only',Limits(full_completion_history=True))
        for i,color in enumerate(['red','blue','green','yellow','purple']):c.remember(view('old'+str(i),color),'old observation')
        return c
    def test_completion_has_all_legally_seen_native_frames_and_no_hidden_image(self):
        original=view('now','white');seen=[]
        def judge(_,v,candidate):
            seen.append(v);self.assertEqual(len(v.images),6)
            self.assertEqual(v.images[0].raw,original.images[0].raw)
            for image,color in zip(v.images[1:],['red','blue','green','yellow','purple']):
                self.assertEqual(image.raw,view(color=color).images[0].raw);self.assertEqual(image.role,'reference')
            self.assertIn('NOT proof',v.messages[-1]['content']);return verdict(v)
        self.ctl(judge).inspect('verify',original,'STOP',{'name':'stop'})
        self.assertEqual(original.messages,view('now','white').messages)
    def test_normal_decisions_keep_the_original_three_reference_bound(self):
        def judge(_,v,candidate):self.assertEqual(len(v.images),4);return verdict(v)
        self.ctl(judge).inspect('verify',view(),'SCROLL',{'name':'scroll'})
    def test_more_history_is_not_automatic_support(self):
        c=self.ctl(lambda _,v,text:verdict(v,'insufficient'))
        result=c.inspect('verify',view(),'STOP',{'name':'stop'})
        self.assertEqual(result['action']['status'],'insufficient')
    def test_full_history_still_deduplicates_current_and_past_frames(self):
        c=self.ctl(lambda *_:None);c.remember(view('duplicate','purple'),'duplicate')
        v=c.reference_view(view('now','purple'),'STOP',all_history=True)
        self.assertEqual(len(v.images),5);self.assertEqual(len({digest(i.raw)for i in v.images}),5)

if __name__=='__main__':unittest.main()
