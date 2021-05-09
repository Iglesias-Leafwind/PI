from django.test import TestCase
from app.models import ImageNeo
from app.utils import getImagesPerUri,getRandomNumber
import os
dir_path = os.path.dirname(os.path.realpath(__file__))

class BGGTestCase(TestCase):

    def setUp(self):
        print("\n\\|/Testing utils")

    def test_random_num(self):
        self.assertTrue(1 <= getRandomNumber() <= (1 << 63))
    def test_images_in_uri(self):
        #dirsAndFiles = {}  # key - dir name, value - list of files (imgs)
        dirsAndFiles = getImagesPerUri(dir_path)
        self.assertEquals(dirsAndFiles[dir_path],["face.jpg"])