from django.test import TestCase
from app.models import ImageNeo
from app.nlpFilterSearch import tokenizeText,filter_punctuation,filter_stop_words,stemming_method,pos_tagging,lemmatization_method,get_synsets,process_query

phrase = ""
class Nlptestcase(TestCase):

    def setUp(self):
        global phrase
        phrase = "loving someone is something beautiful, just like the nature. I love the world."
        print("\n\\|/Testing NLP Filter Search")

    def test_tokenize(self):
        global phrase
        tokens = tokenize_text(phrase)
        self.assertTrue(isinstance(tokens, list))
    def test_filterPunct(self):
        global phrase
        tokens = tokenize_text(phrase)
        tokens = filter_punctuation(tokens)
        self.assertTrue("." not in tokens)
        self.assertTrue("," not in tokens)
        self.assertTrue("." not in tokens)
    def test_filterStopWords(self):
        global phrase
        tokens = tokenize_text(phrase)
        tokens = filter_stop_words(tokens)
        self.assertTrue("is" not in tokens)
        self.assertTrue("just" not in tokens)
        self.assertTrue("the" not in tokens)
    def test_stemming(self):
        global phrase
        tokens = tokenize_text(phrase)
        tokens = stemming_method(tokens)
        self.assertTrue("loving" not in tokens)
        self.assertTrue("love" in tokens)
    def test_posTag(self):
        global phrase
        tokens = tokenize_text(phrase)
        tokens = stemming_method(tokens)
        tokens = pos_tagging(tokens)
        self.assertTrue(tokens)
    def test_lemmatization(self):
        global phrase
        tokens = tokenize_text(phrase)
        tokens = stemming_method(tokens)
        tokens = pos_tagging(tokens)
        tokens = lemmatization_method(tokens)
        self.assertTrue("is" not in tokens)
        self.assertTrue("be" in tokens)
        self.assertTrue("beautiful" not in tokens)
        self.assertTrue("beauty" in tokens)
    def test_all(self):
        global phrase
        tokens = tokenize_text(phrase)
        tokens = filter_punctuation(tokens)
        tokens = filter_stop_words(tokens)
        tokens = stemming_method(tokens)
        tokens = pos_tagging(tokens)
        tokens = lemmatization_method(tokens)
        tokens = get_synsets(tokens)
        self.assertTrue(tokens == process_query(phrase))
