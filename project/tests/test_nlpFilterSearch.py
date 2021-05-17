from django.test import TestCase
from app.models import ImageNeo
from app.nlpFilterSearch import *


class nlpTestCase(TestCase):

    def setUp(self):
        print("\n\\|/Testing NLP Filter Search")

    def test_tokenize(self):
        tokens = tokenizeText("loving someone is something beautiful, just like the nature. I love the world.")
        self.assertTrue(isinstance(tokens, list))
    def test_filterPunct(self):
        tokens = tokenizeText("loving someone is something beautiful, just like the nature. I love the world.")
        tokens = filterPunctuation(tokens)
        self.assertTrue("." not in tokens)
        self.assertTrue("," not in tokens)
        self.assertTrue("." not in tokens)
    def test_filterStopWords(self):
        tokens = tokenizeText("loving someone is something beautiful, just like the nature. I love the world.")
        tokens = filterStopWords(tokens)
        self.assertTrue("is" not in tokens)
        self.assertTrue("just" not in tokens)
        self.assertTrue("the" not in tokens)
    def test_filterDictwords(self):
        tokens = tokenizeText("loving someone is something beautiful, just like the nature. I love the world.")
        tokens = filteredDictWords(tokens)
        self.assertTrue("I" not in tokens)
        self.assertTrue("." not in tokens)
        self.assertTrue("," not in tokens)
    def test_stemming(self):
        tokens = tokenizeText("loving someone is something beautiful, just like the nature. I love the world.")
        tokens = stemmingMethod(tokens)
        self.assertTrue("loving" not in tokens)
        self.assertTrue("love" in tokens)
    def test_posTag(self):
        tokens = tokenizeText("loving someone is something beautiful, just like the nature. I love the world.")
        tokens = stemmingMethod(tokens)
        tokens = posTagging(tokens)
        self.assertTrue(tokens)
    def test_transformTagging(self):
        tokens = tokenizeText("loving someone is something beautiful, just like the nature. I love the world.")
        tokens = stemmingMethod(tokens)
        tokens = posTagging(tokens)
        tokens = transformTagging(tokens)
        self.assertTrue(tokens)
    def test_lemmatization(self):
        tokens = tokenizeText("loving someone is something beautiful, just like the nature. I love the world.")
        tokens = stemmingMethod(tokens)
        tokens = posTagging(tokens)
        tokens = transformTagging(tokens)
        tokens = lemmatizationMethod(tokens)
        self.assertTrue("is" not in tokens)
        self.assertTrue("be" in tokens)
        self.assertTrue("beautiful" not in tokens)
        self.assertTrue("beauty" in tokens)
    def test_all(self):
        tokens = tokenizeText("loving someone is something beautiful, just like the nature. I love the world.")
        tokens = filterPunctuation(tokens)
        tokens = filterStopWords(tokens)
        tokens = stemmingMethod(tokens)
        tokens = posTagging(tokens)
        tokens = transformTagging(tokens)
        tokens = lemmatizationMethod(tokens)
        self.assertTrue(tokens == processQuery("loving someone is something beautiful, just like the nature. I love the world."))
