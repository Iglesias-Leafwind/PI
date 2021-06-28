## @package app
#  Image feature extraction module
#
#  More details.
import numpy as np
from tensorflow.python.keras.applications.vgg16 import VGG16
from tensorflow.python.keras.applications.vgg16 import preprocess_input
from tensorflow.python.keras.preprocessing import image
from numpy import linalg as LA

## VGG class that will be called throughout the project.
#
#  More details.
class VGGNet:
    ## The constructor.
    def __init__(self):

        self.input_shape = (224, 224, 3)
        self.weight = 'imagenet'
        self.pooling = 'max'
        self.model_vgg = VGG16(weights=self.weight,
                               input_shape=(self.input_shape[0], self.input_shape[1], self.input_shape[2]),
                               pooling=self.pooling, include_top=False)
        self.model_vgg.predict(np.zeros((1, 224, 224, 3)))

    ## Method to extract image features.
    #  @type img_path String
    #  @param img_path Image path of the image whom the features will be extracted from.
    #  @rtype norm_feat numpyarray
    #  @return norm_feat Returns a variable with the features extracted
    def vgg_extract_feat(self, img_path):
        img = image.load_img(img_path, target_size=(self.input_shape[0], self.input_shape[1]))
        img = image.img_to_array(img)
        img = np.expand_dims(img, axis=0)
        img = preprocess_input(img)
        feat = self.model_vgg.predict(img)
        norm_feat = feat[0] / LA.norm(feat[0])

        return norm_feat
