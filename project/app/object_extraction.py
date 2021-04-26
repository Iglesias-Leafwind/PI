from imageai.Detection import ObjectDetection
import os

class ObjectExtraction:
    def __init__(self):
        self.detector = ObjectDetection()
        self.detector.setMOdelTypeAsRetinaNet()
        self.detector.setModelPath(...)
        self.detector.loadModel()

    def detect(self, img_path):
        detections = self.detector.detectObjectsFromImage(input_image=img_path)
        print(detections)
