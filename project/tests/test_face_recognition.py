## @package tests
#  This will test the face recognition file and its functions
#
#  More details.

from django.test import TestCase
from app.models import ImageNeo
from app.face_recognition import FaceRecognition
import os
dir_path = os.path.dirname(os.path.realpath(__file__))
head,_ = os.path.split(dir_path)
dir_path = os.path.join(head,"app/static/tests")
## Test Case class.
#
#  More details.
class FaceRecogTestCase(TestCase):
    ##Setup before each test
    def setUp(self):
        print("\n\\|/Testing Face Recognition")

    ## Testing get face box
    #  @param self The object pointer to itself.
    def test_get_box(self):
        face_recog = FaceRecognition()
        result = face_recog.get_face_boxes(dir_path + "/face.jpg")
        self.assertEqual(result[0] is None, False)
        self.assertEqual(result[1] is None, False)

