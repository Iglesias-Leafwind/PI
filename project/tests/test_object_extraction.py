## @package tests
#  This will test the object extraction file and its functions
#
#  More details.
from django.test import TestCase
from app.models import ImageNeo
from app.object_extraction import ObjectExtract
import os
img_path = os.path.dirname(os.path.realpath(__file__))
head,_ = os.path.split(img_path)
img_path = os.path.join(head,"app/static/tests") + "/face.jpg"
extractor = ObjectExtract()
## Test Case class.
#
#  More details.
class OETestCase(TestCase):

    ##Setup before each test
    def setUp(self):
        print("\n\\|/Testing Object Detection and Extraction")

    ## Testing object extraction
    #  @param self The object pointer to itself.
    def test_getObj(self):
        objs = extractor.get_objects(img_path)
        self.assertTrue("person" in objs["name"][0])