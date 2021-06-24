## @package tests
#  This will test the vgg file and its functions
#
#  More details.
from django.test import TestCase
from app.models import ImageNeo
from app.VGG_ import VGGNet
import os
dir_path = os.path.dirname(os.path.realpath(__file__))
head,_ = os.path.split(dir_path)
dir_path = os.path.join(head,"app/static/tests")
## Test Case class.
#
#  More details.
class BGGTestCase(TestCase):

    ##Setup before each test
    def setUp(self):
        print("\n\\|/Testing VGG")

    ## Testing image feature extraction of a image reserved for testing
    #  @param self The object pointer to itself.
    def test_vgg_extract(self):
        vgg = VGGNet()
        result = vgg.vgg_extract_feat(dir_path + "/face.jpg")
        self.assertEquals(result is None, False)
