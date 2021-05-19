from nltk.corpus import stopwords, words, wordnet
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer, LancasterStemmer, WordNetLemmatizer
from nltk.tag import pos_tag
import string, enchant, time


def tokenizeText(text):
    word_tokens = word_tokenize(text)
    return set(word_tokens)

def filterPunctuation(word_tokens):
    filtered_word_tokens = [w for w in word_tokens if w not in string.punctuation]
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
            continue

    return words_with_tags_

def lemmatizationMethod(words_with_tags_):
    lemmatizer = WordNetLemmatizer()
    lemmatized_words = set()
    for tuple_ in words_with_tags_:
        word = tuple_[0]
        pos = tuple_[1]
        lemmatized_word = lemmatizer.lemmatize(word, pos)
        lemmatized_words |= {lemmatized_word}
    return set(lemmatized_words)

def getSynsets(lemmatized_words):
    setResults = []
    synsetLst = [wordnet.synsets(token) for token in lemmatized_words]
    for lst in synsetLst:
        length = len(lst)
        if length <=3:
            subLst = lst[:-1]
        else:
            subLst = lst[:2]
        for elem in subLst:
            res = elem.lemma_names()[:1]
            setResults += res
    return lemmatized_words | set(setResults)


def processQuery(query):
    text = query.lower()
    results = tokenizeText(text)
    results = filterPunctuation(results)
    results = filterStopWords(results)
    results = stemmingMethod(results)
    results = posTagging(results)
    results = transformTagging(results)
    results = lemmatizationMethod(results)
    results = getSynsets(results)
    return results


text = "loving someone is something beautiful, just like the nature. I love the world."
beginning = time.time()
print(processQuery(text))
end = time.time()
print(end-beginning)






