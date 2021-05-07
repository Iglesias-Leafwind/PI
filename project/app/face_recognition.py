import os
from collections import defaultdict
import cv2
import face_recognition as fr

class FaceRecognition:
    def __init__(self):
        self.name2encodings = defaultdict(list)

    def getFaceBoxes(self, image_path):
        # 'lê' a imagem (dependendo de como esta funcao é chamada, pode-se
        # alterar o parametro para que já entre a imagem 'lida'
        # assim poupa-se tempo!
        image = cv2.imread(image_path)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # detect the (x, y) coordinates of the bounding boxes
        # corresponding to each face
        # model = 'cnn' for accuracy; 'hog' for performance (on CPU, for ex.)
        boxes = fr.face_locations(rgb, model='hog')

        # once again, ver o q retornar dependendo do que é necessário
        return image, boxes

    def saveFaceIdentification(self, image, box, name):
        # dados numericos que representam aquela cara naquela imagem:
        face_encoding = fr.face_encodings(image, [box])

        # guardar esses dados associados ao seu nome
        self.name2encodings[name].append(face_encoding)

        # ver o que retornar aqui para q seja guardado

    def getTheNameOf(self, image, box):
        encoding = fr.face_encodings(image, [box])[0] # a len vai ser smp 1

        matches = {}
        unknown = 0
        # print(exp)
        for k in self.name2encodings:
            # lista de booleanos com os encodings q ele achou parecidos
            listt = fr.compare_faces(self.name2encodings[k], encoding, tolerance=0.2)
            listt = [True if all(i) else False for i in listt]
            print(listt)
            # sum(listt) vai ser o nr de 'Trues' da funcao de cima
            # aqui o sum nao sei se devia ser uma percentagem ou nao...
            # mas para casos em q so tem 1 imagem n ia correr mt bem isso
            matches[sum(listt)] = k
            unknown += len(listt) - sum(listt)

        # definir qual é o criterio..
        # quando é que aparece unknown? quando nenhum encoding
        # é parecido? ou quando não chega a uma percentagem?

        # neste momento está a dar unknown se for mais q 50%
        maxx = max(matches.keys())
        name = 'unknown' if unknown>maxx else matches[maxx]
        return name
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