## @package tests
#  This will test the processing file and its functions
#
#  More details.
from django.test import TestCase
from app.models import ImageNeo
from app.processing import filter_sentence,dhash,get_exif,generate_thumbnail
import cv2
import os
img_path = os.path.dirname(os.path.realpath(__file__))
head,_ = os.path.split(img_path)
img_path = os.path.join(head,"app/static/tests") + "/face.jpg"
## Test Case class.
#
#  More details.
class ProcessingTestCase(TestCase):

    ##Setup before each test
    def setUp(self):
        print("\n\\|/Testing Processing")

    ## Testing filter sentence filters words into "acceptable words"
    #  @param self The object pointer to itself.
    def test_filter(self):
        result = filter_sentence("hello world I to kms good dead hnb lll notaword gfffffffffffffffffffffff")
        expected = ['hello', 'world', 'good', 'dead', 'notaword']
        self.assertEquals(expected,result)

    ## Testing image to hash
    #  @param self The object pointer to itself.
    def test_hash(self):
        img = cv2.imread(img_path)
        hashcode = dhash(img)
        expected = 7288338847964571648
        self.assertEquals(expected,hashcode)

    ## Testing exif extraction
    #  @param self The object pointer to itself.
    def test_exif(self):
        exif = get_exif(img_path)
        expected = {'height': 1080, 'width': 2160}
        self.assertEquals(expected,exif)

    ## Testing creation of a image thumbnail
    #  @param self The object pointer to itself.
    def test_thumbnail(self):
        read_image = cv2.imread(img_path)
        image_hash = dhash(read_image)
        thumbnail_path = generate_thumbnail(img_path, image_hash)
        self.assertTrue(cv2.imread(thumbnail_path) is not None)
        os.remove(thumbnail_path)
        self.assertTrue(cv2.imread(thumbnail_path) is None)