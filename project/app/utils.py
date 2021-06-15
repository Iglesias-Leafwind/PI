import os
import random
import cv2
from PIL import Image
from threading import Lock
import imghdr

from app.models import Tag, ImageNeo, ImageES
from scripts.esScript import es

lock = Lock()
faceRecLock= Lock()
ocrLock= Lock()
processingLock = Lock()
resultsLock = Lock()
uploadLock = Lock()
objectLock = Lock()
breedLock = Lock()
locationLock = Lock()
placesLock = Lock()

showDict = {'verified':False, 'unverified':True}


objectExtractionThreshold = 0.1
faceRecThreshold = 0.35
placesThreshold = 0.1
breedsThreshold = 0.7

is_small = lambda w, h : w * h <= 800*1000
is_medium = lambda w, h : 800*1000 < w * h < 3000*1000
is_large = lambda w, h : 3000*1000 <= w * h

def reset_filters():
    global searchFilterOptions
    global timeHelper
    searchFilterOptions['automatic'] = True,  # isto sao os objects
    searchFilterOptions['manual'] = True,
    searchFilterOptions['folder_name'] = True
    searchFilterOptions['people'] = True
    searchFilterOptions['text'] = True
    searchFilterOptions['exif'] = True
    searchFilterOptions['places'] = True
    searchFilterOptions['breeds'] = True

    searchFilterOptions['objects_range_min'] = int(objectExtractionThreshold * 100)
    searchFilterOptions['objects_range_max'] = 100

    searchFilterOptions['people_range_min'] = int(faceRecThreshold * 100)
    searchFilterOptions['people_range_max'] = 100

    searchFilterOptions['places_range_min'] = int(placesThreshold * 100)
    searchFilterOptions['places_range_max'] = 100

    searchFilterOptions['breeds_range_min'] = int(breedsThreshold * 100)
    searchFilterOptions['breeds_range_max'] = 100


    searchFilterOptions['size_large'] = True
    searchFilterOptions['size_medium'] = True
    searchFilterOptions['size_small'] = True

    searchFilterOptions['insertion_date_activate'] = False
    searchFilterOptions['insertion_date_from'] = None
    searchFilterOptions['insertion_date_to'] = None
    timeHelper['insertion_date_from'] = None
    timeHelper['insertion_date_to'] = None

    searchFilterOptions['taken_date_activate'] = False
    searchFilterOptions['taken_date_from'] = None
    searchFilterOptions['taken_date_to'] = None
    timeHelper['taken_date_from'] = None
    timeHelper['taken_date_to'] = None

timeHelper = {}
searchFilterOptions = {}
reset_filters()

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
                    #print(f, image_type)
                    pass
    return dirsAndFiles

def getRandomNumber():
    return random.randint(1, 1 << 63)

def add_tag(hashcode, tag_name):
    t = Tag.nodes.get_or_none(name=tag_name)
    i = ImageNeo.nodes.get_or_none(hash=hashcode)
    if i is None:
        return
    if t is None:
        t = Tag(name=tag_name).save()
    i.tag.connect(t, {'originalTagName': tag_name, 'originalTagSource': "manual", 'manual': True, 'score': 1})
    add_es_tag(hashcode, tag_name)


def delete_tag(hashcode, tag_name):
    t = Tag.nodes.get_or_none(name=tag_name)
    i = ImageNeo.nodes.get_or_none(hash=hashcode)
    tag_source = "err"
    if i is None or t is None:
        return [tag_name, tag_source]
    if (t in i.tag):
        rel = i.tag.relationship(t)
        tag_source = rel.originalTagSource
        i.tag.disconnect(t)
    if (len(t.image) == 0):
        t.delete()
    delete_es_tag(hashcode, tag_name)
    return [tag_name, tag_source]


def add_es_tag(hashcode, tag):
    a = ImageES.get(using=es, id=hashcode)
    a.tags.append(tag)
    a.tags = list(set(a.tags))
    a.update(using=es, tags=a.tags)
    a.save(using=es)


def delete_es_tag(hashcode, tag):
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

