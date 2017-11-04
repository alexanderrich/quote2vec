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
    # idx2id = {i: original[i].id for i in range(len(original))}
    quoteid = [q.id for q in original]
    sourceid = [q.source_id for q in original]
    sourceid = [s if s is not None else -1 for s in sourceid]
    personid = [q.person_id for q in original]
    if filename:
        parsedstrings = [" ".join(q) + "\n" for q in parsed]
        parsedstrings = ["{}|{}|{}|{}".format(str(quoteid[i]),
                                              str(sourceid[i]),
                                              str(personid[i]),
                                              parsedstrings[i])
                         for i in range(len(parsedstrings))]
        with open(filename, 'w') as f:
            f.writelines(parsedstrings)
    return list(zip(quoteid, sourceid, personid, parsedstrings))


def load_corpus(filename):
    with open(filename, 'r') as f:
        parsed = f.readlines()
        parsed = [q.strip().split("|") for q in parsed]
        parsed = [(int(q[0]), int(q[1]), int(q[2]), q[3].strip().split()) for q in parsed]
    return parsed


class BaseModel:

    def __init__(self, parsed, name):
        self.modelfn = None
        self.model = None
        self.transformed = None
        self.index = None
        self.dictionary = None
        self.id2idx = {v[0]: i for i, v in enumerate(parsed)}
        self.id2source = {v[0]: v[1] for v in parsed}
        self.id2person = {v[0]: v[2] for v in parsed}
        self.parsed = parsed

    def get_similar(self, id, n=10):
        sims = self.index[self.transformed[id]]
        sims = sorted(enumerate(sims), key=lambda item: -item[1])
        sims = sims[:n]
        session = Session()
        ids = [i[0] for i in sims]
        quotes = session.query(Quote).filter(Quote.id.in_(ids)).all()
        session.close()
        return sims, quotes

    def score(self, n_samples=100):
        sample = [x for x in range(len(self.parsed))]
        shuffle(sample)
        sample = sample[:n_samples]
        sample = [self.parsed[s][0] for s in sample]
        person2quotes = {}
        for qid, pid in self.id2person.items():
            if pid not in person2quotes:
                person2quotes[pid] = [qid]
            else:
                person2quotes[pid].append(qid)
        quote2personquotes = {}
        for p, qlist in person2quotes.items():
            for q in qlist:
                quote2personquotes[q] = qlist
        source2quotes = {}
        for qid, sid in self.id2source.items():
            if sid > -1:
                if sid not in source2quotes:
                    source2quotes[sid] = [qid]
                else:
                    source2quotes[sid].append(qid)
        quote2sourcequotes = {}
        for p, qlist in source2quotes.items():
            for q in qlist:
                quote2sourcequotes[q] = qlist
        persondiffs = []
        sourcediffs = []
        # transvec = [self.transformed[x] for x in sample]
        # loopcount = -1
        # for sims in self.index[transvec]:
            # loopcount += 1
            # i = sample[loopcount]
        for i in sample:
            # sims = self.index[self.transformed[i]]
            sims = self.index.similarity_by_id(self.id2idx[i])
            m_all = np.mean(sims)
            sd = np.std(sims)
            ids = quote2personquotes[i]
            idxs = [self.id2idx[id] for id in ids if id != i]
            if len(idxs):
                m_person = np.mean(np.array(sims)[idxs])
                persondiffs.append((m_person-m_all)/sd)
            if i in quote2sourcequotes:
                ids = quote2sourcequotes[i]
                idxs = [self.id2idx[id] for id in ids if id != i]
                if len(idxs):
                    m_source = np.mean(np.array(sims)[idxs])
                    sourcediffs.append((m_source-m_all)/sd)
        persondiff = np.mean(persondiffs)
        sourcediff = np.mean(sourcediffs)
        diff = (sourcediff + persondiff) / 2
        return diff


class LsiWrapper(BaseModel):

    def __init__(self, parsed, num_topics, name):
        super().__init__(parsed, name)
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


class Doc2VecWrapper(BaseModel):
    def __init__(self, parsed, name, **kwargs):
        super().__init__(parsed, name)
        self.name = name
        self.taggeddocs = [models.doc2vec.TaggedDocument(x[3], [x[0]]) for x in parsed]
        try:
            self.model = models.doc2vec.Doc2Vec.load('models/'+name+'.model')
            self.index = similarities.Similarity.load('similarities/'+name+'.index')
            self.transformed = self.model.docvecs
        except:
            self.model = models.doc2vec.Doc2Vec(**kwargs)
            self.model.build_vocab(self.taggeddocs)

    def train(self, alpha):
        shuffle(self.taggeddocs)
        self.model.alpha = alpha
        self.model.min_alpha = alpha
        self.model.train(self.taggeddocs, total_examples=self.model.corpus_count, epochs=1)
        print("finished epoch")

    def finish_training(self):
        self.model.save('models/'+self.name+'.model')
        self.transformed = self.model.docvecs[[x[0] for x in self.parsed]]
        self.index = similarities.Similarity('similarities/'+self.name, self.transformed, self.transformed.shape[1])
        self.index.save('similarities/'+self.name+'.index')

    def get_docvec(self, id):
        return self.model.docvecs[id]


if __name__=="__main__":
    parsed = build_corpus('tokenized.txt')
    model = Doc2VecWrapper(parsed, 'dbow300_withgoogle', size=300, min_count=2, dm=0, negative=5, dbow_words=1, workers=8, sample=10**-3)
    model.model.intersect_word2vec_format('GoogleNews-vectors-negative300.bin', binary=True, lockf=1.0)
    for i in range(20):
        model.train(.025*(.95**i))
    model.finish_training()
    model.model.docvecs.save('models/docvecs')
    print(model.score(n_samples=10000))
