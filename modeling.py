from db import Quote, Session
import spacy
from gensim import corpora, models, similarities
from random import shuffle
import numpy as np
nlp = spacy.load('en')


def build_corpus(filename=None):
    session = Session()
    original = session.query(Quote).all()
    session.close()
    quotes = [q.quote for q in original]

    def lemma(t):
        if t.lemma_ == "-PRON-":
            return str(t)
        else:
            return t.lemma_
    parsed = [[lemma(q) for q in nlp(quote.replace("’", "'").replace("—", " ").replace("-", " ")) if q.pos_ not in ['PUNCT', 'SPACE']] for quote in quotes]
    idx2id = {i: original[i].id for i in range(len(original))}
    if filename:
        parsedstrings = [" ".join(q) + "\n" for q in parsed]
        with open(filename, 'w') as f:
            f.writelines(parsedstrings)
    return idx2id, parsed


def load_corpus(filename):
    session = Session()
    original = session.query(Quote).all()
    idx2id = {i: original[i].id for i in range(len(original))}
    session.close()
    with open(filename, 'r') as f:
        parsed = f.readlines()
        parsed = [q.strip().split() for q in parsed]
    return idx2id, parsed


class BaseModel:

    def __init__(self, idx2id, parsed, name):
        self.modelfn = None
        self.model = None
        self.transformed = None
        self.index = None
        self.dictionary = None
        self.idx2id = idx2id
        self.id2idx = {v: k for k, v in idx2id.items()}
        self.parsed = parsed

    def get_similar(self, idx, n=10):
        sims = self.index[self.transformed[idx]]
        sims = sorted(enumerate(sims), key=lambda item: -item[1])
        sims = sims[:n]
        session = Session()
        ids = [self.idx2id[i[0]] for i in sims]
        quotes = session.query(Quote).filter(Quote.id.in_(ids)).all()
        session.close()
        return sims, quotes

    def score(self, n_samples=100, scoretype="both"):
        # get fresh session
        session = Session()
        # original = session.query(Quote).all()
        sample = [x for x in range(len(self.parsed))]
        shuffle(sample)
        sample = sample[:n_samples]
        if scoretype is not "source":
            diffs = []
            for i in sample:
                sims = self.index[self.transformed[i]]
                shared_person = session.query(Quote).filter(Quote.id==self.idx2id[i]).one()
                shared_person = shared_person.person.quotes
                idxs = [self.id2idx[q.id] for q in shared_person if q.id != self.idx2id[i]]
                if len(idxs):
                    m_all = np.mean(sims)
                    sd = np.std(sims)
                    m_same = np.mean(np.array(sims)[idxs])
                    diffs.append((m_same-m_all)/sd)
            persondiff = np.mean(diffs)
        if scoretype is not "person":
            diffs = []
            for i in sample:
                sims = self.index[self.transformed[i]]
                shared_source = session.query(Quote).filter(Quote.id==self.idx2id[i]).one()
                if shared_source.source:
                    shared_source = shared_source.source.quotes
                    idxs = [self.id2idx[q.id] for q in shared_source if q.id != self.idx2id[i]]
                    if len(idxs):
                        m_all = np.mean(sims)
                        sd = np.std(sims)
                        m_same = np.mean(np.array(sims)[idxs])
                        diffs.append((m_same-m_all)/sd)
            sourcediff = np.mean(diffs)
        if scoretype == "person":
            diff = persondiff
        elif scoretype == "source":
            diff = sourcediff
        else:
            diff = (sourcediff + persondiff) / 2
        session.close()
        return diff


class LsiWrapper(BaseModel):

    def __init__(self, idx2id, parsed, num_topics, name):
        super().__init__(idx2id, parsed, name)
        dictionary = corpora.Dictionary(parsed)
        bow = [dictionary.doc2bow(q) for q in parsed]
        tfidf = models.TfidfModel(bow)
        try:
            lsi = models.LsiModel.load('models/'+name+'.model')
        except:
            lsi = models.LsiModel(tfidf[bow], id2word=dictionary, num_topics=num_topics)
            lsi.save('models/'+name+'.model')
        self.dictionary = dictionary
        self.transformed = lsi[tfidf[bow]]
        self.modelfn = lambda q: lsi[tfidf[dictionary.doc2bow(q)]]
        self.model = lsi
        try:
            self.index = similarities.Similarity.load('similarities/'+name+'.index')
        except:
            self.index = similarities.Similarity('similarities/'+name, self.transformed, num_topics)
            self.index.save('similarities/'+name+'.index')
