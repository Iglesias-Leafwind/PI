## @package tests
#  This will test the nlp filter search file and its functions
#
#  More details.
from django.test import TestCase
from app.models import ImageNeo
from app.nlpFilterSearch import tokenizeText,filter_punctuation,filter_stop_words,stemming_method,pos_tagging,lemmatization_method,get_synsets,process_query

phrase = ""
## Test Case class.
#
#  More details.
class Nlptestcase(TestCase):

    ##Setup before each test
    def setUp(self):
        global phrase
        phrase = "loving someone is something beautiful, just like the nature. I love the world."
        print("\n\\|/Testing NLP Filter Search")

    ## Testing tokenization of text by nlp
    #  @param self The object pointer to itself.
    def test_tokenize(self):
        global phrase
        tokens = tokenize_text(phrase)
        self.assertTrue(isinstance(tokens, list))
    ## Testing filter punctiation
    #  @param self The object pointer to itself.
    def test_filterPunct(self):
        global phrase
        tokens = tokenize_text(phrase)
        tokens = filter_punctuation(tokens)
        self.assertTrue("." not in tokens)
        self.assertTrue("," not in tokens)
        self.assertTrue("." not in tokens)

    ## Testing filtering stop words
    #  @param self The object pointer to itself.
    def test_filterStopWords(self):
        global phrase
        tokens = tokenize_text(phrase)
        tokens = filter_stop_words(tokens)
        self.assertTrue("is" not in tokens)
        self.assertTrue("just" not in tokens)
        self.assertTrue("the" not in tokens)

    ## Testing stemming method
    #  @param self The object pointer to itself.
    def test_stemming(self):
        global phrase
        tokens = tokenize_text(phrase)
        tokens = stemming_method(tokens)
        self.assertTrue("loving" not in tokens)
        self.assertTrue("love" in tokens)
    ## Testing pos tagging
    #  @param self The object pointer to itself.
    def test_posTag(self):
        global phrase
        tokens = tokenize_text(phrase)
        tokens = stemming_method(tokens)
        tokens = pos_tagging(tokens)
        self.assertTrue(tokens)
    ## Testing lemmatization
    #  @param self The object pointer to itself.
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

    ## Testing every filter individually to see if it is the same as the function process_query
    # that calls each function individually
    #  @param self The object pointer to itself.
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
