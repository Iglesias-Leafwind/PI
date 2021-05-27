import os
import random
import cv2
from PIL import Image
from threading import Lock
import imghdr

showDict = {'verified':False, 'unverified':True}
lock = Lock()
faceRecLock= Lock()

def getImagesPerUri(pathName):
    dirsAndFiles = {}  # key - dir name, value - list of files (imgs)

    if os.path.exists(pathName):
        fileList = os.listdir(pathName)

        for f in fileList:
            f = os.path.join(pathName, f)

            if os.path.isdir(f):
                dirsAndFiles.update(getImagesPerUri(f))
            else:
                image_type = imghdr.what(f)
                if f.endswith('jpg') or f.endswith('jpeg') or f.endswith('png') or image_type in ['jpeg', 'png', 'bmp']:
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

def get_and_save_thumbnail(img_path, side_pixels, save_path):
    pil_img = Image.open(img_path)

    crop_side = min(pil_img.size)
    img_width, img_height = pil_img.size
    thumb = pil_img.crop(((img_width - crop_side) // 2,
                         (img_height - crop_side) // 2,
                         (img_width + crop_side) // 2,
                         (img_height + crop_side) // 2))
    thumb = thumb.resize((side_pixels, side_pixels), Image.LANCZOS)
    thumb.save(save_path)






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