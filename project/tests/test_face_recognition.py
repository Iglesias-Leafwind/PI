from django.test import TestCase
from app.models import ImageNeo
from app.face_recognition import FaceRecognition
import os
dir_path = os.path.dirname(os.path.realpath(__file__))

class FaceRecogTestCase(TestCase):

    def setUp(self):
        print("\n\\|/Testing Face Recognition")

    def test_get_box(self):
        faceRecog = FaceRecognition()
        result = faceRecog.getFaceBoxes(dir_path + "/face.jpg")
        self.assertEqual(result[0] is None, False)
        self.assertEqual(result[1] is None, False)

