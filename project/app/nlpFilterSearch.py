from nltk.corpus import stopwords, words, wordnet
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer, LancasterStemmer, WordNetLemmatizer
from nltk.tag import pos_tag
import string, enchant, time
from collections import defaultdict

tag_map = defaultdict(lambda : wordnet.NOUN)
tag_map['J'] = wordnet.ADJ
tag_map['V'] = wordnet.VERB
tag_map['R'] = wordnet.ADV


def tokenizeText(text):
    return set(word_tokenize(text))

def filterPunctuation(word_tokens):
    filtered_word_tokens = [w for w in word_tokens if w not in string.punctuation and all(c not in string.punctuation for c in w)]
    return set(filtered_word_tokens)

def filterStopWords(filtered_word_tokens):
    return set([w for w in filtered_word_tokens if w not in set(stopwords.words('english'))])

'''
def filteredDictWords(filtered_word_tokens_no_stop_words):
    english_vocab = set(w.lower() for w in words.words())
    real_word_tokens = [w for w in filtered_word_tokens_no_stop_words if w in english_vocab]
    return set(real_word_tokens)
'''

def stemmingMethod(real_word_tokens): # DO NOT CHANGE THIS ONE IG, THE PROBLEM IS NOT HERE
    ps = PorterStemmer()
    ls = LancasterStemmer()

    # 1st, let's check the PorterStemmer
    stemmed_words = set()
    d = enchant.Dict("en_UK")
    for word in real_word_tokens:
        stemmed_word = ps.stem(word)
        if not d.check(stemmed_word): # english vocabulary
            stemmed_word = ls.stem(word)    # 2nd, let's try the LancasterStemmer
            if not d.check(stemmed_word):
                stemmed_word = word
        stemmed_words |= {stemmed_word}
    
    return set(stemmed_words)

def posTagging(stemmed_words):
    return set(pos_tag(stemmed_words))

def lemmatizationMethod(words_with_tags):
    lemmatized_words = set()
    lemmatizer = WordNetLemmatizer()
    for token, tag in words_with_tags:
        lemmatized_word = lemmatizer.lemmatize(token, tag_map[tag[0]])
        lemmatized_words |= {lemmatized_word}

    return lemmatized_words

def getSynsets(lemmatized_words):
    synsetLst = [wordnet.synsets(token) for token in lemmatized_words]
    return lemmatized_words | set([elem.lemma_names()[:1][0].lower()  for lst in synsetLst for elem in lst[:5]])


def processQuery(text):
    text = text.lower()
    results = tokenizeText(text)
    results = filterPunctuation(results)
    words = filterStopWords(results)
    results = stemmingMethod(words)
    results = posTagging(results)
    results = lemmatizationMethod(results)
    results = getSynsets(results)
    return results | words


text = "loving someone is something beautiful, just like the nature. I love the world."
text2 = "Didn't I tell you? We're moving to Ovar?"
beginning = time.time()
print(processQuery(text))
end = time.time()
print(end-beginning)






