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

    def score(self, n_samples=100):
        # get fresh session
        session = Session()
        # original = session.query(Quote).all()
        sample = [x for x in range(len(self.parsed))]
        shuffle(sample)
        sample = sample[:n_samples]
        quotes = session.query(Quote).all()
        person2quotes = {}
        for q in quotes:
            if q.person_id not in person2quotes:
                person2quotes[q.person_id] = [q.id]
            else:
                person2quotes[q.person_id].append(q.id)
        quote2personquotes = {}
        for p, qlist in person2quotes.items():
            for q in qlist:
                quote2personquotes[q] = qlist
        quotes = session.query(Quote).all()
        source2quotes = {}
        for q in quotes:
            if q.source_id:
                if q.source_id not in source2quotes:
                    source2quotes[q.source_id] = [q.id]
                else:
                    source2quotes[q.source_id].append(q.id)
        quote2sourcequotes = {}
        for p, qlist in source2quotes.items():
            for q in qlist:
                quote2sourcequotes[q] = qlist
        session.close()
        persondiffs = []
        sourcediffs = []
        # transvec = [self.transformed[x] for x in sample]
        # loopcount = -1
        # for sims in self.index[transvec]:
            # loopcount += 1
            # i = sample[loopcount]
        for i in sample:
            # sims = self.index[self.transformed[i]]
            sims = self.index.similarity_by_id(i)
            m_all = np.mean(sims)
            sd = np.std(sims)
            ids = quote2personquotes[self.idx2id[i]]
            idxs = [self.id2idx[id] for id in ids if self.id2idx[id] != i]
            person_idxs = [i for i in idxs if i < len(self.parsed)]
            if len(person_idxs):
                m_person = np.mean(np.array(sims)[idxs])
                persondiffs.append((m_person-m_all)/sd)
            if self.idx2id[i] in quote2sourcequotes:
                ids = quote2sourcequotes[self.idx2id[i]]
                idxs = [self.id2idx[id] for id in ids if self.id2idx[id] != i]
                source_idxs = [i for i in idxs if i < len(self.parsed)]
                if len(source_idxs):
                    m_source = np.mean(np.array(sims)[idxs])
                    sourcediffs.append((m_source-m_all)/sd)
        persondiff = np.mean(persondiffs)
        sourcediff = np.mean(sourcediffs)
        diff = (sourcediff + persondiff) / 2
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
