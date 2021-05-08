import json
import string
from os.path import join
import random
import imghdr

import numpy as np
from numpyencoder import NumpyEncoder
from app.face_recognition import FaceRecognition
from app.fileSystemManager import SimpleFileSystemManager
from app.models import ImageNeo, Person, Tag, Location, Country, City, Folder, ImageES
from app.object_extraction import ObjectExtract
from app.utils import ImageFeature, getImagesPerUri
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

obj_extr = ObjectExtract()
frr = FaceRecognition()

features = []
imageFeatures = []
fs = SimpleFileSystemManager()
model = VGGNet()


# used in getOCR
east = "frozen_east_text_detection.pb"
net = cv2.dnn.readNet(east)

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
    filtered = [word for word in word_tokens if word not in stop_words if
                len(word) >= 4 and (len(word) <= 8 or word in english_vocab)]
    return filtered


def uploadImages(uri):
    print("----------------------------------------------")
    print("            featrue extraction starts         ")
    print("----------------------------------------------")

    dirFiles = getImagesPerUri(uri)
    for dir in dirFiles.keys():
        img_list = dirFiles[dir]

        if not fs.exist(dir):
            lastNode = fs.createUriInNeo4j(dir)
        else:
            lastNode = fs.getLastNode(dir)

        folderNeoNode = Folder.nodes.get(id_=lastNode.id)

        for index, img_name in enumerate(img_list):
            img_path = os.path.join(dir, img_name)
            i = ImageFeature()

            read_image = cv2.imread(img_path)
            if read_image is None:
                continue
            hash = dhash(read_image)

            existed = ImageNeo.nodes.get_or_none(hash=hash)
            i.hash = hash

            if existed:  # if an image already exists in DB (found an ImageNeo with the same hashcode)
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

                image = ImageNeo(folder_uri=os.path.split(img_path)[0],
                                 name=img_name,
                                 processing=iJson,
                                 format=img_name.split(".")[1],
                                 width=width,
                                 height=height,
                                 hash=hash).save()

                image.folder.connect(folderNeoNode)

                res = obj_extr.get_objects(img_path)

                for object in res["name"]:
                    tag = Tag.nodes.get_or_none(name=object)
                    if tag is None:
                        tag = Tag(name=object).save()
                        tags.append(object)

                    image.tag.connect(tag)

                openimage, boxes = frr.getFaceBoxes(img_path)
                for b in boxes:
                    name = ''.join(random.choice(string.ascii_letters) for i in range(10))
                    frr.saveFaceIdentification(openimage, b, name)

                    p = Person.nodes.get_or_none(name=name) # TODO : get icon
                    if p is None:
                        p = Person(name=name).save()
                        tags.append(name)
                    image.person.connect(p, {'coordinates': list(b)})

                places = getPlaces(img_path)
                if places:
                    places = places.split("/")
                    for place in places:
                        p = " ".join(place.split("_")).strip()
                        t = Tag.nodes.get_or_none(name=p)
                        if t is None:
                            t = Tag(name=p).save()
                            tags.append(p)
                        image.tag.connect(t)

                wordList = getOCR(read_image)
                if wordList and len(wordList) > 0:
                    for word in wordList:
                        t = Tag.nodes.get_or_none(name=word)
                        if t is None:
                            t = Tag(name=word).save()
                            tags.append(word)
                        image.tag.connect(t)

                l = Location.nodes.get_or_none(name="UA")
                if l is None:
                    l = Location(name="UA").save()

                image.location.connect(l, {"latitude": 10.0, "longitude": 20.0, "altitude": 30.0})

                c = City.nodes.get_or_none(name="Aveiro")
                if c is None:
                    c = City(name="Aveiro").save()

                l.city.connect(c, {"latitude": 10.0, "longitude": 20.0, "altitude": 30.0})

                ct = Country.nodes.get_or_none(name="PT")
                if ct is None:
                    ct = Country(name="PT").save()

                c.country.connect(ct, {"latitude": 10.0, "longitude": 20.0, "altitude": 30.0})

                # add features to "cache"
                features.append(norm_feat)
                i.features = norm_feat
                imageFeatures.append(i)

                ImageES(meta={'id': image.hash}, uri=uri, tags=tags, hash=image.hash).save(using=es)

            print("extracting feature from image %s " % (img_path))

def alreadyProcessed(img_path):
    image = cv2.imread(img_path)
    hash = dhash(image)
    existed = ImageNeo.nodes.get_or_none(hash=hash)

    return True if existed else False

def findSimilarImages(uri):
    norm_feat, height, width = model.vgg_extract_feat(uri)  # extrair infos
    feats = np.array(features)
    scores = np.dot(norm_feat, feats.T)
    rank = np.argsort(scores)[::-1]
    rank_score = scores[rank]

    maxres = 40  # 40 imagens com maiores scores

    imlist = []
    for i, index in enumerate(rank[0:maxres]):
        imlist.append(imageFeatures[index])
        print("image names: " + str(imageFeatures[index].name) + " scores: %f" % rank_score[i])


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
    # load installed tesseract-ocr from users pc
    pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'
    custom_config = r'--oem 3 --psm 6'
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
                if ("pixel_x_dimension" in current_image.list_all()):
                    returning["width"] = current_image.pixel_x_dimension
                if ("pixel_y_dimension" in current_image.list_all()):
                    returning["height"] = current_image.pixel_y_dimension
                if ("gps_latitude" in current_image.list_all()):
                    returning["latitude"] = current_image.gps_latitude
                if ("gps_longitude" in current_image.list_all()):
                    returning["longitude"] = current_image.gps_longitude
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

    for image in images:
        i = ImageFeature(**json.loads(image.processing))
        if i.features is None:
            continue
        i.features = np.array(json.loads(i.features))
        features.append(i.features)
        imageFeatures.append(i)

        tags = [tag.name for tag in image.tag]
        persons = [p.name for p in image.person]

        locations = set()
        for l in image.location:
            locations.add(l.name)

            for c in l.city:
                locations.add(c.name)

                for ct in c.country:
                    locations.add(ct.name)

        locations = list(locations)

        tags.extend(persons)
        tags.extend(locations)

        uri = join(image.folder_uri, image.name)
        try:
            savedImage = ImageES.get(using=es, index='image', id=image.hash)
            savedImage.update(using=es, index='image', tags=tags)
            savedImage.save()

        except:
            savedImage = ImageES(meta={'id': image.hash}, uri=uri, tags=tags, hash=image.hash).save(using=es)


    loadCatgoriesPlaces()
    loadFileSystemManager()

def generateThumbnail(imagepath):
    thumbnailH = 225
    thumbnailW = 225

    # load the input image
    image = cv2.imread(imagepath)
    w,h, = image.shape
    ratio = w/h
    thumbnailW = int(thumbnailH * ratio)
    dim = (thumbnailH,thumbnailW)

    # resize image
    resized = cv2.resize(image, dim, interpolation = cv2.INTERAREA)
    saving = "/thumbnails/" + re.split("[\\\/]+", imagepath)[-1]
    cv2.imwrite(saving , resized,  [cv2.IMWRITE_JPEG_QUALITY, 25])
    # 83 087 673
    # 00 288 957
    # 99,65 %
    return(saving)


setUp()