import json
import string

from app.breed_classifier import BreedClassifier
import time
import sys
from datetime import datetime
from os.path import join
import random
import numpy as np
import requests
from neomodel import db
from numpyencoder import NumpyEncoder
from app.face_recognition import FaceRecognition
from app.fileSystemManager import SimpleFileSystemManager
from app.models import ImageNeo, Person, Tag, Location, Country, City, Folder, ImageES
from app.object_extraction import ObjectExtract
from app.utils import ImageFeature, getImagesPerUri, ImageFeaturesManager, lock,faceRecLock, ocrLock, get_and_save_thumbnail
import torch
from torch.autograd import Variable as V
import torchvision.models as models
from torchvision import transforms as trn
from torch.nn import functional as F
import os
from PIL import Image
from imutils.object_detection import non_max_suppression
import cv2
import pytesseract
import re
from nltk.corpus import stopwords, words
from nltk.tokenize import word_tokenize
from exif import Image as ImgX
from app.VGG_ import VGGNet
from manage import es
import app.utils
from scripts.pathsPC import do,numThreads
import logging

import psutil, time
from scripts.pcVariables import ocrPath

cpuPerThread = 1
ramPerThread = 1
def testingThreadCapacity():
    global cpuPerThread
    global ramPerThread

    cpuNormal = psutil.cpu_percent()
    ramNormal = psutil.virtual_memory().percent
    cpuHigh = 0
    ramHigh = 0
    dir_path = os.path.dirname(os.path.realpath(__file__))
    head,_ = os.path.split(dir_path)
    dir_path = os.path.join(head,"tests")
    wait = do(processing, {dir_path: ["face.jpg"]})
    while not wait.done():
        cpuCurr = psutil.cpu_percent()
        ramCurr = psutil.virtual_memory().percent
        if(cpuCurr > cpuHigh):
            cpuHigh = cpuCurr
        if(ramCurr > ramHigh):
            ramHigh = ramCurr
    deleteFolder(dir_path)
    cpuPerThread = cpuHigh - cpuNormal
    if(cpuPerThread <= 0):
        cpuPerThread = (cpuPerThread * -1) + 1

    ramPerThread = ramHigh - ramNormal
    if(ramPerThread <= 0):
        ramPerThread = (ramPerThread * -1) + 1

obj_extr = ObjectExtract()
frr = FaceRecognition()
bc = BreedClassifier()

ftManager = ImageFeaturesManager()
fs = SimpleFileSystemManager()
model = VGGNet()

faceimageindex=0
THUMBNAIL_PIXELS=100

# used in getOCR
east = "frozen_east_text_detection.pb"
net = cv2.dnn.readNet(east)

# load installed tesseract-ocr from users pc
# CHANGE TO YOUR PATH!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#Windows Iglesias:
#pytesseract.pytesseract.tesseract_cmd = r'D:\Programs\tesseract-OCR\tesseract'

# Ubuntu:
#pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

# Wei:
#pytesseract.pytesseract.tesseract_cmd = r'D:\OCR\tesseract'


pytesseract.pytesseract.tesseract_cmd = ocrPath
custom_config = r'--oem 3 --psm 6'

# used in getPlaces
arch = 'resnet18'  # th architecture to use
# load the pre-trained weights
model_file = '%s_places365.pth.tar' % arch
places_model = models.__dict__[arch](num_classes=365)
checkpoint = torch.load(model_file, map_location=lambda storage, loc: storage)
state_dict = {str.replace(k, 'module.', ''): v for k, v in checkpoint['state_dict'].items()}
places_model.load_state_dict(state_dict)
places_model.eval()

# load the image transformer
centre_crop = trn.Compose([
    trn.Resize((256, 256)),
    trn.CenterCrop(224),
    trn.ToTensor(),
    trn.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])


logging.basicConfig(level=logging.INFO)

def filterSentence(sentence):
    english_vocab = set(w.lower() for w in words.words())
    stop_words = set(w.lower() for w in stopwords.words('english'))
    word_tokens = word_tokenize(sentence)
    filtered = [word for word in word_tokens if word not in stop_words if
                len(word) >= 4 and (len(word) <= 8 or word in english_vocab)]
    return filtered


def uploadImages(uri):
    print("----------------------------------------------")
    print("            featrue extraction starts         ")
    print("----------------------------------------------")

    dirFiles = getImagesPerUri(uri)

    cpuCurr = psutil.cpu_percent()
    ramCurr = psutil.virtual_memory().percent
    freeCPU = (100 - cpuCurr)/2
    freeRAM = (100 - ramCurr)/2
    threads = freeCPU/cpuPerThread
    threadsRAM = freeRAM/ramPerThread
    if(threadsRAM < threads):
        threads = threadsRAM
    threads = int(threads)
    if(threads > numThreads):
        threads = numThreads
    if(threads <= 0):
        threads = 1
    tasks = divideTasksInMany(dirFiles,threads)
    i = 1
    for task in tasks:
        print("------------------task", i, "------------------")
        do(processing, task)
        i += 1

def divideTasksInMany(dirFiles,qty):
    threading = 0
    tasks = []

    for i in range(1,qty+1):
        tasks.append({})

    # dirFiles -> {key: values}  key -> C:users/user/databse, values-> 1.jpg, 2.jpg
    for path in dirFiles.keys():
        for image in dirFiles[path]:
            if(path not in tasks[threading].keys()):
                tasks[threading][path] = [image]
            else:
                tasks[threading][path] += [image]
            threading += 1
            if(threading >= len(tasks)):
                threading = 0

    return tasks

def face_rec_part(read_image, img_path, tags, image):
    # image aberta -> read_image
    print("--- comeca a parte de face rec da img: ",img_path, " ---")
    openimage, boxes = frr.getFaceBoxes(open_img=read_image, image_path=img_path)

    for b in boxes:
        name, enc, conf = frr.getTheNameOf(openimage, b)
        if name is None:
            # esta verificacao terá de ser alterada para algo mais preciso
            # por exemplo, definir um grau de certeza
            name = ''.join(random.choice(string.ascii_letters) for i in range(10))
        frr.saveFaceIdentification(name=name, encoding = enc, conf=conf, imghash=image.hash)

        # face_thumb_path = os.path.join('app', 'static', 'face-thumbnails', str(int(round(time.time() * 1000))) + '.jpg')
        face_thumb_path = os.path.join('static', 'face-thumbnails', str(int(round(time.time() * 1000))) + '.jpg')
        face_icon = app.utils.getFaceThumbnail(openimage, b, save_in=os.path.join('app', face_thumb_path))
        p = Person.nodes.get_or_none(name=name)
        if p is None:
            #p = Person(name=name, icon=face_thumb_path).save()
            p = Person(name=name).save()

        tags.append(name)

        # encodings falta
        image.person.connect(p, {'coordinates': list(b), 'icon': face_thumb_path, 'confiance': conf, 'encodings': enc, 'approved': False})
        # """
        print("-- face rec end --")

def classifyBreedPart(read_image, tags, imageDB):
    breed, breed_conf = bc.predict_image(read_image)
    if breed_conf > 0.7:  # TODO: adapt!
        tags.append(breed)

        tag = Tag.nodes.get_or_none(name=breed)
        if tag is None:
            tag = Tag(name=breed).save()
        imageDB.tag.connect(tag, {'originalTagName':breed, 'originalTagSource': 'breeds', 'score':breed_conf})


def processing(dirFiles):
    for dir in dirFiles.keys():
        img_list = dirFiles[dir]

        if not fs.exist(dir):
            lastNode = fs.createUriInNeo4j(dir)
        else:
            lastNode = fs.getLastNode(dir)

        commit = True
        folderNeoNode = Folder.nodes.get(id_=lastNode.id)
        for index, img_name in enumerate(img_list):
            db.begin()  # start the transaction
            try:
                img_path = os.path.join(dir, img_name)
                print("I am in: ",img_path)
                i = ImageFeature()

                read_image = cv2.imread(img_path)
                if read_image is None:
                    print('read img is none')
                    continue
                hash = dhash(read_image)

                existed = ImageNeo.nodes.get_or_none(hash=hash)
                i.hash = hash

                if existed:  # if an image already exists in DB (found an ImageNeo with the same hashcode)

                    logging.info("Image " + img_path + " has already been processed")

                    if existed.folder_uri == dir:
                        continue

                    # if the current image's folder is different
                    existed.folder.connect(folderNeoNode)
                else:
                    tags = []

                    # extract infos
                    norm_feat, height, width = model.vgg_extract_feat(img_path)
                    f = json.dumps(norm_feat, cls=NumpyEncoder)
                    i.features = f
                    iJson = json.dumps(i.__dict__)

                    propertiesdict = getExif(img_path)
                    generateThumbnail(img_path, hash)

                    if "datetime" in propertiesdict:
                        image = ImageNeo(folder_uri=os.path.split(img_path)[0],
                                         name=img_name,
                                         processing=iJson,
                                         format=img_name.split(".")[1],
                                         width=width,
                                         height=height,
                                         hash=hash,
                                         creation_date=propertiesdict["datetime"],
                                         insertion_date=datetime.now())
                    else:
                        image = ImageNeo(folder_uri=os.path.split(img_path)[0],
                                         name=img_name,
                                         processing=iJson,
                                         format=img_name.split(".")[1],
                                         width=width,
                                         height=height,
                                         hash=hash,
                                         insertion_date=datetime.now())

                    lock.acquire()
                    existed = ImageNeo.nodes.get_or_none(hash=hash)
                    if existed:
                        if existed.folder_uri != dir:
                            # if the current image's folder is different
                            existed.folder.connect(folderNeoNode)
                        lock.release()
                        continue
                    try:
                        image.save()
                    except Exception as e:
                        print(e)
                        db.commit()
                        continue
                    finally:
                        lock.release()

                    if "latitude" in propertiesdict and "longitude" in propertiesdict:
                        location = Location.nodes.get(name=propertiesdict["location"])
                        if location is None:
                            location = Location(name=propertiesdict["location"]).save()

                        tags.append(location)
                        image.location.connect(location, {'latitude': propertiesdict["latitude"], 'longitude': propertiesdict["longitude"]})

                        city = City.nodes.get(name=propertiesdict["city"])
                        if city is None:
                            city = City(name=propertiesdict["city"]).save()

                        tags.append(city)
                        location.city.connect(city)

                        country = Country.nodes.get(name=propertiesdict["country"])
                        if country is None:
                            country = Country(name=propertiesdict["country"]).save()

                        tags.append(country)
                        city.country.connect(country)

                    image.folder.connect(folderNeoNode)

                    res = obj_extr.get_objects(img_path)

                    for object in res["name"]:
                        tag = Tag.nodes.get_or_none(name=object)
                        if tag is None:
                            tag = Tag(name=object).save()
                        tags.append(object)
                        image.tag.connect(tag,{'originalTagName': object, 'originalTagSource': 'object'})

                        if object in ['cat', 'dog']:
                            classifyBreedPart(read_image, tags, image)

                    faceRecLock.acquire()
                    face_rec_part(read_image, img_path, tags, image)
                    faceRecLock.release()
                    #     p = Person.nodes.get_or_none(name=name)

                    places = getPlaces(img_path)
                    if places:
                        places = places.split("/")
                        for place in places:
                            p = " ".join(place.split("_")).strip()
                            t = Tag.nodes.get_or_none(name=p)
                            if t is None:
                                t = Tag(name=p).save()
                            tags.append(p)
                            image.tag.connect(t,{'originalTagName': p, 'originalTagSource': 'places'})

                    wordList = getOCR(read_image)
                    if wordList and len(wordList) > 0:
                        for word in wordList:
                            t = Tag.nodes.get_or_none(name=word)
                            if t is None:
                                t = Tag(name=word).save()
                            tags.append(word)
                            image.tag.connect(t,{'originalTagName': word, 'originalTagSource': 'ocr'})

                    # add features to "cache"
                    ftManager.npFeatures.append(norm_feat)
                    i.features = norm_feat
                    ftManager.imageFeatures.append(i)

                    print('tags: ', tags)
                    ImageES(meta={'id': image.hash}, uri=img_path, tags=tags, hash=image.hash).save(using=es)

                    print("extracting feature from image %s " % (img_path))
                    db.commit()
                    commit &= True
            except Exception as e:
                db.rollback()
                fs.deleteFolderFromFs(dir)
                commit &= False
                print("Error during processing: ", e)

        if not commit:
            fs.deleteFolderFromFs(dir)

def alreadyProcessed(img_path):
    image = cv2.imread(img_path)
    hash = dhash(image)
    existed = ImageNeo.nodes.get_or_none(hash=hash)

    return existed

def deleteFolder(uri):

    deletedImages = fs.deleteFolderFromFs(uri)
    if deletedImages is None or len(deletedImages) == 0:
        return

    imgfs = set(ftManager.imageFeatures)
    for di in deletedImages:
        frr.removeImage(di.hash)
        imgfs.remove(di)

    ftManager.imageFeatures = list(imgfs)
    f = []
    for i in ftManager.imageFeatures:
        f.append(i.features)

    ftManager.npFeatures = f

def findSimilarImages(uri):
    norm_feat, height, width = model.vgg_extract_feat(uri)  # extrair infos
    feats = np.array(ftManager.npFeatures)
    scores = np.dot(norm_feat, feats.T)
    rank = np.argsort(scores)[::-1]
    rank_score = scores[rank]

    maxres = 42  # 42 imagens com maiores scores

    imlist = []
    for i, index in enumerate(rank[0:maxres]):
        imlist.append(str(ftManager.imageFeatures[index].hash) )

    return imlist

def getPlaces(img_path):
    # load the test image
    img = Image.open(img_path).convert('RGB')
    input_img = V(centre_crop(img).unsqueeze(0))

    # forward pass
    logit = places_model.forward(input_img)
    h_x = F.softmax(logit, 1).data.squeeze()
    probs, idx = h_x.sort(0, True)

    return classes[idx[0]] if probs[0] > 0.6 else None


def getOCR(image):
    min_confidence = 0.6
    results = []
    # These must be multiple of 32
    newW = 128
    newH = 128
    orig = image.copy()
    (H, W) = image.shape[:2]

    # set the new width and height and then determine the ratio in change
    # for both the width and height
    rW = W / float(newW)
    rH = H / float(newH)

    # resize the image and grab the new image dimensions
    image = cv2.resize(image, (newW, newH))
    (H, W) = image.shape[:2]

    # define the two output layer names for the EAST detector model that
    # we are interested -- the first is the output probabilities and the
    # second can be used to derive the bounding box coordinates of text
    layerNames = [
        "feature_fusion/Conv_7/Sigmoid",
        "feature_fusion/concat_3"]

    # construct a blob from the image and then perform a forward pass of
    # the model to obtain the two output layer sets
    blob = cv2.dnn.blobFromImage(image, 1.0, (W, H),
                                 (123.68, 116.78, 103.94), swapRB=True, crop=False)
    ocrLock.acquire()
    net.setInput(blob)
    (scores, geometry) = net.forward(layerNames)
    ocrLock.release()

    # grab the number of rows and columns from the scores volume, then
    # initialize our set of bounding box rectangles and corresponding
    # confidence scores
    (numRows, numCols) = scores.shape[2:4]
    rects = []
    confidences = []
    # loop over the number of rows
    for y in range(0, numRows):
        # extract the scores (probabilities), followed by the geometrical
        # data used to derive potential bounding box coordinates that
        # surround text
        scoresData = scores[0, 0, y]
        xData0 = geometry[0, 0, y]
        xData1 = geometry[0, 1, y]
        xData2 = geometry[0, 2, y]
        xData3 = geometry[0, 3, y]
        anglesData = geometry[0, 4, y]
        # loop over the number of columns
        for x in range(0, numCols):
            # if our score does not have sufficient probability, ignore it
            if scoresData[x] < min_confidence:
                continue
            # compute the offset factor as our resulting feature maps will
            # be 4x smaller than the input image
            (offsetX, offsetY) = (x * 4.0, y * 4.0)
            # extract the rotation angle for the prediction and then
            # compute the sin and cosine
            angle = anglesData[x]
            cos = np.cos(angle)
            sin = np.sin(angle)
            # use the geometry volume to derive the width and height of
            # the bounding box
            h = xData0[x] + xData2[x]
            w = xData1[x] + xData3[x]
            # compute both the starting and ending (x, y)-coordinates for
            # the text prediction bounding box
            endX = int(offsetX + (cos * xData1[x]) + (sin * xData2[x]))
            endY = int(offsetY - (sin * xData1[x]) + (cos * xData2[x]))
            startX = int(endX - w)
            startY = int(endY - h)
            # add the bounding box coordinates and probability score to
            # our respective lists
            rects.append((startX, startY, endX, endY))
            confidences.append(scoresData[x])
    # apply non-maxima suppression to suppress weak, overlapping bounding
    # boxes
    boxes = non_max_suppression(np.array(rects), probs=confidences)
    # loop over the bounding boxes
    (maxH, maxW) = orig.shape[:2]
    for (startX, startY, endX, endY) in boxes:
        # scale the bounding box coordinates based on the respective
        # ratios
        startX = int(startX * rW) - 20
        if (startX <= 0):
            startX = 1
        startY = int(startY * rH) - 20
        if (startY <= 0):
            startY = 1
        endX = int(endX * rW) + 20
        if (endX >= maxW):
            endX = maxW - 1
        endY = int(endY * rH) + 20
        if (endY >= maxH):
            endY = maxH - 1
        # draw the bounding box on the image
        ROI = orig[startY:endY, startX:endX]
        imageText = pytesseract.image_to_string(ROI, config=custom_config)
        result = imageText.replace("\x0c", " ").replace("\n", " ")
        results += (re.sub('[^0-9a-zA-Z -]+', '', result)).split(" ")

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Load image, grayscale, Gaussian blur, adaptive threshold
    gray = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (9, 9), 0)
    thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 30)

    # Dilate to combine adjacent text contours
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    dilate = cv2.dilate(thresh, kernel, iterations=4)

    # Find contours, highlight text areas, and extract ROIs
    cnts = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]

    for c in cnts:
        area = cv2.contourArea(c)
        if area > 10000:
            x, y, w, h = cv2.boundingRect(c)
            ROI = orig[y:y + h, x:x + w]
            imageText = pytesseract.image_to_string(ROI, config=custom_config)
            result = imageText.replace("\x0c", " ").replace("\n", " ")
            results += (re.sub('[^0-9a-zA-Z -]+', '', result)).split(" ")

    # Transform set into a single string
    # filter words
    retrn = []
    phrase = ""
    for ele in set(results):
        phrase += ele
        phrase += " "
    for elem in filterSentence(phrase):
        retrn += [elem]
    return set(retrn)


def dhash(image, hashSize=8):
    # convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # resize the grayscale image, adding a single column (width) so we
    # can compute the horizontal gradient
    resized = cv2.resize(gray, (hashSize + 1, hashSize))
    # compute the (relative) horizontal gradient between adjacent
    # column pixels
    diff = resized[:, 1:] > resized[:, :-1]
    # convert the difference image to a hash
    h = sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])
    return convert_hash(h)


def convert_hash(h):
    # convert the hash to NumPy's 64-bit float and then back to
    # Python's built in int
    return int(np.array(h, dtype="float64"))


def loadCatgoriesPlaces():
    # load the class label for scene recognition
    file_name = 'categories_places365.txt'
    global classes
    classes = list()
    with open(file_name) as class_file:
        for line in class_file:
            classes.append(line.strip().split(' ')[0][3:])
    classes = tuple(classes)


def loadFileSystemManager():
    roots = Folder.nodes.filter(root=True)

    if not roots: return

    def buildUri(node, uri, ids):
        if not node: return
        uri += node.name + "/"
        ids.append(node.id_)

        if node.terminated:
            fs.addFullPathUri(uri, ids)

        for child in node.children:
            buildUri(child, uri, ids)
            ids.pop()  # backtracking

    for root in roots:
        uri = root.name + "/"
        ids = [root.id_]
        for child in root.children:
            buildUri(child, uri, ids)
            ids.pop()  # backtracking


def getExif(img_path):
    returning = {}
    try:
        with open(img_path, 'rb') as image_file:
            # transform into exif image format
            current_image = ImgX(image_file)
            # check if it has a exif
            if (current_image.has_exif):
                if ("datetime" in current_image.list_all()):
                    returning["datetime"] = current_image.datetime
                if ("pixel_x_dimension" in current_image.list_all()):
                    returning["width"] = current_image.pixel_x_dimension
                if ("pixel_y_dimension" in current_image.list_all()):
                    returning["height"] = current_image.pixel_y_dimension
                if ("gps_latitude" in current_image.list_all()):
                    returning["latitude"] = current_image.gps_latitude
                if ("gps_longitude" in current_image.list_all()):
                    returning["longitude"] = current_image.gps_longitude

                if 'latitude' in returning and 'longitude' in returning:
                    geoInfos = requests.get(
                        "https://api.bigdatacloud.net/data/reverse-geocode-client?latitude="
                        + returning["latitude"] + "&longitude=" + returning["longitude"]).json()
                    returning['location'] = geoInfos['city']
                    returning['city'] = geoInfos['city']
                    returning['country'] = geoInfos['countryName']
            else:
                raise Exception("No exif")
    except Exception as e:
        image = cv2.imread(img_path)
        (H, W) = image.shape[:2]
        returning["height"] = H
        returning["width"] = W
    return returning


# load all images to memory
def setUp():
    images = ImageNeo.nodes.all()
    npfeatures = []
    imageFeatures = []

    for image in images:
        i = ImageFeature(**json.loads(image.processing))
        if i.features is None:
            continue
        i.features = np.array(json.loads(i.features))
        npfeatures.append(i.features)
        imageFeatures.append(i)

    loadCatgoriesPlaces()
    loadFileSystemManager()
    ftManager.npFeatures = npfeatures
    ftManager.imageFeatures = imageFeatures
    testingThreadCapacity()

def generateThumbnail(imagepath, hash):
    thumbnailH = 225
    thumbnailW = 225

    dim = (thumbnailW, thumbnailH)

    # load the input image
    image = cv2.imread(imagepath)
    h,w,p = image.shape

    paddingLR = 0
    paddingTB = 0
    if(w - thumbnailW > h - thumbnailH):
        ratio = thumbnailW/w
        thumbnailH = int(h * ratio)
        paddingTB = int((thumbnailW-thumbnailH)/2)
    else:
        ratio = thumbnailH/h
        thumbnailW = int(w * ratio)
        paddingLR = int((thumbnailH-thumbnailW)/2)

    image = cv2.copyMakeBorder(image, paddingTB, paddingTB, paddingLR, paddingLR, cv2.BORDER_REPLICATE)
    # resize image
    resized = cv2.resize(image, dim, interpolation = cv2.INTER_AREA)
    saving = os.path.join("app", "static", "thumbnails", str(hash)) + ".jpg"
    cv2.imwrite(saving, resized, [cv2.IMWRITE_JPEG_QUALITY, 25])
    image = cv2.imread(saving)
    # 83 087 673
    # 00 288 957
    # 99,65 %
    return(saving)

setUp()
