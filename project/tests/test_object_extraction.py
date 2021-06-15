from django.test import TestCase
from app.models import ImageNeo
from app.object_extraction import ObjectExtract
import os
img_path = os.path.dirname(os.path.realpath(__file__))
head,_ = os.path.split(img_path)
img_path = os.path.join(head,"app/static/tests") + "/face.jpg"
extractor = ObjectExtract()
class OETestCase(TestCase):

    def setUp(self):
        print("\n\\|/Testing Object Detection and Extraction")

    def test_getObj(self):
        objs = extractor.get_objects(img_path)
        self.assertTrue("person" in objs["name"][0])