## @package app
#  This module contains various functions that are usefull overall
#  and contain the locks used to lock threads
#  More details.
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
## Resets all filters to the startup filters
#
#  More details.
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

## Gets all images of a path
#
#  More details.
def get_images_per_uri(path_name):
    dirs_and_files = {}  # key - dir name, value - list of files (imgs)

    if os.path.exists(path_name):
        file_list = os.listdir(path_name)

        for f in file_list:
            f = os.path.join(path_name, f)

            if os.path.isdir(f):
                dirs_and_files.update(get_images_per_uri(f))
            else:
                check_file_type(dirs_and_files, f, path_name)
    return dirs_and_files

## Checks image file type (if it is a valid image or not)
#
#  More details.
def check_file_type(dirs_and_files, f, path_name):
    image_type = imghdr.what(f)
    if f.endswith('jpg') or f.endswith('jpeg') or f.endswith('png') or f.endswith('JPG') or image_type in ['jpeg',
                                                                                                           'png',
                                                                                                           'bmp']:
        if path_name in dirs_and_files.keys():
            dirs_and_files[path_name].append(os.path.basename(f))
        else:
            dirs_and_files[path_name] = [os.path.basename(f)]

## Gets a random number integer between 1 and 1 << 63
#
#  More details.
def get_random_number():
    return random.randint(1, 1 << 63)
## Adds a tag to a image with a specific hash
#  @param hashcode Image hashcode
#  @param tag_name Manual tag, tag name
#  More details.
def add_tag(hashcode, tag_name):
    t = Tag.nodes.get_or_none(name=tag_name)
    i = ImageNeo.nodes.get_or_none(hash=hashcode)
    if i is None:
        return
    if t is None:
        t = Tag(name=tag_name).save()
    i.tag.connect(t, {'originalTagName': tag_name, 'originalTagSource': "manual", 'manual': True, 'score': 1})
    add_es_tag(hashcode, tag_name)

## Deletes a tag of a specific image
#  @param hashcode Image hashcode
#  @param tag_name Tag name
#  More details.
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

## Adds a tag to a update elastic search
#  @param hashcode Image hashcode
#  @param tag Neo4j Tag class
#  More details.
def add_es_tag(hashcode, tag):
    a = ImageES.get(using=es, id=hashcode)
    a.tags.append(tag)
    a.tags = list(set(a.tags))
    a.update(using=es, tags=a.tags)
    a.save(using=es)

## Deletes a tag of a image
#  @param hashcode Image hashcode
#  @param tag Neo4j Tag class
#  More details.
def delete_es_tag(hashcode, tag):
    a = ImageES.get(using=es, id=hashcode)
    a.tags.remove(tag)
    a.tags = list(set(a.tags))
    a.update(using=es, tags=a.tags)
    a.save(using=es)
## Create face thumbnail
#
#  More details.
def get_face_thumbnail(img, box, save_in=None):
    top, right, bottom, left= box
    cropimg = img[top:bottom, left:right]
    cropimg = cv2.resize(cropimg, (50,50))
    if save_in is not None:
        # assumindo que a imagem tem sempre uma extensao no fim
        # (ou seja, tem um '.png' ou '.'+ qq outra extensao no fim
        # new_path = img_path.split('.')[-2] + '_face.' + img_path.split('.')[-1]
        cv2.imwrite(save_in, cropimg)
    return cropimg
## Gets and saves the img?
#
#  More details.
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
## Image Features class that contains image features
#
#  More details.
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
        self.image_features = []
        self.np_features = []

