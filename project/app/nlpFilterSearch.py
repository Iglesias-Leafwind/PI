from nltk.corpus import stopwords, words, wordnet
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer, LancasterStemmer, WordNetLemmatizer
from nltk.tag import pos_tag
import string, enchant, time


def tokenizeText(text):
    word_tokens = word_tokenize(text)
    return set(word_tokens)

def filterPunctuation(word_tokens):
    filtered_word_tokens = [w for w in word_tokens if w not in string.punctuation and all(c not in string.punctuation for c in w)]
    return set(filtered_word_tokens)

def filterStopWords(filtered_word_tokens):
    stop_words = set(stopwords.words('english'))
    filtered_word_tokens_no_stop_words = [w for w in filtered_word_tokens if w not in stop_words]
    return set(filtered_word_tokens_no_stop_words)

def filteredDictWords(filtered_word_tokens_no_stop_words):
    english_vocab = set(w.lower() for w in words.words())
    real_word_tokens = [w for w in filtered_word_tokens_no_stop_words if w in english_vocab]
    return set(real_word_tokens)


def stemmingMethod(real_word_tokens):
    ps = PorterStemmer()
    ls = LancasterStemmer()

    # 1st, let's check the PorterStemmer
    stemmed_words = set()
    d = enchant.Dict("en_UK")
    for word in real_word_tokens:
        stemmed_word = ps.stem(word)
        if stemmed_word not in words.words() or not d.check(stemmed_word): # english vocabulary
            stemmed_word = ls.stem(word)    # 2nd, let's try the LancasterStemmer
            if stemmed_word not in words.words() or not d.check(stemmed_word):
                stemmed_word = word
        stemmed_words |= {stemmed_word}
    
    return list(set(stemmed_words))

def posTagging(stemmed_words):
    words_with_tags = pos_tag(stemmed_words)
    return set(words_with_tags)

def transformTagging(words_with_tags):
    words_with_tags_ = set()
    for tuple_ in words_with_tags:
        if tuple_[1].startswith("N"):
            words_with_tags_ |= {(tuple_[0], wordnet.NOUN)}
        elif tuple_[1].startswith("V"):
            words_with_tags_ |= {(tuple_[0], wordnet.VERB)}
        elif tuple_[1].startswith("A"):
            words_with_tags_ |= {(tuple_[0], wordnet.ADJ)}
        elif tuple_[1].startswith("R"):
            words_with_tags_ |= {(tuple_[0], wordnet.ADV)}
        else:
            words_with_tags_ |= {tuple_[0]}

    return words_with_tags_

def lemmatizationMethod(words_with_tags_):
    lemmatizer = WordNetLemmatizer()
    words_with_no_tags = [tuple_ for tuple_ in words_with_tags_ if type(tuple_) is not tuple]
    lemmatized_words = [lemmatizer.lemmatize(tuple_[0], tuple_[1]) for tuple_ in words_with_tags_ if type(tuple_) is tuple]
    return set(lemmatized_words + words_with_no_tags)

def getSynsets(lemmatized_words):
    setResults = []
    synsetLst = [wordnet.synsets(token) for token in lemmatized_words]
    setResults = [elem.lemma_names()[:1][0].lower()  for lst in synsetLst for elem in lst[:5]]
    return lemmatized_words | set(setResults)


def processQuery(text):
    text = text.lower()
    results = tokenizeText(text)
    print(str(results) + "\n")
    results = filterPunctuation(results)
    print(str(results) + "\n")
    results = filterStopWords(results)
    print(str(results) + "\n")
    results = stemmingMethod(results)
    print(str(results) + "\n")
    results = posTagging(results)
    print(str(results) + "\n")
    results = transformTagging(results)
    print(str(results) + "\n")
    results = lemmatizationMethod(results)
    print(str(results) + "\n")
    results = getSynsets(results)
    print(str(results) + "\n")
    return results


text = "loving someone is something beautiful, just like the nature. I love the world."
text2 = "Didn't I tell you? We're moving to Ovar?"
beginning = time.time()
print(processQuery(text2))
end = time.time()
print(end-beginning)






