import os
import random
import cv2
from PIL import Image
from threading import Lock
import imghdr

from app.models import Tag, ImageNeo, ImageES
from manage import es

showDict = {'verified':False, 'unverified':True}
lock = Lock()
faceRecLock= Lock()
ocrLock= Lock()


searchFilterOptions = {
    'automatic': True, # isto sao os objects
    'manual': True,
    'folder_name': True,
    'people': True,
    'text': True,
    'exif': True,
    'places' : True,
    'breeds': True
}

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
                if f.endswith('jpg') or f.endswith('jpeg') or f.endswith('png') or f.endswith('JPG') or image_type in ['jpeg', 'png', 'bmp']:
                    if pathName in dirsAndFiles.keys():
                        dirsAndFiles[pathName].append(os.path.basename(f))
                    else:
                        dirsAndFiles[pathName] = [os.path.basename(f)]
                else:
                    print(f, image_type)
    return dirsAndFiles

def getRandomNumber():
    return random.randint(1, 1 << 63)


def addTagWithOldTag(hashcode, tagName, oldTagName, oldTagSource):
    t = Tag.nodes.get_or_none(name=tagName)
    i = ImageNeo.nodes.get_or_none(hash=hashcode)
    if i is None:
        return
    if t is None:
        t = Tag(name=tagName).save()
    i.tag.connect(t, {'originalTagName': oldTagName, 'originalTagSource': oldTagSource, 'manual': True})
    addESTag(hashcode, tagName)


def addTag(hashcode, tagName):
    t = Tag.nodes.get_or_none(name=tagName)
    i = ImageNeo.nodes.get_or_none(hash=hashcode)
    if i is None:
        return
    if t is None:
        t = Tag(name=tagName).save()
    i.tag.connect(t, {'originalTagName': tagName, 'originalTagSource': "manual", 'manual': True})
    addESTag(hashcode, tagName)


def deleteTag(hashcode, tagName):
    t = Tag.nodes.get_or_none(name=tagName)
    i = ImageNeo.nodes.get_or_none(hash=hashcode)
    tagSource = "err"
    if i is None or t is None:
        return [tagName, tagSource]
    if (t in i.tag):
        rel = i.tag.relationship(t)
        tagSource = rel.originalTagSource
        i.tag.disconnect(t)
    if (len(t.image) == 0):
        t.delete()
    deleteESTag(hashcode, tagName)
    return [tagName, tagSource]


def addESTag(hashcode, tag):
    a = ImageES.get(using=es, id=hashcode)
    a.tags.append(tag)
    a.tags = list(set(a.tags))
    a.update(using=es, tags=a.tags)
    a.save(using=es)


def deleteESTag(hashcode, tag):
    a = ImageES.get(using=es, id=hashcode)
    a.tags.remove(tag)
    a.tags = list(set(a.tags))
    a.update(using=es, tags=a.tags)
    a.save(using=es)
    
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

