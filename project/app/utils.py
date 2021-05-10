import os
import random
import cv2


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

def getFaceThumbnail(img, box, save_in=None):
    top, right, bottom, left= box
    # img = cv2.imread(img_path)
    cropimg = img[top:bottom, left:right]
    cropimg = cv2.resize(cropimg, (50,50))
    if save_in is not None:
        # assumindo que a imagem tem sempre uma extensao no fim
        # (ou seja, tem um '.png' ou '.'+ qq outra extensao no fim
        # new_path = img_path.split('.')[-2] + '_face.' + img_path.split('.')[-1]
        cv2.imwrite(save_in, cropimg)
    return cropimg



class ImageFeature:
    def __init__(self, features=None, hash=None):
        self.features = features
        self.hash = hash

    def __hash__(self):
        return hash(self.hash)

    def __eq__(self, other):
        return self.hash == other.hash
