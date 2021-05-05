import os
import random


def getImagesPerUri(pathName):
    dirsAndFiles = {}  # key - dir name, value - list of files (imgs)

    if os.path.exists(pathName):
        fileList = os.listdir(pathName)

        for f in fileList:
            f = os.path.join(pathName, f)

            if os.path.isdir(f):
                dirsAndFiles.update(getImagesPerUri(f))

            elif f.endswith(".jpg") or f.endswith(".png"):
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
        self.hash = hash

    def __hash__(self):
        return hash(self.hash)

    def __eq__(self, other):
        return self.hash == other.hash
