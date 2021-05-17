import os
from collections import defaultdict
import cv2
import numpy as np

import face_recognition as fr


PEN_THRESHOLD = 50

class FaceRecognition:
    def __init__(self):
        self.name2encodings = defaultdict(list)

    def getFaceBoxes(self, open_img=None, image_path=None):
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

    def saveFaceIdentification(self, image, box, name, conf=1, encoding=None):
        face_encoding = encoding
        if face_encoding is None:
            # dados numericos que representam aquela cara naquela imagem:
            face_encoding = fr.face_encodings(image, [box])

        # guardar esses dados associados ao seu nome
        self.name2encodings[name].append((face_encoding, conf))

        # ver o que retornar aqui para q seja guardado
        print('guardou nova cara!! : ', name)
        return face_encoding

    def getTheNameOf(self, image, box):
        print('entrou 1')

        encoding = fr.face_encodings(image, [box])[0] # a len vai ser smp 1

        if self.name2encodings == {}:
            return None, encoding, 1
        matches = {}
        unknown = 0

        unknown_list = []
        # print(exp)
        for k in self.name2encodings:
            print('entrou no loop')
            # lista de booleanos com os encodings q ele achou parecidos
            # if len(self.name2encodings[k]) <10:
            #    continue
            n = len(self.name2encodings[k])
            print('n : ', n)


            listt = fr.face_distance([ a for (a, b) in self.name2encodings[k] ], encoding) #, tolerance=0.2)
            listt = np.multiply(-1, np.add(listt, -1))
            # listt = [True if all(i) else False for i in listt]
            pen = 0 if n >= PEN_THRESHOLD else (PEN_THRESHOLD - n)/PEN_THRESHOLD
            print('pen : ', pen)

            score = np.multiply(listt, 0.85) + np.multiply(0.15, np.array([ b for (a, b) in self.name2encodings[k] ]))
            print('score1 : ', score)

            score = np.average(score) - pen * 0.1
            print('score2 : ', score)

            # sum(listt) vai ser o nr de 'Trues' da funcao de cima
            #matches[sum(listt)] = k

            matches[score] = k
            unknown_list.append(len(listt) - sum(listt))
            # unknown += len(listt) - sum(listt)

        if matches == {}:
            return None, encoding, 1

        print('fim')
        maxx = max(matches.keys())
        if maxx < 0.4:
            return None, encoding, 1
        #name = None if unknown>maxx else matches[maxx]
        name = matches[maxx]
        return name, encoding, maxx

"""
def teste():
    print('tá a correr o teste!')
    frr = FaceRecognition()
    # 1o vou buscar as pastas:
    path1 = '/home/mar/Documents/UA/6-semester/PI/learning/face-rec/dataset2/Diogo/'
    path2 = '/home/mar/Documents/UA/6-semester/PI/learning/face-rec/dataset2/Mariana/'
    i = 0
    # passar por tds os ficheiros dentro de cada uma
    l = [ path1 + f for f in os.listdir(path1) if f[-4:] == '.jpg']
    print(l)
    for foto in l:
        image, boxes = frr.getFaceBoxes(foto)
        for b in boxes:
            frr.saveFaceIdentification(image, b, 'Diogo')
        print('foto no.', i)
        i+=1
    print('acabou de treinar nas do diogo.')
    i = 0
    # passar por tds os ficheiros dentro de cada uma (v2)
    l = [ path2 + f for f in os.listdir(path2) if f[-4:] == '.jpg']
    for foto in l:
        image, boxes = frr.getFaceBoxes(foto)
        for b in boxes:
            frr.saveFaceIdentification(image, b, 'Mariana')
        print('foto no.', i)
        i+=1
    print('acabou de treinar nas da mariana.')
    # por fim, testar!
    foto_teste = '/home/mar/Documents/UA/6-semester/PI/learning/face-rec/examples/teste6.jpg'
    image, boxes = frr.getFaceBoxes(foto_teste)
    i = 0
    print('hm')
    for b in boxes:
        name = frr.getTheNameOf(image, b)
        print(i,'Encontrou '+ name +'!!')
        i+=1
    print('//')
teste()
"""