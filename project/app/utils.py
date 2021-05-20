import os
import random
from threading import Lock
import imghdr

from app.models import Tag, ImageNeo, ImageES
from manage import es

lock = Lock()

def getImagesPerUri(pathName):
    dirsAndFiles = {}  # key - dir name, value - list of files (imgs)

    if os.path.exists(pathName):
        fileList = os.listdir(pathName)

        for f in fileList:
            f = os.path.join(pathName, f)

            if os.path.isdir(f):
                dirsAndFiles.update(getImagesPerUri(f))

            elif f.endswith('jpg') or f.endswith('jpeg') or f.endswith('png'):
                if pathName in dirsAndFiles.keys():
                    dirsAndFiles[pathName].append(os.path.basename(f))
                else:
                    dirsAndFiles[pathName] = [os.path.basename(f)]

    return dirsAndFiles

def getRandomNumber():
    return random.randint(1, 1 << 63)

def addTag(hashcode, tagName):
    t = Tag.nodes.get_or_none(name=tagName)
    i = ImageNeo.nodes.get_or_none(hash=hashcode)
    if i is None:
        return
    if t is None:
        t = Tag(name=tagName,
            originalTagName=tagName,
            originalTagSource='user').save()
    i.tag.connect(t)
    addESTag(hashcode, tagName)

def deleteTag(hashcode, tagName):
    t = Tag.nodes.get_or_none(name=tagName)
    i = ImageNeo.nodes.get_or_none(hash=hashcode)
    if i is None or t is None:
        return
    if (t in i.tag):
        i.tag.disconnect(t)
    if (len(t.image) == 0):
        t.delete()
    deleteESTag(hashcode, tagName)


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

