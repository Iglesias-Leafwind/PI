import os
import random
from threading import Lock
import imghdr

lock = Lock()

def getImagesPerUri(pathName):
    dirsAndFiles = {}  # key - dir name, value - list of files (imgs)

    if os.path.exists(pathName):
        fileList = os.listdir(pathName)

        for f in fileList:
            f = os.path.join(pathName, f)

            if os.path.isdir(f):
                dirsAndFiles.update(getImagesPerUri(f))

            elif imghdr.what(f) in ['jpeg', 'png', 'bmp']:
                if pathName in dirsAndFiles.keys():
                    dirsAndFiles[pathName].append(os.path.basename(f))
                else:
                    dirsAndFiles[pathName] = [os.path.basename(f)]

    return dirsAndFiles

def getRandomNumber():
    return random.randint(1, 1 << 63)


class ImageFeature:
    def __init__(self, features=None, hash=None):
        self.features = features
        self.hash = int(hash) if hash else None

    def __hash__(self):
        return self.hash

    def __eq__(self, other):
        return self.hash == other.hash

class ImageFeaturesManager:
    def __init__(self):
        self.imageFeatures = []
        self.npFeatures = []