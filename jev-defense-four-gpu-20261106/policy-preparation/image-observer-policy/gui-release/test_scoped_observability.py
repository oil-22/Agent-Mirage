import copy,unittest
from types import SimpleNamespace
from scoped_observability import check_explicit_image_sources as check

class SourceBounds(unittest.TestCase):
    def setUp(self):self.v=SimpleNamespace(images=[SimpleNamespace(role='current')])
    def test_absent_source_rejected(self):self.assertTrue(check({'reason':'The button is visible in reference image 1.'},self.v)['reject'])
    def test_missing_source_predicate_rejected(self):self.assertTrue(check({'reason':'Image index 2 shows pagination.'},self.v)['reject'])
    def test_current_source_permitted(self):self.assertFalse(check({'reason':'Image 0 shows the footer.'},self.v)['reject'])
    def test_wrong_role_rejected(self):self.assertTrue(check({'reason':'The footer is visible in reference image 0.'},self.v)['reject'])
    def test_real_reference_permitted(self):
        self.v.images.append(SimpleNamespace(role='reference'));self.assertFalse(check({'reason':'It is visible in reference image 1.'},self.v)['reject'])
    def test_denial_not_rejected(self):self.assertFalse(check({'reason':'No reference image 1 is supplied.'},self.v)['reject'])
    def test_quoted_report_abstains(self):self.assertFalse(check({'reason':'The candidate says "image 1 shows a button".'},self.v)['reject'])
    def test_unrecognized_source_wording_abstains(self):self.assertFalse(check({'reason':'There might be an old screenshot elsewhere.'},self.v)['reject'])
    def test_nested_description_checked(self):self.assertTrue(check({'claims':[{'evidence':[{'description':'Image 5 shows a title.'}]}]},self.v)['reject'])
    def test_original_values_unchanged(self):
        x={'action':{'status':'supported','reason':'Image 3 shows a button.'}};old=copy.deepcopy(x);check(x,self.v);self.assertEqual(x,old)
    def test_number_without_source_not_checked(self):self.assertFalse(check({'reason':'There are 50 listings.'},self.v)['reject'])

if __name__=='__main__':unittest.main()
