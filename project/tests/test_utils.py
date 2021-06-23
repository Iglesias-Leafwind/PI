## @package tests
#  This will test the utils file and its functions
#
#  More details.
from django.test import TestCase
from app.models import ImageNeo
from app.utils import get_images_per_uri,get_random_number
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
        print("\n\\|/Testing utils")

    ## Testing the random number generator
    #  @param self The object pointer to itself.
    def test_random_num(self):
        self.assertTrue(1 <= get_random_number() <= (1 << 63))
    ## Testing if path gives us all images in this path
    #  @param self The object pointer to itself.
    def test_images_in_uri(self):
        dirs_and_files = get_images_per_uri(dir_path)
        self.assertEquals(dirs_and_files[dir_path],["face.jpg"])