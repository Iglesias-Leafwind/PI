import json
from os.path import join

import numpy as np
from numpyencoder import NumpyEncoder

from manage import es

from app.models import ImageNeo, Person, Tag, Location, Country, City, ImageES
from app.utils import get_imlist, ImageFeature

import torch
from torch.autograd import Variable as V
import torchvision.models as models
from torchvision import transforms as trn
from torch.nn import functional as F
import os
from PIL import Image
from app.VGG_ import VGGNet



class Preprocessing():
    features = []
    imageFeatures = []

    model = VGGNet()

    def uploadImages(self, uri):
        print("----------------------------------------------")
        print("            featrue extraction starts         ")
        print("----------------------------------------------")

        img_list = get_imlist(uri)
        s = set(self.imageFeatures)
        for index, img_path in enumerate(img_list):
            img_name = os.path.split(img_path)[1]
            i = ImageFeature(img_path)
            if i in s:
                print("Image " + img_path + " has already been processed")
                continue

            norm_feat, height, width = self.model.vgg_extract_feat(img_path)  # extrair infos
            f = json.dumps(norm_feat, cls=NumpyEncoder)
            iJson = json.dumps(i.__dict__)

            image = ImageNeo(folder_uri=os.path.split(img_path)[0],
                             name=img_name,
                             processing=iJson,
                             format=img_name.split(".")[1],
                             width=width,
                             height=height)
            image.save()
            p = Person(name="wei")
            p.save()
            image.person.connect(p, {'coordinates':0.0})

            place = self.getPlaces(img_path)
            if place:
                t = Tag(name=place)
                t.save()
                image.tag.connect(t)

            l = Location(name="UA")
            l.save()
            image.location.connect(l, {"latitude":10.0, "longitude":20.0, "altitude":30.0})

            c = City(name="Aveiro")
            c.save()
            l.city.connect(c)

            ct = Country(name="PT")
            ct.save()
            ct.city.connect(c)

            # add features to "cache"
            self.features.append(norm_feat)
            i.features = np.array(json.loads(f))
            self.imageFeatures.append(i)
            s.add(i)

            print("extracting feature from image No. %d , %d images in total " % ((index + 1), len(img_list)))


    def findSimilarImages(self, uri):
        norm_feat = self.model.vgg_extract_feat(uri)  # extrair infos
        feats = np.array(self.features)
        scores = np.dot(norm_feat, feats.T)
        rank = np.argsort(scores)[::-1]
        rank_score = scores[rank]

        maxres = 40  # 40 imagens com maiores scores

        imlist = []
        for i, index in enumerate(rank[0:maxres]):
            imlist.append(self.imageFeatures[index])
            print("image names: " + str(self.imageFeatures[index].name) + " scores: %f" % rank_score[i])


    def getPlaces(self, img_name):
        # th architecture to use
        arch = 'resnet18'

        # load the pre-trained weights
        model_file = '%s_places365.pth.tar' % arch
        model = models.__dict__[arch](num_classes=365)
        checkpoint = torch.load(model_file, map_location=lambda storage, loc: storage)
        state_dict = {str.replace(k, 'module.', ''): v for k, v in checkpoint['state_dict'].items()}
        model.load_state_dict(state_dict)
        model.eval()

        # load the image transformer
        centre_crop = trn.Compose([
            trn.Resize((256, 256)),
            trn.CenterCrop(224),
            trn.ToTensor(),
            trn.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

        # load the test image
        img = Image.open(img_name)
        input_img = V(centre_crop(img).unsqueeze(0))

        # forward pass
        logit = model.forward(input_img)
        h_x = F.softmax(logit, 1).data.squeeze()
        probs, idx = h_x.sort(0, True)

        return classes[idx[0]]



    # load all images to memory
    def __init__(self):
        print('setUp')
        images = ImageNeo.nodes.all()

        for image in images:
            i = ImageFeature(**json.loads(image.processing))
            if i.features is None:
                continue
            i.features = np.array(json.loads(i.features))
            self.features.append(i.features)
            self.imageFeatures.append(i)

            tags = []
            for tag in image.tag:
                tags.append(tag.name)

            persons = []
            for p in image.person:
                persons.append(p.name)

            locations = set()
            for l in image.location:
                locations.add(l.name)

                for c in l.city:
                    locations.add(c.name)

                    for ct in c.country:
                        locations.add(ct.name)

            locations = list(locations)

            uri = join(image.folder_uri, image.name)
            ImageES(meta={'id': uri}, uri=uri,
                    tags=tags, locations=locations, persons=persons)\
                .save(using=es)

        # load the class label for scene recognition
        file_name = 'categories_places365.txt'
        global classes
        classes = list()
        with open(file_name) as class_file:
            for line in class_file:
                classes.append(line.strip().split(' ')[0][3:])
        classes = tuple(classes)
        print('fim setup')

