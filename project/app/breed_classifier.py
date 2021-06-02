import cv2
import numpy as np
from keras.models import load_model

MODEL_PATH = 'app/resources/breedclassifier-model/breedclassifier'
IMG_SIZE = 299

class BreedClassifier:
    def __init__(self):
        self.model = load_model(MODEL_PATH)
        print('model finished loading!')
        self.breeds = ['abyssinian', 'american_bulldog', 'american_pit_bull_terrier', 'basset_hound', 'beagle', 'bengal', 'birman', 'bombay', 'boxer', 'british_shorthair', 'chihuahua', 'egyptian_mau', 'english_cocker_spaniel', 'english_setter', 'german_shorthaired', 'great_pyrenees', 'havanese', 'japanese_chin', 'keeshond', 'leonberger', 'maine_coon', 'miniature_pinscher', 'newfoundland', 'persian', 'pomeranian', 'pug', 'ragdoll', 'russian_blue', 'saint_bernard', 'samoyed', 'scottish_terrier', 'shiba_inu', 'siamese', 'sphynx', 'staffordshire_bull_terrier', 'wheaten_terrier', 'yorkshire_terrier']

    def predict_image(self, image):
        X = self.preprocess(image)

        pred_array = self.model.predict(X)
        pred_index = np.argmax(pred_array)
        conf = np.max(pred_array)

        print('PREDICTION:', self.breeds[pred_index].replace('_', ' '), conf)
        return self.breeds[pred_index].replace('_', ' '), conf

    def preprocess(self, image):
        X = [cv2.resize(image, (IMG_SIZE, IMG_SIZE))]
        return np.array(X).reshape(-1, IMG_SIZE, IMG_SIZE, 3)


