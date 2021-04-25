import os


def get_imlist(path):
    return [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.jpg')]


class ImageFeature:
    def __init__(self, name, features=None):
        self.name = name
        self.features = features

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name
