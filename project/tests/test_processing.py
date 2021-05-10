from django.test import TestCase
from app.models import ImageNeo
from app.processing import *
import cv2
import os
img_path = os.path.dirname(os.path.realpath(__file__)) + "/face.jpg"
class ProcessingTestCase(TestCase):

    def setUp(self):
        print("\n\\|/Testing Processing")

    def test_filter(self):
        result = filterSentence("hello world I to kms good dead hnb lll notaword gfffffffffffffffffffffff")
        expected = ['hello', 'world', 'good', 'dead', 'notaword']
        self.assertEquals(expected,result)

    def test_hash(self):
        img = cv2.imread(img_path)
        hashcode = dhash(img)
        expected = 7288338847964571648
        self.assertEquals(expected,hashcode)

    def test_exif(self):
        exif = getExif(img_path)
        expected = {'height': 1080, 'width': 2160}
        self.assertEquals(expected,exif)

    def test_thumbnail(self):
        read_image = cv2.imread(img_path)
        hash = dhash(read_image)
        thumbnailPath = generateThumbnail(img_path, hash)
        self.assertTrue(cv2.imread(thumbnailPath) is not None)
        os.remove(thumbnailPath)
        self.assertTrue(cv2.imread(thumbnailPath) is None)