import json
import string
import reverse_geocoder as rg
import threading
from app.face_recognition import FaceRecognition
from app.breed_classifier import BreedClassifier
from datetime import datetime
from urllib.parse import unquote
import random
import numpy as np
from neomodel import db
from numpyencoder import NumpyEncoder
from app.fileSystemManager import SimpleFileSystemManager
from app.models import ImageNeo, Person, Tag, Location, Country, City, Folder, ImageES, Region
from app.object_extraction import ObjectExtract
from app.utils import ImageFeature, get_images_per_uri, ImageFeaturesManager, ocrLock, processingLock, resultsLock, uploadLock, objectLock, breedLock,locationLock,faceRecLock,placesLock, lock
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



def testing_thread_capacity():
    global cpuPerThread
    global ramPerThread

    dir_path = os.path.dirname(os.path.realpath(__file__))
    dir_path = os.path.join(dir_path,"static/tests")
    threadTasks[dir_path] = 0
    wait = do(processing, {dir_path: ["face.jpg"]})
    cpu_normal = psutil.cpu_percent()
    ram_normal = psutil.virtual_memory().percent

    cpu_sum = 0
    ram_sum = 0
    iterating = 0
    while not wait.done():
        time.sleep(0.1)
        cpu_sum += psutil.cpu_percent()
        ram_sum += psutil.virtual_memory().percent
        iterating += 1

    cpu_med = (cpu_sum / iterating)
    ram_med = (ram_sum / iterating)

    delete_folder(dir_path, frr)
    cpuPerThread = cpu_med - cpu_normal
    cpuPerThread /= 2

    if(cpuPerThread <= 0):
        cpuPerThread = (cpuPerThread * -1) + 1

    ramPerThread = ram_med - ram_normal
    ramPerThread /= 2

    if(ramPerThread <= 0):
        ramPerThread = (ramPerThread * -1) + 1
        
logging.info("[Loading]: [INFO] Loading Object Extraction")
obj_extr = do(ObjectExtract)

logging.info("[Loading]: [INFO] Loading face recognition")
frr = do(FaceRecognition)

logging.info("[Loading]: [INFO] Loading breed classifier")
bc = do(BreedClassifier)

while not obj_extr.done():
    time.sleep(0.1)

obj_extr = obj_extr.result()
logging.info("[Loading]: [INFO] Finished loading Object Extraction")

while not frr.done():
    time.sleep(0.1)
frr = frr.result()
logging.info("[Loading]: [INFO] Finished loading face recognition")

while not bc.done():
    time.sleep(0.1)
bc = bc.result()
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



def filter_sentence(sentence):
    english_vocab = set(w.lower() for w in words.words())
    stop_words = set(w.lower() for w in stopwords.words('english'))
    word_tokens = word_tokenize(sentence)
    filtered = [word.lower() for word in word_tokens if word not in stop_words if
                len(word) >= 4 and (len(word) <= 8 or word in english_vocab)]
    return filtered

def upload_images(uri):
    logging.info("----------------------------------------------")
    logging.info("            feature extraction starts         ")
    logging.info("----------------------------------------------")

    dir_files = get_images_per_uri(uri)

    cpu_curr = psutil.cpu_percent()
    ram_curr = psutil.virtual_memory().percent
    free_cpu = (100 - cpu_curr) / 5
    free_ram = (100 - ram_curr) / 5
    threads = free_cpu / cpuPerThread
    threads_ram = free_ram / ramPerThread

    if(threads_ram < threads):
        threads = threads_ram
    threads = int(threads)
    if(threads > numThreads):
        threads = numThreads

    if(threads <= 0):
        threads = 1
    threads = int(threads)
    logging.info("[Uploading]: Dividing")
    tasks = divide_tasks_to_many(dir_files, threads)
    folders = []
    for task in tasks:
        logging.info("[Processing]: [INFO] Task found: " + str(task))
        folders += list(task.keys())
    folders = list(set(folders))
    logging.info("[Uploading]: Folders found " + str(folders))
    try:
        uploadLock.acquire()
        for dir_path in folders:
            if dir_path in threadTasks:
                [task.pop(dir_path) for task in tasks if dir_path in task.keys()]
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

def divide_tasks_to_many(dir_files, qty):
    threading = 0
    tasks = []

    for _ in range(1, qty + 1):
        tasks.append({})

    # dirFiles -> {key: values}  key -> C:users/user/databse, values-> 1.jpg, 2.jpg
    for path in dir_files.keys():
        for image in dir_files[path]:
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
    openimage, boxes = frr.get_face_boxes(open_img=read_image, image_path=img_path)

    for b in boxes:
        name, enc, conf = frr.get_the_name_of(openimage, b)
        if name is None:
            # esta verificacao terá de ser alterada para algo mais preciso
            # por exemplo, definir um grau de certeza
            name = ''.join(random.choice(string.ascii_letters) for _ in range(10))
        frr.save_face_identification(name=name, encoding = enc, conf=conf, imghash=image.hash)

        face_thumb_path = os.path.join('static', 'face-thumbnails', str(int(round(time.time() * 1000))) + '.jpg')
        app.utils.get_face_thumbnail(openimage, b, save_in=os.path.join('app', face_thumb_path))
        p = Person.nodes.get_or_none(name=name)
        if p is None:
            p = Person(name=name).save()

        tags.append(name)

        # encodings falta
        image.person.connect(p, {'coordinates': list(b), 'icon': face_thumb_path, 'confiance': conf, 'encodings': enc, 'approved': False})
        # """

def classify_breed_part(read_image, tags, image_db):
    breed, breed_conf = bc.predict_image(read_image)
    if breed_conf > app.utils.breedsThreshold:
        tags.append(breed)

        tag = Tag.nodes.get_or_none(name=breed)
        if tag is None:
            tag = Tag(name=breed).save()
        image_db.tag.connect(tag, {'originalTagName':breed, 'originalTagSource': 'breeds', 'score':breed_conf})

def processing(dir_files):
    proc_string = "[Processing]:"

    add_thread_tasks(dir_files)

    for dir in dir_files.keys():
        img_list = dir_files[dir]

        last_node = check_if_folder_exists_and_create_it(dir)

        at_least_one = False
        folder_neo_node = Folder.nodes.get(id_=last_node.id)
        for index, img_name in enumerate(img_list):
            skip, at_least_one = extraction_process(at_least_one, dir, folder_neo_node, img_list, img_name, index,
                                              proc_string)
            if skip:
                continue
        if not at_least_one:
            try:
                processingLock.acquire()
                fs.delete_folder_from_fs(dir, frr)
            finally:
                processingLock.release()

        subtract_thread_tasks(dir)

    remove_thread_tasks()

    logging.info("[Processing]: [INFO] Tasks to be completed: " + str(threadTasks))


def extraction_process(at_least_one, dir, folder_neo_node, img_list, img_name, index, proc_string):
    try:
        img_path = os.path.join(dir, img_name)
        logging.info(
            proc_string + " " + threading.current_thread().name + " [INFO] Doing " + str(index + 1) + " / " + str(
                len(img_list)))

        logging.info(proc_string + " " + threading.current_thread().name + " [INFO] I am in " + img_path)
        i = ImageFeature()

        read_image = cv2.imread(img_path)
        (h, w) = read_image.shape[:2]
        if read_image is None:
            logging.info(
                proc_string + " " + threading.current_thread().name + " [ERR] Read of " + img_path + " is None")
            return True, at_least_one
        image_hash = dhash(read_image)

        existed = ImageNeo.nodes.get_or_none(hash=image_hash)
        i.hash = image_hash

        if existed:  # if an image already exists in DB (found an ImageNeo with the same hashcode)

            logging.info(
                proc_string + " " + threading.current_thread().name + " [INFO] Image " + img_path + " has already been processed")

            skip, at_least_one = check_dir_and_connect(at_least_one, dir, existed, folder_neo_node)
            if skip:
                return True, at_least_one
        else:
            tags = []

            image, norm_feat, propertiesdict = creating_image_neo_object_and_extracting_exif_and_image_features(
                h, w, image_hash, i, img_name, img_path, proc_string)

            skip, at_least_one = checking_if_image_exists(at_least_one, dir, folder_neo_node, image, image_hash,
                                                          img_path, proc_string)
            if skip:
                return True, at_least_one
            skip = extract_locations(image, img_path, proc_string, propertiesdict, tags)
            if skip:
                return True, at_least_one

            image.folder.connect(folder_neo_node)

            extract_objects_and_breeds(image, img_path, proc_string, read_image, tags)

            extract_faces(image, img_path, proc_string, read_image, tags)

            extract_places(image, img_path, proc_string, tags)

            extract_text(image, img_path, proc_string, read_image, tags)

            adding_to_es(i, image, img_path, norm_feat, tags)

            completed = index + 1
            logging.info(proc_string + " " + threading.current_thread().name + " [INFO] Finished " + img_path)
            logging.info(
                proc_string + " " + threading.current_thread().name + " [INFO] Done " + str(completed) + " / " + str(
                    len(img_list)))
            at_least_one |= True
    except Exception as e:
        logging.info("[Processing]: [ERR] In " + threading.current_thread().name + ": " + str(e))
    return False, at_least_one


def check_dir_and_connect(at_least_one, dir, existed, folder_neo_node):
    if existed.folder_uri == dir:
        at_least_one |= True
        return True, at_least_one
    try:
        processingLock.acquire()
        # if the current image's folder is different
        existed.folder.connect(folder_neo_node)
    finally:
        processingLock.release()
    at_least_one |= True
    return True, at_least_one


def checking_if_image_exists(at_least_one, dir, folder_neo_node, image, image_hash, img_path, proc_string):
    try:
        processingLock.acquire()
        existed = ImageNeo.nodes.get_or_none(hash=image_hash)
        if existed:
            if existed.folder_uri != dir:
                # if the current image's folder is different
                existed.folder.connect(folder_neo_node)
            at_least_one |= True
            logging.info(
                proc_string + " " + threading.current_thread().name + " [INFO] Image " + img_path + " already exists!")
            return True, at_least_one
        try:
            image.save()
            at_least_one |= True
        except Exception as e:
            logging.info(proc_string + " " + threading.current_thread().name + " [ERR] Saving image err " + str(e))
            return True, at_least_one
    finally:
        processingLock.release()
    return False, at_least_one


def extract_locations(image, img_path, proc_string, propertiesdict, tags):
    if "latitude" in propertiesdict and "longitude" in propertiesdict:
        # crc = [city,region,country] names array
        try:
            locationLock.acquire()
            logging.info(proc_string + " " + threading.current_thread().name + " [INFO] Location of " + img_path)
            crc = get_locations(propertiesdict["latitude"], propertiesdict["longitude"])
            crc[0] = crc[0].lower()
            crc[1] = crc[1].lower()
            crc[2] = crc[2].lower()
        finally:
            locationLock.release()

        try:
            processingLock.acquire()
            db.begin()
            location = Location.nodes.get_or_none(name=crc[0])
            if location is None:
                location = Location(name=crc[0]).save()

            tags.append(crc[0])
            image.location.connect(location,
                                   {'latitude': propertiesdict["latitude"], 'longitude': propertiesdict["longitude"]})

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
        except Exception as e:
            logging.info(proc_string + " " + threading.current_thread().name + " [ERR] Extracting locations " + str(e))
            db.rollback()
            return True
        finally:
            processingLock.release()
    return False


def adding_to_es(i, image, img_path, norm_feat, tags):
    # add features to "cache"
    try:
        resultsLock.acquire()
        ftManager.np_features.append(norm_feat)
        i.features = norm_feat
        ftManager.image_features.append(i)
    finally:
        resultsLock.release()
    ImageES(meta={'id': image.hash}, uri=img_path, tags=tags, hash=image.hash).save(using=es)


def extract_text(image, img_path, proc_string, read_image, tags):
    try:
        ocrLock.acquire()
        logging.info(proc_string + " " + threading.current_thread().name + " [INFO] OCR of " + img_path)

        word_list = get_ocr(read_image)
    finally:
        ocrLock.release()
    if word_list and len(word_list) > 0:
        for word in word_list:
            try:
                processingLock.acquire()
                t = Tag.nodes.get_or_none(name=word)
                if t is None:
                    t = Tag(name=word).save()
                tags.append(word)
                image.tag.connect(t, {'originalTagName': word, 'originalTagSource': 'ocr', 'score': 0.6})
            finally:
                processingLock.release()


def extract_places(image, img_path, proc_string, tags):
    try:
        placesLock.acquire()
        logging.info(proc_string + " " + threading.current_thread().name + " [INFO] Places of " + img_path)

        places_list = get_places(img_path)
    finally:
        placesLock.release()
    for places, prob in places_list:

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


def extract_faces(image, img_path, proc_string, read_image, tags):
    try:
        faceRecLock.acquire()
        logging.info(proc_string + " " + threading.current_thread().name + " [INFO] Face Recognition of " + img_path)

        db.begin()
        face_rec_part(read_image, img_path, tags, image)
        db.commit()
    finally:
        faceRecLock.release()


def extract_objects_and_breeds(image, img_path, proc_string, read_image, tags):
    try:
        objectLock.acquire()
        logging.info(proc_string + " " + threading.current_thread().name + " [INFO] Objects of " + img_path)
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
            image.tag.connect(tag, {'originalTagName': object, 'originalTagSource': 'object', 'score': confidence})
        finally:
            processingLock.release()

        if object in ['cat', 'dog']:
            try:
                breedLock.acquire()
                logging.info(proc_string + " " + threading.current_thread().name + " [INFO] Breeds of " + img_path)

                classify_breed_part(read_image, tags, image)
            finally:
                breedLock.release()


def creating_image_neo_object_and_extracting_exif_and_image_features(h, w, image_hash, i, img_name, img_path, proc_string):
    # extract infos
    norm_feat = model.vgg_extract_feat(img_path)
    f = json.dumps(norm_feat, cls=NumpyEncoder)
    i.features = f
    i_json = json.dumps(i.__dict__)
    logging.info(proc_string + " " + threading.current_thread().name + " [INFO] Exif of " + img_path)
    propertiesdict = get_exif(img_path)
    logging.info(proc_string + " " + threading.current_thread().name + " [INFO] Thumbnail of " + img_path)
    generate_thumbnail(img_path, image_hash)
    if "datetime" in propertiesdict:
        image = ImageNeo(folder_uri=os.path.split(img_path)[0],
                         name=img_name,
                         processing=i_json,
                         format=img_name.split(".")[1],
                         width=w,
                         height=h,
                         hash=image_hash,
                         creation_date=propertiesdict["datetime"],
                         insertion_date=datetime.now())
    else:
        image = ImageNeo(folder_uri=os.path.split(img_path)[0],
                         name=img_name,
                         processing=i_json,
                         format=img_name.split(".")[1],
                         width=w,
                         height=h,
                         hash=image_hash,
                         insertion_date=datetime.now())
    return image, norm_feat, propertiesdict


def check_if_folder_exists_and_create_it(dir):
    try:
        processingLock.acquire()
        db.begin()
        if not fs.exist(dir):
            last_node = fs.create_uri_in_neo4j(dir)
        else:
            last_node = fs.get_last_node(dir)
    finally:
        db.commit()
        processingLock.release()
    return last_node


def remove_thread_tasks():
    try:
        uploadLock.acquire()
        for dir in threadTasks:
            if threadTasks[dir] == 0:
                threadTasks.pop(dir)
    finally:
        uploadLock.release()


def subtract_thread_tasks(dir):
    try:
        uploadLock.acquire()
        threadTasks[dir] -= 1
    finally:
        uploadLock.release()


def add_thread_tasks(dir_files):
    for dir in dir_files.keys():
        try:
            uploadLock.acquire()
            threadTasks[dir] += 1
        finally:
            uploadLock.release()


def get_locations(latitude, longitude):
    results = rg.search((latitude,longitude), mode=1)
    return [results[0]['name'], results[0]['admin2'], results[0]['admin1']]


def already_processed(img_path):
    image = cv2.imread(img_path)
    image_hash = dhash(image)
    existed = ImageNeo.nodes.get_or_none(hash=image_hash)

    return existed

to_be_deleted = set()
deleting = False
def delete_folder(uri, frr=frr):
    logging.info("[Deleting]: [INFO] Trying to delete " + uri)
    deleted_images = None
    global deleting, to_be_deleted

    lock.acquire()
    try:
        if deleting:
            to_be_deleted.add(uri)
            logging.info("[Deleting]: [INFO] Uri " + uri +  " added to to_be_deleted, waiting..." )
            return
    finally:
        lock.release()

    if fs.exist(uri):
        try:
            processingLock.acquire()
            deleting = True
            deleted_images = fs.delete_folder_from_fs(uri, frr)
        finally:
            deleting = False
            processingLock.release()
    else:
        return

    logging.info("[Deleting]: [INFO] Finished deleting folder " + uri)
    if deleted_images is None or len(deleted_images) == 0:
        return

    resultsLock.acquire()
    try:
        imgfs = set(ftManager.image_features)
        for di in deleted_images:
            imgfs.remove(di)
        ftManager.image_features = list(imgfs)
        f = []
        for i in ftManager.image_features:
            f.append(i.features)

        ftManager.np_features = f
    finally:
        resultsLock.release()
    logging.info("[Deleting]: [INFO] Finished deleting images from cache")

    try:
        if len(to_be_deleted) != 0:
            delete_folder(to_be_deleted.pop(), frr)
    except Exception as e:
        logging.info("[Deleting]: [ERROR] " + str(e))

def find_similar_images(uri):
    if len(ftManager.np_features) == 0:
        return []
    norm_feat = model.vgg_extract_feat(uri)
    feats = np.array(ftManager.np_features)
    scores = np.dot(norm_feat, feats.T)
    rank = np.argsort(scores)[::-1]

    maxres = 42  # 42 imagens com maiores scores

    imlist = []
    for i, index in enumerate(rank[0:maxres]):
        imlist.append(str(ftManager.image_features[index].hash))

    return imlist

def get_all_images_of_folder(folder, page):
    folder = unquote(folder)
    folder = fs.get_last_node(folder)
    node = Folder.nodes.get_or_none(id_=folder.id)
    if node:
        results = node.getImagesByPage(page)
        if len(results):
            return [(i, i.tag.all(), i.getPersonsName()) for i in results]
    return []

def get_places(img_path):
    # load the test image
    img = Image.open(img_path).convert('RGB')
    input_img = V(centre_crop(img).unsqueeze(0))

    # forward pass
    logit = places_model.forward(input_img)
    h_x = F.softmax(logit, 1).data.squeeze()
    probs, idx = h_x.sort(0, True)

    return [(classes[idx[i]], probs[i]) for i in range(0, 10) if probs[i] > app.utils.placesThreshold]


def get_ocr(image):
    min_confidence = 0.6
    results = []
    # These must be multiple of 32
    new_w = 128
    new_h = 128
    orig = image.copy()
    (H, W) = image.shape[:2]

    # set the new width and height and then determine the ratio in change
    # for both the width and height
    r_w = W / float(new_w)
    r_h = H / float(new_h)

    # resize the image and grab the new image dimensions
    image = cv2.resize(image, (new_w, new_h))
    (H, W) = image.shape[:2]

    # define the two output layer names for the EAST detector model that
    # we are interested -- the first is the output probabilities and the
    # second can be used to derive the bounding box coordinates of text
    layer_names = [
        "feature_fusion/Conv_7/Sigmoid",
        "feature_fusion/concat_3"]

    # construct a blob from the image and then perform a forward pass of
    # the model to obtain the two output layer sets
    blob = cv2.dnn.blobFromImage(image, 1.0, (W, H),
                                 (123.68, 116.78, 103.94), swapRB=True, crop=False)

    net.setInput(blob)
    (scores, geometry) = net.forward(layer_names)

    # grab the number of rows and columns from the scores volume, then
    # initialize our set of bounding box rectangles and corresponding
    # confidence scores
    (num_rows, num_cols) = scores.shape[2:4]
    rects = []
    confidences = []
    # loop over the number of rows
    results = ocr_boxes_algorithm(confidences, geometry, min_confidence, num_cols, num_rows, orig, r_h, r_w, rects, results,
                                  scores)

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
            image_text = pytesseract.image_to_string(ROI, config=custom_config)
            result = image_text.replace("\x0c", " ").replace("\n", " ")
            results += (re.sub('[^0-9a-zA-Z ]+', '', result)).split(" ")

    # Transform set into a single string
    # filter words
    retrn = []
    phrase = ""
    for ele in set(results):
        phrase += ele
        phrase += " "
    for elem in filter_sentence(phrase):
        retrn += [elem]
    return set(retrn)


def ocr_boxes_algorithm(confidences, geometry, min_confidence, num_cols, num_rows, orig, r_h, r_w, rects, results, scores):
    for y in range(0, num_rows):
        # extract the scores (probabilities), followed by the geometrical
        # data used to derive potential bounding box coordinates that
        # surround text
        scores_data = scores[0, 0, y]
        x_data0 = geometry[0, 0, y]
        x_data1 = geometry[0, 1, y]
        x_data2 = geometry[0, 2, y]
        x_data3 = geometry[0, 3, y]
        angles_data = geometry[0, 4, y]
        # loop over the number of columns
        for x in range(0, num_cols):
            # if our score does not have sufficient probability, ignore it
            if scores_data[x] < min_confidence:
                continue
            # compute the offset factor as our resulting feature maps will
            # be 4x smaller than the input image
            (offset_x, offset_y) = (x * 4.0, y * 4.0)
            # extract the rotation angle for the prediction and then
            # compute the sin and cosine
            angle = angles_data[x]
            cos = np.cos(angle)
            sin = np.sin(angle)
            # use the geometry volume to derive the width and height of
            # the bounding box
            h = x_data0[x] + x_data2[x]
            w = x_data1[x] + x_data3[x]
            # compute both the starting and ending (x, y)-coordinates for
            # the text prediction bounding box
            end_x = int(offset_x + (cos * x_data1[x]) + (sin * x_data2[x]))
            end_y = int(offset_y - (sin * x_data1[x]) + (cos * x_data2[x]))
            start_x = int(end_x - w)
            start_y = int(end_y - h)
            # add the bounding box coordinates and probability score to
            # our respective lists
            rects.append((start_x, start_y, end_x, end_y))
            confidences.append(scores_data[x])
    # apply non-maxima suppression to suppress weak, overlapping bounding
    # boxes
    boxes = non_max_suppression(np.array(rects), probs=confidences)
    # loop over the bounding boxes
    (max_h, max_w) = orig.shape[:2]
    for (start_x, start_y, end_x, end_y) in boxes:
        # scale the bounding box coordinates based on the respective
        # ratios
        start_x = int(start_x * r_w) - 20
        if (start_x <= 0):
            start_x = 1
        start_y = int(start_y * r_h) - 20
        if (start_y <= 0):
            start_y = 1
        end_x = int(end_x * r_w) + 20
        if (end_x >= max_w):
            end_x = max_w - 1
        end_y = int(end_y * r_h) + 20
        if (end_y >= max_h):
            end_y = max_h - 1
        # draw the bounding box on the image
        ROI = orig[start_y:end_y, start_x:end_x]
        image_text = pytesseract.image_to_string(ROI, config=custom_config)
        result = image_text.replace("\x0c", " ").replace("\n", " ")
        results += (re.sub('[^0-9a-zA-Z ]+', '', result)).split(" ")
    return results


def dhash(image, hash_size=8):
    # convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # resize the grayscale image, adding a single column (width) so we
    # can compute the horizontal gradient
    resized = cv2.resize(gray, (hash_size + 1, hash_size))
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


def load_catgories_places():
    # load the class label for scene recognition
    file_name = 'categories_places365.txt'
    global classes
    classes = list()
    with open(file_name) as class_file:
        for line in class_file:
            classes.append(line.strip().split(' ')[0][3:])
    classes = tuple(classes)


def load_file_system_manager():
    roots = Folder.nodes.filter(root=True)

    if not roots: return

    def build_uri(node, uri, ids):
        if not node: return
        uri += node.name + "/"
        ids.append(node.id_)

        if node.terminated:
            fs.add_full_path_uri(uri, ids)

        for child in node.children:
            build_uri(child, uri, ids)
            ids.pop()  # backtracking

    for root in roots:
        uri = root.name + "/"
        ids = [root.id_]
        for child in root.children:
            build_uri(child, uri, ids)
            ids.pop()  # backtracking

class ExifNotFound(Exception):
    """Raised when the exif is not found"""
    pass

def get_exif(img_path):
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
                raise ExifNotFound

    except Exception:
        pass

    image = cv2.imread(img_path)
    (H, W) = image.shape[:2]
    returning["height"] = H
    returning["width"] = W
    return returning


# load all images to memory
def set_up():
    images = ImageNeo.nodes.all()
    npfeatures = []
    image_features = []

    for image in images:
        i = ImageFeature(**json.loads(image.processing))
        if i.features is None:
            continue
        i.features = np.array(json.loads(i.features))
        npfeatures.append(i.features)
        image_features.append(i)
    logging.info("[Loading]: [INFO] Loading places")
    plc = do(load_catgories_places)
    logging.info("[Loading]: [INFO] Loading file system")
    filess = do(load_file_system_manager)

    while not plc.done():
        time.sleep(0.1)
    logging.info("[Loading]: [INFO] Finished loading places")
    while not filess.done():
        time.sleep(0.1)
    logging.info("[Loading]: [INFO] Finished loading file system")

    ftManager.np_features = npfeatures
    ftManager.image_features = image_features
    testing_thread_capacity()

def generate_thumbnail(imagepath, image_hash):
    thumbnail_h = 225
    thumbnail_w = 225

    dim = (thumbnail_w, thumbnail_h)

    # load the input image
    image = cv2.imread(imagepath)
    h,w,p = image.shape

    padding_lr = 0
    padding_tb = 0
    if(w - thumbnail_w > h - thumbnail_h):
        ratio = thumbnail_w/w
        thumbnail_h = int(h * ratio)
        padding_tb = int((thumbnail_w-thumbnail_h)/2)
    else:
        ratio = thumbnail_h/h
        thumbnail_w = int(w * ratio)
        padding_lr = int((thumbnail_h-thumbnail_w)/2)

    image = cv2.copyMakeBorder(image, padding_tb, padding_tb, padding_lr, padding_lr, cv2.BORDER_REPLICATE)
    # resize image
    resized = cv2.resize(image, dim, interpolation = cv2.INTER_AREA)
    saving = os.path.join("app", "static", "thumbnails", str(image_hash)) + ".jpg"
    cv2.imwrite(saving, resized, [cv2.IMWRITE_JPEG_QUALITY, 25])

    # 83 087 673
    # 00 288 957
    # 99,65 %
    return(saving)

set_up()
