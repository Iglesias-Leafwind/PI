## @package project
#  This package will check if nltk has everything downloaded
#  and will startup manage.py file with the correct arguments.
#
#  More details.
import sys
import manage
import nltk
nltk.download("words")
nltk.download("stopwords")
nltk.download("punkt")
nltk.download("wordnet")
nltk.download('averaged_perceptron_tagger')
sys.argv.extend(['runserver','--noreload'])
manage.main()
