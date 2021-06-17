import os
import random
import string
from collections import defaultdict
import cv2
import numpy as np

import face_recognition as fr

from app.models import Person, DisplayA, ImageNeo, ImageES
from app.utils import faceRecThreshold
from scripts.esScript import es

PEN_THRESHOLD = 50

class FaceRecognition:
    def __init__(self):
        self.name2encodings = defaultdict(list) # [(face_encoding, conf, approved), ..]
        self.update_data()

    def update_data(self):
        all_people = Person.nodes.all()
        for p in all_people:
            rels = [ (img, rrr) for img in p.image.all() for rrr in p.image.all_relationships(img)]
            self.name2encodings[p.name] = [ (r[1].encodings, r[1].confiance, r[1].approved, r[0].hash) for r in rels ]

    def get_face_boxes(self, open_img=None, image_path=None):
        # 'lê' a imagem (dependendo de como esta funcao é chamada, pode-se
        # alterar o parametro para que já entre a imagem 'lida'
        # assim poupa-se tempo!
        assert not (open_img is None and image_path is None)
        if open_img is None:
            image = cv2.imread(image_path)
        else:
            image = open_img
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # detect the (x, y) coordinates of the bounding boxes
        # corresponding to each face
        # model = 'cnn' for accuracy; 'hog' for performance (on CPU, for ex.)
        boxes = fr.face_locations(rgb, model='hog')

        # once again, ver o q retornar dependendo do que é necessário
        return image, boxes

    def save_face_identification(self, image=None, box = None, name=None, conf=1, encoding=None, approved=False, imghash=None):
        face_encoding = encoding
        if face_encoding is None:
            # dados numericos que representam aquela cara naquela imagem:
            face_encoding = fr.face_encodings(image, [box])[0]

        if face_encoding is None or len(face_encoding) == 0:
            return None

        #print('save face id ', type(face_encoding))
        # guardar esses dados associados ao seu nome
        self.name2encodings[name].append((face_encoding, conf, approved, imghash))

        # ver o que retornar aqui para q seja guardado
        #print('guardou nova cara!! : ', name)
        return face_encoding

    def get_the_name_of(self, image=None, box=None, encoding=None):
        #print('entrou 1')

        if encoding is None:
            encoding = fr.face_encodings(image, [box])[0] # a len vai ser smp 1
            #print('encoding gerado: ', type(encoding))
        #else:
            #print('encoding dado: ', type(encoding))
            # encoding = encoding[0]

        if self.name2encodings == {}:
            return None, encoding, 1
        matches = {}
        unknown = 0

        unknown_list = []
        # print(exp)


        #print("names: ", self.name2encodings.keys())
        for k in self.name2encodings:
            if len(self.name2encodings[k]) == 0:
                #print('name q passou: ', k)
                continue

            #print('entrou no loop')
            # lista de booleanos com os encodings q ele achou parecidos
            # if len(self.name2encodings[k]) <10:
            #    continue
            n = len(self.name2encodings[k])
            #print('n : ', n)


            listt = fr.face_distance([ a[0] for a in self.name2encodings[k] ], encoding) #, tolerance=0.2)
            listt = np.multiply(-1, np.add(listt, -1))
            pen = 0 if n >= PEN_THRESHOLD else (PEN_THRESHOLD - n)/PEN_THRESHOLD
            #print('pen : ', pen)

            score = np.multiply(listt, 0.85) + np.multiply(0.15, np.array([ a[1] for a in self.name2encodings[k] ]))
            #print(k ,'score1 : ', score)

            score = np.average(score) - pen * 0.1
            #print(k, 'score2 : ', score)

            # sum(listt) vai ser o nr de 'Trues' da funcao de cima
            #matches[sum(listt)] = k

            matches[score] = k
            unknown_list.append(len(listt) - sum(listt))
            # unknown += len(listt) - sum(listt)

        if matches == {}:
            return None, encoding, 1

        #print('fim')
        maxx = max(matches.keys())
        if maxx < faceRecThreshold:
            return None, encoding, 1

        name = matches[maxx]
        return name, encoding, maxx

    def reload(self):
        self.temp = self.name2encodings
        self.name2encodings = defaultdict(list)
        # 1. vou buscar todos os 'approved'
        for k in self.temp:
            # if approved then GOOD
            self.name2encodings[k] = [ data for data in self.temp[k] if data[2]]

        for k in self.temp:
            # if not approved then BAD
            for enc, conf, appr, imghash in [data for data in self.temp[k] if not data[2]]:
                #print(appr , " <- should be false!!!! ")
                #print('changing some names')
                # first: we see who it is
                name, enc, conf = self.get_the_name_of(encoding=np.array(enc))
                if name is None:
                    name = ''.join(random.choice(string.ascii_letters) for _ in range(10))

                self.save_face_identification(name=name, encoding=enc, conf=conf, approved=appr, imghash=imghash) # appr == False

                # now we change the BD
                self.change_relationship(imghash, name, k, confiance=conf, approved=False, enc=enc)
                self.change_name_tag_es(imghash, name, k)


    # -- helper --
    def change_relationship(self, image_hash, new_personname, old_personname, confiance=1.0, approved=True, enc=None, thumbnail=None):
        img = ImageNeo.nodes.get_or_none(hash=image_hash)
        #if img is None:
            #print('IMAGE IS NONE')
            #print(image_hash, new_personname, old_personname, confiance, approved, enc, thumbnail)

        new_person = Person.nodes.get_or_none(name=new_personname)
        if new_person is None:
            new_person = Person(name=new_personname).save()
            #print('new person was created')

        old_person = Person.nodes.get_or_none(name=old_personname)
        #if old_person is None:
            #print('OLD PERSON IS NONE')

        existent_rel = old_person.image.all_relationships(img)

        #print('change relationship')
        to_stay = []
        neww = {}
        for ex_rel in existent_rel:
            relinfo = {
                'coordinates': ex_rel.coordinates,
                'encodings': ex_rel.encodings,
                'icon': ex_rel.icon,
                'confiance': ex_rel.confiance, #[0] if not isinstance(ex_rel.confiance, float) else ex_rel.confiance,
                'approved': ex_rel.approved
            }

            if (enc is not None and all([ex_rel.encodings[i] == enc[i] for i in range(len(enc))])) or (thumbnail is not None and thumbnail == ex_rel.icon):
                #print('found rel!!')
                # overwrite
                relinfo['confiance'] = confiance#[0] if not isinstance(confiance, float) else confiance,
                relinfo['approved'] = approved
                neww = relinfo
                continue
            to_stay.append(relinfo)

        old_person.image.disconnect(img)
        for relinfo in to_stay:
            if isinstance(relinfo['confiance'], tuple):
                #print('is tuple')
                relinfo['confiance'] = relinfo['confiance'][0]
            old_person.image.connect(img, relinfo)

        if neww == {}:
            return
        if isinstance(neww['confiance'], tuple):
            neww['confiance'] = neww['confiance'][0]
        img.person.connect(new_person, neww)

    def change_name_tag_es(self, image_hash, new_personname, old_personname):
        img = ImageES.get(using=es, id=image_hash)
        img_tags = img.tags
        if old_personname in img_tags:
            ind = img_tags.index(old_personname)
            img_tags.pop(ind)

        img_tags.append(new_personname)
        img.tags = img_tags
        img.update(using=es, tags=img.tags)
        img.save(using=es)

    def remove_image(self, image_hash):
        self.delete_thumbs(image_hash)

        # [(r[1].encodings, r[1].confiance, r[1].approved, r[0].hash) for r in rels]
        temp = self.name2encodings
        keys_to_remove = set()
        for k in temp:
            self.name2encodings[k] = [ data for data in temp[k] if data[3] != image_hash ]

            if len(self.name2encodings[k]) == 0:
                keys_to_remove.add(k)

        for k in keys_to_remove:
            del self.name2encodings[k]

            p = Person.nodes.get_or_none(name=k)
            if p is not None:
                p.delete()

    def delete_thumbs(self, image_hash):
        img = ImageNeo.nodes.get_or_none(hash=image_hash)
        if img is None:
            return

        people = img.person.all()
        thumbs = [rel.icon for rels in [img.person.all_relationships(p) for p in people] for rel in rels ]
        for t in thumbs:
            tt = os.path.join('app', t)
            if os.path.exists(tt):
                os.remove(tt)
            else:
                print("n existe")
                print(tt, t)
