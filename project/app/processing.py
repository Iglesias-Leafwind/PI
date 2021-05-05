import numpy as np
from imutils.object_detection import non_max_suppression
import cv2
import pytesseract
import re
from nltk.corpus import stopwords, words
from nltk.tokenize import word_tokenize

from exif import Image as ImgX

east = "frozen_east_text_detection.pb"
net = cv2.dnn.readNet(east)

def filterSentence(sentence):
    english_vocab = set(w.lower() for w in words.words())
    stop_words = set(w.lower() for w in stopwords.words('english'))
    word_tokens = word_tokenize(sentence)
    filtered = [word for word in word_tokens if word not in stop_words if len(word) >= 4 and (len(word)<=8 or word in english_vocab) ]
    return filtered


def getOCR(img_path):
        #load installed tesseract-ocr from users pc
    pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'
    custom_config = r'--oem 3 --psm 6'
    min_confidence = 0.6
    results = []
    #These must be multiple of 32
    newW = 128
    newH = 128
    image = cv2.imread(img_path)
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
            if(startX <= 0):
                startX = 1
            startY = int(startY * rH) - 20
            if(startY <= 0):
                startY = 1
            endX = int(endX * rW) + 20
            if(endX >= maxW):
                endX = maxW-1
            endY = int(endY * rH) + 20
            if(endY >= maxH):
                endY = maxH-1
            # draw the bounding box on the image
            ROI = orig[startY:endY, startX:endX]
            imageText = pytesseract.image_to_string(ROI, config=custom_config)
            result = imageText.replace("\x0c", " ").replace("\n", " ")
            results += (re.sub('[^0-9a-zA-Z -]+', '', result)).split(" ")

    #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Load image, grayscale, Gaussian blur, adaptive threshold
    gray = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (9,9), 0)
    thresh = cv2.adaptiveThreshold(blur,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV,11,30)

    # Dilate to combine adjacent text contours
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9,9))
    dilate = cv2.dilate(thresh, kernel, iterations=4)

    # Find contours, highlight text areas, and extract ROIs
    cnts = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]

    for c in cnts:
        area = cv2.contourArea(c)
        if area > 10000:
            x,y,w,h = cv2.boundingRect(c)
            ROI = orig[y:y+h, x:x+w]
            imageText = pytesseract.image_to_string(ROI, config=custom_config)
            result = imageText.replace("\x0c", " ").replace("\n", " ")
            results += (re.sub('[^0-9a-zA-Z -]+', '', result)).split(" ")

    #set(results)
    #Transform set into a single string
    #filter words
    retrn = []
    phrase = ""
    for ele in set(results):
        phrase += ele
        phrase += " "
    for elem in filterSentence(phrase):
        retrn += [elem]
    return set(retrn)


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

