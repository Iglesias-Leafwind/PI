import torch
# https://github.com/ultralytics/yolov5/issues/36

class ObjectExtract:
    def __init__(self):
        # exige que o utilizador esteja ligado à net da primeira vez (ele faz uns downloads)
        self.model = torch.hub.load('ultralytics/yolov5', 'yolov5s')

        """ # exemplo de como se faz pra n ter de tar ligado à net
        path = '/some/local/path/pytorch/vision'
        model = torch.hub.load(path, 'resnet50', pretrained=True)
        """

    def get_objects(self, image_path):
        results = self.model(image_path)

        res = results.pandas().xyxy[0][['confidence', 'name']]
        return res