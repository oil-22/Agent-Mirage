"""Regression for the preserved real non-square-image mixed-unit failure."""
import io,unittest
from PIL import Image
from defense.core import PublicView,VisibleImage,validate_point,ValidationError

class PointUnitFailureTests(unittest.TestCase):
    def setUp(self):
        raw=io.BytesIO();Image.new('RGB',(1280,720),'white').save(raw,format='PNG')
        self.view=PublicView('029-obs035',[],(VisibleImage(raw.getvalue(),'current'),),'','',0)
        self.query={'x':523,'y':679}
    def result(self,box,units):
        return {'kind':'button','visible_text':'1','reason':'fixture geometry only',
            'evidence':[{'observation_id':'029-obs035','image_index':0,'coordinate_space':units,
                'box_xyxy':box,'description':'test region'}]}
    def test_original_mixed_unit_responses_still_rejected(self):
        for box in [[655,655,700,710],[650,650,705,715]]:
            with self.subTest(box=box),self.assertRaisesRegex(ValidationError,'Point not inside'):
                validate_point(self.result(box,'normalized_1000'),self.view,self.query)
    def test_two_consistent_unit_descriptions_accept_same_actual_button(self):
        for box,units in [([654,470,694,510],'pixels'),([510.9375,652.7777777778,542.1875,708.3333333333],'normalized_1000')]:
            with self.subTest(units=units):
                value=validate_point(self.result(box,units),self.view,self.query)
                ev=value['evidence'][0];region=ev.get('resolved_box_pixels',ev['box_xyxy'])
                self.assertLessEqual(region[0],669.44);self.assertGreaterEqual(region[2],669.44)
                self.assertLessEqual(region[1],488.88);self.assertGreaterEqual(region[3],488.88)

if __name__=='__main__':unittest.main()
