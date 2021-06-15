import sys
import manage
import nltk
nltk.download("words")
nltk.download("stopwords")
nltk.download("punkt")
nltk.download("wordnet")
sys.argv.extend(['runserver','--noreload'])
manage.main()
