## @package app
#  This module contains every function that is needed for nlp filtering
#
#  More details.
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

## Transform a string into many tokens
#
#  More details.
def tokenize_text(text):
    return set(word_tokenize(text))
## Filters punctuation
#
#  More details.
def filter_punctuation(word_tokens):
    filtered_word_tokens = [w for w in word_tokens if (w not in string.punctuation and all(c not in string.punctuation for c in w)) or "-" in w]
    return set(filtered_word_tokens)
## Filters stop words from the tokens
#
#  More details.
def filter_stop_words(filtered_word_tokens):
    return set([w for w in filtered_word_tokens if w not in set(stopwords.words('english'))])
## Applys the stemming method on the filtered tokens
#
#  More details.
def stemming_method(real_word_tokens):
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
## Applies pos_tagging to the stemmed words
#
#  More details.
def pos_tagging(stemmed_words):
    return set(pos_tag(stemmed_words))
## Applies lemmatization on pos tagging tokens
#
#  More details.
def lemmatization_method(words_with_tags):
    lemmatized_words = set()
    lemmatizer = WordNetLemmatizer()
    for token, tag in words_with_tags:
        lemmatized_word = lemmatizer.lemmatize(token, tag_map[tag[0]])
        lemmatized_words |= {lemmatized_word}

    return lemmatized_words
## Gets synonims ets from lemmatized tokens
#
#  More details.
def get_synsets(lemmatized_words):
    synset_lst = [wordnet.synsets(token) for token in lemmatized_words]
    return lemmatized_words | set([elem.lemma_names()[:1][0].lower()  for lst in synset_lst for elem in lst[:5]])
## Filters a single string into a bunch of tokens without punctuation
#
#  More details.
def process_text(text):
    text = text.lower()
    results = tokenize_text(text)
    results = filter_punctuation(results)
    return results
## Filters with every filter by order to get a group of related tokens from a string
#
#  More details.
def process_query(text):
    text = text.lower()
    words = process_text(text)
    results = filter_stop_words(words)
    results = stemming_method(results)
    results = pos_tagging(results)
    results = lemmatization_method(results)
    results = get_synsets(results)
    return results | words




text = "loving someone is something beautiful, just like the nature. I love the world."
text2 = "Didn't I tell you? We're moving to Ovar?"
beginning = time.time()
#print(processQuery(text))
end = time.time()
#print(end-beginning)






