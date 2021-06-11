import json
import string
import reverse_geocoder as rg
import threading
#from app.face_recognition import FaceRecognition
#from app.breed_classifier import BreedClassifier
import time
import sys
from datetime import datetime
from os.path import join
import random
import numpy as np
import requests
from neomodel import db
from numpyencoder import NumpyEncoder
from app.fileSystemManager import SimpleFileSystemManager
from app.models import ImageNeo, Person, Tag, Location, Country, City, Folder, ImageES, Region
from app.object_extraction import ObjectExtract
from app.utils import ImageFeature, getImagesPerUri, ImageFeaturesManager, ocrLock, processingLock, resultsLock, uploadLock, objectLock, breedLock,locationLock,faceRecLock,placesLock
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
from scripts.esScript import es
import app.utils
from scripts.pathsPC import do,numThreads
import logging

import psutil, time
from scripts.pcVariables import ocrPath

logging.basicConfig(level=logging.INFO)
cpuPerThread = 1
ramPerThread = 1
threadTasks = {}

def testingThreadCapacity():
    global cpuPerThread
    global ramPerThread

    dir_path = os.path.dirname(os.path.realpath(__file__))
    dir_path = os.path.join(dir_path,"static/tests")
    threadTasks[dir_path] = 0
    wait = do(processing, {dir_path: ["face.jpg"]})
    cpuNormal = psutil.cpu_percent()
    ramNormal = psutil.virtual_memory().percent

    cpuSum = 0
    ramSum = 0
    iter = 0
    while not wait.done():
        time.sleep(0.1)
        cpuSum += psutil.cpu_percent()
        ramSum += psutil.virtual_memory().percent
        iter += 1

    cpuM = (cpuSum / iter)
    ramM = (ramSum / iter)

    deleteFolder(dir_path)
    cpuPerThread = cpuM - cpuNormal
    cpuPerThread /= 2

    if(cpuPerThread <= 0):
        cpuPerThread = (cpuPerThread * -1) + 1

    ramPerThread = ramM - ramNormal
    ramPerThread /= 2

    if(ramPerThread <= 0):
        ramPerThread = (ramPerThread * -1) + 1
        
logging.info("[Loading]: [INFO] Loading Object Extraction")
obj_extr = do(ObjectExtract)

logging.info("[Loading]: [INFO] Loading face recognition")
#frr = do(FaceRecognition)

logging.info("[Loading]: [INFO] Loading breed classifier")
#bc = do(BreedClassifier)

while not obj_extr.done():
    time.sleep(0.1)

obj_extr = obj_extr.result()
logging.info("[Loading]: [INFO] Finished loading Object Extraction")

#while not frr.done():
#    time.sleep(0.1)
#frr = frr.result()
logging.info("[Loading]: [INFO] Finished loading face recognition")

#while not bc.done():
#    time.sleep(0.1)
#bc = bc.result()
logging.info("[Loading]: [INFO] Finished loading breed classifier")

ftManager = ImageFeaturesManager()
fs = SimpleFileSystemManager()
model = VGGNet()

faceimageindex=0
THUMBNAIL_PIXELS=100

# used in getOCR
east = "frozen_east_text_detection.pb"
net = cv2.dnn.readNet(east)

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



def filterSentence(sentence):
    english_vocab = set(w.lower() for w in words.words())
    stop_words = set(w.lower() for w in stopwords.words('english'))
    word_tokens = word_tokenize(sentence)
    filtered = [word.lower() for word in word_tokens if word not in stop_words if
                len(word) >= 4 and (len(word) <= 8 or word in english_vocab)]
    return filtered

def uploadImages(uri):
    logging.info("----------------------------------------------")
    logging.info("            feature extraction starts         ")
    logging.info("----------------------------------------------")

    dirFiles = getImagesPerUri(uri)

    cpuCurr = psutil.cpu_percent()
    ramCurr = psutil.virtual_memory().percent
    freeCPU = (100 - cpuCurr) / 5
    freeRAM = (100 - ramCurr) / 5
    threads = freeCPU / cpuPerThread
    threadsRAM = freeRAM / ramPerThread

    if(threadsRAM < threads):
        threads = threadsRAM
    threads = int(threads)
    if(threads > numThreads):
        threads = numThreads

    if(threads <= 0):
        threads = 1

    logging.info("[Uploading]: Dividing")
    tasks = divideTasksInMany(dirFiles, threads)
    folders = []
    for task in tasks:
        print(task)
        folders += list(task.keys())
    folders = list(set(folders))
    logging.info("[Uploading]: Folders found " + str(folders))
    try:
        uploadLock.acquire()
        for dir_path in folders:
            if dir_path in threadTasks:
                for task in tasks:
                    if dir_path in task.keys():
                        task.pop(dir_path)
            else:
                threadTasks[dir_path] = 0
    finally:
        uploadLock.release()

    i = 1
    for task in tasks:
        logging.info("------------------task " + str(i) +" ------------------")
        if task == {}:
            continue
        do(processing, task)

        i += 1

def divideTasksInMany(dirFiles,qty):
    threading = 0
    tasks = []

    for i in range(1, qty + 1):
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

def classifyBreedPart(read_image, tags, imageDB):
    breed, breed_conf = bc.predict_image(read_image)
    if breed_conf > app.utils.breedsThreshold:  # TODO: adapt!
        tags.append(breed)

        tag = Tag.nodes.get_or_none(name=breed)
        if tag is None:
            tag = Tag(name=breed).save()
        imageDB.tag.connect(tag, {'originalTagName':breed, 'originalTagSource': 'breeds', 'score':breed_conf})

def processing(dirFiles):
    for dir in dirFiles.keys():
        try:
            uploadLock.acquire()
            threadTasks[dir] += 1
        finally:
            uploadLock.release()

    for dir in dirFiles.keys():
        img_list = dirFiles[dir]
        try:
            processingLock.acquire()
            db.begin()
            if not fs.exist(dir):
                lastNode = fs.createUriInNeo4j(dir)
            else:
                lastNode = fs.getLastNode(dir)
        finally:
            db.commit()
            processingLock.release()
        atLeastOne = False
        folderNeoNode = Folder.nodes.get(id_=lastNode.id)
        for index, img_name in enumerate(img_list):
            try:
                img_path = os.path.join(dir, img_name)
                logging.info("[Processing]: " + threading.current_thread().name + " [INFO] Doing " + str(index+1) + " / " + str(len(img_list)))

                logging.info("[Processing]: " + threading.current_thread().name + " [INFO] I am in " + img_path)
                i = ImageFeature()

                read_image = cv2.imread(img_path)
                (H, W) = read_image.shape[:2]
                if read_image is None:
                    logging.info("[Processing]: " + threading.current_thread().name + " [ERR] Read of " + img_path + " is None")
                    continue
                hash = dhash(read_image)

                existed = ImageNeo.nodes.get_or_none(hash=hash)
                i.hash = hash

                if existed:  # if an image already exists in DB (found an ImageNeo with the same hashcode)

                    logging.info("[Processing]: " + threading.current_thread().name + " [INFO] Image " + img_path + " has already been processed")

                    if existed.folder_uri == dir:
                        atLeastOne |= True
                        continue

                    try:
                        processingLock.acquire()
                        # if the current image's folder is different
                        existed.folder.connect(folderNeoNode)
                    finally:
                        processingLock.release()
                    atLeastOne |= True
                    continue
                else:
                    tags = []

                    # extract infos
                    norm_feat = model.vgg_extract_feat(img_path)
                    f = json.dumps(norm_feat, cls=NumpyEncoder)
                    i.features = f
                    iJson = json.dumps(i.__dict__)

                    logging.info("[Processing]: " + threading.current_thread().name + " [INFO] Exif of " + img_path)
                    propertiesdict = getExif(img_path)
                    logging.info("[Processing]: " + threading.current_thread().name + " [INFO] Thumbnail of " + img_path)
                    generateThumbnail(img_path, hash)

                    if "datetime" in propertiesdict:
                        image = ImageNeo(folder_uri=os.path.split(img_path)[0],
                                         name=img_name,
                                         processing=iJson,
                                         format=img_name.split(".")[1],
                                         width=W,
                                         height=H,
                                         hash=hash,
                                         creation_date=propertiesdict["datetime"],
                                         insertion_date=datetime.now())
                    else:
                        image = ImageNeo(folder_uri=os.path.split(img_path)[0],
                                         name=img_name,
                                         processing=iJson,
                                         format=img_name.split(".")[1],
                                         width=W,
                                         height=H,
                                         hash=hash,
                                         insertion_date=datetime.now())

                    try:
                        processingLock.acquire()
                        existed = ImageNeo.nodes.get_or_none(hash=hash)
                        if existed:
                            if existed.folder_uri != dir:
                                # if the current image's folder is different
                                existed.folder.connect(folderNeoNode)
                            atLeastOne |= True
                            continue
                        try:
                            image.save()
                            atLeastOne |= True
                        except Exception as e:
                            logging.info("[Processing]: " + threading.current_thread().name + " [ERR] Saving image err " + str(e))
                            continue
                    finally:
                        processingLock.release()

                    if "latitude" in propertiesdict and "longitude" in propertiesdict:
                        # crc = [city,region,country] names array
                        logging.info("[Processing]: " + threading.current_thread().name + " [INFO] Location of " + img_path)
                        try:
                            locationLock.acquire()
                            crc = getLocations(propertiesdict["latitude"], propertiesdict["longitude"])
                        finally:
                            locationLock.release()

                        try:
                            processingLock.acquire()
                            db.begin()
                            location = Location.nodes.get_or_none(name=crc[0])
                            if location is None:
                                location = Location(name=crc[0]).save()

                            tags.append(crc[0])
                            image.location.connect(location, {'latitude': propertiesdict["latitude"], 'longitude': propertiesdict["longitude"]})

                            city = City.nodes.get_or_none(name=crc[0])
                            if city is None:
                                city = City(name=crc[0]).save()

                            tags.append(crc[0])
                            location.city.connect(city)

                            region = Region.nodes.get_or_none(name=crc[1])
                            if region is None:
                                region = Region(name=crc[1]).save()
                            tags.append(crc[1])
                            city.region.connect(region)

                            country = Country.nodes.get_or_none(name=crc[2])
                            if country is None:
                                country = Country(name=crc[2]).save()

                            tags.append(crc[2])
                            region.country.connect(country)
                            db.commit()
                        except:
                            db.rollback()
                            continue
                        finally:
                            processingLock.release()

                    image.folder.connect(folderNeoNode)


                    logging.info("[Processing]: " + threading.current_thread().name + " [INFO] Objects of " + img_path)
                    try:
                        objectLock.acquire()
                        res = obj_extr.get_objects(img_path)
                    finally:
                        objectLock.release()


                    for object, confidence in res:
                        try:
                            processingLock.acquire()
                            tag = Tag.nodes.get_or_none(name=object)
                            if tag is None:
                                tag = Tag(name=object).save()
                            tags.append(object)
                            image.tag.connect(tag,{'originalTagName': object, 'originalTagSource': 'object', 'score': confidence})
                        finally:
                            processingLock.release()

                        if object in ['cat', 'dog']:
                            logging.info("[Processing]: " + threading.current_thread().name + " [INFO] Breeds of " + img_path)
                            try:
                                breedLock.acquire()
                                classifyBreedPart(read_image, tags, image)
                            finally:
                                breedLock.release()

                    try:
                        faceRecLock.acquire()
                        db.begin()
                        #face_rec_part(read_image, img_path, tags, image)
                    finally:
                        faceRecLock.release()
                        db.commit()
                    #     p = Person.nodes.get_or_none(name=name)

                    logging.info("[Processing]: " + threading.current_thread().name + " [INFO] Places of " + img_path)
                    try:
                        placesLock.acquire()
                        placesList = getPlaces(img_path)
                    finally:
                        placesLock.release()
                    for places, prob in placesList:

                        places = places.split("/")
                        for place in places:
                            try:
                                processingLock.acquire()
                                p = " ".join(place.split("_")).strip()
                                t = Tag.nodes.get_or_none(name=p)
                                if t is None:
                                    t = Tag(name=p,
                                            originalTagName=p,
                                            originalTagSource='places').save()
                                tags.append(p)
                                image.tag.connect(t, {'originalTagName': p, 'originalTagSource': 'places', 'score': prob})
                            finally:
                                processingLock.release()
                    logging.info("[Processing]: " + threading.current_thread().name + " [INFO] OCR of " + img_path)

                    try:
                        ocrLock.acquire()
                        wordList = getOCR(read_image)
                    finally:
                        ocrLock.release()

                    if wordList and len(wordList) > 0:
                        for word in wordList:
                            try:
                                processingLock.acquire()
                                t = Tag.nodes.get_or_none(name=word)
                                if t is None:
                                    t = Tag(name=word).save()
                                tags.append(word)
                                image.tag.connect(t,{'originalTagName': word, 'originalTagSource': 'ocr', 'score': 0.6})
                            finally:
                                processingLock.release()

                    # add features to "cache"
                    try:
                        resultsLock.acquire()
                        ftManager.npFeatures.append(norm_feat)
                        i.features = norm_feat
                        ftManager.imageFeatures.append(i)
                    finally:
                        resultsLock.release()

                    ImageES(meta={'id': image.hash}, uri=img_path, tags=tags, hash=image.hash).save(using=es)


                    completed = index+1
                    logging.info("[Processing]: " + threading.current_thread().name + " [INFO] Finished " + img_path)
                    logging.info("[Processing]: " + threading.current_thread().name + " [INFO] Done " + str(completed) + " / " + str(len(img_list)))
                    atLeastOne |= True
            except Exception as e:
                logging.info("[Processing]: [ERR] In " + threading.current_thread().name + ": " + e)

        if not atLeastOne:
            try:
                processingLock.acquire()
                fs.deleteFolderFromFs(dir)
            finally:
                processingLock.release()

        try:
            uploadLock.acquire()
            threadTasks[dir]-= 1
        finally:
            uploadLock.release()

    try:
        uploadLock.acquire()
        for dir in threadTasks:
            if threadTasks[dir] == 0:
                threadTasks.pop(dir)
    finally:
        uploadLock.release()

def getLocations(latitude,longitude):
    results = rg.search((latitude,longitude))
    return [results[0]['name'], results[0]['admin2'], results[0]['admin1']]


def alreadyProcessed(img_path):
    image = cv2.imread(img_path)
    hash = dhash(image)
    existed = ImageNeo.nodes.get_or_none(hash=hash)

    return existed

def deleteFolder(uri):
    logging.info("[Deleting]: [INFO] Trying to delete " + uri)
    deletedImages = None
    if fs.exist(uri):
        try:
            processingLock.acquire()
            deletedImages = fs.deleteFolderFromFs(uri)
        finally:
            processingLock.release()
    else:
        return

    logging.info("[Deleting]: [INFO] Finished deleting folder " + uri)
    if deletedImages is None or len(deletedImages) == 0:
        return

    logging.info("[Deleting]: [INFO] Starting to delete images from database")
    imgfs = set(ftManager.imageFeatures)
    for di in deletedImages:
        imgfs.remove(di)
        frr.removeImage(di.hash)

    ftManager.imageFeatures = list(imgfs)
    f = []
    for i in ftManager.imageFeatures:
        f.append(i.features)

    ftManager.npFeatures = f
    logging.info("[Deleting]: [INFO] Finished deleting images from database")

def findSimilarImages(uri):
    if len(ftManager.npFeatures) == 0:
        return []
    norm_feat = model.vgg_extract_feat(uri)  # extrair infos
    feats = np.array(ftManager.npFeatures)
    scores = np.dot(norm_feat, feats.T)
    rank = np.argsort(scores)[::-1]

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

    return [(classes[idx[i]], probs[i]) for i in range(0, 10) if probs[i] > 0.1]


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

    net.setInput(blob)
    (scores, geometry) = net.forward(layerNames)

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

                if ("gps_latitude" in current_image.list_all()):
                    latitude = current_image.gps_latitude[0]
                    latitude += current_image.gps_latitude[1]/60
                    latitude += current_image.gps_latitude[2]/3600
                    if (current_image.gps_latitude_ref == "S"):
                        latitude *= -1
                    returning["latitude"] = latitude
                if ("gps_longitude" in current_image.list_all()):
                    longitude = current_image.gps_longitude[0]
                    longitude += current_image.gps_longitude[1]/60
                    longitude += current_image.gps_longitude[2]/3600
                    if (current_image.gps_longitude_ref == "W"):
                        longitude *= -1
                    returning["longitude"] = longitude
            else:
                raise Exception("No exif")

    except Exception as e:
        pass

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
    logging.info("[Loading]: [INFO] Loading places")
    plc = do(loadCatgoriesPlaces)
    logging.info("[Loading]: [INFO] Loading file system")
    filess = do(loadFileSystemManager)

    while not plc.done():
        time.sleep(0.1)
    logging.info("[Loading]: [INFO] Finished loading places")
    while not filess.done():
        time.sleep(0.1)
    logging.info("[Loading]: [INFO] Finished loading file system")

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

    # 83 087 673
    # 00 288 957
    # 99,65 %
    return(saving)

setUp()
