from django.test import TestCase
from app.models import ImageNeo
from app.VGG_ import VGGNet
import os
dir_path = os.path.dirname(os.path.realpath(__file__))

class BGGTestCase(TestCase):

    def setUp(self):
        print("\n\\|/Testing VGG")

    def test_vgg_extract(self):
        vgg = VGGNet()
        result = vgg.vgg_extract_feat(dir_path + "/face.jpg")
        self.assertEquals(result is None, False)
